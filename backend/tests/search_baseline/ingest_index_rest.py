"""Ingest the two real articles in ``index_rest/`` into two domains and verify retrieval.

The two files belong to two domains (document sets):
  - foot_bal.txt -> "Sports"      (BBC article on Vinicius / Brazil / World Cup)
  - news1.txt    -> "WorldNews"   (Iran nuclear deal / US negotiations)

Each file is split into ~1200-char chunks, embedded with the real model server,
tagged with its domain document set, and indexed via the migrated new interface
(``DocumentIndex.index(chunks, IndexingMetadata)``).

Then it:
  1. queries Vespa directly to confirm the chunks landed (and their document_sets),
  2. runs domain-specific search queries through the same harness used by the
     baseline tests and prints document_id + score so relevance/scoring can be checked,
  3. asserts the right domain doc wins its own query and that the domain filter isolates results.

Run inside the backend container (Postgres + Vespa + model server reachable):

    INDEX_REST_DIR=/app/index_rest python -m tests.search_baseline.ingest_index_rest
"""

import os
from datetime import datetime
from datetime import timezone

from onyx.access.models import default_public_access
from onyx.configs.constants import DocumentSource
from onyx.connectors.models import Document
from onyx.connectors.models import TextSection
from onyx.db.engine.sql_engine import get_session_with_current_tenant
from onyx.db.engine.sql_engine import SqlEngine
from onyx.db.search_settings import get_current_search_settings
from onyx.document_index.interfaces_new import IndexingMetadata
from onyx.indexing.models import ChunkEmbedding
from onyx.indexing.models import DocMetadataAwareIndexChunk
from onyx.indexing.models import IndexChunk
from onyx.natural_language_processing.search_nlp_models import EmbeddingModel
from shared_configs.configs import MODEL_SERVER_HOST
from shared_configs.configs import MODEL_SERVER_PORT
from shared_configs.configs import POSTGRES_DEFAULT_SCHEMA
from shared_configs.enums import EmbedTextType
from tests.search_baseline.harness import ensure_index_ready
from tests.search_baseline.harness import get_index
from tests.search_baseline.harness import refresh_opensearch
from tests.search_baseline.harness import run_search


DOMAIN_SPORTS = "Sports"
DOMAIN_WORLD_NEWS = "WorldNews"
ALL_DOMAINS = [DOMAIN_SPORTS, DOMAIN_WORLD_NEWS]

INGEST_DATE = datetime(2026, 6, 13, tzinfo=timezone.utc)


# (filename, doc_id, domain, search-friendly title)
FILES = [
    (
        "foot_bal.txt",
        "index_rest::foot_bal",
        DOMAIN_SPORTS,
        "Vinicius Junior Brazil World Cup 2026",
    ),
    (
        "news1.txt",
        "index_rest::news1",
        DOMAIN_WORLD_NEWS,
        "Iran nuclear deal US negotiations ceasefire",
    ),
]


def _chunk_text(text: str, max_chars: int = 1200) -> list[str]:
    """Split text into ~max_chars chunks on paragraph/line boundaries."""
    paras = [p.strip() for p in text.split("\n") if p.strip()]
    chunks: list[str] = []
    cur = ""
    for p in paras:
        if cur and len(cur) + len(p) + 1 > max_chars:
            chunks.append(cur)
            cur = p
        else:
            cur = f"{cur}\n{p}" if cur else p
    if cur:
        chunks.append(cur)
    return chunks or [text.strip()]


def _build_doc_chunks(
    doc_id: str,
    title: str,
    domain: str,
    source: DocumentSource,
    contents: list[str],
    content_embeddings: list[list[float]],
    title_embedding: list[float],
) -> list[DocMetadataAwareIndexChunk]:
    document = Document(
        id=doc_id,
        source=source,
        sections=[TextSection(text="\n".join(contents), link=None)],
        metadata={},
        semantic_identifier=title,
        title=title,
        doc_updated_at=INGEST_DATE,
    )

    out: list[DocMetadataAwareIndexChunk] = []
    for i, (content, emb) in enumerate(zip(contents, content_embeddings)):
        index_chunk = IndexChunk(
            chunk_id=i,
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
            embeddings=ChunkEmbedding(full_embedding=emb, mini_chunk_embeddings=[]),
            title_embedding=title_embedding,
        )
        out.append(
            DocMetadataAwareIndexChunk.from_index_chunk(
                index_chunk=index_chunk,
                access=default_public_access,
                document_sets={domain},
                user_project=[],
                boost=0,
                aggregated_chunk_boost_factor=1.0,
                tenant_id=POSTGRES_DEFAULT_SCHEMA,
            )
        )
    return out


def ingest(index_dir: str, engine: str = "vespa") -> dict[str, int]:
    """Chunk, embed, and index both files into `engine`. Returns {doc_id: num_chunks}."""
    with get_session_with_current_tenant() as db_session:
        search_settings = get_current_search_settings(db_session)
        model = EmbeddingModel.from_db_model(
            search_settings=search_settings,
            server_host=MODEL_SERVER_HOST,
            server_port=MODEL_SERVER_PORT,
        )

        all_chunks: list[DocMetadataAwareIndexChunk] = []
        per_doc: dict[str, int] = {}
        for filename, doc_id, domain, title in FILES:
            path = os.path.join(index_dir, filename)
            with open(path, encoding="utf-8") as f:
                text = f.read()
            contents = _chunk_text(text)
            content_embeddings = model.encode(contents, text_type=EmbedTextType.PASSAGE)
            title_embedding = model.encode([title], text_type=EmbedTextType.PASSAGE)[0]
            chunks = _build_doc_chunks(
                doc_id, title, domain, DocumentSource.FILE,
                contents, content_embeddings, title_embedding,
            )
            all_chunks.extend(chunks)
            per_doc[doc_id] = len(chunks)
            print(f"  {filename}: {len(chunks)} chunks -> domain '{domain}'")

        ensure_index_ready(engine, db_session)
        index = get_index(engine, db_session)
        records = index.index(
            chunks=all_chunks,
            indexing_metadata=IndexingMetadata(doc_id_to_chunk_cnt_diff={}),
        )
        print(
            f"  indexed {len(records)} docs into {type(index).__name__} "
            f"({getattr(index, 'index_name', '?')}) [engine={engine}]"
        )
        if engine == "opensearch":
            refresh_opensearch(db_session)
    return per_doc


def verify_in_engine(per_doc: dict[str, int], engine: str) -> None:
    """Query the engine directly to confirm the chunks are present."""
    if engine == "vespa":
        from tests.integration.common_utils.vespa import vespa_fixture

        with get_session_with_current_tenant() as db_session:
            index_name = get_current_search_settings(db_session).index_name
        client = vespa_fixture(index_name=index_name)
        found = client.get_documents_by_id(list(per_doc.keys()))
        docs = found.get("documents") or found.get("document") or []
        print(f"\nVespa direct lookup: {len(docs)} chunk records for {len(per_doc)} docs")
        by_doc: dict[str, dict] = {}
        for d in docs:
            fields = d.get("fields", {})
            did = fields.get("document_id")
            by_doc.setdefault(did, {"chunks": 0, "document_sets": set()})
            by_doc[did]["chunks"] += 1
            ds = fields.get("document_sets")
            if isinstance(ds, dict):
                by_doc[did]["document_sets"].update(ds.keys())
            elif isinstance(ds, list):
                by_doc[did]["document_sets"].update(ds)
        for did, info in by_doc.items():
            print(f"  {did}: {info['chunks']} chunks, document_sets={sorted(info['document_sets'])}")
        return

    # OpenSearch: confirm the index exists and report id-based chunk counts.
    from onyx.document_index.opensearch.client import OpenSearchIndexClient

    with get_session_with_current_tenant() as db_session:
        index_name = get_current_search_settings(db_session).index_name
    client = OpenSearchIndexClient(index_name=index_name)
    print(
        f"\nOpenSearch direct check: index '{index_name}' exists="
        f"{client.index_exists()}, reachable={client.ping()}"
    )


def verify_retrieval(engine: str = "vespa") -> None:
    """Run domain-specific queries and print document_id + score, then assert."""
    with get_session_with_current_tenant() as db_session:
        index = get_index(engine, db_session)

        cases = [
            ("Will Vinicius shine for Brazil at the 2026 World Cup?",
             "index_rest::foot_bal"),
            ("Iran nuclear deal negotiations and US sanctions",
             "index_rest::news1"),
        ]

        print("\n=== Retrieval verification (scoped to the two domains) ===")
        for query, expected_doc in cases:
            hits = run_search(
                index,
                query=query,
                db_session=db_session,
                document_sets=ALL_DOMAINS,
                limit=10,
            )
            top = [(h.document_id, h.chunk_id, h.score) for h in hits[:5]]
            print(f"\nQuery: {query!r}")
            for did, cid, score in top:
                marker = "  <-- expected" if did == expected_doc else ""
                print(f"   {score:>8.4f}  {did} (chunk {cid}){marker}")
            assert hits, f"No results for {query!r}"
            assert hits[0].document_id == expected_doc, (
                f"Expected {expected_doc} to rank first for {query!r}, "
                f"got {hits[0].document_id}"
            )

        # Domain filter isolation: a sports query restricted to WorldNews must
        # return only the news doc (no football doc leaks through).
        print("\n=== Domain filter isolation ===")
        sports_query = "World Cup football star striker goals"
        news_only = run_search(
            index, query=sports_query, db_session=db_session,
            document_sets=[DOMAIN_WORLD_NEWS], limit=10,
        )
        returned = {h.document_id for h in news_only}
        print(f"Sports query restricted to '{DOMAIN_WORLD_NEWS}': {sorted(returned)}")
        assert "index_rest::foot_bal" not in returned, "Football doc leaked into WorldNews filter"

    print("\nAll retrieval checks passed.")


def main() -> None:
    try:
        SqlEngine.init_engine(pool_size=5, max_overflow=5)
    except Exception:
        pass

    engine = os.environ.get("SEARCH_ENGINE", "vespa")
    index_dir = os.environ.get("INDEX_REST_DIR", "/app/index_rest")
    print(f"Ingesting from: {index_dir}  [engine={engine}]")
    per_doc = ingest(index_dir, engine=engine)
    verify_in_engine(per_doc, engine=engine)
    verify_retrieval(engine=engine)


if __name__ == "__main__":
    main()
