"""App-side rescore of hybrid search hits (feedback boost + freshness).

OpenSearch's normalization processor runs last in a hybrid search, so any
in-query boosting is undone by the min-max / z-score stretch (see README.md,
"On time decay and boosting"). Instead the final normalized hybrid score of
each hit is multiplied here, after OpenSearch returns:

    adjusted = score x feedback_boost_multiplier(boost) x freshness_multiplier(age)

- feedback_boost_multiplier: piecewise sigmoid of the document `boost`
  (curator / feedback votes); 1.0 at boost 0, bounded to (0.5, 2.0).
- freshness_multiplier: 1 / (1 + decay x age_in_years), never below a floor
  (default 0.75). Documents without `updated_at` are treated as
  REFERENCE_MISSING_DOCUMENT_AGE_SECONDS old.

Everything here is pure (no I/O, `now` injected) so it can be unit-tested
without a cluster. Settings are read from the config modules at call time so
tests can monkeypatch them. Off by default (OPENSEARCH_HYBRID_RESCORE_ENABLED).
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from datetime import timezone

import om.configs.app_configs as app_configs
import om.configs.chat_configs as chat_configs
from om.context.search.enums import RecencyBiasSetting
from om.context.search.models import InferenceChunk
from om.utils.logger import setup_logger

logger = setup_logger(__name__)


SECONDS_PER_YEAR = 31_536_000
# Assumed age for documents with no `updated_at` (~91.3 days). Matches the
# historical rank expression exactly (decided 2026-10-30), so it intentionally
# differs from ASSUMED_DOCUMENT_AGE_DAYS (90), which only drives time filters.
REFERENCE_MISSING_DOCUMENT_AGE_SECONDS = 7_890_000
# Sigmoid steepness for the feedback boost: boost / 3.
FEEDBACK_BOOST_SCALE = 3.0
# |boost| beyond this cannot change the factor measurably; clamping avoids
# math.exp overflow for absurd stored values.
_MAX_ABS_BOOST = 1_500
# Added after shifting negative scores so the lowest hit keeps a non-zero score.
_NEGATIVE_SCORE_SHIFT_EPSILON = 1e-6

MIN_OVERFETCH_FACTOR = 1.0
MAX_OVERFETCH_FACTOR = 5.0


@dataclass(frozen=True)
class HybridRescoreSettings:
    enabled: bool
    freshness_enabled: bool
    feedback_boost_enabled: bool
    freshness_decay_per_year: float
    freshness_floor: float
    overfetch_factor: float

    @property
    def any_factor_enabled(self) -> bool:
        return self.enabled and (self.freshness_enabled or self.feedback_boost_enabled)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def load_hybrid_rescore_settings(
    recency_bias_multiplier: float = 1.0,
) -> HybridRescoreSettings:
    """Reads the current config. `recency_bias_multiplier` is the per-request /
    per-agent factor (see recency_bias_multiplier_for_setting); it scales the
    global DOC_TIME_DECAY x RECENCY_BIAS_MULTIPLIER decay."""
    return HybridRescoreSettings(
        enabled=app_configs.OPENSEARCH_HYBRID_RESCORE_ENABLED,
        freshness_enabled=app_configs.OPENSEARCH_RESCORE_FRESHNESS_ENABLED,
        feedback_boost_enabled=app_configs.OPENSEARCH_RESCORE_FEEDBACK_BOOST_ENABLED,
        freshness_decay_per_year=(
            chat_configs.DOC_TIME_DECAY
            * app_configs.RECENCY_BIAS_MULTIPLIER
            * recency_bias_multiplier
        ),
        freshness_floor=_clamp(
            app_configs.OPENSEARCH_RESCORE_FRESHNESS_FLOOR, 0.0, 1.0
        ),
        overfetch_factor=_clamp(
            app_configs.OPENSEARCH_RESCORE_OVERFETCH_FACTOR,
            MIN_OVERFETCH_FACTOR,
            MAX_OVERFETCH_FACTOR,
        ),
    )


def recency_bias_multiplier_for_setting(
    setting: RecencyBiasSetting | None,
) -> float:
    """Maps an agent's recency setting to a freshness decay multiplier.

    FAVOR_RECENT doubles the decay, NO_DECAY disables freshness, BASE_DECAY and
    AUTO (no query-time detection exists) keep the base decay.
    """
    if setting == RecencyBiasSetting.FAVOR_RECENT:
        return chat_configs.FAVOR_RECENT_DECAY_MULTIPLIER
    if setting == RecencyBiasSetting.NO_DECAY:
        return 0.0
    return 1.0


def feedback_boost_multiplier(boost: int) -> float:
    """0.5..1.0 for negative boost, 1.0..2.0 for non-negative boost."""
    clamped = _clamp(float(boost), -_MAX_ABS_BOOST, _MAX_ABS_BOOST)
    sigmoid = 1.0 / (1.0 + math.exp(-clamped / FEEDBACK_BOOST_SCALE))
    if clamped < 0:
        return 0.5 + sigmoid
    return 2.0 * sigmoid


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def freshness_multiplier(
    updated_at: datetime | None,
    now: datetime,
    decay_per_year: float,
    floor: float,
) -> float:
    """max(1 / (1 + decay x age_years), floor); 1.0 when decay <= 0.

    Future `updated_at` counts as age 0. Naive datetimes are treated as UTC.
    """
    if decay_per_year <= 0:
        return 1.0
    if updated_at is None:
        age_seconds = float(REFERENCE_MISSING_DOCUMENT_AGE_SECONDS)
    else:
        age_seconds = max((_as_utc(now) - _as_utc(updated_at)).total_seconds(), 0.0)
    age_years = age_seconds / SECONDS_PER_YEAR
    return max(1.0 / (1.0 + decay_per_year * age_years), floor)


def chunk_rescore_factor(
    chunk: InferenceChunk, *, now: datetime, settings: HybridRescoreSettings
) -> float:
    """Combined multiplier for one chunk (1.0 when everything is off)."""
    if not settings.enabled:
        return 1.0
    factor = 1.0
    if settings.feedback_boost_enabled:
        factor *= feedback_boost_multiplier(chunk.boost)
    if settings.freshness_enabled:
        factor *= freshness_multiplier(
            chunk.updated_at,
            now,
            settings.freshness_decay_per_year,
            settings.freshness_floor,
        )
    return factor


def apply_rescore_factors(
    chunks: Sequence[InferenceChunk],
    base_scores: Sequence[float | None],
    *,
    now: datetime,
    settings: HybridRescoreSettings,
) -> list[float | None]:
    """Multiplies each base score by the chunk's factor.

    If any score is negative (z-score pipeline, cross-encoder logits) all
    scores are first shifted by -min + epsilon, because multiplying a negative
    score by a boost would push it down. `None` scores stay `None`.
    """
    if len(chunks) != len(base_scores):
        raise ValueError(
            f"Bug: {len(chunks)} chunks but {len(base_scores)} scores to rescore."
        )
    present = [score for score in base_scores if score is not None]
    shift = 0.0
    if present and min(present) < 0:
        shift = -min(present) + _NEGATIVE_SCORE_SHIFT_EPSILON
    adjusted: list[float | None] = []
    for chunk, score in zip(chunks, base_scores):
        if score is None:
            adjusted.append(None)
            continue
        adjusted.append(
            (score + shift) * chunk_rescore_factor(chunk, now=now, settings=settings)
        )
    return adjusted


def _order_by_scores(scores: Sequence[float | None]) -> list[int]:
    """Indices sorted by score desc, stable on ties, `None` last in input order."""
    scored = [i for i, score in enumerate(scores) if score is not None]
    unscored = [i for i, score in enumerate(scores) if score is None]
    scored.sort(key=lambda i: scores[i], reverse=True)  # type: ignore[arg-type,return-value]
    return scored + unscored


def rescore_hybrid_chunks(
    chunks: Sequence[InferenceChunk],
    *,
    now: datetime,
    settings: HybridRescoreSettings,
    preserve_score_scale: bool = True,
) -> list[InferenceChunk]:
    """Returns a new list of chunks with adjusted scores, best first.

    With `preserve_score_scale` the adjusted scores are rescaled so the batch
    maximum equals the original maximum score. Order is unchanged by this, but
    the scores stay on the scale OpenSearch produced, so federated results
    (merged by raw score in search_runner.combine_retrieval_results) are not
    crowded out by boosted scores above 1.0.

    When the switch (or every factor) is off the input is returned unchanged,
    as a new list.
    """
    if not settings.any_factor_enabled or not chunks:
        return list(chunks)

    base_scores = [chunk.score for chunk in chunks]
    adjusted = apply_rescore_factors(chunks, base_scores, now=now, settings=settings)

    if preserve_score_scale:
        present_base = [score for score in base_scores if score is not None]
        present_adjusted = [score for score in adjusted if score is not None]
        if present_base and present_adjusted:
            max_base = max(present_base)
            max_adjusted = max(present_adjusted)
            # Only rescale when it keeps the order (both maxima positive).
            if max_base > 0 and max_adjusted > 0:
                ratio = max_base / max_adjusted
                adjusted = [
                    None if score is None else score * ratio for score in adjusted
                ]

    order = _order_by_scores(adjusted)
    rescored: list[InferenceChunk] = []
    for i in order:
        chunk = chunks[i]
        if adjusted[i] is None:
            rescored.append(chunk)
            continue
        logger.debug(
            "Hybrid rescore %s#%s: base=%s adjusted=%s boost=%s updated_at=%s",
            chunk.document_id,
            chunk.chunk_id,
            chunk.score,
            adjusted[i],
            chunk.boost,
            chunk.updated_at,
        )
        rescored.append(chunk.model_copy(update={"score": adjusted[i]}))
    return rescored


def rescore_cross_encoder_scores(
    chunks: Sequence[InferenceChunk],
    scores: Sequence[float],
    now: datetime | None = None,
) -> list[float]:
    """Applies the same factors to cross-encoder rerank scores.

    Returns `scores` unchanged (as a list) when the switch is off. Uses the
    global decay (the per-agent multiplier is not available at rerank time).
    """
    settings = load_hybrid_rescore_settings()
    if not settings.any_factor_enabled:
        return list(scores)
    adjusted = apply_rescore_factors(
        chunks,
        list(scores),
        now=now or datetime.now(timezone.utc),
        settings=settings,
    )
    return [score if score is not None else 0.0 for score in adjusted]


def get_rescore_fetch_size(
    num_to_retrieve: int, overfetch_factor: float, cap: int
) -> int:
    """Over-fetched candidate count: ceil(n x factor), at most `cap`, never < n."""
    return max(num_to_retrieve, min(math.ceil(num_to_retrieve * overfetch_factor), cap))
