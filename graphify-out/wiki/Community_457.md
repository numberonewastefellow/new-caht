# Community 457

> 33 nodes · cohesion 0.11

## Key Concepts

- **refresh_oauth_token()** (11 connections) — `backend/om/auth/oauth_refresher.py`
- **check_and_refresh_oauth_tokens()** (8 connections) — `backend/om/auth/oauth_refresher.py`
- **_test_expire_oauth_token()** (8 connections) — `backend/om/auth/oauth_refresher.py`
- **test_oauth_refresher.py** (7 connections) — `backend/tests/unit/om/auth/test_oauth_refresher.py`
- **oauth_refresher.py** (6 connections) — `backend/om/auth/oauth_refresher.py`
- **check_oauth_account_has_refresh_token()** (6 connections) — `backend/om/auth/oauth_refresher.py`
- **get_oauth_accounts_requiring_refresh_token()** (6 connections) — `backend/om/auth/oauth_refresher.py`
- **User** (5 connections) — `backend/om/auth/oauth_refresher.py`
- **AsyncSession** (5 connections) — `backend/tests/unit/om/auth/test_oauth_refresher.py`
- **test_check_and_refresh_oauth_tokens()** (4 connections) — `backend/tests/unit/om/auth/test_oauth_refresher.py`
- **test_expire_oauth_token()** (4 connections) — `backend/tests/unit/om/auth/test_oauth_refresher.py`
- **test_refresh_oauth_token_failure()** (4 connections) — `backend/tests/unit/om/auth/test_oauth_refresher.py`
- **test_refresh_oauth_token_no_refresh_token()** (4 connections) — `backend/tests/unit/om/auth/test_oauth_refresher.py`
- **test_refresh_oauth_token_success()** (4 connections) — `backend/tests/unit/om/auth/test_oauth_refresher.py`
- **OAuthAccount** (4 connections) — `backend/om/auth/oauth_refresher.py`
- **test_check_oauth_account_has_refresh_token()** (3 connections) — `backend/tests/unit/om/auth/test_oauth_refresher.py`
- **test_get_oauth_accounts_requiring_refresh_token()** (3 connections) — `backend/tests/unit/om/auth/test_oauth_refresher.py`
- **Any** (3 connections) — `backend/om/auth/oauth_refresher.py`
- **AsyncSession** (3 connections) — `backend/om/auth/oauth_refresher.py`
- **BaseUserManager** (3 connections) — `backend/om/auth/oauth_refresher.py`
- **Check if any OAuth tokens are expired or about to expire and refresh them.** (1 connections) — `backend/om/auth/oauth_refresher.py`
- **Check if an OAuth account has a refresh token.     Returns True if a refresh tok** (1 connections) — `backend/om/auth/oauth_refresher.py`
- **Returns a list of OAuth accounts for a user that are missing refresh tokens.** (1 connections) — `backend/om/auth/oauth_refresher.py`
- **# NOTE: Keeping this as a utility function for potential future debugging,** (1 connections) — `backend/om/auth/oauth_refresher.py`
- **Utility function for testing - Sets an OAuth token to expire in a short time** (1 connections) — `backend/om/auth/oauth_refresher.py`
- *... and 8 more nodes in this community*

## Relationships

- No strong cross-community connections detected

## Source Files

- `backend/om/auth/oauth_refresher.py`
- `backend/tests/unit/om/auth/test_oauth_refresher.py`

## Audit Trail

- EXTRACTED: 100 (88%)
- INFERRED: 14 (12%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*