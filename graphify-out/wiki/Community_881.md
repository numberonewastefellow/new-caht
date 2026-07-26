# Community 881

> 15 nodes · cohesion 0.23

## Key Concepts

- **RateLimiterEngine** (18 connections) — `backend/om/server/rate_limits/engine.py`
- **.estimate_used()** (6 connections) — `backend/om/server/rate_limits/engine.py`
- **.record_usage()** (6 connections) — `backend/om/server/rate_limits/engine.py`
- **.seed_current_window()** (5 connections) — `backend/om/server/rate_limits/engine.py`
- **engine.py** (4 connections) — `backend/om/server/rate_limits/engine.py`
- **._key()** (4 connections) — `backend/om/server/rate_limits/engine.py`
- **._now_ms()** (4 connections) — `backend/om/server/rate_limits/engine.py`
- **.compute()** (4 connections) — `backend/om/server/rate_limits/engine.py`
- **Redis** (2 connections) — `backend/om/server/rate_limits/engine.py`
- **.__init__()** (2 connections) — `backend/om/server/rate_limits/engine.py`
- **Core rate-limiting engine: a token-weighted sliding-window counter over Redis.** (1 connections) — `backend/om/server/rate_limits/engine.py`
- **Sliding-window token counter for a single tenant.      One instance wraps one** (1 connections) — `backend/om/server/rate_limits/engine.py`
- **Return the current sliding-window token estimate for a subject (no mutation).** (1 connections) — `backend/om/server/rate_limits/engine.py`
- **Add ``tokens`` to the current window and return the new sliding estimate.** (1 connections) — `backend/om/server/rate_limits/engine.py`
- **Cold-start reconciliation: seed the current window from a durable roll-up.** (1 connections) — `backend/om/server/rate_limits/engine.py`

## Relationships

- [[Community 333]] (12 shared connections)

## Source Files

- `backend/om/server/rate_limits/engine.py`

## Audit Trail

- EXTRACTED: 50 (83%)
- INFERRED: 10 (17%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*