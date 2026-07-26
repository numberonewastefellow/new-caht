# Community 210

> 61 nodes · cohesion 0.07

## Key Concepts

- **team.py** (23 connections) — `backend/om/db/team.py`
- **Session** (20 connections) — `backend/om/db/team.py`
- **update_team()** (13 connections) — `backend/om/db/team.py`
- **audit_event()** (11 connections) — `backend/om/access/rbac/audit.py`
- **UUID** (10 connections) — `backend/om/db/team.py`
- **add_users_to_team()** (10 connections) — `backend/om/db/team.py`
- **prepare_team_for_deletion()** (9 connections) — `backend/om/db/team.py`
- **api.py** (9 connections) — `backend/om/server/team/api.py`
- **fetch_team()** (8 connections) — `backend/om/db/team.py`
- **fetch_teams_for_user()** (8 connections) — `backend/om/db/team.py`
- **insert_team()** (8 connections) — `backend/om/db/team.py`
- **add_users()** (8 connections) — `backend/om/server/team/api.py`
- **create_team()** (8 connections) — `backend/om/server/team/api.py`
- **_enforce()** (8 connections) — `backend/om/server/team/api.py`
- **patch_team()** (8 connections) — `backend/om/server/team/api.py`
- **Session** (7 connections) — `backend/om/server/team/api.py`
- **User** (7 connections) — `backend/om/server/team/api.py`
- **_add_memberships()** (7 connections) — `backend/om/db/team.py`
- **set_user_curator()** (7 connections) — `backend/om/server/team/api.py`
- **delete_team()** (6 connections) — `backend/om/db/team.py`
- **fetch_teams()** (6 connections) — `backend/om/db/team.py`
- **mark_team_as_synced()** (6 connections) — `backend/om/db/team.py`
- **_recompute_curator_role()** (6 connections) — `backend/om/db/team.py`
- **update_user_curator_relationship()** (6 connections) — `backend/om/db/team.py`
- **delete_team_endpoint()** (6 connections) — `backend/om/server/team/api.py`
- *... and 36 more nodes in this community*

## Relationships

- [[Community 103]] (10 shared connections)
- [[Connector Indexing Types]] (9 shared connections)
- [[Community 61]] (7 shared connections)
- [[User Roles & Agent Config]] (4 shared connections)
- [[Community 618]] (3 shared connections)
- [[Community 217]] (2 shared connections)
- [[Phoenix GraphQL DataLoaders]] (1 shared connections)

## Source Files

- `backend/om/access/rbac/audit.py`
- `backend/om/db/team.py`
- `backend/om/server/team/api.py`

## Audit Trail

- EXTRACTED: 251 (81%)
- INFERRED: 57 (19%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*