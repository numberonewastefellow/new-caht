# Community 1193

> 9 nodes · cohesion 0.22

## Key Concepts

- **TenantService** (7 connections) — `backend/om/tenancy/service.py`
- **.create_tenant()** (3 connections) — `backend/om/tenancy/service.py`
- **.list_tenants()** (3 connections) — `backend/om/tenancy/service.py`
- **service.py** (2 connections) — `backend/om/tenancy/service.py`
- **TenantListResponse** (1 connections) — `backend/om/tenancy/service.py`
- **Tenant-administration service (clean-room, no billing).  Thin orchestration la** (1 connections) — `backend/om/tenancy/service.py`
- **Superuser-facing tenant administration. All methods are side-effect logged.** (1 connections) — `backend/om/tenancy/service.py`
- **Every tenant that appears in the mapping table, with user counts.** (1 connections) — `backend/om/tenancy/service.py`
- **Provision a new tenant (blocking) and return its id.          Delegates to :fu** (1 connections) — `backend/om/tenancy/service.py`

## Relationships

- [[Community 718]] (3 shared connections)
- [[Community 1066]] (1 shared connections)

## Source Files

- `backend/om/tenancy/service.py`

## Audit Trail

- EXTRACTED: 19 (95%)
- INFERRED: 1 (5%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*