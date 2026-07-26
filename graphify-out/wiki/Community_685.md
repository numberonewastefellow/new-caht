# Community 685

> 21 nodes · cohesion 0.13

## Key Concepts

- **test_rate_limit_engine.py** (14 connections) — `backend/tests/unit/om/server/rate_limits/test_rate_limit_engine.py`
- **subject_key()** (10 connections) — `backend/om/server/rate_limits/constants.py`
- **_sliding_estimate()** (6 connections) — `backend/tests/unit/om/server/rate_limits/test_rate_limit_engine.py`
- **constants.py** (5 connections) — `backend/om/server/rate_limits/constants.py`
- **UUID** (2 connections) — `backend/om/server/rate_limits/constants.py`
- **test_budget_decision_boundary()** (2 connections) — `backend/tests/unit/om/server/rate_limits/test_rate_limit_engine.py`
- **test_sliding_weight_full_at_window_start()** (2 connections) — `backend/tests/unit/om/server/rate_limits/test_rate_limit_engine.py`
- **test_sliding_weight_linear_midpoint()** (2 connections) — `backend/tests/unit/om/server/rate_limits/test_rate_limit_engine.py`
- **test_sliding_weight_zero_at_window_end()** (2 connections) — `backend/tests/unit/om/server/rate_limits/test_rate_limit_engine.py`
- **test_subject_key_requires_matching_subject()** (2 connections) — `backend/tests/unit/om/server/rate_limits/test_rate_limit_engine.py`
- **test_subject_key_tenant_wide_uses_scope_name()** (2 connections) — `backend/tests/unit/om/server/rate_limits/test_rate_limit_engine.py`
- **test_subject_key_user_and_team()** (2 connections) — `backend/tests/unit/om/server/rate_limits/test_rate_limit_engine.py`
- **RateLimitScope** (1 connections) — `backend/om/server/rate_limits/constants.py`
- **Enums, namespaces, and key/subject helpers for the rate-limits subsystem.  Kep** (1 connections) — `backend/om/server/rate_limits/constants.py`
- **Stable string that identifies a policy's subject bucket.      Tenant-wide scop** (1 connections) — `backend/om/server/rate_limits/constants.py`
- **Unit tests for the rate-limits core logic (no live Redis/DB required).  Covers** (1 connections) — `backend/tests/unit/om/server/rate_limits/test_rate_limit_engine.py`
- **Mirror of the engine's Lua weighting so the algorithm is asserted independently.** (1 connections) — `backend/tests/unit/om/server/rate_limits/test_rate_limit_engine.py`
- **test_policy_args_validation()** (1 connections) — `backend/tests/unit/om/server/rate_limits/test_rate_limit_engine.py`
- **test_window_math_indices_and_elapsed()** (1 connections) — `backend/tests/unit/om/server/rate_limits/test_rate_limit_engine.py`
- **test_window_math_rejects_nonpositive_period()** (1 connections) — `backend/tests/unit/om/server/rate_limits/test_rate_limit_engine.py`
- **test_window_math_reset_seconds_decreases_through_window()** (1 connections) — `backend/tests/unit/om/server/rate_limits/test_rate_limit_engine.py`

## Relationships

- [[Community 72]] (2 shared connections)
- [[Community 333]] (2 shared connections)
- [[Community 405]] (1 shared connections)
- [[Community 537]] (1 shared connections)

## Source Files

- `backend/om/server/rate_limits/constants.py`
- `backend/tests/unit/om/server/rate_limits/test_rate_limit_engine.py`

## Audit Trail

- EXTRACTED: 51 (85%)
- INFERRED: 9 (15%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*