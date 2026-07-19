"""Admin/curator search + tag lookup (clean-room).

- ``admin_search`` runs a direct keyword search (no expansion) that additionally
  surfaces hidden documents, for the admin Document Explorer. An empty query
  returns a random sample (browse mode). Results are de-duplicated by document.
  ACL still applies via Contract 2, so a curator only sees permitted documents.
- ``get_valid_tags`` lists metadata tags for filtering; an ``author=bob`` pattern
  matches key AND value prefixes.
"""

from sqlalchemy.orm import Session

from om.configs.constants import DocumentSource
from om.context.search.models import BaseFilters
from om.context.search.models import SearchDoc
from om.db.models import Tag as TagRow
from om.db.models import User
from om.db.search_settings import get_current_search_settings
from om.db.tag import find_tags
from om.document_index.factory import get_default_document_index
from om.search.filters import build_index_filters
from om.search.log_events import ACTION_EXECUTE
from om.search.log_events import ACTION_READ
from om.search.log_events import emit_search_event
from om.search.log_events import STATUS_SUCCESS
from om.search.log_events import timed_search_event

_DEFAULT_ADMIN_NUM_RESULTS = 50
_DEFAULT_TAG_LIMIT = 50
_KEY_VALUE_SEP = "="


def admin_search(
    query: str,
    filters: BaseFilters | None,
    user: User,
    db_session: Session,
    num_to_retrieve: int = _DEFAULT_ADMIN_NUM_RESULTS,
) -> list[SearchDoc]:
    with timed_search_event(
        event="search.admin", action=ACTION_EXECUTE, actor_user_id=user.id
    ) as fields:
        search_settings = get_current_search_settings(db_session)
        document_index = get_default_document_index(search_settings, None)
        index_filters = build_index_filters(user, db_session, filters)

        if not query or not query.strip():
            # Browse mode: a random permitted sample.
            chunks = document_index.random_retrieval(
                filters=index_filters, num_to_retrieve=max(1, num_to_retrieve)
            )
        else:
            # Admin search exposes hidden docs so admins can inspect/unhide them.
            chunks = document_index.keyword_retrieval(
                query=query,
                filters=index_filters,
                num_to_retrieve=max(1, num_to_retrieve),
                include_hidden=True,
            )

        documents = SearchDoc.from_chunks_or_sections(chunks)
        deduped: list[SearchDoc] = []
        seen: set[str] = set()
        for document in documents:
            if document.document_id not in seen:
                seen.add(document.document_id)
                deduped.append(document)
        fields["num_results"] = len(deduped)
        return deduped


def get_valid_tags(
    db_session: Session,
    match_pattern: str | None = None,
    sources: list[DocumentSource] | None = None,
    limit: int = _DEFAULT_TAG_LIMIT,
) -> list[TagRow]:
    key_prefix = match_pattern
    value_prefix = match_pattern
    require_both_to_match = False
    # "author=bob" -> match key prefix "author" AND value prefix "bob".
    if match_pattern and _KEY_VALUE_SEP in match_pattern:
        head, _, tail = match_pattern.partition(_KEY_VALUE_SEP)
        key_prefix, value_prefix = head, tail
        require_both_to_match = True

    tags = find_tags(
        tag_key_prefix=key_prefix,
        tag_value_prefix=value_prefix,
        sources=sources,
        limit=limit,
        db_session=db_session,
        require_both_to_match=require_both_to_match,
    )
    emit_search_event(
        event="search.tags_read",
        action=ACTION_READ,
        status=STATUS_SUCCESS,
        entity="tag",
        num_rows=len(tags),
    )
    return tags
