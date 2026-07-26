# Community 1062

> 12 nodes · cohesion 0.21

## Key Concepts

- **test_pool_metrics.py** (12 connections) — `backend/tests/unit/om/server/test_pool_metrics.py`
- **_make_conn_record()** (5 connections) — `backend/tests/unit/om/server/test_pool_metrics.py`
- **test_checkin_event_observes_hold_duration()** (4 connections) — `backend/tests/unit/om/server/test_pool_metrics.py`
- **test_checkin_with_missing_endpoint_uses_unknown()** (4 connections) — `backend/tests/unit/om/server/test_pool_metrics.py`
- **test_checkout_event_stores_endpoint_and_increments_gauge()** (4 connections) — `backend/tests/unit/om/server/test_pool_metrics.py`
- **test_build_route_map_extracts_api_routes()** (3 connections) — `backend/tests/unit/om/server/test_pool_metrics.py`
- **Unit tests for SQLAlchemy connection pool Prometheus metrics.** (1 connections) — `backend/tests/unit/om/server/test_pool_metrics.py`
- **Verify checkin event reads endpoint from conn_record and observes hold time.** (1 connections) — `backend/tests/unit/om/server/test_pool_metrics.py`
- **Verify checkin gracefully handles missing endpoint info.** (1 connections) — `backend/tests/unit/om/server/test_pool_metrics.py`
- **Verify _build_route_map extracts APIRoute path regexes.** (1 connections) — `backend/tests/unit/om/server/test_pool_metrics.py`
- **Create a mock connection record with an info dict.** (1 connections) — `backend/tests/unit/om/server/test_pool_metrics.py`
- **Verify checkout event stores handler on conn_record and increments metrics.** (1 connections) — `backend/tests/unit/om/server/test_pool_metrics.py`

## Relationships

- [[Community 743]] (4 shared connections)
- [[Community 1131]] (4 shared connections)
- [[Community 974]] (2 shared connections)

## Source Files

- `backend/tests/unit/om/server/test_pool_metrics.py`

## Audit Trail

- EXTRACTED: 34 (89%)
- INFERRED: 4 (11%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*