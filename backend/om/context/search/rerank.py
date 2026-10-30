"""Optional cross-encoder reranking of retrieved chunks.

Shared by the search page (``SearchOrchestrator``) and the chat search tool
(``SearchPipeline``). Disabled unless ``RERANK_ENABLED=true``. The scoring is done
by an OpenAI/Cohere-style ``/v1/rerank`` endpoint (the Cortex vLLM reranker).

The step FAILS OPEN: if the reranker is down, slow or returns something unexpected,
the original retrieval order is returned unchanged, so retrieval can never break
because reranking is unavailable.
"""

import time

from om.configs.app_configs import RERANK_API_KEY
from om.configs.app_configs import RERANK_ENABLED
from om.configs.app_configs import RERANK_MAX_CHARS_PER_DOC
from om.configs.app_configs import RERANK_MODEL
from om.configs.app_configs import RERANK_SERVER_URL
from om.configs.app_configs import RERANK_TIMEOUT_SECONDS
from om.configs.app_configs import RERANK_TOP_N
from om.context.search.models import InferenceChunk
from om.document_index.opensearch.hybrid_rescore import rescore_cross_encoder_scores
from om.natural_language_processing.search_nlp_models import RerankingModel
from om.utils.logger import setup_logger
from shared_configs.enums import RerankerProvider

logger = setup_logger()


def _chunk_text(chunk: InferenceChunk) -> str:
    """Passage sent to the reranker: title, newline, content (as the original
    implementation did), since titles and file names carry relevance signal. The title
    counts toward the character budget so a long title cannot push the passage past the
    token limit."""
    content = (chunk.content or chunk.blurb or "").strip()
    title = (chunk.semantic_identifier or chunk.title or "").strip()
    text = f"{title}\n{content}" if title else content
    # Empty documents make some servers reject the whole request
    return text[:RERANK_MAX_CHARS_PER_DOC] or "."


def rerank_chunks(query: str, chunks: list[InferenceChunk]) -> list[InferenceChunk]:
    """Reorder the top ``RERANK_TOP_N`` chunks by cross-encoder relevance.

    Chunks beyond ``RERANK_TOP_N`` keep their original order after the reranked head.
    """
    return rerank_chunks_with_status(query, chunks)[0]


def rerank_chunks_with_status(
    query: str, chunks: list[InferenceChunk]
) -> tuple[list[InferenceChunk], bool]:
    """Like :func:`rerank_chunks`, also reporting whether the rerank actually ran
    (False when disabled, skipped, or failed open)."""
    if not RERANK_ENABLED or len(chunks) < 2 or not query.strip():
        return chunks, False

    top_n = min(RERANK_TOP_N, len(chunks))
    head, tail = chunks[:top_n], chunks[top_n:]
    started = time.monotonic()
    try:
        model = RerankingModel(
            model_name=RERANK_MODEL,
            provider_type=RerankerProvider.LITELLM,
            api_key=RERANK_API_KEY,
            api_url=RERANK_SERVER_URL,
            timeout=RERANK_TIMEOUT_SECONDS,
        )
        scores = model.predict(query, [_chunk_text(chunk) for chunk in head])
        if len(scores) != len(head):
            raise ValueError(
                f"reranker returned {len(scores)} scores for {len(head)} chunks"
            )
        # --- hybrid-rescore (lane L3) --- apply the feedback-boost / freshness
        # factors to the cross-encoder scores too; unchanged unless
        # OPENSEARCH_HYBRID_RESCORE_ENABLED.
        scores = rescore_cross_encoder_scores(head, scores)
        # sorted() is stable, so equal scores keep their retrieval order
        order = sorted(range(len(head)), key=lambda i: scores[i], reverse=True)
        reranked = [head[i] for i in order]
        logger.info(
            f"rerank applied: chunks={len(head)} moved_to_top={order[0]} "
            f"elapsed_ms={(time.monotonic() - started) * 1000:.0f} model={RERANK_MODEL}"
        )
        return reranked + tail, True
    except Exception as exc:
        logger.warning(
            f"rerank skipped (failing open, original order kept): {type(exc).__name__}: {exc}"
        )
        return chunks, False


def rerank_scored_chunks(
    query: str, scored_chunks: list[tuple[InferenceChunk, float]]
) -> list[tuple[InferenceChunk, float]]:
    """Same as :func:`rerank_chunks` for ``(chunk, fused_score)`` pairs."""
    if not RERANK_ENABLED or len(scored_chunks) < 2:
        return scored_chunks
    score_by_id = {id(chunk): score for chunk, score in scored_chunks}
    reordered = rerank_chunks(query, [chunk for chunk, _ in scored_chunks])
    return [(chunk, score_by_id[id(chunk)]) for chunk in reordered]
