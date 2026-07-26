# Community 542

> 28 nodes · cohesion 0.14

## Key Concepts

- **test_rate_limiters.py** (16 connections) — `phoenix/packages/phoenix-client/tests/client/utils/test_rate_limiters.py`
- **AdaptiveTokenBucket** (12 connections) — `phoenix/packages/phoenix-client/src/phoenix/client/utils/rate_limiters.py`
- **freeze_time()** (12 connections) — `phoenix/packages/phoenix-client/tests/client/utils/test_rate_limiters.py`
- **warp_time()** (9 connections) — `phoenix/packages/phoenix-client/tests/client/utils/test_rate_limiters.py`
- **Any** (4 connections) — `phoenix/packages/phoenix-client/tests/client/utils/test_rate_limiters.py`
- **.make_request_if_ready()** (4 connections) — `phoenix/packages/phoenix-client/src/phoenix/client/utils/rate_limiters.py`
- **async_warp_time()** (4 connections) — `phoenix/packages/phoenix-client/tests/client/utils/test_rate_limiters.py`
- **.async_wait_until_ready()** (3 connections) — `phoenix/packages/phoenix-client/src/phoenix/client/utils/rate_limiters.py`
- **.available_requests()** (3 connections) — `phoenix/packages/phoenix-client/src/phoenix/client/utils/rate_limiters.py`
- **.increase_rate()** (3 connections) — `phoenix/packages/phoenix-client/src/phoenix/client/utils/rate_limiters.py`
- **.wait_until_ready()** (3 connections) — `phoenix/packages/phoenix-client/src/phoenix/client/utils/rate_limiters.py`
- **test_token_bucket_adaptively_increases_rate_over_time()** (3 connections) — `phoenix/packages/phoenix-client/tests/client/utils/test_rate_limiters.py`
- **test_token_bucket_does_not_increase_rate_past_maximum()** (3 connections) — `phoenix/packages/phoenix-client/tests/client/utils/test_rate_limiters.py`
- **test_token_bucket_resets_rate_after_inactivity()** (3 connections) — `phoenix/packages/phoenix-client/tests/client/utils/test_rate_limiters.py`
- **test_token_rate_limiter_async_waits_until_tokens_are_available()** (3 connections) — `phoenix/packages/phoenix-client/tests/client/utils/test_rate_limiters.py`
- **test_token_rate_limiter_can_accumulate_tokens_before_waiting()** (3 connections) — `phoenix/packages/phoenix-client/tests/client/utils/test_rate_limiters.py`
- **test_token_rate_limiter_can_async_accumulate_tokens_before_waiting()** (3 connections) — `phoenix/packages/phoenix-client/tests/client/utils/test_rate_limiters.py`
- **test_token_rate_limiter_can_block_until_tokens_are_available()** (3 connections) — `phoenix/packages/phoenix-client/tests/client/utils/test_rate_limiters.py`
- **.max_tokens()** (2 connections) — `phoenix/packages/phoenix-client/src/phoenix/client/utils/rate_limiters.py`
- **test_token_bucket_decreases_rate()** (2 connections) — `phoenix/packages/phoenix-client/tests/client/utils/test_rate_limiters.py`
- **test_token_bucket_decreases_rate_once_per_cooldown_period()** (2 connections) — `phoenix/packages/phoenix-client/tests/client/utils/test_rate_limiters.py`
- **test_token_bucket_gains_tokens_over_time()** (2 connections) — `phoenix/packages/phoenix-client/tests/client/utils/test_rate_limiters.py`
- **test_token_rate_limiter_can_max_out_on_requests()** (2 connections) — `phoenix/packages/phoenix-client/tests/client/utils/test_rate_limiters.py`
- **test_token_rate_limiter_cannot_spend_unavailable_tokens()** (2 connections) — `phoenix/packages/phoenix-client/tests/client/utils/test_rate_limiters.py`
- **test_token_rate_limiter_spends_tokens()** (2 connections) — `phoenix/packages/phoenix-client/tests/client/utils/test_rate_limiters.py`
- *... and 3 more nodes in this community*

## Relationships

- [[Community 238]] (1 shared connections)
- [[Phoenix Playground LLM Clients]] (1 shared connections)
- [[Community 1751]] (1 shared connections)

## Source Files

- `phoenix/packages/phoenix-client/src/phoenix/client/utils/rate_limiters.py`
- `phoenix/packages/phoenix-client/tests/client/utils/test_rate_limiters.py`

## Audit Trail

- EXTRACTED: 108 (97%)
- INFERRED: 3 (3%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*