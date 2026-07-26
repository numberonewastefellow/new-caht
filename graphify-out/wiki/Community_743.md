# Community 743

> 19 nodes · cohesion 0.16

## Key Concepts

- **middleware.py** (11 connections) — `backend/om/utils/middleware.py`
- **_build_route_map()** (9 connections) — `backend/om/utils/middleware.py`
- **_match_route()** (6 connections) — `backend/om/utils/middleware.py`
- **FastAPI** (5 connections) — `backend/om/utils/middleware.py`
- **add_endpoint_context_middleware()** (5 connections) — `backend/om/utils/middleware.py`
- **add_onyx_request_id_middleware()** (5 connections) — `backend/om/utils/middleware.py`
- **test_match_route_exact_paths()** (4 connections) — `backend/tests/unit/om/server/test_pool_metrics.py`
- **test_match_route_resolves_parameterized_paths()** (4 connections) — `backend/tests/unit/om/server/test_pool_metrics.py`
- **test_match_route_returns_none_for_unknown_paths()** (4 connections) — `backend/tests/unit/om/server/test_pool_metrics.py`
- **add_onyx_tenant_id_middleware()** (4 connections) — `backend/om/utils/middleware.py`
- **LoggerAdapter** (2 connections) — `backend/om/utils/middleware.py`
- **Pattern** (2 connections) — `backend/om/utils/middleware.py`
- **Verify _match_route resolves /api/items/abc-123 to /api/items/{item_id}.** (1 connections) — `backend/tests/unit/om/server/test_pool_metrics.py`
- **Verify _match_route returns None for paths not in the route map.** (1 connections) — `backend/tests/unit/om/server/test_pool_metrics.py`
- **Verify _match_route handles exact (non-parameterized) paths.** (1 connections) — `backend/tests/unit/om/server/test_pool_metrics.py`
- **Set CURRENT_ENDPOINT_CONTEXTVAR so Prometheus pool metrics can     attribute DB** (1 connections) — `backend/om/utils/middleware.py`
- **# NOTE: possible we'll want more input bytes if id's aren't unique enough** (1 connections) — `backend/om/utils/middleware.py`
- **Build a list of (compiled regex, route template) from the app's routes.      Use** (1 connections) — `backend/om/utils/middleware.py`
- **Match a request path against the route map and return the template.** (1 connections) — `backend/om/utils/middleware.py`

## Relationships

- [[Community 1062]] (4 shared connections)
- [[Community 1533]] (3 shared connections)
- [[Community 505]] (2 shared connections)
- [[Community 807]] (2 shared connections)
- [[Community 161]] (1 shared connections)

## Source Files

- `backend/om/utils/middleware.py`
- `backend/tests/unit/om/server/test_pool_metrics.py`

## Audit Trail

- EXTRACTED: 51 (75%)
- INFERRED: 17 (25%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*