# Community 674

> 22 nodes · cohesion 0.19

## Key Concepts

- **auth.py** (14 connections) — `phoenix/src/phoenix/server/api/routers/auth.py`
- **get_env_disable_basic_auth()** (13 connections) — `phoenix/src/phoenix/config.py`
- **_create_auth_response()** (11 connections) — `phoenix/src/phoenix/server/api/routers/auth.py`
- **_login()** (11 connections) — `phoenix/src/phoenix/server/api/routers/auth.py`
- **_ldap_login()** (10 connections) — `phoenix/src/phoenix/server/api/routers/auth.py`
- **_initiate_password_reset()** (9 connections) — `phoenix/src/phoenix/server/api/routers/auth.py`
- **_reset_password()** (9 connections) — `phoenix/src/phoenix/server/api/routers/auth.py`
- **Request** (8 connections) — `phoenix/src/phoenix/server/api/routers/auth.py`
- **Response** (8 connections) — `phoenix/src/phoenix/server/api/routers/auth.py`
- **_refresh_tokens()** (7 connections) — `phoenix/src/phoenix/server/api/routers/auth.py`
- **_check_brute_force_limit()** (4 connections) — `phoenix/src/phoenix/server/api/routers/auth.py`
- **_record_brute_force_success()** (4 connections) — `phoenix/src/phoenix/server/api/routers/auth.py`
- **.__post_init__()** (3 connections) — `phoenix/src/phoenix/server/api/mutations/user_mutations.py`
- **_record_brute_force_failure()** (3 connections) — `phoenix/src/phoenix/server/api/routers/auth.py`
- **User** (2 connections) — `phoenix/src/phoenix/server/api/routers/auth.py`
- **Gets the value of the ENV_PHOENIX_DISABLE_BASIC_AUTH environment variable.** (1 connections) — `phoenix/src/phoenix/config.py`
- **Authenticate user via email/password and return access/refresh tokens.** (1 connections) — `phoenix/src/phoenix/server/api/routers/auth.py`
- **Refresh access and refresh tokens.** (1 connections) — `phoenix/src/phoenix/server/api/routers/auth.py`
- **Send password reset email to user.** (1 connections) — `phoenix/src/phoenix/server/api/routers/auth.py`
- **Reset user password using a valid reset token.** (1 connections) — `phoenix/src/phoenix/server/api/routers/auth.py`
- **Authenticate user via LDAP and return access/refresh tokens.** (1 connections) — `phoenix/src/phoenix/server/api/routers/auth.py`
- **Creates access and refresh tokens for the user and sets them as cookies in the r** (1 connections) — `phoenix/src/phoenix/server/api/routers/auth.py`

## Relationships

- [[Community 251]] (9 shared connections)
- [[Community 103]] (6 shared connections)
- [[Phoenix Server Ops & Email]] (5 shared connections)
- [[Community 110]] (4 shared connections)
- [[Phoenix Dataset Events]] (3 shared connections)
- [[Community 90]] (3 shared connections)
- [[Community 947]] (2 shared connections)
- [[Community 101]] (1 shared connections)
- [[Community 180]] (1 shared connections)
- [[Community 156]] (1 shared connections)
- [[Community 905]] (1 shared connections)
- [[Community 836]] (1 shared connections)

## Source Files

- `phoenix/src/phoenix/config.py`
- `phoenix/src/phoenix/server/api/mutations/user_mutations.py`
- `phoenix/src/phoenix/server/api/routers/auth.py`

## Audit Trail

- EXTRACTED: 110 (89%)
- INFERRED: 13 (11%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*