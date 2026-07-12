"""Seed the fixed baseline corpus into the document index/indices with REAL embeddings.

Run from the ``backend/`` directory with the dev stack (Postgres + Vespa + model
server) running:

    python -m tests.search_baseline.seed_search_corpus

By default this indexes into every index returned by ``get_all_document_indices``
(Vespa always; OpenSearch too when ``ENABLE_OPENSEARCH_INDEXING_FOR_ONYX=true``),
so the same corpus backs both the Vespa baseline and the later OpenSearch compare.

This reuses the production indexing primitives (``VespaIndex.index`` /
``DocMetadataAwareIndexChunk``) exactly like ``scripts/query_time_check/seed_dummy_docs.py``,
but computes real passage embeddings from the model server so semantic search and
relevance are meaningful.
"""

from collections import Counter

from sqlalchemy.orm import Session

from om.access.models import default_public_access
from om.connectors.models import Document
from om.connectors.models import TextSection
from om.db.engine.sql_engine import get_session_with_current_tenant
from om.db.search_settings import get_current_search_settings
from om.document_index.factory import get_all_document_indices
from om.document_index.interfaces_new import DocumentIndex
from om.document_index.interfaces_new import IndexingMetadata
from om.indexing.models import ChunkEmbedding
from om.indexing.models import DocMetadataAwareIndexChunk
from om.indexing.models import IndexChunk
from om.natural_language_processing.search_nlp_models import EmbeddingModel
from om.utils.logger import setup_logger
from shared_configs.configs import MODEL_SERVER_HOST
from shared_configs.configs import MODEL_SERVER_PORT
from shared_configs.configs import POSTGRES_DEFAULT_SCHEMA
from shared_configs.enums import EmbedTextType
from tests.search_baseline.corpus import CORPUS
from tests.search_baseline.corpus import CorpusDoc
from tests.search_baseline.harness import ensure_index_ready
from tests.search_baseline.harness import get_index

logger = setup_logger()


def _build_chunk(
    doc: CorpusDoc,
    content_embedding: list[float],
    title_embedding: list[float],
) -> DocMetadataAwareIndexChunk:
    document = Document(
        id=doc.doc_id,
        source=doc.source,
        sections=[TextSection(text=doc.content, link=None)],
        metadata=dict(doc.metadata),
        semantic_identifier=doc.title,
        title=doc.title,
        doc_updated_at=doc.updated_at,
    )

    index_chunk = IndexChunk(
        chunk_id=0,
        blurb=doc.content[:200],
        content=doc.content,
        source_links={0: ""},
        image_file_id=None,
        section_continuation=False,
        source_document=document,
        # Keep title_prefix empty so stored content is not mutated/stripped on
        # retrieval cleanup -- we want predictable content in the baseline.
        title_prefix="",
        metadata_suffix_semantic="",
        metadata_suffix_keyword="",
        contextual_rag_reserved_tokens=0,
        doc_summary="",
        chunk_context="",
        mini_chunk_texts=None,
        large_chunk_id=None,
        large_chunk_reference_ids=[],
        embeddings=ChunkEmbedding(
            full_embedding=content_embedding,
            mini_chunk_embeddings=[],
        ),
        title_embedding=title_embedding,
    )

    return DocMetadataAwareIndexChunk.from_index_chunk(
        index_chunk=index_chunk,
        access=default_public_access,
        document_sets=set(doc.document_sets),
        user_project=[],
        # Neutral boosts so ranking reflects pure relevance (good for a baseline).
        boost=0,
        aggregated_chunk_boost_factor=1.0,
        tenant_id=POSTGRES_DEFAULT_SCHEMA,
    )


def build_metadata_chunks(db_session: Session) -> list[DocMetadataAwareIndexChunk]:
    """Build one metadata-aware chunk per corpus doc, with real model embeddings."""
    search_settings = get_current_search_settings(db_session)
    model = EmbeddingModel.from_db_model(
        search_settings=search_settings,
        server_host=MODEL_SERVER_HOST,
        server_port=MODEL_SERVER_PORT,
    )

    contents = [doc.content for doc in CORPUS]
    titles = [doc.title for doc in CORPUS]

    content_embeddings = model.encode(contents, text_type=EmbedTextType.PASSAGE)
    title_embeddings = model.encode(titles, text_type=EmbedTextType.PASSAGE)

    return [
        _build_chunk(doc, content_embeddings[i], title_embeddings[i])
        for i, doc in enumerate(CORPUS)
    ]


def seed_corpus(
    db_session: Session,
    engine: str | None = None,
    indices: list[DocumentIndex] | None = None,
) -> int:
    """Index the corpus into the given engine / indices.

    - engine="vespa"|"opensearch": index ONLY into that engine (creates the
      OpenSearch index/pipeline first). Use this when only one engine is up.
    - engine=None and indices=None: index into all configured indices
      (`get_all_document_indices`, writes to both when dual-indexing is enabled).

    Returns the number of documents indexed (per index).
    """
    chunks = build_metadata_chunks(db_session)

    if indices is None:
        if engine is None:
            search_settings = get_current_search_settings(db_session)
            indices = get_all_document_indices(
                search_settings=search_settings,
                secondary_search_settings=None,
            )
        else:
            ensure_index_ready(engine, db_session)
            indices = [get_index(engine, db_session)]

    for index in indices:
        records = index.index(
            chunks=chunks,
            # Empty diff => no stale-chunk cleanup, plain upsert.
            indexing_metadata=IndexingMetadata(doc_id_to_chunk_cnt_diff={}),
        )
        logger.info(
            f"Indexed {len(records)} documents into "
            f"{type(index).__name__} ({getattr(index, 'index_name', '?')})"
        )

    return len(CORPUS)


def _print_distribution() -> None:
    by_kb: Counter[str] = Counter()
    by_source: Counter[str] = Counter()
    by_recency = Counter()
    from tests.search_baseline.corpus import TIME_CUTOFF_BETWEEN

    for doc in CORPUS:
        for kb in doc.document_sets:
            by_kb[kb] += 1
        by_source[doc.source.value] += 1
        by_recency["recent" if doc.updated_at >= TIME_CUTOFF_BETWEEN else "old"] += 1

    print(f"Total docs: {len(CORPUS)}")
    print(f"By knowledge base: {dict(by_kb)}")
    print(f"By source_type:    {dict(by_source)}")
    print(f"By recency:        {dict(by_recency)}")


def main() -> None:
    _print_distribution()
    with get_session_with_current_tenant() as db_session:
        count = seed_corpus(db_session)
    print(f"\nSeeded {count} documents into all configured indices.")

    # Verify the docs landed in Vespa.
    try:
        from om.db.engine.sql_engine import get_session_with_current_tenant as _s
        from tests.integration.common_utils.vespa import vespa_fixture

        with _s() as db_session:
            search_settings = get_current_search_settings(db_session)
        client = vespa_fixture(index_name=search_settings.index_name)
        found = client.get_documents_by_id([doc.doc_id for doc in CORPUS])
        n = len(found.get("documents", found.get("document", []) or []))
        print(f"Vespa verification: found {n} chunk records for the corpus.")
    except Exception as e:  # pragma: no cover - verification is best-effort
        print(f"(Vespa verification skipped: {e})")


if __name__ == "__main__":
    main()
