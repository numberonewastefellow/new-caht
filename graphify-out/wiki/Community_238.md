# Community 238

> 57 nodes · cohesion 0.07

## Key Concepts

- **BruteForceLoginRateLimiter** (19 connections) — `phoenix/src/phoenix/server/rate_limiters.py`
- **test_rate_limiters.py** (15 connections) — `phoenix/tests/unit/server/test_rate_limiters.py`
- **ServerRateLimiter** (14 connections) — `phoenix/src/phoenix/server/rate_limiters.py`
- **freeze_time()** (14 connections) — `phoenix/tests/unit/server/test_rate_limiters.py`
- **rate_limiters.py** (11 connections) — `phoenix/src/phoenix/server/rate_limiters.py`
- **TokenBucket** (11 connections) — `phoenix/src/phoenix/server/rate_limiters.py`
- **PhoenixException** (10 connections)
- **._cleanup_expired()** (7 connections) — `phoenix/src/phoenix/server/rate_limiters.py`
- **._fetch_record()** (6 connections) — `phoenix/src/phoenix/server/rate_limiters.py`
- **fastapi_ip_rate_limiter()** (6 connections) — `phoenix/src/phoenix/server/rate_limiters.py`
- **._cleanup_expired_limiters()** (6 connections) — `phoenix/src/phoenix/server/rate_limiters.py`
- **._active_partition_indices()** (5 connections) — `phoenix/src/phoenix/server/rate_limiters.py`
- **._current_partition_index()** (5 connections) — `phoenix/src/phoenix/server/rate_limiters.py`
- **._fetch_token_bucket()** (5 connections) — `phoenix/src/phoenix/server/rate_limiters.py`
- **.make_request()** (5 connections) — `phoenix/src/phoenix/server/rate_limiters.py`
- **._inactive_partition_indices()** (4 connections) — `phoenix/src/phoenix/server/rate_limiters.py`
- **fastapi_route_rate_limiter()** (4 connections) — `phoenix/src/phoenix/server/rate_limiters.py`
- **._reset_rate_limiters()** (4 connections) — `phoenix/src/phoenix/server/rate_limiters.py`
- **.make_request_if_ready()** (4 connections) — `phoenix/src/phoenix/server/rate_limiters.py`
- **.check()** (3 connections) — `phoenix/src/phoenix/server/rate_limiters.py`
- **.record_failure()** (3 connections) — `phoenix/src/phoenix/server/rate_limiters.py`
- **._reset_partitions()** (3 connections) — `phoenix/src/phoenix/server/rate_limiters.py`
- **_LoginAttemptRecord** (3 connections) — `phoenix/src/phoenix/server/rate_limiters.py`
- **.available_tokens()** (3 connections) — `phoenix/src/phoenix/server/rate_limiters.py`
- **.max_tokens()** (3 connections) — `phoenix/src/phoenix/server/rate_limiters.py`
- *... and 32 more nodes in this community*

## Relationships

- [[Phoenix Playground LLM Clients]] (4 shared connections)
- [[Community 112]] (3 shared connections)
- [[Community 553]] (2 shared connections)
- [[Community 176]] (2 shared connections)
- [[Community 117]] (1 shared connections)
- [[Community 87]] (1 shared connections)
- [[Phoenix Server Ops & Email]] (1 shared connections)
- [[Community 947]] (1 shared connections)
- [[Community 542]] (1 shared connections)

## Source Files

- `phoenix/packages/phoenix-client/src/phoenix/client/utils/rate_limiters.py`
- `phoenix/src/phoenix/server/rate_limiters.py`
- `phoenix/tests/unit/server/test_rate_limiters.py`

## Audit Trail

- EXTRACTED: 214 (88%)
- INFERRED: 30 (12%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*