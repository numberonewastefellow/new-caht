"""Demonstrate the full SearchTool reranking pipeline layer-by-layer.

This reproduces what `SearchTool.run` does, but calls the *same underlying functions*
directly so every intermediate stage is visible/printable. It runs on the two-domain
`index_rest` data (Sports / WorldNews) seeded by `ingest_index_rest.py`.

Layers (none is a cross-encoder; the LLM is a batched selector, not a per-chunk scorer):
  0. Query expansion (LLM): semantic rephrase + keyword expansion variants.
  1. Per-query Vespa ranking: each variant retrieved independently (hybrid_retrieval).
  2. Weighted RRF fusion: merge the per-variant ranked lists (algorithmic, no LLM).
  3. LLM relevance selection: ONE batched call picks the relevant sections.
  4. Per-section context classification: one LLM call per *selected* section.

Run inside the backend container:

    INDEX_REST_DIR=/app/index_rest python -m tests.search_baseline.demo_reranking_layers
"""

from sqlalchemy.orm import Session

from om.configs.constants import MessageType
from om.context.search.models import ChunkIndexRequest
from om.context.search.models import IndexFilters
from om.context.search.models import InferenceChunk
from om.context.search.models import InferenceSection
from om.context.search.pipeline import merge_individual_chunks
from om.context.search.retrieval.search_runner import search_chunks
from om.db.engine.sql_engine import get_session_with_current_tenant
from om.db.engine.sql_engine import SqlEngine
from om.llm.factory import get_default_llm
from om.llm.interfaces import LLM
from om.secondary_llm_flows.document_filter import classify_section_relevance
from om.secondary_llm_flows.document_filter import select_sections_for_expansion
from om.secondary_llm_flows.query_expansion import keyword_query_expansion
from om.secondary_llm_flows.query_expansion import semantic_query_rephrase
from om.tools.models import ChatMinimalTextMessage
from om.tools.tool_implementations.search.constants import KEYWORD_QUERY_HYBRID_ALPHA
from om.tools.tool_implementations.search.constants import LLM_KEYWORD_QUERY_WEIGHT
from om.tools.tool_implementations.search.constants import LLM_SEMANTIC_QUERY_WEIGHT
from om.tools.tool_implementations.search.constants import MAX_CHUNKS_FOR_RELEVANCE
from om.tools.tool_implementations.search.constants import ORIGINAL_QUERY_WEIGHT
from om.tools.tool_implementations.search.search_utils import (
    weighted_reciprocal_rank_fusion,
)
from tests.search_baseline.harness import get_index
from tests.search_baseline.ingest_index_rest import ALL_DOMAINS


def _retrieve(
    db_session: Session,
    index: object,
    query: str,
    domains: list[str],
    hybrid_alpha: float | None,
    limit: int,
) -> list[InferenceChunk]:
    """Layer 1: one query variant -> Vespa hybrid_retrieval -> ranked InferenceChunks."""
    filters = IndexFilters(
        document_set=domains,
        source_type=None,
        time_cutoff=None,
        tags=None,
        access_control_list=None,
    )
    request = ChunkIndexRequest(
        query=query,
        hybrid_alpha=hybrid_alpha,
        query_keywords=None,
        filters=filters,
        limit=limit,
    )
    return search_chunks(
        query_request=request,
        user_id=None,
        document_index=index,  # type: ignore[arg-type]
        db_session=db_session,
    )


def _fmt(chunk: InferenceChunk) -> str:
    score = f"{chunk.score:.4f}" if chunk.score is not None else "  n/a "
    return f"{score}  {chunk.document_id} (chunk {chunk.chunk_id})"


def demonstrate(
    query: str,
    llm: LLM,
    db_session: Session,
    domains: list[str] | None = None,
    num_hits: int = 20,
    top_n_print: int = 5,
) -> dict:
    """Run all layers for one query, printing each stage. Returns key intermediates."""
    domains = domains or ALL_DOMAINS
    index = get_index("vespa", db_session)

    print("\n" + "=" * 78)
    print(f"USER QUERY: {query!r}   (domains scoped to {domains})")
    print("=" * 78)

    # ---- Layer 0: query expansion (LLM) ----------------------------------- #
    history = [ChatMinimalTextMessage(message=query, message_type=MessageType.USER)]
    try:
        semantic_query = semantic_query_rephrase(history, llm)
    except Exception as e:
        semantic_query = None
        print(f"[layer0] semantic rephrase failed: {e}")
    try:
        keyword_queries = keyword_query_expansion(history, llm) or []
    except Exception as e:
        keyword_queries = []
        print(f"[layer0] keyword expansion failed: {e}")

    print("\n[Layer 0] Query expansion (LLM):")
    print(f"   original : {query}")
    print(f"   semantic : {semantic_query}")
    print(f"   keyword  : {keyword_queries}")

    # Build variants with weights, mirroring SearchTool.run.
    # Semantic group (hybrid_alpha=None -> semantic ranking profile):
    variants: list[tuple[str, float, float | None]] = []  # (query, weight, hybrid_alpha)
    if semantic_query:
        variants.append((semantic_query, LLM_SEMANTIC_QUERY_WEIGHT, None))
    variants.append((query, ORIGINAL_QUERY_WEIGHT, None))
    # Keyword group (hybrid_alpha=0.2 -> keyword ranking profile):
    for kw in keyword_queries:
        variants.append((kw, LLM_KEYWORD_QUERY_WEIGHT, KEYWORD_QUERY_HYBRID_ALPHA))

    # ---- Layer 1: per-query Vespa ranking --------------------------------- #
    print("\n[Layer 1] Per-query Vespa ranking (each variant retrieved independently):")
    ranked_lists: list[list[InferenceChunk]] = []
    weights: list[float] = []
    for variant_query, weight, alpha in variants:
        chunks = _retrieve(db_session, index, variant_query, domains, alpha, num_hits)
        ranked_lists.append(chunks)
        weights.append(weight)
        profile = "keyword" if alpha is not None and alpha <= 0.3 else "semantic"
        print(f"\n   variant ({profile}, weight={weight}): {variant_query!r}")
        for c in chunks[:top_n_print]:
            print(f"      {_fmt(c)}")

    # ---- Layer 2: weighted RRF fusion ------------------------------------- #
    fused = weighted_reciprocal_rank_fusion(
        ranked_results=ranked_lists,
        weights=weights,
        id_extractor=lambda c: f"{c.document_id}_{c.chunk_id}",
    )
    print("\n[Layer 2] Weighted RRF fusion across variants (algorithmic, no LLM):")
    for c in fused[:top_n_print]:
        print(f"   {c.document_id} (chunk {c.chunk_id})")

    # ---- Layer 3: sections + LLM relevance selection ---------------------- #
    sections: list[InferenceSection] = merge_individual_chunks(fused)[:num_hits]
    selected_sections, best_doc_ids = select_sections_for_expansion(
        sections=sections,
        user_query=query,
        llm=llm,
        max_chunks_per_section=MAX_CHUNKS_FOR_RELEVANCE,
    )
    selected_doc_ids = [s.center_chunk.document_id for s in selected_sections]
    print("\n[Layer 3] LLM relevance selection (ONE batched call over all sections):")
    print(f"   candidate sections : {[s.center_chunk.document_id for s in sections]}")
    print(f"   LLM-selected       : {selected_doc_ids}")
    print(f"   marked best (excl) : {best_doc_ids}")

    # ---- Layer 4: per-section context classification (LLM) ----------------- #
    print("\n[Layer 4] Per-section context classification (LLM, only selected sections):")
    classifications: dict[str, str] = {}
    for section in selected_sections:
        cls = classify_section_relevance(
            document_title=section.center_chunk.semantic_identifier,
            section_text=section.combined_content,
            user_query=query,
            llm=llm,
            section_above_text=None,
            section_below_text=None,
        )
        classifications[section.center_chunk.document_id] = cls.value
        print(f"   {section.center_chunk.document_id}: {cls.value}")

    return {
        "semantic_query": semantic_query,
        "keyword_queries": keyword_queries,
        "fused_top_ids": [c.document_id for c in fused[:top_n_print]],
        "candidate_doc_ids": [s.center_chunk.document_id for s in sections],
        "selected_doc_ids": selected_doc_ids,
        "classifications": classifications,
    }


def main() -> None:
    try:
        SqlEngine.init_engine(pool_size=5, max_overflow=5)
    except Exception:
        pass

    # Ensure the two-domain data exists (idempotent upsert).
    import os

    from tests.search_baseline.ingest_index_rest import ingest

    index_dir = os.environ.get("INDEX_REST_DIR", "/app/index_rest")
    with get_session_with_current_tenant() as db_session:
        ingest(index_dir)

    queries = [
        "Will Vinicius shine for Brazil at the 2026 World Cup?",
        "What are the terms of the Iran nuclear deal with the US?",
    ]
    with get_session_with_current_tenant() as db_session:
        llm = get_default_llm()
        for q in queries:
            demonstrate(q, llm=llm, db_session=db_session)


if __name__ == "__main__":
    main()
