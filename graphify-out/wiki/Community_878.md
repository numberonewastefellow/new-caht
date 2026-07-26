# Community 878

> 15 nodes · cohesion 0.19

## Key Concepts

- **emit_background_error()** (8 connections) — `backend/om/background/error_logging.py`
- **OmConfluence** (6 connections) — `backend/om/external_permissions/confluence/group_sync.py`
- **confluence_group_sync()** (6 connections) — `backend/om/external_permissions/confluence/group_sync.py`
- **_build_final_group_to_member_email_map()** (5 connections) — `backend/om/external_permissions/confluence/group_sync.py`
- **_build_group_member_email_map()** (5 connections) — `backend/om/external_permissions/confluence/group_sync.py`
- **_build_group_member_email_map_from_om_users()** (5 connections) — `backend/om/external_permissions/confluence/group_sync.py`
- **group_sync.py** (4 connections) — `backend/om/external_permissions/confluence/group_sync.py`
- **create_background_error()** (4 connections) — `backend/om/db/background_error.py`
- **ConnectorCredentialPair** (3 connections) — `backend/om/external_permissions/confluence/group_sync.py`
- **ExternalUserGroup** (3 connections) — `backend/om/external_permissions/confluence/group_sync.py`
- **Session** (1 connections) — `backend/om/db/background_error.py`
- **error_logging.py** (1 connections) — `backend/om/background/error_logging.py`
- **Currently just saves a row in the background_errors table.      In the future, c** (1 connections) — `backend/om/background/error_logging.py`
- **Hacky, but it's the only way to do this as long as the     Confluence APIs are b** (1 connections) — `backend/om/external_permissions/confluence/group_sync.py`
- **background_error.py** (1 connections) — `backend/om/db/background_error.py`

## Relationships

- [[Confluence Connector]] (4 shared connections)
- [[Community 320]] (3 shared connections)
- [[Community 59]] (2 shared connections)
- [[Backend Agent/API Test Fixtures]] (2 shared connections)
- [[Community 601]] (1 shared connections)
- [[Community 161]] (1 shared connections)
- [[User Roles & Agent Config]] (1 shared connections)

## Source Files

- `backend/om/background/error_logging.py`
- `backend/om/db/background_error.py`
- `backend/om/external_permissions/confluence/group_sync.py`

## Audit Trail

- EXTRACTED: 36 (67%)
- INFERRED: 18 (33%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*