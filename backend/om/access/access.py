"""Document-access resolution (Contract 2 public API).

Two directions, one ACL vocabulary (:mod:`om.access.utils`):

* **write-side** — ``get_access_for_document(s)`` resolve a document's principals
  (internal user emails, internal **teams**, external emails/groups, public) into
  a :class:`DocumentAccess`, whose ``to_acl()`` is stamped into the index.
* **read-side** — ``get_acl_for_user`` expands a user into the principal set used
  to build the query-time access filter. A document is visible iff the two sets
  intersect.

The signatures here are frozen (WS-D/WS-E import them); only the bodies are the
WS-B clean-room rewrite. The lazy imports inside the functions are deliberate:
``om.db.team`` and ``om.external_permissions.sync_params`` both transitively
import back into this module, so importing them at call time breaks a hard cycle
that would otherwise take down every celery worker at autodiscovery.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import cast

from sqlalchemy.orm import joinedload
from sqlalchemy.orm import Session

from om.access.models import DocumentAccess
from om.access.utils import prefix_external_team
from om.access.utils import prefix_team
from om.access.utils import prefix_user_email
from om.configs.constants import DocumentSource
from om.configs.constants import PUBLIC_DOC_PAT
from om.db.document import get_access_info_for_documents
from om.db.document import get_document_sources
from om.db.document import get_documents_by_ids
from om.db.external_perm import fetch_external_teams_for_user
from om.db.external_perm import fetch_public_external_team_ids
from om.db.models import KnowledgeFile
from om.db.models import User
from om.utils.logger import setup_logger

logger = setup_logger()


def get_null_document_access() -> DocumentAccess:
    """Least-permissive access — nobody but admins, not public."""
    return DocumentAccess.build(
        user_emails=[],
        teams=[],
        external_user_emails=[],
        external_team_ids=[],
        is_public=False,
    )


def _mit_access_for_documents(
    document_ids: list[str],
    db_session: Session,
) -> dict[str, DocumentAccess]:
    """Base per-document access ignoring teams/external groups (the always-on
    subset). Documents not yet indexed fall back to null (least-permissive)."""
    doc_access: dict[str, DocumentAccess] = {}
    for document_id, user_emails, is_public in get_access_info_for_documents(
        db_session=db_session, document_ids=document_ids
    ):
        doc_access[document_id] = DocumentAccess.build(
            user_emails=[email for email in user_emails if email],
            teams=[],
            is_public=is_public,
            external_user_emails=[],
            external_team_ids=[],
        )
    for doc_id in document_ids:
        doc_access.setdefault(doc_id, get_null_document_access())
    return doc_access


def _resolve_access_for_documents(
    document_ids: list[str],
    db_session: Session,
) -> dict[str, DocumentAccess]:
    from om.db.team import fetch_teams_for_documents

    base_access = _mit_access_for_documents(document_ids, db_session)

    teams_by_document: dict[str, list[str]] = {
        document_id: team_names
        for document_id, team_names in fetch_teams_for_documents(
            db_session=db_session, document_ids=document_ids
        )
    }
    documents = get_documents_by_ids(db_session=db_session, document_ids=document_ids)
    document_by_id = {doc.id: doc for doc in documents}
    source_by_document = get_document_sources(
        db_session=db_session, document_ids=document_ids
    )
    public_external_team_ids = set(fetch_public_external_team_ids(db_session))

    access_by_document: dict[str, DocumentAccess] = {}
    for document_id, base in base_access.items():
        document = document_by_id.get(document_id)
        source = source_by_document.get(document_id)
        if document is None or source is None:
            logger.error("Document %s missing document row or source", document_id)
            continue

        # A censoring-only source is public during search; its access is enforced
        # afterwards by post-query censoring (so retrieval must not hide it).
        from om.external_permissions.sync_params import get_source_perm_sync_config

        perm_sync_config = get_source_perm_sync_config(source)
        is_censoring_only = bool(
            perm_sync_config
            and perm_sync_config.censoring_config is not None
            and perm_sync_config.doc_sync_config is None
        )

        external_emails = set(document.external_user_emails or [])
        external_team_ids = set(document.external_team_ids or [])

        is_public_anywhere = (
            document.is_public
            or base.is_public
            or is_censoring_only
            or bool(external_team_ids & public_external_team_ids)
        )

        access_by_document[document_id] = DocumentAccess.build(
            user_emails=list(base.user_emails),
            teams=teams_by_document.get(document_id, []),
            is_public=is_public_anywhere,
            external_user_emails=list(external_emails),
            external_team_ids=list(external_team_ids),
        )
    return access_by_document


def get_access_for_document(
    document_id: str,
    db_session: Session,
) -> DocumentAccess:
    access_by_document = _resolve_access_for_documents([document_id], db_session)
    return access_by_document.get(document_id, get_null_document_access())


def get_access_for_documents(
    document_ids: list[str],
    db_session: Session,
) -> dict[str, DocumentAccess]:
    """Fetch access information for all of the given documents."""
    return _resolve_access_for_documents(document_ids, db_session)


def _acl_for_user_without_teams(user: User) -> set[str]:
    """The always-on ACL entries: the user's own email + public. Anonymous users
    can only ever see public documents."""
    if user.is_anonymous:
        return {PUBLIC_DOC_PAT}
    return {prefix_user_email(user.email), PUBLIC_DOC_PAT}


def get_acl_for_user(user: User, db_session: Session | None = None) -> set[str]:
    """The set of ACL principals a user matches. A document is visible to the
    user iff its ``access_control_list`` shares at least one entry with this set.
    """
    from om.db.team import fetch_teams_for_user

    acl = _acl_for_user_without_teams(user)
    if user.is_anonymous or db_session is None:
        return acl

    acl.update(
        prefix_team(team.name) for team in fetch_teams_for_user(db_session, user.id)
    )
    acl.update(
        prefix_external_team(external.external_team_id)
        for external in fetch_external_teams_for_user(db_session, user.id)
    )
    return acl


def source_should_fetch_permissions_during_indexing(source: DocumentSource) -> bool:
    from om.external_permissions.sync_params import (
        source_should_fetch_permissions_during_indexing as _impl,
    )

    fn = cast(Callable[[DocumentSource], bool], _impl)
    return fn(source)


def get_access_for_knowledge_files(
    knowledge_file_ids: list[str],
    db_session: Session,
) -> dict[str, DocumentAccess]:
    """User-file access: a knowledge file is private to its owner, or public when
    it has no owner."""
    knowledge_files = (
        db_session.query(KnowledgeFile)
        .options(joinedload(KnowledgeFile.user))
        .filter(KnowledgeFile.id.in_(knowledge_file_ids))
        .all()
    )
    return {
        str(knowledge_file.id): DocumentAccess.build(
            user_emails=[knowledge_file.user.email] if knowledge_file.user else [],
            teams=[],
            is_public=knowledge_file.user is None,
            external_user_emails=[],
            external_team_ids=[],
        )
        for knowledge_file in knowledge_files
    }
