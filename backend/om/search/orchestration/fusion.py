"""Weighted reciprocal-rank fusion + chunk->section merging.

Reciprocal-rank fusion combines several independently-ranked result lists using
only rank position, so lists with incomparable score scales (keyword/BM25 vs
semantic) fuse without any score normalization:

    score(d) = Σ_m  weight_m / (k + rank_m(d))          (rank is 1-indexed)

``k`` (default 60) dampens the influence of very-top ranks; per-list ``weight``
lets us value the original query above expansion variants and semantic above
keyword variants. See README for the research basis.
"""

from dataclasses import dataclass

from om.context.search.models import InferenceChunk
from om.context.search.models import InferenceSection
from om.context.search.utils import inference_section_from_chunks

# Default rank constant; k in [40, 80] performs comparably in the literature.
DEFAULT_RRF_K = 60


@dataclass
class RankedList:
    """One retrieval result list plus its fusion weight."""

    chunks: list[InferenceChunk]
    weight: float


def weighted_reciprocal_rank_fusion(
    ranked_lists: list[RankedList],
    k: int = DEFAULT_RRF_K,
) -> list[tuple[InferenceChunk, float]]:
    """Fuse ranked chunk lists via weighted RRF.

    Chunk identity is ``InferenceChunk.unique_id`` (``document_id__chunk_id``).
    When a chunk appears in multiple lists we accumulate its weighted RRF
    contribution and keep the instance with the highest original retrieval score
    (best metadata/highlights). Returns ``(chunk, fused_score)`` sorted by fused
    score descending; ties broken by the chunk's own ordering.
    """
    if k < 1:
        k = 1
    fused_scores: dict[str, float] = {}
    best_chunk: dict[str, InferenceChunk] = {}

    for ranked_list in ranked_lists:
        if ranked_list.weight <= 0:
            continue
        for rank, chunk in enumerate(ranked_list.chunks, start=1):
            uid = chunk.unique_id
            fused_scores[uid] = fused_scores.get(uid, 0.0) + ranked_list.weight / (
                k + rank
            )
            existing = best_chunk.get(uid)
            if existing is None or (chunk.score or 0.0) > (existing.score or 0.0):
                best_chunk[uid] = chunk

    # Stable sort by fused score desc; ties keep first-seen (best-rank) order.
    ordered = sorted(fused_scores.items(), key=lambda item: item[1], reverse=True)
    return [(best_chunk[uid], score) for uid, score in ordered]


def merge_chunks_into_sections(
    scored_chunks: list[tuple[InferenceChunk, float]],
    max_sections: int,
) -> list[InferenceSection]:
    """Group fused chunks by document into per-document sections.

    Document order follows the best (first-seen) fused rank of any of its chunks.
    The section's center chunk is that best-fused chunk; combined content is the
    document's retrieved chunks ordered by ``chunk_id`` for readability.
    """
    by_doc: dict[str, list[InferenceChunk]] = {}
    order: list[str] = []
    for chunk, _score in scored_chunks:
        if chunk.document_id not in by_doc:
            by_doc[chunk.document_id] = []
            order.append(chunk.document_id)
        by_doc[chunk.document_id].append(chunk)

    sections: list[InferenceSection] = []
    for document_id in order[:max_sections]:
        doc_chunks = by_doc[document_id]
        center = doc_chunks[0]  # best fused chunk for this document
        ordered_chunks = sorted(doc_chunks, key=lambda c: c.chunk_id)
        section = inference_section_from_chunks(center, ordered_chunks)
        if section is not None:
            sections.append(section)
    return sections
