# Community 948

> 14 nodes · cohesion 0.14

## Key Concepts

- **test_pat_api.py** (7 connections) — `backend/tests/integration/tests/pat/test_pat_api.py`
- **test_pat_expiration_flow()** (2 connections) — `backend/tests/integration/tests/pat/test_pat_api.py`
- **test_pat_lifecycle_happy_path()** (2 connections) — `backend/tests/integration/tests/pat/test_pat_api.py`
- **test_pat_role_based_access_control()** (2 connections) — `backend/tests/integration/tests/pat/test_pat_api.py`
- **test_pat_sorting_and_last_used()** (2 connections) — `backend/tests/integration/tests/pat/test_pat_api.py`
- **test_pat_user_isolation_and_authentication()** (2 connections) — `backend/tests/integration/tests/pat/test_pat_api.py`
- **test_pat_validation_errors()** (2 connections) — `backend/tests/integration/tests/pat/test_pat_api.py`
- **Integration tests for Personal Access Token (PAT) API.  Test Suite: 1. test_pat_** (1 connections) — `backend/tests/integration/tests/pat/test_pat_api.py`
- **Expiration timestamp is end-of-day (23:59:59 UTC); never-expiring tokens work; r** (1 connections) — `backend/tests/integration/tests/pat/test_pat_api.py`
- **Validate input errors: empty name, name too long, negative/zero expiration.** (1 connections) — `backend/tests/integration/tests/pat/test_pat_api.py`
- **PATs are sorted by created_at DESC; last_used_at updates after authentication.** (1 connections) — `backend/tests/integration/tests/pat/test_pat_api.py`
- **Complete PAT lifecycle: create, authenticate, revoke.** (1 connections) — `backend/tests/integration/tests/pat/test_pat_api.py`
- **PATs inherit user roles and permissions:     - Admin PAT: Full access to admin-o** (1 connections) — `backend/tests/integration/tests/pat/test_pat_api.py`
- **PATs authenticate as real users, and users can only see/manage their own tokens.** (1 connections) — `backend/tests/integration/tests/pat/test_pat_api.py`

## Relationships

- No strong cross-community connections detected

## Source Files

- `backend/tests/integration/tests/pat/test_pat_api.py`

## Audit Trail

- EXTRACTED: 26 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*