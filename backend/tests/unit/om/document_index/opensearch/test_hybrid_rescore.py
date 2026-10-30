"""Unit tests for om/document_index/opensearch/hybrid_rescore.py (pure functions)."""

from datetime import datetime
from datetime import timedelta
from datetime import timezone

import pytest

import om.configs.app_configs as app_configs
import om.configs.chat_configs as chat_configs
from om.configs.constants import DocumentSource
from om.context.search.enums import RecencyBiasSetting
from om.context.search.models import InferenceChunk
from om.document_index.opensearch import hybrid_rescore
from om.document_index.opensearch.hybrid_rescore import feedback_boost_multiplier
from om.document_index.opensearch.hybrid_rescore import freshness_multiplier
from om.document_index.opensearch.hybrid_rescore import get_rescore_fetch_size
from om.document_index.opensearch.hybrid_rescore import HybridRescoreSettings
from om.document_index.opensearch.hybrid_rescore import load_hybrid_rescore_settings
from om.document_index.opensearch.hybrid_rescore import (
    recency_bias_multiplier_for_setting,
)
from om.document_index.opensearch.hybrid_rescore import rescore_cross_encoder_scores
from om.document_index.opensearch.hybrid_rescore import rescore_hybrid_chunks

NOW = datetime(2026, 10, 30, 12, 0, 0, tzinfo=timezone.utc)


def _settings(**overrides: object) -> HybridRescoreSettings:
    values: dict[str, object] = dict(
        enabled=True,
        freshness_enabled=True,
        feedback_boost_enabled=True,
        freshness_decay_per_year=0.5,
        freshness_floor=0.75,
        overfetch_factor=2.0,
    )
    values.update(overrides)
    return HybridRescoreSettings(**values)  # type: ignore[arg-type]


def _chunk(
    doc: str,
    score: float | None,
    boost: int = 0,
    age_days: float | None = 0,
) -> InferenceChunk:
    return InferenceChunk(
        chunk_id=0,
        blurb="b",
        content="c",
        source_links=None,
        image_file_id=None,
        section_continuation=False,
        document_id=doc,
        source_type=DocumentSource.FILE,
        semantic_identifier=doc,
        title=doc,
        boost=boost,
        score=score,
        hidden=False,
        metadata={},
        match_highlights=[],
        doc_summary="",
        chunk_context="",
        updated_at=None if age_days is None else NOW - timedelta(days=age_days),
    )


# --- feedback boost -------------------------------------------------------


def test_boost_zero_is_neutral() -> None:
    assert feedback_boost_multiplier(0) == pytest.approx(1.0)


@pytest.mark.parametrize(
    "boost,expected",
    [(-3, 0.76894), (3, 1.46212), (10, 1.93111), (-10, 0.53445)],
)
def test_boost_values(boost: int, expected: float) -> None:
    assert feedback_boost_multiplier(boost) == pytest.approx(expected, abs=1e-5)


def test_boost_bounds_and_monotonic() -> None:
    values = [feedback_boost_multiplier(b) for b in range(-60, 61)]
    assert all(a <= b for a, b in zip(values, values[1:]))
    assert all(0.5 <= v <= 2.0 for v in values)
    # Absurd stored values must not overflow.
    assert feedback_boost_multiplier(-(10**9)) == pytest.approx(0.5)
    assert feedback_boost_multiplier(10**9) == pytest.approx(2.0)


# --- freshness ------------------------------------------------------------


def test_freshness_age_zero_is_one() -> None:
    assert freshness_multiplier(NOW, NOW, 0.5, 0.75) == pytest.approx(1.0)


def test_freshness_floor() -> None:
    old = NOW - timedelta(days=3650)
    assert freshness_multiplier(old, NOW, 0.5, 0.75) == pytest.approx(0.75)
    assert freshness_multiplier(old, NOW, 0.5, 0.0) < 0.75


def test_freshness_missing_date_uses_reference_age() -> None:
    # 7_890_000 s = 0.25019 years -> 1 / (1 + 0.5 * 0.25019)
    assert freshness_multiplier(None, NOW, 0.5, 0.75) == pytest.approx(
        0.88881, abs=1e-5
    )


def test_freshness_future_date_is_one() -> None:
    future = NOW + timedelta(days=30)
    assert freshness_multiplier(future, NOW, 0.5, 0.75) == pytest.approx(1.0)


def test_freshness_decay_zero_or_negative_is_one() -> None:
    old = NOW - timedelta(days=3650)
    assert freshness_multiplier(old, NOW, 0.0, 0.75) == 1.0
    assert freshness_multiplier(old, NOW, -1.0, 0.75) == 1.0


def test_freshness_naive_datetimes_treated_as_utc() -> None:
    naive = (NOW - timedelta(days=30)).replace(tzinfo=None)
    aware = NOW - timedelta(days=30)
    assert freshness_multiplier(naive, NOW, 0.5, 0.75) == pytest.approx(
        freshness_multiplier(aware, NOW, 0.5, 0.75)
    )


# --- rescore_hybrid_chunks -------------------------------------------------


def test_boosted_doc_promoted_old_doc_demoted() -> None:
    chunks = [
        _chunk("old", 0.9, age_days=3650),
        _chunk("mid", 0.85),
        _chunk("boosted", 0.8, boost=5),
    ]
    out = rescore_hybrid_chunks(chunks, now=NOW, settings=_settings())
    assert [c.document_id for c in out] == ["boosted", "mid", "old"]


def test_input_not_mutated_and_new_list() -> None:
    chunks = [_chunk("a", 0.5, boost=3), _chunk("b", 0.4)]
    out = rescore_hybrid_chunks(chunks, now=NOW, settings=_settings())
    assert chunks[0].score == 0.5
    assert out is not chunks


def test_preserve_score_scale_keeps_batch_max() -> None:
    chunks = [_chunk("a", 0.7, boost=10), _chunk("b", 0.9)]
    out = rescore_hybrid_chunks(chunks, now=NOW, settings=_settings())
    assert max(c.score or 0 for c in out) == pytest.approx(0.9)
    raw = rescore_hybrid_chunks(
        chunks, now=NOW, settings=_settings(), preserve_score_scale=False
    )
    assert raw[0].score == pytest.approx(0.7 * 1.93111, abs=1e-5)
    assert [c.document_id for c in out] == [c.document_id for c in raw]


def test_stable_on_ties() -> None:
    chunks = [_chunk(f"d{i}", 0.5) for i in range(6)]
    out = rescore_hybrid_chunks(chunks, now=NOW, settings=_settings())
    assert [c.document_id for c in out] == [f"d{i}" for i in range(6)]


def test_none_scores_kept_at_end_in_order() -> None:
    chunks = [
        _chunk("n1", None),
        _chunk("a", 0.3),
        _chunk("n2", None),
        _chunk("b", 0.6),
    ]
    out = rescore_hybrid_chunks(chunks, now=NOW, settings=_settings())
    assert [c.document_id for c in out] == ["b", "a", "n1", "n2"]
    assert out[2].score is None and out[3].score is None


def test_negative_scores_are_shifted_so_boost_helps() -> None:
    # z-score style scores: shifted by -min so multiplying by a boost raises a
    # hit instead of pushing it further negative.
    chunks = [_chunk("a", -0.1), _chunk("b", -0.12, boost=10), _chunk("c", -0.5)]
    out = rescore_hybrid_chunks(
        chunks, now=NOW, settings=_settings(), preserve_score_scale=False
    )
    assert [c.document_id for c in out] == ["b", "a", "c"]
    assert all((c.score or 0) > 0 for c in out)


def test_sub_toggles() -> None:
    chunks = [_chunk("old", 0.9, age_days=3650), _chunk("boosted", 0.8, boost=2)]
    only_boost = _settings(freshness_enabled=False)
    out = rescore_hybrid_chunks(
        chunks, now=NOW, settings=only_boost, preserve_score_scale=False
    )
    assert out[0].document_id == "boosted"
    assert out[1].score == pytest.approx(0.9)  # no freshness penalty

    only_fresh = _settings(feedback_boost_enabled=False)
    out = rescore_hybrid_chunks(
        chunks, now=NOW, settings=only_fresh, preserve_score_scale=False
    )
    assert out[0].document_id == "boosted"  # 0.8 vs 0.9 * 0.75
    assert out[0].score == pytest.approx(0.8)  # no boost


@pytest.mark.parametrize(
    "settings",
    [
        _settings(enabled=False),
        _settings(freshness_enabled=False, feedback_boost_enabled=False),
    ],
)
def test_everything_off_returns_identical_chunks(
    settings: HybridRescoreSettings,
) -> None:
    chunks = [_chunk("a", 0.9, age_days=3650), _chunk("b", 0.8, boost=9)]
    out = rescore_hybrid_chunks(chunks, now=NOW, settings=settings)
    assert out == chunks
    assert all(o is c for o, c in zip(out, chunks))


# --- settings / helpers -----------------------------------------------------


def test_load_settings_reads_config_at_call_time(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(app_configs, "OPENSEARCH_HYBRID_RESCORE_ENABLED", True)
    monkeypatch.setattr(app_configs, "OPENSEARCH_RESCORE_FRESHNESS_FLOOR", 7.0)
    monkeypatch.setattr(app_configs, "OPENSEARCH_RESCORE_OVERFETCH_FACTOR", 50.0)
    monkeypatch.setattr(app_configs, "RECENCY_BIAS_MULTIPLIER", 3.0)
    monkeypatch.setattr(chat_configs, "DOC_TIME_DECAY", 0.5)
    settings = load_hybrid_rescore_settings(recency_bias_multiplier=2.0)
    assert settings.enabled
    assert settings.freshness_floor == 1.0  # clamped
    assert settings.overfetch_factor == 5.0  # clamped
    assert settings.freshness_decay_per_year == pytest.approx(0.5 * 3.0 * 2.0)


def test_default_settings_are_off() -> None:
    assert app_configs.OPENSEARCH_HYBRID_RESCORE_ENABLED is False
    assert load_hybrid_rescore_settings().any_factor_enabled is False


@pytest.mark.parametrize(
    "setting,expected",
    [
        (RecencyBiasSetting.FAVOR_RECENT, 2.0),
        (RecencyBiasSetting.BASE_DECAY, 1.0),
        (RecencyBiasSetting.AUTO, 1.0),
        (RecencyBiasSetting.NO_DECAY, 0.0),
        (None, 1.0),
    ],
)
def test_recency_setting_mapping(
    setting: RecencyBiasSetting | None, expected: float
) -> None:
    assert recency_bias_multiplier_for_setting(setting) == expected


@pytest.mark.parametrize(
    "n,factor,cap,expected",
    [
        (10, 2.0, 500, 20),
        (10, 1.0, 500, 10),
        (300, 2.0, 500, 500),
        (800, 2.0, 500, 800),
    ],
)
def test_fetch_size(n: int, factor: float, cap: int, expected: int) -> None:
    assert get_rescore_fetch_size(n, factor, cap) == expected


def test_cross_encoder_scores_unchanged_when_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(app_configs, "OPENSEARCH_HYBRID_RESCORE_ENABLED", False)
    chunks = [_chunk("a", 0.1, boost=10), _chunk("b", 0.2)]
    assert rescore_cross_encoder_scores(chunks, [0.3, 0.9], now=NOW) == [0.3, 0.9]


def test_cross_encoder_scores_rescored_when_on(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        hybrid_rescore.app_configs, "OPENSEARCH_HYBRID_RESCORE_ENABLED", True
    )
    chunks = [_chunk("a", 0.1, boost=10), _chunk("b", 0.2, age_days=3650)]
    out = rescore_cross_encoder_scores(chunks, [0.5, 0.6], now=NOW)
    assert out[0] == pytest.approx(0.5 * 1.93111, abs=1e-5)
    assert out[1] == pytest.approx(0.6 * 0.75, abs=1e-6)
