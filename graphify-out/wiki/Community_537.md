# Community 537

> 28 nodes · cohesion 0.11

## Key Concepts

- **RateLimitRepository** (19 connections) — `backend/om/server/rate_limits/repository.py`
- **_hour_bucket()** (7 connections) — `backend/om/server/rate_limits/repository.py`
- **RateLimitPolicy** (5 connections) — `backend/om/server/rate_limits/repository.py`
- **RateLimitScope** (5 connections) — `backend/om/server/rate_limits/repository.py`
- **repository.py** (5 connections) — `backend/om/server/rate_limits/repository.py`
- **.create_policy()** (5 connections) — `backend/om/server/rate_limits/repository.py`
- **.fetch_history()** (5 connections) — `backend/om/server/rate_limits/repository.py`
- **.increment_usage()** (5 connections) — `backend/om/server/rate_limits/repository.py`
- **.list_enabled_for_subjects()** (4 connections) — `backend/om/server/rate_limits/repository.py`
- **.sum_recent_tokens()** (4 connections) — `backend/om/server/rate_limits/repository.py`
- **datetime** (3 connections) — `backend/om/server/rate_limits/repository.py`
- **UUID** (3 connections) — `backend/om/server/rate_limits/repository.py`
- **.list_policies()** (3 connections) — `backend/om/server/rate_limits/repository.py`
- **.update_policy()** (3 connections) — `backend/om/server/rate_limits/repository.py`
- **.get_policy()** (2 connections) — `backend/om/server/rate_limits/repository.py`
- **.__init__()** (2 connections) — `backend/om/server/rate_limits/repository.py`
- **test_hour_bucket_truncates_to_utc_hour()** (2 connections) — `backend/tests/unit/om/server/rate_limits/test_rate_limit_engine.py`
- **RateLimitAlgorithm** (2 connections) — `backend/om/server/rate_limits/repository.py`
- **RateLimitUsage** (1 connections) — `backend/om/server/rate_limits/repository.py`
- **Session** (1 connections) — `backend/om/server/rate_limits/repository.py`
- **.any_enabled_policy_exists()** (1 connections) — `backend/om/server/rate_limits/repository.py`
- **.delete_policy()** (1 connections) — `backend/om/server/rate_limits/repository.py`
- **Persistence for rate-limit policies + the durable usage roll-up.  Kept as a th** (1 connections) — `backend/om/server/rate_limits/repository.py`
- **Atomically add to the current hour's roll-up row (UPSERT; no read-modify-write r** (1 connections) — `backend/om/server/rate_limits/repository.py`
- **Total tokens recorded for a subject over the last ``period_hours`` (roll-up).** (1 connections) — `backend/om/server/rate_limits/repository.py`
- *... and 3 more nodes in this community*

## Relationships

- [[Community 405]] (5 shared connections)
- [[Phoenix Annotation Mutations]] (1 shared connections)
- [[Community 333]] (1 shared connections)
- [[Community 685]] (1 shared connections)

## Source Files

- `backend/om/server/rate_limits/repository.py`
- `backend/tests/unit/om/server/rate_limits/test_rate_limit_engine.py`

## Audit Trail

- EXTRACTED: 85 (90%)
- INFERRED: 9 (10%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*