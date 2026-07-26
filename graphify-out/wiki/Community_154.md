# Community 154

> 82 nodes · cohesion 0.05

## Key Concepts

- **PermissionService** (32 connections) — `backend/om/access/rbac/service.py`
- **test_rbac.py** (19 connections) — `backend/tests/unit/om/access/test_rbac.py`
- **FakeRepo** (17 connections) — `backend/tests/unit/om/access/test_rbac.py`
- **User** (17 connections) — `backend/om/access/rbac/service.py`
- **Permission** (17 connections) — `backend/om/access/rbac/permissions.py`
- **AccessDecision** (14 connections) — `backend/om/access/rbac/service.py`
- **ResourceType** (13 connections) — `backend/om/access/rbac/permissions.py`
- **.decide_team_permission()** (13 connections) — `backend/om/access/rbac/service.py`
- **Session** (11 connections) — `backend/om/access/rbac/service.py`
- **global_permissions_for()** (11 connections) — `backend/om/access/rbac/permissions.py`
- **_user()** (10 connections) — `backend/tests/unit/om/access/test_rbac.py`
- **.has_global_permission()** (10 connections) — `backend/om/access/rbac/service.py`
- **.decide_curate_resource()** (9 connections) — `backend/om/access/rbac/service.py`
- **Permission** (8 connections) — `backend/om/access/rbac/service.py`
- **permissions.py** (7 connections) — `backend/om/access/rbac/permissions.py`
- **._allow()** (7 connections) — `backend/om/access/rbac/service.py`
- **._deny()** (7 connections) — `backend/om/access/rbac/service.py`
- **PermissionDenied** (6 connections) — `backend/om/access/rbac/models.py`
- **TeamRole** (6 connections) — `backend/om/access/rbac/permissions.py`
- **.decide_create_team()** (6 connections) — `backend/om/access/rbac/service.py`
- **.decide_delete_team()** (6 connections) — `backend/om/access/rbac/service.py`
- **UserRole** (5 connections) — `backend/om/access/rbac/service.py`
- **AccessDecision** (5 connections) — `backend/om/access/rbac/models.py`
- **team_permissions_for()** (5 connections) — `backend/om/access/rbac/permissions.py`
- **.decide_edit_team()** (5 connections) — `backend/om/access/rbac/service.py`
- *... and 57 more nodes in this community*

## Relationships

- [[User Roles & Agent Config]] (14 shared connections)
- [[Community 618]] (8 shared connections)
- [[Community 72]] (7 shared connections)
- [[Community 260]] (1 shared connections)

## Source Files

- `backend/om/access/rbac/models.py`
- `backend/om/access/rbac/permissions.py`
- `backend/om/access/rbac/service.py`
- `backend/tests/unit/om/access/test_rbac.py`

## Audit Trail

- EXTRACTED: 300 (76%)
- INFERRED: 94 (24%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*