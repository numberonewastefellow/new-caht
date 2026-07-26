# Community 884

> 15 nodes · cohesion 0.15

## Key Concepts

- **get_tenant_session()** (8 connections) — `backend/om/tenancy/context.py`
- **context.py** (7 connections) — `backend/om/tenancy/context.py`
- **Session** (4 connections) — `backend/om/tenancy/context.py`
- **get_current_tenant_session()** (4 connections) — `backend/om/tenancy/context.py`
- **active_user_count_for_tenant()** (4 connections) — `backend/om/tenancy/invitations.py`
- **get_tenant_session_dependency()** (3 connections) — `backend/om/tenancy/context.py`
- **.active_user_count_in_schema()** (3 connections) — `backend/om/tenancy/repository.py`
- **tenant_context()** (2 connections) — `backend/om/tenancy/context.py`
- **Contract 3 — the single tenant-context surface every workstream imports.  This** (1 connections) — `backend/om/tenancy/context.py`
- **FastAPI dependency yielding a tenant-scoped session.      Rejects unauthentica** (1 connections) — `backend/om/tenancy/context.py`
- **Temporarily bind the current tenant for a block of work (background jobs, tests)** (1 connections) — `backend/om/tenancy/context.py`
- **Session for the tenant currently bound in the contextvar (request-scoped default** (1 connections) — `backend/om/tenancy/context.py`
- **Session for an explicit tenant (background jobs / cross-tenant iteration).** (1 connections) — `backend/om/tenancy/context.py`
- **Number of real, active seats in a tenant.      A seat counts when the email has** (1 connections) — `backend/om/tenancy/invitations.py`
- **Count users that are active *inside the tenant schema* (real seats).** (1 connections) — `backend/om/tenancy/repository.py`

## Relationships

- [[Community 635]] (4 shared connections)
- [[Community 161]] (1 shared connections)
- [[Backend Agent/API Test Fixtures]] (1 shared connections)
- [[Community 73]] (1 shared connections)
- [[Community 742]] (1 shared connections)
- [[Community 1066]] (1 shared connections)
- [[Community 1246]] (1 shared connections)

## Source Files

- `backend/om/tenancy/context.py`
- `backend/om/tenancy/invitations.py`
- `backend/om/tenancy/repository.py`

## Audit Trail

- EXTRACTED: 33 (79%)
- INFERRED: 9 (21%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*