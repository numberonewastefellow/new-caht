# Community 890

> 15 nodes · cohesion 0.18

## Key Concepts

- **test_session_lifecycle.py** (9 connections) — `code-interpreter/code-interpreter/tests/integration_tests/session_tests/test_session_lifecycle.py`
- **Session** (6 connections) — `code-interpreter/code-interpreter/tests/integration_tests/session_tests/test_session_lifecycle.py`
- **test_multiple_sessions_independent()** (4 connections) — `code-interpreter/code-interpreter/tests/integration_tests/session_tests/test_session_lifecycle.py`
- **test_create_session_returns_session_id()** (3 connections) — `code-interpreter/code-interpreter/tests/integration_tests/session_tests/test_session_lifecycle.py`
- **test_delete_nonexistent_session_returns_404()** (3 connections) — `code-interpreter/code-interpreter/tests/integration_tests/session_tests/test_session_lifecycle.py`
- **test_delete_session_returns_204()** (3 connections) — `code-interpreter/code-interpreter/tests/integration_tests/session_tests/test_session_lifecycle.py`
- **test_ephemeral_execution_still_works()** (3 connections) — `code-interpreter/code-interpreter/tests/integration_tests/session_tests/test_session_lifecycle.py`
- **test_execute_with_invalid_session_returns_404()** (3 connections) — `code-interpreter/code-interpreter/tests/integration_tests/session_tests/test_session_lifecycle.py`
- **Tests for session create / delete / error handling lifecycle.** (1 connections) — `code-interpreter/code-interpreter/tests/integration_tests/session_tests/test_session_lifecycle.py`
- **POST /v1/sessions returns 201 with a session_id string.** (1 connections) — `code-interpreter/code-interpreter/tests/integration_tests/session_tests/test_session_lifecycle.py`
- **DELETE /v1/sessions/{id} returns 204 and removes the session.** (1 connections) — `code-interpreter/code-interpreter/tests/integration_tests/session_tests/test_session_lifecycle.py`
- **DELETE on a fake session_id should 404.** (1 connections) — `code-interpreter/code-interpreter/tests/integration_tests/session_tests/test_session_lifecycle.py`
- **Executing against a session that doesn't exist should 404.** (1 connections) — `code-interpreter/code-interpreter/tests/integration_tests/session_tests/test_session_lifecycle.py`
- **POST /v1/execute without session_id should still work (backward compat).** (1 connections) — `code-interpreter/code-interpreter/tests/integration_tests/session_tests/test_session_lifecycle.py`
- **Two sessions should not share state.** (1 connections) — `code-interpreter/code-interpreter/tests/integration_tests/session_tests/test_session_lifecycle.py`

## Relationships

- [[Community 748]] (2 shared connections)
- [[Community 365]] (1 shared connections)

## Source Files

- `code-interpreter/code-interpreter/tests/integration_tests/session_tests/test_session_lifecycle.py`

## Audit Trail

- EXTRACTED: 41 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*