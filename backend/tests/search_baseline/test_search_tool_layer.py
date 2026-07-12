"""Tests for the post-retrieval "reranking/reordering" layer above raw retrieval.

Application-level cross-encoder reranking was REMOVED from this codebase (alembic
migration 78ebc66946a0). What remains and is exercised here:

  1. RRF-style fusion / dedup across query variants  -> combine_retrieval_results
     (deterministic, no services).
  2. The deterministic chunk-window selection used before LLM relevance scoring
     -> select_chunks_for_relevance (deterministic, no services).
  3. The LLM relevance/selection step -> select_sections_for_expansion
     (non-deterministic; marked `llm`, skipped unless an LLM is configured).
  4. A guard asserting the cross-encoder rerank path is truly gone, so the
     OpenSearch migration does not need to replicate it.
"""

from datetime import datetime
from datetime import timezone

import pytest

from om.configs.constants import DocumentSource
from om.context.search.models import InferenceChunk
from om.context.search.models import InferenceSection
from om.context.search.retrieval.search_runner import combine_retrieval_results
from om.secondary_llm_flows.document_filter import select_chunks_for_relevance


def _chunk(doc_id: str, chunk_id: int, score: float | None) -> InferenceChunk:
    return InferenceChunk(
        chunk_id=chunk_id,
        blurb=f"blurb {doc_id}:{chunk_id}",
        content=f"content {doc_id}:{chunk_id}",
        source_links={0: ""},
        image_file_id=None,
        section_continuation=False,
        document_id=doc_id,
        source_type=DocumentSource.FILE,
        semantic_identifier=doc_id,
        title=doc_id,
        boost=0,
        score=score,
        hidden=False,
        metadata={},
        match_highlights=[],
        doc_summary="",
        chunk_context="",
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


# --------------------------------------------------------------------------- #
# 1. RRF fusion / dedup across query variants (deterministic)
# --------------------------------------------------------------------------- #


def test_combine_dedups_and_sorts_by_score() -> None:
    set_a = [_chunk("d1", 0, 0.9), _chunk("d2", 0, 0.5)]
    set_b = [_chunk("d3", 0, 0.7), _chunk("d2", 0, 0.6)]

    combined = combine_retrieval_results([set_a, set_b])

    # Deduped by (document_id, chunk_id): d2 appears once.
    keys = [(c.document_id, c.chunk_id) for c in combined]
    assert keys.count(("d2", 0)) == 1
    # Sorted by score descending.
    scores = [c.score for c in combined]
    assert scores == sorted(scores, reverse=True)
    # d1 (0.9) first, d3 (0.7) second, d2 (max of 0.5/0.6 = 0.6) last.
    assert [c.document_id for c in combined] == ["d1", "d3", "d2"]


def test_combine_keeps_higher_score_on_duplicate() -> None:
    set_a = [_chunk("d2", 0, 0.5)]
    set_b = [_chunk("d2", 0, 0.95)]
    combined = combine_retrieval_results([set_a, set_b])
    assert len(combined) == 1
    assert combined[0].score == 0.95


def test_combine_handles_empty_sets() -> None:
    assert combine_retrieval_results([[], []]) == []


# --------------------------------------------------------------------------- #
# 2. Deterministic chunk-window selection (no LLM)
# --------------------------------------------------------------------------- #


def test_select_chunks_for_relevance_window() -> None:
    chunks = [_chunk("d1", i, 1.0 - i * 0.1) for i in range(5)]
    section = InferenceSection(
        center_chunk=chunks[2],
        chunks=chunks,
        combined_content=" ".join(c.content for c in chunks),
    )
    selected = select_chunks_for_relevance(section, max_chunks=3)
    # Center chunk (id 2) plus one neighbor on each side.
    selected_ids = [c.chunk_id for c in selected]
    assert 2 in selected_ids
    assert len(selected_ids) == 3
    assert selected_ids == [1, 2, 3]


def test_select_chunks_single() -> None:
    chunks = [_chunk("d1", 0, 0.9)]
    section = InferenceSection(
        center_chunk=chunks[0], chunks=chunks, combined_content=chunks[0].content
    )
    selected = select_chunks_for_relevance(section, max_chunks=3)
    assert [c.chunk_id for c in selected] == [0]


# --------------------------------------------------------------------------- #
# 3. LLM relevance/selection (non-deterministic; opt-in)
# --------------------------------------------------------------------------- #


@pytest.mark.llm
def test_llm_section_selection_plumbing() -> None:
    """Exercise the LLM selection layer end-to-end (plumbing only, not ordering).

    Skipped unless a default LLM provider is configured in the DB.
    """
    from om.secondary_llm_flows.document_filter import select_sections_for_expansion

    try:
        from om.llm.factory import get_default_llm

        llm = get_default_llm()
    except Exception as e:  # pragma: no cover - depends on env config
        pytest.skip(f"No default LLM available: {e}")

    chunks = [_chunk(f"d{i}", 0, 0.9 - i * 0.1) for i in range(3)]
    sections = [
        InferenceSection(center_chunk=c, chunks=[c], combined_content=c.content)
        for c in chunks
    ]

    selected, _excl = select_sections_for_expansion(
        sections=sections,
        user_query="content d0",
        llm=llm,
        max_sections=5,
    )
    # The layer ran and returned a subset (possibly all) of the input sections.
    assert selected, "LLM selection returned nothing"
    selected_ids = {s.center_chunk.document_id for s in selected}
    assert selected_ids.issubset({"d0", "d1", "d2"})


# --------------------------------------------------------------------------- #
# 4. Cross-encoder rerank path is gone (deterministic, documents the migration)
# --------------------------------------------------------------------------- #


def test_no_cross_encoder_rerank_columns() -> None:
    """SearchSettings must not carry rerank config (removed in migration 78ebc66946a0)."""
    from om.db.models import SearchSettings

    column_names = {c.name for c in SearchSettings.__table__.columns}
    rerank_cols = {c for c in column_names if "rerank" in c.lower()}
    assert not rerank_cols, (
        f"Unexpected rerank columns still on SearchSettings: {rerank_cols}. "
        "Application-level reranking was removed; baseline assumes none."
    )
