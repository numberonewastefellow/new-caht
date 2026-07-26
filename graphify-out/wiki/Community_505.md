# Community 505

> 30 nodes · cohesion 0.11

## Key Concepts

- **lifespan()** (16 connections) — `backend/om/main.py`
- **main.py** (15 connections) — `backend/om/main.py`
- **get_application()** (14 connections) — `backend/om/main.py`
- **FastAPI** (12 connections) — `backend/om/main.py`
- **include_auth_router_with_prefix()** (7 connections) — `backend/om/main.py`
- **include_router_with_global_prefix_prepended()** (7 connections) — `backend/om/main.py`
- **check_router_auth()** (6 connections) — `backend/om/server/auth_check.py`
- **auth_check.py** (5 connections) — `backend/om/server/auth_check.py`
- **add_latency_logging_middleware()** (4 connections) — `backend/om/server/middleware/latency_logging.py`
- **rate_limiting.py** (4 connections) — `backend/om/server/middleware/rate_limiting.py`
- **use_route_function_names_as_operation_ids()** (4 connections) — `backend/om/main.py`
- **check_ee_router_auth()** (4 connections) — `backend/om/server/auth_check.py`
- **FastAPI** (3 connections) — `backend/om/server/auth_check.py`
- **setup_auth_limiter()** (3 connections) — `backend/om/server/middleware/rate_limiting.py`
- **is_route_in_spec_list()** (3 connections) — `backend/om/server/auth_check.py`
- **FastAPI** (2 connections) — `backend/om/server/middleware/latency_logging.py`
- **latency_logging.py** (2 connections) — `backend/om/server/middleware/latency_logging.py`
- **close_auth_limiter()** (2 connections) — `backend/om/server/middleware/rate_limiting.py`
- **get_auth_rate_limiters()** (2 connections) — `backend/om/server/middleware/rate_limiting.py`
- **rate_limit_key()** (2 connections) — `backend/om/server/middleware/rate_limiting.py`
- **LoggerAdapter** (1 connections) — `backend/om/server/middleware/latency_logging.py`
- **Request** (1 connections) — `backend/om/server/middleware/rate_limiting.py`
- **BaseRoute** (1 connections) — `backend/om/server/auth_check.py`
- **OpenAPI generation defaults to naming the operation with the     function + rou** (1 connections) — `backend/om/main.py`
- **Adds the global prefix to all routes in the router.** (1 connections) — `backend/om/main.py`
- *... and 5 more nodes in this community*

## Relationships

- [[Community 70]] (12 shared connections)
- [[Community 85]] (3 shared connections)
- [[Community 91]] (2 shared connections)
- [[Community 743]] (2 shared connections)
- [[Community 73]] (2 shared connections)
- [[Community 119]] (1 shared connections)
- [[Community 148]] (1 shared connections)
- [[Community 161]] (1 shared connections)
- [[Community 1316]] (1 shared connections)
- [[Community 643]] (1 shared connections)
- [[Community 549]] (1 shared connections)
- [[Backend Agent/API Test Fixtures]] (1 shared connections)

## Source Files

- `backend/om/main.py`
- `backend/om/server/auth_check.py`
- `backend/om/server/middleware/latency_logging.py`
- `backend/om/server/middleware/rate_limiting.py`

## Audit Trail

- EXTRACTED: 94 (74%)
- INFERRED: 33 (26%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*