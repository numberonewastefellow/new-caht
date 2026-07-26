# Community 567

> 26 nodes · cohesion 0.16

## Key Concepts

- **test_single_tenant_jwt_strategy.py** (14 connections) — `backend/tests/unit/om/auth/test_single_tenant_jwt_strategy.py`
- **_make_strategy()** (12 connections) — `backend/tests/unit/om/auth/test_single_tenant_jwt_strategy.py`
- **_make_user()** (12 connections) — `backend/tests/unit/om/auth/test_single_tenant_jwt_strategy.py`
- **test_read_token_returns_none_for_bad_signature()** (6 connections) — `backend/tests/unit/om/auth/test_single_tenant_jwt_strategy.py`
- **_make_user_manager()** (5 connections) — `backend/tests/unit/om/auth/test_single_tenant_jwt_strategy.py`
- **test_read_token_returns_none_for_expired_token()** (5 connections) — `backend/tests/unit/om/auth/test_single_tenant_jwt_strategy.py`
- **test_read_token_returns_none_for_none()** (5 connections) — `backend/tests/unit/om/auth/test_single_tenant_jwt_strategy.py`
- **test_read_token_returns_user()** (5 connections) — `backend/tests/unit/om/auth/test_single_tenant_jwt_strategy.py`
- **test_destroy_token_is_noop()** (4 connections) — `backend/tests/unit/om/auth/test_single_tenant_jwt_strategy.py`
- **test_refresh_token_returns_new_jwt()** (4 connections) — `backend/tests/unit/om/auth/test_single_tenant_jwt_strategy.py`
- **test_refresh_token_with_none_creates_new()** (4 connections) — `backend/tests/unit/om/auth/test_single_tenant_jwt_strategy.py`
- **test_write_token_iat_is_accurate()** (4 connections) — `backend/tests/unit/om/auth/test_single_tenant_jwt_strategy.py`
- **test_write_token_no_lifetime_omits_exp()** (4 connections) — `backend/tests/unit/om/auth/test_single_tenant_jwt_strategy.py`
- **test_write_token_produces_valid_jwt()** (4 connections) — `backend/tests/unit/om/auth/test_single_tenant_jwt_strategy.py`
- **UUID** (3 connections) — `backend/tests/unit/om/auth/test_single_tenant_jwt_strategy.py`
- **SingleTenantJWTStrategy** (3 connections) — `backend/tests/unit/om/auth/test_single_tenant_jwt_strategy.py`
- **read_token should return None when the token has expired.** (1 connections) — `backend/tests/unit/om/auth/test_single_tenant_jwt_strategy.py`
- **destroy_token should not raise — JWTs can't be server-side invalidated.** (1 connections) — `backend/tests/unit/om/auth/test_single_tenant_jwt_strategy.py`
- **refresh_token should issue a fresh JWT (different from the original).** (1 connections) — `backend/tests/unit/om/auth/test_single_tenant_jwt_strategy.py`
- **refresh_token(None, user) should create a brand-new token.** (1 connections) — `backend/tests/unit/om/auth/test_single_tenant_jwt_strategy.py`
- **When lifetime_seconds is None, the token should have no exp claim.** (1 connections) — `backend/tests/unit/om/auth/test_single_tenant_jwt_strategy.py`
- **write_token should return a JWT whose claims contain sub and iat.** (1 connections) — `backend/tests/unit/om/auth/test_single_tenant_jwt_strategy.py`
- **The iat claim should be close to the current time.** (1 connections) — `backend/tests/unit/om/auth/test_single_tenant_jwt_strategy.py`
- **read_token should decode the JWT and return the corresponding user.** (1 connections) — `backend/tests/unit/om/auth/test_single_tenant_jwt_strategy.py`
- **read_token should return None when token is None.** (1 connections) — `backend/tests/unit/om/auth/test_single_tenant_jwt_strategy.py`
- *... and 1 more nodes in this community*

## Relationships

- [[Community 70]] (2 shared connections)

## Source Files

- `backend/tests/unit/om/auth/test_single_tenant_jwt_strategy.py`

## Audit Trail

- EXTRACTED: 102 (98%)
- INFERRED: 2 (2%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*