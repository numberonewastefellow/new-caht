"""Pytest fixtures for the search baseline suite.

These are *integration* tests: they require the dev stack (Postgres + OpenSearch
+ model server) to be running. Fixtures initialize the SQL engine, verify the
required services are reachable (skipping the suite otherwise), and seed the
fixed corpus once per session.
"""

from collections.abc import Iterator

import httpx
import pytest
from sqlalchemy.orm import Session

from om.db.engine.sql_engine import get_session_with_current_tenant
from om.db.engine.sql_engine import SqlEngine
from om.db.search_settings import get_current_search_settings
from shared_configs.configs import MODEL_SERVER_HOST
from shared_configs.configs import MODEL_SERVER_PORT
from tests.search_baseline.seed_search_corpus import seed_corpus


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "llm: tests that require a configured LLM provider (non-deterministic).",
    )


@pytest.fixture(scope="session", autouse=True)
def _init_sql_engine() -> None:
    try:
        SqlEngine.init_engine(pool_size=5, max_overflow=5)
    except Exception:
        # Already initialized (or cannot be); downstream fixtures surface errors.
        pass


def _service_up(url: str) -> bool:
    try:
        resp = httpx.get(url, timeout=5.0)
        return resp.status_code < 500
    except Exception:
        return False


@pytest.fixture
def db_session() -> Iterator[Session]:
    with get_session_with_current_tenant() as session:
        yield session


# --------------------------------------------------------------------------- #
# OpenSearch fixtures
# --------------------------------------------------------------------------- #


def _opensearch_up() -> bool:
    try:
        from om.document_index.opensearch.client import OpenSearchIndexClient

        with get_session_with_current_tenant() as session:
            index_name = get_current_search_settings(session).index_name
        return OpenSearchIndexClient(index_name=index_name).ping()
    except Exception:
        return False


@pytest.fixture(scope="session")
def require_opensearch() -> None:
    """Skip if OpenSearch or the model server are unreachable."""
    if not _service_up(f"http://{MODEL_SERVER_HOST}:{MODEL_SERVER_PORT}/health"):
        pytest.skip(
            f"Model server not reachable at {MODEL_SERVER_HOST}:{MODEL_SERVER_PORT}"
        )
    if not _opensearch_up():
        pytest.skip("OpenSearch not reachable")


@pytest.fixture(scope="session")
def seeded_corpus_opensearch(require_opensearch: None) -> None:
    """Seed the fixed corpus into OpenSearch once per session (idempotent upsert)."""
    from tests.search_baseline.harness import refresh_opensearch

    with get_session_with_current_tenant() as session:
        count = seed_corpus(session, engine="opensearch")
        refresh_opensearch(session)
    print(f"\n[seeded_corpus_opensearch] indexed {count} corpus documents")
