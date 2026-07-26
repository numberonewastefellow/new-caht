# Community 836

> 17 nodes · cohesion 0.19

## Key Concepts

- **LDAPUserInfo** (23 connections) — `phoenix/src/phoenix/server/api/routers/ldap.py`
- **get_or_create_ldap_user()** (11 connections) — `phoenix/src/phoenix/server/api/routers/ldap.py`
- **ldap.py** (5 connections) — `phoenix/src/phoenix/server/api/routers/ldap.py`
- **_lookup_by_email()** (5 connections) — `phoenix/src/phoenix/server/api/routers/ldap.py`
- **_lookup_by_unique_id()** (5 connections) — `phoenix/src/phoenix/server/api/routers/ldap.py`
- **TestMultiServerFailover** (5 connections) — `phoenix/tests/unit/server/test_ldap.py`
- **AsyncSession** (4 connections) — `phoenix/src/phoenix/server/api/routers/ldap.py`
- **User** (4 connections) — `phoenix/src/phoenix/server/api/routers/ldap.py`
- **.test_multiple_servers_created()** (4 connections) — `phoenix/tests/unit/server/test_ldap.py`
- **.test_whitespace_stripped_from_hosts()** (4 connections) — `phoenix/tests/unit/server/test_ldap.py`
- **LDAPConfig** (2 connections) — `phoenix/src/phoenix/server/api/routers/ldap.py`
- **Look up LDAP user by immutable unique ID (objectGUID, entryUUID, etc.).      U** (1 connections) — `phoenix/src/phoenix/server/api/routers/ldap.py`
- **Look up LDAP user by email (case-insensitive).      Note: Both sides of the co** (1 connections) — `phoenix/src/phoenix/server/api/routers/ldap.py`
- **Retrieves an existing LDAP user or creates a new one.      User Identity Strat** (1 connections) — `phoenix/src/phoenix/server/api/routers/ldap.py`
- **Test failover behavior with multiple LDAP servers.** (1 connections) — `phoenix/tests/unit/server/test_ldap.py`
- **Test multiple servers are created from comma-separated hosts.** (1 connections) — `phoenix/tests/unit/server/test_ldap.py`
- **Test whitespace is stripped from host entries.** (1 connections) — `phoenix/tests/unit/server/test_ldap.py`

## Relationships

- [[Community 157]] (12 shared connections)
- [[Community 799]] (3 shared connections)
- [[Community 282]] (2 shared connections)
- [[Community 306]] (1 shared connections)
- [[Community 679]] (1 shared connections)
- [[Community 954]] (1 shared connections)
- [[Community 593]] (1 shared connections)
- [[Community 251]] (1 shared connections)
- [[Phoenix Server Ops & Email]] (1 shared connections)
- [[Community 90]] (1 shared connections)
- [[Community 674]] (1 shared connections)
- [[Community 103]] (1 shared connections)

## Source Files

- `phoenix/src/phoenix/server/api/routers/ldap.py`
- `phoenix/tests/unit/server/test_ldap.py`

## Audit Trail

- EXTRACTED: 50 (65%)
- INFERRED: 27 (35%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*