"""Cross-verification: our hybrid rescore vs an independent transcription of the
historical rank expression (the old chunk rank profile's global phase).

The oracle below is written from the formula only and deliberately does not
import anything from hybrid_rescore.py:

    document_boost = boost < 0 ? 0.5 + 1/(1+exp(-boost/3)) : 2/(1+exp(-boost/3))
    document_age   = max(now - updated_at (or 7_890_000 s if missing), 0) / 31_536_000
    recency_bias   = max(1 / (1 + decay * document_age), 0.75)
    final          = normalized_hybrid_score * document_boost * recency_bias
"""

import math
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from unittest.mock import MagicMock

import pytest

import om.configs.app_configs as app_configs
from om.configs.constants import DocumentSource
from om.context.search.enums import QueryType
from om.context.search.models import IndexFilters
from om.context.search.models import InferenceChunk
from om.document_index.interfaces_new import TenantState
from om.document_index.opensearch.client import SearchHit
from om.document_index.opensearch.hybrid_rescore import feedback_boost_multiplier
from om.document_index.opensearch.hybrid_rescore import freshness_multiplier
from om.document_index.opensearch.hybrid_rescore import HybridRescoreSettings
from om.document_index.opensearch.hybrid_rescore import rescore_hybrid_chunks
from om.document_index.opensearch.opensearch_document_index import (
    OpenSearchDocumentIndex,
)
from om.document_index.opensearch.schema import DocumentChunkWithoutVectors
from shared_configs.contextvars import get_current_tenant_id

TOL = 1e-6
NOW = datetime(2026, 10, 30, tzinfo=timezone.utc)


# --- independent oracle -------------------------------------------------------


def oracle_boost(boost: int) -> float:
    if boost < 0:
        return 0.5 + 1 / (1 + math.exp(-boost / 3))
    return 2 / (1 + math.exp(-boost / 3))


def oracle_recency(
    age_seconds: float | None, multiplier: float, floor: float = 0.75
) -> float:
    decay = 0.5 * multiplier
    age = max(7_890_000 if age_seconds is None else age_seconds, 0) / 31_536_000
    return max(1 / (1 + decay * age), floor)


def _days(d: float) -> float:
    return d * 86_400


def _settings(decay: float = 0.5, **kw: bool) -> HybridRescoreSettings:
    return HybridRescoreSettings(
        enabled=kw.get("enabled", True),
        freshness_enabled=kw.get("freshness", True),
        feedback_boost_enabled=kw.get("boost", True),
        freshness_decay_per_year=decay,
        freshness_floor=0.75,
        overfetch_factor=2.0,
    )


# --- factor tables (plan section 9a) ------------------------------------------


@pytest.mark.parametrize(
    "boost,expected",
    [
        (-10, 0.53445),
        (-3, 0.76894),
        (-2, 0.83924),
        (0, 1.00000),
        (2, 1.32151),
        (3, 1.46212),
        (10, 1.93111),
    ],
)
def test_boost_table(boost: int, expected: float) -> None:
    assert feedback_boost_multiplier(boost) == pytest.approx(
        oracle_boost(boost), abs=TOL
    )
    assert oracle_boost(boost) == pytest.approx(expected, abs=1e-5)


FRESHNESS_TABLE = {
    0.0: [1.00000, 1.00000, 1.00000, 1.00000],
    1.0: [1.00000, 0.96053, 0.75000, 0.75000],
    2.0: [1.00000, 0.92405, 0.75000, 0.75000],
}


@pytest.mark.parametrize("multiplier", sorted(FRESHNESS_TABLE))
@pytest.mark.parametrize("col,age_days", list(enumerate([0, 30, 365, 3650])))
def test_freshness_table(multiplier: float, col: int, age_days: int) -> None:
    ours = freshness_multiplier(
        NOW - timedelta(days=age_days), NOW, 0.5 * multiplier, 0.75
    )
    ref = oracle_recency(_days(age_days), multiplier)
    assert ours == pytest.approx(ref, abs=TOL)
    assert ref == pytest.approx(FRESHNESS_TABLE[multiplier][col], abs=1e-5)


def test_missing_date_matches_reference_exactly() -> None:
    # Decided 2026-10-30: undated docs use the reference 7_890_000 s age.
    ours = freshness_multiplier(None, NOW, 0.5, 0.75)
    assert ours == pytest.approx(oracle_recency(None, 1.0), abs=TOL)
    assert ours == pytest.approx(0.88881, abs=1e-5)


def test_edge_cases() -> None:
    future = NOW + timedelta(days=10)
    assert freshness_multiplier(future, NOW, 0.5, 0.75) == pytest.approx(
        oracle_recency(-_days(10), 1.0), abs=TOL
    )
    assert freshness_multiplier(future, NOW, 0.5, 0.75) == 1.0
    year_old = NOW - timedelta(days=365)
    assert freshness_multiplier(year_old, NOW, 0.5, 0.5) == pytest.approx(
        oracle_recency(_days(365), 1.0, floor=0.5), abs=TOL
    )
    assert oracle_recency(_days(365), 1.0, floor=0.5) == pytest.approx(
        0.66667, abs=1e-5
    )


def test_combined_case() -> None:
    ref = 0.8 * oracle_boost(2) * oracle_recency(_days(30), 1.0)
    assert ref == pytest.approx(1.01548, abs=1e-5)
    chunk = _chunk("x", 0.8, 2, 30)
    out = rescore_hybrid_chunks(
        [chunk], now=NOW, settings=_settings(), preserve_score_scale=False
    )
    assert out[0].score == pytest.approx(ref, abs=TOL)


# --- ordering -----------------------------------------------------------------

CASES = [
    ("A", 0.90, -2, 3650),
    ("B", 0.85, 0, 365),
    ("C", 0.80, 2, 30),
    ("D", 0.70, 0, 0),
]


def _chunk(doc: str, score: float, boost: int, age_days: float) -> InferenceChunk:
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
        updated_at=NOW - timedelta(days=age_days),
    )


def _oracle_products() -> dict[str, float]:
    return {
        doc: score * oracle_boost(boost) * oracle_recency(_days(age), 1.0)
        for doc, score, boost, age in CASES
    }


def test_oracle_products_and_order() -> None:
    products = _oracle_products()
    expected = {"A": 0.56649, "B": 0.63750, "C": 1.01548, "D": 0.70}
    for doc, value in expected.items():
        assert products[doc] == pytest.approx(value, abs=1e-5)
    assert sorted(products, key=products.__getitem__, reverse=True) == [
        "C",
        "D",
        "B",
        "A",
    ]


def test_rescore_matches_oracle_order_and_scores() -> None:
    chunks = [_chunk(*case) for case in CASES]
    products = _oracle_products()
    raw = rescore_hybrid_chunks(
        chunks, now=NOW, settings=_settings(), preserve_score_scale=False
    )
    assert [c.document_id for c in raw] == ["C", "D", "B", "A"]
    for c in raw:
        assert c.score == pytest.approx(products[c.document_id], abs=TOL)

    # Default mode (federated-safe): same order, oracle scores x one constant.
    scaled = rescore_hybrid_chunks(chunks, now=NOW, settings=_settings())
    assert [c.document_id for c in scaled] == ["C", "D", "B", "A"]
    ratio = 0.90 / max(products.values())
    for c in scaled:
        assert c.score == pytest.approx(products[c.document_id] * ratio, abs=TOL)


@pytest.mark.parametrize(
    "settings",
    [_settings(enabled=False), _settings(freshness=False, boost=False)],
)
def test_all_toggles_off_keeps_order(settings: HybridRescoreSettings) -> None:
    chunks = [_chunk(*case) for case in CASES]
    out = rescore_hybrid_chunks(chunks, now=NOW, settings=settings)
    assert [c.document_id for c in out] == ["A", "B", "C", "D"]
    assert [c.score for c in out] == [0.90, 0.85, 0.80, 0.70]


# --- through the index (mocked client) -----------------------------------------


def _index_with_cases() -> OpenSearchDocumentIndex:
    tenant = TenantState(tenant_id=get_current_tenant_id(), multitenant=False)
    now = datetime.now(timezone.utc)
    hits = [
        SearchHit(
            document_chunk=DocumentChunkWithoutVectors(
                document_id=doc,
                chunk_index=0,
                title=doc,
                chunk_text="t",
                source_type="file",
                updated_at=now - timedelta(days=age),
                is_public=True,
                access_control_list=[],
                boost=boost,
                display_name=doc,
                snippet="s",
                document_summary="",
                contextual_summary="",
                tenant_id=tenant,
            ),
            score=score,
        )
        for doc, score, boost, age in CASES
    ]
    index = object.__new__(OpenSearchDocumentIndex)
    index._index_name = "parity"
    index._tenant_state = tenant
    index._client = MagicMock()
    index._client.search.return_value = hits
    return index


@pytest.mark.parametrize("enabled", [True, False])
def test_order_through_hybrid_retrieval(
    monkeypatch: pytest.MonkeyPatch, enabled: bool
) -> None:
    monkeypatch.setattr(app_configs, "OPENSEARCH_HYBRID_RESCORE_ENABLED", enabled)
    index = _index_with_cases()
    out = index.hybrid_retrieval(
        "q",
        [0.1, 0.2],
        None,
        QueryType.SEMANTIC,
        IndexFilters(access_control_list=None),
        4,
    )
    size = index._client.search.call_args.kwargs["body"]["size"]
    if enabled:
        assert [c.document_id for c in out] == ["C", "D", "B", "A"]
        assert size == 8
        products = _oracle_products()
        ratio = 0.90 / max(products.values())
        for c in out:
            assert c.score == pytest.approx(products[c.document_id] * ratio, abs=1e-5)
    else:
        assert [c.document_id for c in out] == ["A", "B", "C", "D"]
        assert size == 4
        assert [c.score for c in out] == [0.90, 0.85, 0.80, 0.70]
