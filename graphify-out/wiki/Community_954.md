# Community 954

> 14 nodes · cohesion 0.14

## Key Concepts

- **TestSocketLeakPrevention** (9 connections) — `phoenix/tests/unit/server/test_ldap.py`
- **.authenticator()** (4 connections) — `phoenix/tests/unit/server/test_ldap.py`
- **.test_establish_connection_closes_socket_on_anonymous_bind_failure()** (4 connections) — `phoenix/tests/unit/server/test_ldap.py`
- **.config()** (3 connections) — `phoenix/tests/unit/server/test_ldap.py`
- **.test_verify_user_password_closes_socket_on_bind_failure()** (3 connections) — `phoenix/tests/unit/server/test_ldap.py`
- **.test_verify_user_password_closes_socket_on_open_failure()** (3 connections) — `phoenix/tests/unit/server/test_ldap.py`
- **.test_verify_user_password_closes_socket_on_start_tls_failure()** (3 connections) — `phoenix/tests/unit/server/test_ldap.py`
- **Test that LDAP connections are properly closed to prevent file descriptor leaks.** (1 connections) — `phoenix/tests/unit/server/test_ldap.py`
- **Minimal LDAP configuration for testing.** (1 connections) — `phoenix/tests/unit/server/test_ldap.py`
- **Create authenticator instance.** (1 connections) — `phoenix/tests/unit/server/test_ldap.py`
- **Socket must be closed even when bind() fails (wrong password).** (1 connections) — `phoenix/tests/unit/server/test_ldap.py`
- **Socket must be closed when start_tls() raises.** (1 connections) — `phoenix/tests/unit/server/test_ldap.py`
- **Socket must be closed when open() raises.** (1 connections) — `phoenix/tests/unit/server/test_ldap.py`
- **Anonymous bind must close socket when start_tls() fails.** (1 connections) — `phoenix/tests/unit/server/test_ldap.py`

## Relationships

- [[Community 157]] (8 shared connections)
- [[Community 836]] (1 shared connections)
- [[Community 799]] (1 shared connections)

## Source Files

- `phoenix/tests/unit/server/test_ldap.py`

## Audit Trail

- EXTRACTED: 35 (97%)
- INFERRED: 1 (3%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*