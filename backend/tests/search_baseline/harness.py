"""Backend-agnostic retrieval harness for the search baseline.

Runs the *deterministic* production retrieval path (``search_chunks`` ->
``_embed_and_search`` -> ``document_index.hybrid_retrieval``) against the
``OpenSearchDocumentIndex`` and normalizes the results into stable ``BaselineHit``
rows that can be snapshotted and diffed.

No LLM is involved, so results are reproducible for a fixed corpus + query +
ranking profile.
"""

from datetime import datetime

from pydantic import BaseModel
from sqlalchemy.orm import Session

from om.configs.chat_configs import NUM_RETURNED_HITS
from om.configs.constants import DocumentSource
from om.context.search.models import ChunkIndexRequest
from om.context.search.models import IndexFilters
from om.context.search.retrieval.search_runner import search_chunks
from om.db.search_settings import get_current_search_settings
from om.document_index.factory import get_default_document_index
from om.document_index.interfaces_new import DocumentIndex
from om.document_index.interfaces_new import TenantState
from om.document_index.opensearch.opensearch_document_index import (
    OpenSearchDocumentIndex,
)
from om.indexing.models import IndexingSetting
from shared_configs.configs import MULTI_TENANT
from shared_configs.contextvars import get_current_tenant_id


# hybrid_alpha values that select the ranking profile in _embed_and_search:
#   alpha <= 0.3 -> KEYWORD ranking profile
#   alpha  > 0.3 -> SEMANTIC ranking profile
KEYWORD_ALPHA = 0.2
SEMANTIC_ALPHA = 0.5


class BaselineHit(BaseModel):
    """A normalized, snapshot-stable view of a single retrieved chunk."""

    rank: int
    document_id: str
    chunk_id: int
    semantic_identifier: str
    source_type: str
    # Rounded so tiny floating point differences don't churn the snapshot.
    # Used for diagnostics; ordering is the primary baseline invariant.
    score: float | None

    @property
    def key(self) -> tuple[str, int]:
        return (self.document_id, self.chunk_id)


def get_index(engine: str, db_session: Session) -> DocumentIndex:
    """Return a DocumentIndex for the requested engine.

    engine: "default" (env-configured) or "opensearch".
    """
    search_settings = get_current_search_settings(db_session)
    if engine == "default":
        return get_default_document_index(search_settings, None)
    tenant_state = TenantState(
        tenant_id=get_current_tenant_id(), multitenant=MULTI_TENANT
    )
    if engine == "opensearch":
        indexing_setting = IndexingSetting.from_db_model(search_settings)
        return OpenSearchDocumentIndex(
            tenant_state=tenant_state,
            index_name=search_settings.index_name,
            embedding_dim=indexing_setting.final_embedding_dim,
            embedding_precision=indexing_setting.embedding_precision,
        )
    raise ValueError(f"Unknown engine: {engine!r}")


def run_search(
    document_index: DocumentIndex,
    *,
    query: str,
    db_session: Session,
    hybrid_alpha: float | None = None,
    document_sets: list[str] | None = None,
    source_types: list[DocumentSource] | None = None,
    time_cutoff: datetime | None = None,
    query_keywords: list[str] | None = None,
    limit: int = NUM_RETURNED_HITS,
    score_ndigits: int = 4,
) -> list[BaselineHit]:
    """Run one retrieval and return normalized, ranked hits.

    Mirrors production retrieval exactly: builds an IndexFilters + ChunkIndexRequest
    and calls search_chunks (which embeds the query, applies filters, and calls
    hybrid_retrieval on the given index). ACL is bypassed (access_control_list=None)
    because the baseline corpus is public.
    """
    filters = IndexFilters(
        source_type=source_types,
        document_set=document_sets,
        time_cutoff=time_cutoff,
        tags=None,
        access_control_list=None,
    )

    request = ChunkIndexRequest(
        query=query,
        hybrid_alpha=hybrid_alpha,
        query_keywords=query_keywords,
        filters=filters,
        limit=limit,
    )

    chunks = search_chunks(
        query_request=request,
        user_id=None,
        document_index=document_index,
        db_session=db_session,
    )

    hits: list[BaselineHit] = []
    for rank, chunk in enumerate(chunks):
        hits.append(
            BaselineHit(
                rank=rank,
                document_id=chunk.document_id,
                chunk_id=chunk.chunk_id,
                semantic_identifier=chunk.semantic_identifier,
                source_type=(
                    chunk.source_type.value
                    if hasattr(chunk.source_type, "value")
                    else str(chunk.source_type)
                ),
                score=(
                    round(chunk.score, score_ndigits)
                    if chunk.score is not None
                    else None
                ),
            )
        )
    return hits


def hit_doc_ids(hits: list[BaselineHit]) -> list[str]:
    """Ordered list of document ids (the primary baseline invariant)."""
    return [h.document_id for h in hits]


def ensure_index_ready(engine: str, db_session: Session) -> None:
    """Make the engine's index ready for indexing/retrieval.

    For OpenSearch in single-tenant mode the index + search pipeline are NOT
    auto-created on construction, so we create them here (idempotent). For any
    other engine value this is a no-op.
    """
    if engine != "opensearch":
        return
    search_settings = get_current_search_settings(db_session)
    indexing_setting = IndexingSetting.from_db_model(search_settings)
    index = get_index("opensearch", db_session)
    # verify_and_create_index_if_necessary lives on the concrete OpenSearch class.
    index.verify_and_create_index_if_necessary(  # type: ignore[attr-defined]
        embedding_dim=indexing_setting.final_embedding_dim,
        embedding_precision=indexing_setting.embedding_precision,
    )


def refresh_opensearch(db_session: Session) -> None:
    """Force an OpenSearch refresh so freshly-indexed docs are searchable now."""
    from om.document_index.opensearch.client import OpenSearchIndexClient

    index_name = get_current_search_settings(db_session).index_name
    OpenSearchIndexClient(index_name=index_name).refresh_index()
