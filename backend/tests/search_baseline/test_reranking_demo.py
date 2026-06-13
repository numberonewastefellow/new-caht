"""End-to-end test of the full reranking pipeline (marked `llm`).

Runs the layer-by-layer demonstration (`demonstrate`) for a sports query against the
two-domain `index_rest` data and asserts the relevant document survives the LLM
relevance-selection layer. This exercises query expansion + per-query Vespa ranking +
weighted RRF fusion + LLM section selection + per-section context classification.

Marked `llm` because it makes real LLM calls (non-deterministic); skipped unless a
default LLM provider is configured and run with the `llm` marker.

Run inside the backend container:
    INDEX_REST_DIR=/app/index_rest python -m pytest tests/search_baseline/test_reranking_demo.py -v -s -rs
"""

import os

import pytest
from sqlalchemy.orm import Session

from onyx.db.engine.sql_engine import get_session_with_current_tenant
from onyx.db.engine.sql_engine import SqlEngine
from tests.search_baseline.demo_reranking_layers import demonstrate
from tests.search_baseline.ingest_index_rest import ingest


@pytest.fixture(scope="module", autouse=True)
def _ensure_two_domain_corpus() -> None:
    try:
        SqlEngine.init_engine(pool_size=5, max_overflow=5)
    except Exception:
        pass
    index_dir = os.environ.get("INDEX_REST_DIR", "/app/index_rest")
    if not os.path.isdir(index_dir):
        pytest.skip(f"index_rest data dir not found: {index_dir}")
    with get_session_with_current_tenant() as db_session:
        ingest(index_dir)


@pytest.fixture
def db_session() -> Session:
    with get_session_with_current_tenant() as session:
        yield session


@pytest.mark.llm
def test_reranking_pipeline_sports_query(db_session: Session) -> None:
    try:
        from onyx.llm.factory import get_default_llm

        llm = get_default_llm()
    except Exception as e:  # pragma: no cover - depends on env config
        pytest.skip(f"No default LLM available: {e}")

    result = demonstrate(
        "Will Vinicius shine for Brazil at the 2026 World Cup?",
        llm=llm,
        db_session=db_session,
    )

    # The football article must survive RRF fusion AND the LLM relevance selection.
    assert "index_rest::foot_bal" in result["fused_top_ids"], result["fused_top_ids"]
    assert "index_rest::foot_bal" in result["selected_doc_ids"], result["selected_doc_ids"]
    # The LLM must not classify the clearly-relevant football doc as NOT_RELEVANT.
    assert result["classifications"].get("index_rest::foot_bal") != "not_relevant"
