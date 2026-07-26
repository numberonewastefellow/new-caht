# Community 959

> 14 nodes · cohesion 0.19

## Key Concepts

- **run_in_background()** (12 connections) — `backend/om/utils/threadpool_concurrency.py`
- **wait_on_background()** (11 connections) — `backend/om/utils/threadpool_concurrency.py`
- **test_multiple_background_tasks()** (4 connections) — `backend/tests/unit/om/utils/test_threadpool_concurrency.py`
- **test_run_in_background_and_wait_success()** (4 connections) — `backend/tests/unit/om/utils/test_threadpool_concurrency.py`
- **test_run_in_background_propagates_exceptions()** (4 connections) — `backend/tests/unit/om/utils/test_threadpool_concurrency.py`
- **test_run_in_background_with_args_and_kwargs()** (4 connections) — `backend/tests/unit/om/utils/test_threadpool_concurrency.py`
- **test_run_in_background_preserves_contextvar()** (4 connections) — `backend/tests/unit/om/utils/test_threadpool_contextvars.py`
- **Test that args and kwargs are properly passed to the background function** (1 connections) — `backend/tests/unit/om/utils/test_threadpool_concurrency.py`
- **Test running multiple background tasks concurrently** (1 connections) — `backend/tests/unit/om/utils/test_threadpool_concurrency.py`
- **Test that run_in_background and wait_on_background work correctly for successful** (1 connections) — `backend/tests/unit/om/utils/test_threadpool_concurrency.py`
- **Test that exceptions in background tasks are properly propagated** (1 connections) — `backend/tests/unit/om/utils/test_threadpool_concurrency.py`
- **Test that run_in_background preserves contextvar values and modifications are is** (1 connections) — `backend/tests/unit/om/utils/test_threadpool_contextvars.py`
- **Runs a function in a background thread. Returns a TimeoutThread object that can** (1 connections) — `backend/om/utils/threadpool_concurrency.py`
- **Used in conjunction with run_in_background. blocks until the task is finished,** (1 connections) — `backend/om/utils/threadpool_concurrency.py`

## Relationships

- [[Community 621]] (6 shared connections)
- [[Community 654]] (4 shared connections)
- [[Agent Chat Packets & Citations]] (4 shared connections)
- [[Community 1011]] (1 shared connections)
- [[Community 253]] (1 shared connections)

## Source Files

- `backend/om/utils/threadpool_concurrency.py`
- `backend/tests/unit/om/utils/test_threadpool_concurrency.py`
- `backend/tests/unit/om/utils/test_threadpool_contextvars.py`

## Audit Trail

- EXTRACTED: 26 (52%)
- INFERRED: 24 (48%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*