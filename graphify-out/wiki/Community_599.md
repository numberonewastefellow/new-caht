# Community 599

> 25 nodes · cohesion 0.11

## Key Concepts

- **verify_email_is_invited()** (15 connections) — `backend/om/auth/users.py`
- **TestWhitelistBehavior** (8 connections) — `backend/tests/unit/om/auth/test_user_registration.py`
- **TestSAMLOIDCBehavior** (6 connections) — `backend/tests/unit/om/auth/test_user_registration.py`
- **verify_email_in_whitelist()** (5 connections) — `backend/om/auth/users.py`
- **.test_sso_bypasses_whitelist()** (4 connections) — `backend/tests/unit/om/auth/test_user_registration.py`
- **test_verify_email_is_invited_skips_whitelist_for_sso()** (4 connections) — `backend/tests/unit/om/auth/test_verify_email_invite.py`
- **.test_basic_auth_enforces_whitelist()** (3 connections) — `backend/tests/unit/om/auth/test_user_registration.py`
- **.test_empty_whitelist_allows_all()** (3 connections) — `backend/tests/unit/om/auth/test_user_registration.py`
- **.test_whitelist_allows_invited_case_insensitive()** (3 connections) — `backend/tests/unit/om/auth/test_user_registration.py`
- **.test_whitelist_blocks_non_invited()** (3 connections) — `backend/tests/unit/om/auth/test_user_registration.py`
- **test_verify_email_invite.py** (3 connections) — `backend/tests/unit/om/auth/test_verify_email_invite.py`
- **test_verify_email_is_invited_enforced_for_basic_auth()** (3 connections) — `backend/tests/unit/om/auth/test_verify_email_invite.py`
- **test_verify_email_is_invited_skipped_when_invite_only_disabled()** (3 connections) — `backend/tests/unit/om/auth/test_verify_email_invite.py`
- **workspace_invite_only_enabled()** (3 connections) — `backend/om/auth/users.py`
- **AuthType** (3 connections) — `backend/tests/unit/om/auth/test_user_registration.py`
- **MonkeyPatch** (3 connections) — `backend/tests/unit/om/auth/test_verify_email_invite.py`
- **.test_invite_only_disabled_allows_non_invited_users()** (2 connections) — `backend/tests/unit/om/auth/test_user_registration.py`
- **Test SSO (SAML/OIDC) bypass of invite whitelist.** (1 connections) — `backend/tests/unit/om/auth/test_user_registration.py`
- **SAML/OIDC should bypass invite whitelist.** (1 connections) — `backend/tests/unit/om/auth/test_user_registration.py`
- **Basic auth should enforce invite whitelist.** (1 connections) — `backend/tests/unit/om/auth/test_user_registration.py`
- **Test invite whitelist scenarios.** (1 connections) — `backend/tests/unit/om/auth/test_user_registration.py`
- **Empty whitelist should allow all users.** (1 connections) — `backend/tests/unit/om/auth/test_user_registration.py`
- **Populated whitelist should block non-invited users.** (1 connections) — `backend/tests/unit/om/auth/test_user_registration.py`
- **Whitelist should match emails case-insensitively.** (1 connections) — `backend/tests/unit/om/auth/test_user_registration.py`
- **AuthType** (1 connections) — `backend/tests/unit/om/auth/test_verify_email_invite.py`

## Relationships

- [[Community 70]] (9 shared connections)
- [[Community 137]] (3 shared connections)
- [[Community 402]] (2 shared connections)
- [[Community 443]] (1 shared connections)
- [[Community 73]] (1 shared connections)
- [[Community 103]] (1 shared connections)
- [[Community 161]] (1 shared connections)

## Source Files

- `backend/om/auth/users.py`
- `backend/tests/unit/om/auth/test_user_registration.py`
- `backend/tests/unit/om/auth/test_verify_email_invite.py`

## Audit Trail

- EXTRACTED: 54 (66%)
- INFERRED: 28 (34%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*