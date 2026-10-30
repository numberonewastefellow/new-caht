"""OpenSearchDocumentIndex.hybrid_retrieval with the hybrid rescore switch.

The OpenSearch client is mocked; no cluster needed.
"""

import json
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from typing import Any
from unittest.mock import MagicMock

import pytest

import om.configs.app_configs as app_configs
import om.context.search.rerank as rerank_module
from om.context.search.enums import QueryType
from om.context.search.models import IndexFilters
from om.context.search.models import InferenceChunk
from om.context.search.retrieval.search_runner import combine_retrieval_results
from om.document_index.chunk_content_enrichment import cleanup_content_for_chunks
from om.document_index.interfaces_new import TenantState
from om.document_index.opensearch import opensearch_document_index as osdi
from om.document_index.opensearch.client import SearchHit
from om.document_index.opensearch.opensearch_document_index import (
    OpenSearchDocumentIndex,
)
from om.document_index.opensearch.opensearch_document_index import (
    OpenSearchIndexPair,
)
from om.document_index.opensearch.schema import DocumentChunkWithoutVectors
from om.document_index.opensearch.search import DocumentQuery
from om.document_index.opensearch.search import (
    get_normalization_pipeline_name_and_config,
)
from shared_configs.contextvars import get_current_tenant_id

TENANT = TenantState(tenant_id=get_current_tenant_id(), multitenant=False)
FILTERS = IndexFilters(access_control_list=None)
EMBEDDING = [0.1, 0.2, 0.3, 0.4]
NOW = datetime.now(timezone.utc)


def _doc_chunk(
    doc: str, boost: int = 0, age_days: float | None = 0
) -> DocumentChunkWithoutVectors:
    return DocumentChunkWithoutVectors(
        document_id=doc,
        chunk_index=0,
        title=f"title {doc}",
        chunk_text=f"text of {doc}",
        source_type="file",
        updated_at=(
            None
            if age_days is None
            else (NOW - timedelta(days=age_days)).replace(microsecond=0)
        ),
        is_public=True,
        access_control_list=[],
        boost=boost,
        display_name=doc,
        snippet=f"snippet {doc}",
        document_summary="",
        contextual_summary="",
        tenant_id=TENANT,
    )


# Base scores 0.90 / 0.85 / 0.80 / 0.70 with (boost, age_days):
# A (-2, 3650), B (0, 365), C (+2, 30), D (0, 0) -> rescored order C, D, B, A.
HITS = [
    SearchHit(document_chunk=_doc_chunk("A", -2, 3650), score=0.90),
    SearchHit(document_chunk=_doc_chunk("B", 0, 365), score=0.85),
    SearchHit(document_chunk=_doc_chunk("C", 2, 30), score=0.80),
    SearchHit(document_chunk=_doc_chunk("D", 0, 0), score=0.70),
]


def _index(hits: list[SearchHit]) -> OpenSearchDocumentIndex:
    index = object.__new__(OpenSearchDocumentIndex)
    index._index_name = "test_index"
    index._tenant_state = TENANT
    index._client = MagicMock()
    index._client.search.return_value = hits
    return index


def _retrieve(
    index: OpenSearchDocumentIndex | OpenSearchIndexPair, n: int = 4, **kwargs: Any
) -> list[InferenceChunk]:
    return index.hybrid_retrieval(
        "query", EMBEDDING, None, QueryType.SEMANTIC, FILTERS, n, **kwargs
    )


def _search_kwargs(index: OpenSearchDocumentIndex) -> dict[str, Any]:
    return index._client.search.call_args.kwargs


def _dump(chunks: list[InferenceChunk]) -> str:
    return json.dumps([c.model_dump(mode="json") for c in chunks], sort_keys=True)


@pytest.fixture
def rescore_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app_configs, "OPENSEARCH_HYBRID_RESCORE_ENABLED", True)


@pytest.fixture
def rescore_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app_configs, "OPENSEARCH_HYBRID_RESCORE_ENABLED", False)


# --- switch off: byte-identical to the previous implementation ---------------


@pytest.mark.usefixtures("rescore_off")
@pytest.mark.parametrize("multiplier", [1.0, 0.0, 2.0])
def test_flag_off_is_byte_identical(multiplier: float) -> None:
    index = _index(HITS)
    out = _retrieve(index, n=4, recency_bias_multiplier=multiplier)

    # Exactly what the pre-rescore implementation produced.
    expected_body = DocumentQuery.get_hybrid_search_query(
        query_text="query",
        query_vector=EMBEDDING,
        num_hits=4,
        tenant_state=TENANT,
        index_filters=FILTERS,
        include_hidden=False,
    )
    expected_chunks = cleanup_content_for_chunks(
        [
            osdi._convert_retrieved_opensearch_chunk_to_inference_chunk_uncleaned(
                hit.document_chunk, hit.score, hit.match_highlights
            )
            for hit in HITS
        ]
    )
    kwargs = _search_kwargs(index)
    assert json.dumps(kwargs["body"], sort_keys=True) == json.dumps(
        expected_body, sort_keys=True
    )
    assert (
        kwargs["search_pipeline_id"] == get_normalization_pipeline_name_and_config()[0]
    )
    assert _dump(out) == _dump(expected_chunks)
    assert [c.document_id for c in out] == ["A", "B", "C", "D"]


# --- switch on ----------------------------------------------------------------


@pytest.mark.usefixtures("rescore_on")
def test_flag_on_overfetches_rescores_and_truncates() -> None:
    index = _index(HITS)
    out = _retrieve(index, n=3)
    assert _search_kwargs(index)["body"]["size"] == 6  # ceil(3 * 2.0)
    assert [c.document_id for c in out] == ["C", "D", "B"]


@pytest.mark.usefixtures("rescore_on")
def test_flag_on_full_order_and_scale_preserved() -> None:
    out = _retrieve(_index(HITS), n=4)
    assert [c.document_id for c in out] == ["C", "D", "B", "A"]
    # Batch max is kept at the original max (0.90) for the federated merge.
    assert out[0].score == pytest.approx(0.90)


@pytest.mark.usefixtures("rescore_on")
def test_overfetch_capped_and_never_below_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(osdi, "DEFAULT_NUM_HYBRID_SUBQUERY_CANDIDATES", 5)
    index = _index(HITS)
    _retrieve(index, n=4)
    assert _search_kwargs(index)["body"]["size"] == 5
    index = _index(HITS)
    _retrieve(index, n=8)
    assert _search_kwargs(index)["body"]["size"] == 8


@pytest.mark.usefixtures("rescore_on")
def test_no_decay_agent_ignores_age() -> None:
    # Freshness off via the per-agent multiplier: only boost applies.
    # A 0.9*0.839=0.755, B 0.85, C 0.8*1.3215=1.057, D 0.70 -> C, B, A, D
    out = _retrieve(_index(HITS), n=4, recency_bias_multiplier=0.0)
    assert [c.document_id for c in out] == ["C", "B", "A", "D"]


@pytest.mark.usefixtures("rescore_on")
def test_index_pair_delegates_multiplier() -> None:
    primary = _index(HITS)
    pair = object.__new__(OpenSearchIndexPair)
    pair._primary = primary
    out = _retrieve(pair, n=4, recency_bias_multiplier=0.0)
    assert [c.document_id for c in out] == ["C", "B", "A", "D"]


@pytest.mark.usefixtures("rescore_on")
def test_sub_toggles_all_off_keeps_original(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app_configs, "OPENSEARCH_RESCORE_FRESHNESS_ENABLED", False)
    monkeypatch.setattr(app_configs, "OPENSEARCH_RESCORE_FEEDBACK_BOOST_ENABLED", False)
    index = _index(HITS)
    out = _retrieve(index, n=4)
    assert _search_kwargs(index)["body"]["size"] == 4
    assert [c.document_id for c in out] == ["A", "B", "C", "D"]


# --- admin paths untouched ----------------------------------------------------


@pytest.mark.parametrize("enabled", [False, True])
def test_keyword_and_random_retrieval_not_rescored(
    monkeypatch: pytest.MonkeyPatch, enabled: bool
) -> None:
    monkeypatch.setattr(app_configs, "OPENSEARCH_HYBRID_RESCORE_ENABLED", enabled)
    index = _index(HITS)
    keyword = index.keyword_retrieval("query", FILTERS, 4)
    assert _search_kwargs(index)["body"]["size"] == 4
    random_hits = index.random_retrieval(FILTERS, 4)
    assert [c.document_id for c in keyword] == ["A", "B", "C", "D"]
    assert [c.document_id for c in random_hits] == ["A", "B", "C", "D"]
    assert [c.score for c in keyword] == [0.90, 0.85, 0.80, 0.70]


# --- federated merge ----------------------------------------------------------


@pytest.mark.usefixtures("rescore_on")
def test_federated_not_crowded_out() -> None:
    ours = _retrieve(_index(HITS), n=4)
    federated = ours[0].model_copy(
        update={"document_id": "slack-1", "score": 0.95, "is_federated": True}
    )
    merged = combine_retrieval_results([ours, [federated]])
    # Our boosted top hit (raw product 1.015) was rescaled to 0.90, so the
    # 0.95 federated hit still ranks first, as it would without the rescore.
    assert merged[0].document_id == "slack-1"
    assert [c.document_id for c in merged[1:]] == ["C", "D", "B", "A"]


# --- cross-encoder rerank -----------------------------------------------------


def _reranked_order(monkeypatch: pytest.MonkeyPatch, enabled: bool) -> list[str]:
    monkeypatch.setattr(app_configs, "OPENSEARCH_HYBRID_RESCORE_ENABLED", enabled)
    monkeypatch.setattr(rerank_module, "RERANK_ENABLED", True)
    model = MagicMock()
    # Cross-encoder prefers A slightly; A is old and down-voted, C is boosted.
    model.predict.return_value = [0.62, 0.55, 0.50, 0.40]
    monkeypatch.setattr(rerank_module, "RerankingModel", MagicMock(return_value=model))
    chunks = cleanup_content_for_chunks(
        [
            osdi._convert_retrieved_opensearch_chunk_to_inference_chunk_uncleaned(
                hit.document_chunk, hit.score, hit.match_highlights
            )
            for hit in HITS
        ]
    )
    reranked, applied = rerank_module.rerank_chunks_with_status("query", chunks)
    assert applied
    return [c.document_id for c in reranked]


def test_rerank_unchanged_when_flag_off(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _reranked_order(monkeypatch, enabled=False) == ["A", "B", "C", "D"]


def test_rerank_applies_factors_when_flag_on(monkeypatch: pytest.MonkeyPatch) -> None:
    # A 0.62*0.839*0.75=0.390, B 0.55*0.75=0.4125, C 0.50*1.3215*0.9605=0.635,
    # D 0.40 -> C, B, D, A
    assert _reranked_order(monkeypatch, enabled=True) == ["C", "B", "D", "A"]
