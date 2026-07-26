# Community 1021

> 12 nodes · cohesion 0.17

## Key Concepts

- **log_ratelimit_event()** (10 connections) — `backend/om/server/rate_limits/metrics.py`
- **metrics.py** (8 connections) — `backend/om/server/rate_limits/metrics.py`
- **observe_remaining_budget()** (4 connections) — `backend/om/server/rate_limits/metrics.py`
- **._publish_scope_gauges()** (4 connections) — `backend/om/server/rate_limits/service.py`
- **observe_check()** (3 connections) — `backend/om/server/rate_limits/metrics.py`
- **observe_recorded_tokens()** (2 connections) — `backend/om/server/rate_limits/metrics.py`
- **Any** (1 connections) — `backend/om/server/rate_limits/metrics.py`
- **Observability for the rate-limits subsystem: Prometheus metrics + structured eve** (1 connections) — `backend/om/server/rate_limits/metrics.py`
- **Set the per-scope remaining-budget gauge (caller passes the tightest value for t** (1 connections) — `backend/om/server/rate_limits/metrics.py`
- **Emit one OpenSearch-friendly JSON event line. Never raises.** (1 connections) — `backend/om/server/rate_limits/metrics.py`
- **Set the per-scope remaining-budget gauge to the tightest value seen for each sco** (1 connections) — `backend/om/server/rate_limits/service.py`
- **RateLimitDecision** (1 connections) — `backend/om/server/rate_limits/metrics.py`

## Relationships

- [[Community 333]] (10 shared connections)
- [[Community 405]] (4 shared connections)
- [[Community 106]] (1 shared connections)

## Source Files

- `backend/om/server/rate_limits/metrics.py`
- `backend/om/server/rate_limits/service.py`

## Audit Trail

- EXTRACTED: 25 (68%)
- INFERRED: 12 (32%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*