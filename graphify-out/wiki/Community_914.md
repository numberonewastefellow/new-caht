# Community 914

> 14 nodes · cohesion 0.18

## Key Concepts

- **test_jwt_provisioning.py** (6 connections) — `backend/tests/unit/om/auth/test_jwt_provisioning.py`
- **MonkeyPatch** (4 connections) — `backend/tests/unit/om/auth/test_jwt_provisioning.py`
- **test_get_or_create_user_handles_race_conditions()** (3 connections) — `backend/tests/unit/om/auth/test_jwt_provisioning.py`
- **test_get_or_create_user_provisions_new_user()** (3 connections) — `backend/tests/unit/om/auth/test_jwt_provisioning.py`
- **test_get_or_create_user_skips_inactive()** (3 connections) — `backend/tests/unit/om/auth/test_jwt_provisioning.py`
- **test_get_or_create_user_updates_expiry()** (3 connections) — `backend/tests/unit/om/auth/test_jwt_provisioning.py`
- **test_extract_email_requires_valid_format()** (2 connections) — `backend/tests/unit/om/auth/test_jwt_provisioning.py`
- **test_get_or_create_user_requires_email_claim()** (2 connections) — `backend/tests/unit/om/auth/test_jwt_provisioning.py`
- **If provisioning races, newly inactive users should still be blocked.** (1 connections) — `backend/tests/unit/om/auth/test_jwt_provisioning.py`
- **Helper should validate email format before returning value.** (1 connections) — `backend/tests/unit/om/auth/test_jwt_provisioning.py`
- **A brand new JWT user should be provisioned automatically.** (1 connections) — `backend/tests/unit/om/auth/test_jwt_provisioning.py`
- **Tokens without a usable email claim should be ignored.** (1 connections) — `backend/tests/unit/om/auth/test_jwt_provisioning.py`
- **Existing web-login users should be returned and their expiry synced.** (1 connections) — `backend/tests/unit/om/auth/test_jwt_provisioning.py`
- **Inactive users should not be re-authenticated via JWT.** (1 connections) — `backend/tests/unit/om/auth/test_jwt_provisioning.py`

## Relationships

- No strong cross-community connections detected

## Source Files

- `backend/tests/unit/om/auth/test_jwt_provisioning.py`

## Audit Trail

- EXTRACTED: 32 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*