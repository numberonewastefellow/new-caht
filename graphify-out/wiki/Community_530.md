# Community 530

> 29 nodes · cohesion 0.13

## Key Concepts

- **_LDAPRequestHandler** (14 connections) — `phoenix/tests/integration/_mock_ldap_server.py`
- **._handle_search()** (8 connections) — `phoenix/tests/integration/_mock_ldap_server.py`
- **._send_search_done()** (7 connections) — `phoenix/tests/integration/_mock_ldap_server.py`
- **._create_group_search_entry()** (6 connections) — `phoenix/tests/integration/_mock_ldap_server.py`
- **._create_user_search_entry()** (6 connections) — `phoenix/tests/integration/_mock_ldap_server.py`
- **.handle()** (6 connections) — `phoenix/tests/integration/_mock_ldap_server.py`
- **._handle_bind()** (6 connections) — `phoenix/tests/integration/_mock_ldap_server.py`
- **._handle_group_search()** (6 connections) — `phoenix/tests/integration/_mock_ldap_server.py`
- **._handle_user_search()** (6 connections) — `phoenix/tests/integration/_mock_ldap_server.py`
- **ProtocolOp** (6 connections) — `phoenix/tests/integration/_mock_ldap_server.py`
- **._authenticate()** (5 connections) — `phoenix/tests/integration/_mock_ldap_server.py`
- **._create_bind_response()** (5 connections) — `phoenix/tests/integration/_mock_ldap_server.py`
- **LDAPMessage** (5 connections) — `phoenix/tests/integration/_mock_ldap_server.py`
- **._read_ldap_message()** (3 connections) — `phoenix/tests/integration/_mock_ldap_server.py`
- **._validate_dn()** (3 connections) — `phoenix/tests/integration/_mock_ldap_server.py`
- **Any** (2 connections) — `phoenix/tests/integration/_mock_ldap_server.py`
- **TCP request handler for LDAP protocol messages.      Processes incoming LDAP m** (1 connections) — `phoenix/tests/integration/_mock_ldap_server.py`
- **Process LDAP protocol messages from client.          Handles multiple messages** (1 connections) — `phoenix/tests/integration/_mock_ldap_server.py`
- **Read a complete BER-encoded LDAP message from the socket.          LDAP messag** (1 connections) — `phoenix/tests/integration/_mock_ldap_server.py`
- **Handle LDAP bind request (authentication).          Args:             message** (1 connections) — `phoenix/tests/integration/_mock_ldap_server.py`
- **Authenticate user credentials.          Args:             dn: Bind DN** (1 connections) — `phoenix/tests/integration/_mock_ldap_server.py`
- **Validate DN syntax using ldap3's parser.          This ensures the mock server** (1 connections) — `phoenix/tests/integration/_mock_ldap_server.py`
- **Handle LDAP search request.          Supports two types of searches:** (1 connections) — `phoenix/tests/integration/_mock_ldap_server.py`
- **Handle user search request.          Args:             message_id: LDAP messa** (1 connections) — `phoenix/tests/integration/_mock_ldap_server.py`
- **Handle POSIX group search request.          Searches for groups where a specif** (1 connections) — `phoenix/tests/integration/_mock_ldap_server.py`
- *... and 4 more nodes in this community*

## Relationships

- [[Community 346]] (4 shared connections)
- [[Community 282]] (1 shared connections)

## Source Files

- `phoenix/tests/integration/_mock_ldap_server.py`

## Audit Trail

- EXTRACTED: 106 (99%)
- INFERRED: 1 (1%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*