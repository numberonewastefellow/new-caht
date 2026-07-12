from collections.abc import Callable
from typing import cast

from sqlalchemy.orm import joinedload
from sqlalchemy.orm import Session

from om.access.models import DocumentAccess
from om.access.utils import prefix_external_group
from om.access.utils import prefix_user_email
from om.access.utils import prefix_user_group
from om.configs.constants import DocumentSource
from om.configs.constants import PUBLIC_DOC_PAT
from om.db.document import get_access_info_for_documents
from om.db.document import get_document_sources
from om.db.document import get_documents_by_ids
from om.db.external_perm import fetch_external_groups_for_user
from om.db.external_perm import fetch_public_external_group_ids
from om.db.models import User
from om.db.models import UserFile
from om.utils.logger import setup_logger


logger = setup_logger()


def _get_access_for_document(
    document_id: str,
    db_session: Session,
) -> DocumentAccess:
    id_to_access = _get_access_for_documents([document_id], db_session)
    if len(id_to_access) == 0:
        return DocumentAccess.build(
            user_emails=[],
            user_groups=[],
            external_user_emails=[],
            external_user_group_ids=[],
            is_public=False,
        )

    return next(iter(id_to_access.values()))


def get_access_for_document(
    document_id: str,
    db_session: Session,
) -> DocumentAccess:
    versioned_get_access_for_document_fn = _get_access_for_document
    return versioned_get_access_for_document_fn(document_id, db_session)


def get_null_document_access() -> DocumentAccess:
    return DocumentAccess.build(
        user_emails=[],
        user_groups=[],
        is_public=False,
        external_user_emails=[],
        external_user_group_ids=[],
    )


def _get_access_for_documents_without_groups(
    document_ids: list[str],
    db_session: Session,
) -> dict[str, DocumentAccess]:
    document_access_info = get_access_info_for_documents(
        db_session=db_session,
        document_ids=document_ids,
    )
    doc_access = {}
    for document_id, user_emails, is_public in document_access_info:
        doc_access[document_id] = DocumentAccess.build(
            user_emails=[email for email in user_emails if email],
            # MIT version will wipe all groups and external groups on update
            user_groups=[],
            is_public=is_public,
            external_user_emails=[],
            external_user_group_ids=[],
        )

    # Sometimes the document has not been indexed by the indexing job yet, in those cases
    # the document does not exist and so we use least permissive. Specifically the EE version
    # checks the MIT version permissions and creates a superset. This ensures that this flow
    # does not fail even if the Document has not yet been indexed.
    for doc_id in document_ids:
        if doc_id not in doc_access:
            doc_access[doc_id] = get_null_document_access()
    return doc_access


def _get_access_for_documents(
    document_ids: list[str],
    db_session: Session,
) -> dict[str, DocumentAccess]:
    non_ee_access_dict = _get_access_for_documents_without_groups(
        document_ids=document_ids,
        db_session=db_session,
    )
    # Lazy, NOT module-scope -- see the note on get_source_perm_sync_config below.
    # om.db.user_group -> om.server.user_group.models -> om.server.manage.models ->
    # om.onyxbot.slack.config -> ... -> om.context.search.preprocessing.access_filters
    # -> om.access.access. A top-level import closes that cycle.
    from om.db.user_group import fetch_user_groups_for_documents

    user_group_info: dict[str, list[str]] = {
        document_id: group_names
        for document_id, group_names in fetch_user_groups_for_documents(
            db_session=db_session,
            document_ids=document_ids,
        )
    }
    documents = get_documents_by_ids(
        db_session=db_session,
        document_ids=document_ids,
    )
    doc_id_map = {doc.id: doc for doc in documents}

    # Get all sources in one batch
    doc_id_to_source_map = get_document_sources(
        db_session=db_session,
        document_ids=document_ids,
    )

    all_public_ext_u_group_ids = set(fetch_public_external_group_ids(db_session))

    access_map = {}
    for document_id, non_ee_access in non_ee_access_dict.items():
        document = doc_id_map[document_id]
        source = doc_id_to_source_map.get(document_id)
        if source is None:
            logger.error(f"Document {document_id} has no source")
            continue

        # Imported lazily, NOT at module scope. `om.external_permissions.sync_params`
        # pulls in every connector's doc_sync/group_sync, which transitively imports
        # `om.context.search.preprocessing.access_filters` -> back into this module.
        # A top-level import here is a hard circular import (get_acl_for_user cannot be
        # resolved from the partially-initialized module) and takes down every celery
        # worker at autodiscovery. The pre-merge code dodged this by reaching
        # sync_params only through fetch_versioned_implementation, i.e. at call time.
        from om.external_permissions.sync_params import get_source_perm_sync_config

        perm_sync_config = get_source_perm_sync_config(source)
        is_only_censored = (
            perm_sync_config
            and perm_sync_config.censoring_config is not None
            and perm_sync_config.doc_sync_config is None
        )

        ext_u_emails = (
            set(document.external_user_emails)
            if document.external_user_emails
            else set()
        )

        ext_u_groups = (
            set(document.external_user_group_ids)
            if document.external_user_group_ids
            else set()
        )

        # If the document is determined to be "public" externally (through a SYNC connector)
        # then it's given the same access level as if it were marked public within Onyx
        # If its censored, then it's public anywhere during the search and then permissions are
        # applied after the search
        is_public_anywhere = (
            document.is_public
            or non_ee_access.is_public
            or is_only_censored
            or any(u_group in all_public_ext_u_group_ids for u_group in ext_u_groups)
        )

        # To avoid collisions of group namings between connectors, they need to be prefixed
        access_map[document_id] = DocumentAccess.build(
            user_emails=list(non_ee_access.user_emails),
            user_groups=user_group_info.get(document_id, []),
            is_public=is_public_anywhere,
            external_user_emails=list(ext_u_emails),
            external_user_group_ids=list(ext_u_groups),
        )
    return access_map


def get_access_for_documents(
    document_ids: list[str],
    db_session: Session,
) -> dict[str, DocumentAccess]:
    """Fetches all access information for the given documents."""
    versioned_get_access_for_documents_fn = _get_access_for_documents
    return versioned_get_access_for_documents_fn(document_ids, db_session)


def _get_acl_for_user_without_groups(
    user: User, db_session: Session  # noqa: ARG001
) -> set[str]:
    """Returns a list of ACL entries that the user has access to. This is meant to be
    used downstream to filter out documents that the user does not have access to. The
    user should have access to a document if at least one entry in the document's ACL
    matches one entry in the returned set.

    Anonymous users only have access to public documents.
    """
    if user.is_anonymous:
        return {PUBLIC_DOC_PAT}
    return {prefix_user_email(user.email), PUBLIC_DOC_PAT}


def _get_acl_for_user(user: User, db_session: Session) -> set[str]:
    """Returns a list of ACL entries that the user has access to. This is meant to be
    used downstream to filter out documents that the user does not have access to. The
    user should have access to a document if at least one entry in the document's ACL
    matches one entry in the returned set.

    NOTE: is imported in om.access.access by `fetch_versioned_implementation`
    DO NOT REMOVE."""
    # Lazy import -- om.db.user_group closes an import cycle back into this module.
    from om.db.user_group import fetch_user_groups_for_user

    is_anonymous = user.is_anonymous
    db_user_groups = (
        [] if is_anonymous else fetch_user_groups_for_user(db_session, user.id)
    )
    prefixed_user_groups = [
        prefix_user_group(db_user_group.name) for db_user_group in db_user_groups
    ]

    db_external_groups = (
        [] if is_anonymous else fetch_external_groups_for_user(db_session, user.id)
    )
    prefixed_external_groups = [
        prefix_external_group(db_external_group.external_user_group_id)
        for db_external_group in db_external_groups
    ]

    user_acl = set(prefixed_user_groups + prefixed_external_groups)
    user_acl.update(_get_acl_for_user_without_groups(user, db_session))

    return user_acl


def get_acl_for_user(user: User, db_session: Session | None = None) -> set[str]:
    versioned_acl_for_user_fn = _get_acl_for_user
    return versioned_acl_for_user_fn(user, db_session)


def source_should_fetch_permissions_during_indexing(source: DocumentSource) -> bool:
    from om.external_permissions.sync_params import (
        source_should_fetch_permissions_during_indexing as _impl_source_should_fetch_permissions_during_indexing,
    )
    _source_should_fetch_permissions_during_indexing_func = cast(
        Callable[[DocumentSource], bool],
        _impl_source_should_fetch_permissions_during_indexing,
    )
    return _source_should_fetch_permissions_during_indexing_func(source)


def get_access_for_user_files(
    user_file_ids: list[str],
    db_session: Session,
) -> dict[str, DocumentAccess]:
    user_files = (
        db_session.query(UserFile)
        .options(joinedload(UserFile.user))  # Eager load the user relationship
        .filter(UserFile.id.in_(user_file_ids))
        .all()
    )
    return {
        str(user_file.id): DocumentAccess.build(
            user_emails=[user_file.user.email] if user_file.user else [],
            user_groups=[],
            is_public=True if user_file.user is None else False,
            external_user_emails=[],
            external_user_group_ids=[],
        )
        for user_file in user_files
    }
