# Community 643

> 23 nodes · cohesion 0.11

## Key Concepts

- **test_prometheus_instrumentation.py** (8 connections) — `backend/tests/unit/om/server/test_prometheus_instrumentation.py`
- **slow_request_callback()** (6 connections) — `backend/om/server/metrics/slow_requests.py`
- **_make_info()** (6 connections) — `backend/tests/unit/om/server/test_prometheus_instrumentation.py`
- **setup_prometheus_metrics()** (5 connections) — `backend/om/server/metrics/prometheus_setup.py`
- **test_slow_request_callback_increments_above_threshold()** (3 connections) — `backend/tests/unit/om/server/test_prometheus_instrumentation.py`
- **test_slow_request_callback_skips_at_exact_threshold()** (3 connections) — `backend/tests/unit/om/server/test_prometheus_instrumentation.py`
- **test_slow_request_callback_skips_below_threshold()** (3 connections) — `backend/tests/unit/om/server/test_prometheus_instrumentation.py`
- **prometheus_setup.py** (2 connections) — `backend/om/server/metrics/prometheus_setup.py`
- **slow_requests.py** (2 connections) — `backend/om/server/metrics/slow_requests.py`
- **test_inprogress_gauge_increments_during_request()** (2 connections) — `backend/tests/unit/om/server/test_prometheus_instrumentation.py`
- **test_inprogress_gauge_tracks_concurrent_requests()** (2 connections) — `backend/tests/unit/om/server/test_prometheus_instrumentation.py`
- **test_setup_attaches_instrumentator_to_app()** (2 connections) — `backend/tests/unit/om/server/test_prometheus_instrumentation.py`
- **Info** (1 connections) — `backend/om/server/metrics/slow_requests.py`
- **Any** (1 connections) — `backend/tests/unit/om/server/test_prometheus_instrumentation.py`
- **Prometheus metrics setup for the VertualAi API server.  Orchestrates HTTP reques** (1 connections) — `backend/om/server/metrics/prometheus_setup.py`
- **Initialize HTTP request metrics for the VertualAi API server.      Must be calle** (1 connections) — `backend/om/server/metrics/prometheus_setup.py`
- **Slow request counter metric.  Increments a counter whenever a request exceeds a** (1 connections) — `backend/om/server/metrics/slow_requests.py`
- **Increment slow request counter when duration exceeds threshold.** (1 connections) — `backend/om/server/metrics/slow_requests.py`
- **Unit tests for Prometheus instrumentation module.** (1 connections) — `backend/tests/unit/om/server/test_prometheus_instrumentation.py`
- **Verify the in-progress gauge goes up while a request is in flight.** (1 connections) — `backend/tests/unit/om/server/test_prometheus_instrumentation.py`
- **Verify the gauge correctly counts multiple concurrent in-flight requests.** (1 connections) — `backend/tests/unit/om/server/test_prometheus_instrumentation.py`
- **Build a fake metrics Info object matching the instrumentator's Info shape.** (1 connections) — `backend/tests/unit/om/server/test_prometheus_instrumentation.py`
- **Starlette** (1 connections) — `backend/om/server/metrics/prometheus_setup.py`

## Relationships

- [[Community 505]] (1 shared connections)

## Source Files

- `backend/om/server/metrics/prometheus_setup.py`
- `backend/om/server/metrics/slow_requests.py`
- `backend/tests/unit/om/server/test_prometheus_instrumentation.py`

## Audit Trail

- EXTRACTED: 46 (84%)
- INFERRED: 9 (16%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*