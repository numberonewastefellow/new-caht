# Community 818

> 17 nodes · cohesion 0.18

## Key Concepts

- **test_rest_client_context_caching.py** (8 connections) — `backend/tests/unit/om/connectors/sharepoint/test_rest_client_context_caching.py`
- **_make_connector()** (7 connections) — `backend/tests/unit/om/connectors/sharepoint/test_rest_client_context_caching.py`
- **_noop_load_credentials()** (7 connections) — `backend/tests/unit/om/connectors/sharepoint/test_rest_client_context_caching.py`
- **test_load_credentials_called_on_rebuild()** (4 connections) — `backend/tests/unit/om/connectors/sharepoint/test_rest_client_context_caching.py`
- **test_rebuilds_context_after_max_age()** (4 connections) — `backend/tests/unit/om/connectors/sharepoint/test_rest_client_context_caching.py`
- **test_rebuilds_context_on_site_change()** (4 connections) — `backend/tests/unit/om/connectors/sharepoint/test_rest_client_context_caching.py`
- **test_returns_cached_context_within_max_age()** (4 connections) — `backend/tests/unit/om/connectors/sharepoint/test_rest_client_context_caching.py`
- **SharepointConnector** (2 connections) — `backend/tests/unit/om/connectors/sharepoint/test_rest_client_context_caching.py`
- **_fresh_client_context()** (2 connections) — `backend/tests/unit/om/connectors/sharepoint/test_rest_client_context_caching.py`
- **Unit tests for SharepointConnector._create_rest_client_context caching.** (1 connections) — `backend/tests/unit/om/connectors/sharepoint/test_rest_client_context_caching.py`
- **load_credentials is called every time the context is rebuilt.** (1 connections) — `backend/tests/unit/om/connectors/sharepoint/test_rest_client_context_caching.py`
- **Return a SharepointConnector with minimal credentials wired up.** (1 connections) — `backend/tests/unit/om/connectors/sharepoint/test_rest_client_context_caching.py`
- **Patch load_credentials to just swap in a fresh MagicMock for msal_app.** (1 connections) — `backend/tests/unit/om/connectors/sharepoint/test_rest_client_context_caching.py`
- **Return a MagicMock for ClientContext that produces a distinct object per call.** (1 connections) — `backend/tests/unit/om/connectors/sharepoint/test_rest_client_context_caching.py`
- **Repeated calls with the same site_url within the TTL return the same object.** (1 connections) — `backend/tests/unit/om/connectors/sharepoint/test_rest_client_context_caching.py`
- **After _REST_CTX_MAX_AGE_S the cached context is replaced.** (1 connections) — `backend/tests/unit/om/connectors/sharepoint/test_rest_client_context_caching.py`
- **Switching to a different site_url forces a new context.** (1 connections) — `backend/tests/unit/om/connectors/sharepoint/test_rest_client_context_caching.py`

## Relationships

- No strong cross-community connections detected

## Source Files

- `backend/tests/unit/om/connectors/sharepoint/test_rest_client_context_caching.py`

## Audit Trail

- EXTRACTED: 50 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*