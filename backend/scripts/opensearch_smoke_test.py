"""End-to-end OpenSearch smoke test against a RUNNING stack.

Proves the whole document-index round trip works on OpenSearch -- the only
backend now that Vespa is gone -- using the SAME production primitives the app
uses (``DocumentIndex.index`` for write, ``search_chunks -> hybrid_retrieval``
for read). It is self-cleaning: it indexes a single uniquely-marked document,
searches for it, asserts it comes back, then deletes it, so it is safe to run
against a live dev stack without polluting the index.

Run inside the backend container (Postgres + OpenSearch + model server up):

    docker exec virtualai-background-1 python -m scripts.opensearch_smoke_test

Exit code 0 = PASS, 1 = FAIL. A unique marker id is used per run (seeded from
the env var ``SMOKE_MARKER`` if set) so concurrent runs do not collide.

NOTE: no ``Math.random``/wall-clock is used for the marker by default; pass
``SMOKE_MARKER`` to make the run fully deterministic/repeatable.
"""

from __future__ import annotations

import os
import sys
import uuid
from datetime import datetime
from datetime import timezone

from om.access.models import default_public_access
from om.configs.chat_configs import NUM_RETURNED_HITS
from om.configs.constants import DocumentSource
from om.connectors.models import Document
from om.connectors.models import TextSection
from om.context.search.models import ChunkIndexRequest
from om.context.search.models import IndexFilters
from om.context.search.retrieval.search_runner import search_chunks
from om.db.engine.sql_engine import get_session_with_current_tenant
from om.db.engine.sql_engine import SqlEngine
from om.db.search_settings import get_current_search_settings
from om.document_index.interfaces_new import IndexingMetadata
from om.document_index.interfaces_new import TenantState
from om.document_index.opensearch.client import OpenSearchIndexClient
from om.document_index.opensearch.opensearch_document_index import (
    OpenSearchDocumentIndex,
)
from om.indexing.models import ChunkEmbedding
from om.indexing.models import DocMetadataAwareIndexChunk
from om.indexing.models import IndexChunk
from om.indexing.models import IndexingSetting
from om.natural_language_processing.search_nlp_models import EmbeddingModel
from om.utils.logger import setup_logger
from shared_configs.configs import MODEL_SERVER_HOST
from shared_configs.configs import MODEL_SERVER_PORT
from shared_configs.configs import MULTI_TENANT
from shared_configs.configs import POSTGRES_DEFAULT_SCHEMA
from shared_configs.contextvars import get_current_tenant_id
from shared_configs.enums import EmbedTextType

logger = setup_logger()

# A distinctive, low-collision phrase so retrieval is unambiguous.
_MARKER_PHRASE = "quokka teleporter compliance memo"


def _build_marker_chunk(
    doc_id: str, content: str, content_embedding: list[float], title_embedding: list[float]
) -> DocMetadataAwareIndexChunk:
    document = Document(
        id=doc_id,
        source=DocumentSource.INGESTION_API,
        sections=[TextSection(text=content, link=None)],
        metadata={},
        semantic_identifier=_MARKER_PHRASE,
        title=_MARKER_PHRASE,
        doc_updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    index_chunk = IndexChunk(
        chunk_id=0,
        blurb=content[:200],
        content=content,
        source_links={0: ""},
        image_file_id=None,
        section_continuation=False,
        source_document=document,
        title_prefix="",
        metadata_suffix_semantic="",
        metadata_suffix_keyword="",
        contextual_rag_reserved_tokens=0,
        doc_summary="",
        chunk_context="",
        mini_chunk_texts=None,
        large_chunk_id=None,
        large_chunk_reference_ids=[],
        embeddings=ChunkEmbedding(full_embedding=content_embedding, mini_chunk_embeddings=[]),
        title_embedding=title_embedding,
    )
    return DocMetadataAwareIndexChunk.from_index_chunk(
        index_chunk=index_chunk,
        access=default_public_access,
        document_sets=set(),
        user_project=[],
        boost=0,
        aggregated_chunk_boost_factor=1.0,
        tenant_id=POSTGRES_DEFAULT_SCHEMA,
    )


def run_smoke_test() -> bool:
    marker = os.environ.get("SMOKE_MARKER") or uuid.uuid4().hex[:12]
    doc_id = f"opensearch-smoke::{marker}"
    content = f"{_MARKER_PHRASE}. Unique marker token {marker} for the smoke test."

    with get_session_with_current_tenant() as db_session:
        search_settings = get_current_search_settings(db_session)
        indexing_setting = IndexingSetting.from_db_model(search_settings)
        index_name = search_settings.index_name

    # 1) Heartbeat: OpenSearch must be reachable.
    client = OpenSearchIndexClient(index_name=index_name)
    if not client.ping():
        logger.error("[smoke] FAIL: OpenSearch is not reachable (ping failed).")
        return False
    logger.info("[smoke] OpenSearch reachable, index=%s", index_name)

    index = OpenSearchDocumentIndex(
        tenant_state=TenantState(tenant_id=get_current_tenant_id(), multitenant=MULTI_TENANT),
        index_name=index_name,
        embedding_dim=indexing_setting.final_embedding_dim,
        embedding_precision=indexing_setting.embedding_precision,
    )
    # Idempotent -- the index normally already exists in a running app.
    index.verify_and_create_index_if_necessary(
        embedding_dim=indexing_setting.final_embedding_dim,
        embedding_precision=indexing_setting.embedding_precision,
    )

    ok = False
    try:
        # 2) Embed + index the marker document. Build the model with settings
        # fetched inside a LIVE session -- from_db_model lazy-loads ORM attributes
        # (e.g. cloud_provider), so a detached instance would raise.
        with get_session_with_current_tenant() as db_session:
            live_settings = get_current_search_settings(db_session)
            model = EmbeddingModel.from_db_model(
                search_settings=live_settings,
                server_host=MODEL_SERVER_HOST,
                server_port=MODEL_SERVER_PORT,
            )
            content_embedding = model.encode([content], text_type=EmbedTextType.PASSAGE)[0]
            title_embedding = model.encode(
                [_MARKER_PHRASE], text_type=EmbedTextType.PASSAGE
            )[0]

        chunk = _build_marker_chunk(doc_id, content, content_embedding, title_embedding)
        index.index(
            chunks=[chunk],
            indexing_metadata=IndexingMetadata(doc_id_to_chunk_cnt_diff={}),
        )
        client.refresh_index()
        logger.info("[smoke] indexed marker doc %s", doc_id)

        # 3) Search via the production retrieval path and assert the marker returns.
        with get_session_with_current_tenant() as db_session:
            request = ChunkIndexRequest(
                query=_MARKER_PHRASE,
                hybrid_alpha=None,
                query_keywords=None,
                filters=IndexFilters(
                    source_type=None,
                    document_set=None,
                    time_cutoff=None,
                    tags=None,
                    access_control_list=None,
                ),
                limit=NUM_RETURNED_HITS,
            )
            hits = search_chunks(
                query_request=request,
                user_id=None,
                document_index=index,
                db_session=db_session,
            )
        returned_ids = {h.document_id for h in hits}
        if doc_id in returned_ids:
            logger.info("[smoke] PASS: marker doc retrieved from OpenSearch (%d hits).", len(hits))
            ok = True
        else:
            logger.error(
                "[smoke] FAIL: marker doc %s NOT in results. Got: %s",
                doc_id,
                sorted(returned_ids),
            )
    finally:
        # 4) Cleanup -- always attempt to delete the marker doc.
        try:
            index.delete(document_id=doc_id, chunk_count=1)
            client.refresh_index()
            logger.info("[smoke] cleaned up marker doc %s", doc_id)
        except Exception as e:  # pragma: no cover - best-effort cleanup
            logger.warning("[smoke] cleanup of %s failed: %s", doc_id, e)
        client.close()

    return ok


def main() -> None:
    try:
        SqlEngine.init_engine(pool_size=5, max_overflow=5)
    except Exception:
        pass
    ok = run_smoke_test()
    print("OPENSEARCH SMOKE TEST: " + ("PASS" if ok else "FAIL"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
