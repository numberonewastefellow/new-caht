# Community 635

> 24 nodes · cohesion 0.12

## Key Concepts

- **get_shared_schema_session()** (19 connections) — `backend/om/tenancy/context.py`
- **TenantMappingRepository** (13 connections) — `backend/om/tenancy/repository.py`
- **.assign()** (4 connections) — `backend/om/tenancy/repository.py`
- **.move_user()** (4 connections) — `backend/om/tenancy/repository.py`
- **.get_active_tenant_for_email()** (3 connections) — `backend/om/tenancy/repository.py`
- **.list_tenant_ids()** (3 connections) — `backend/om/tenancy/repository.py`
- **.remove()** (3 connections) — `backend/om/tenancy/repository.py`
- **.resolve_or_activate()** (3 connections) — `backend/om/tenancy/repository.py`
- **.set_tenant_active()** (3 connections) — `backend/om/tenancy/repository.py`
- **.user_counts_by_tenant()** (3 connections) — `backend/om/tenancy/repository.py`
- **repository.py** (2 connections) — `backend/om/tenancy/repository.py`
- **.email_has_any_mapping()** (2 connections) — `backend/om/tenancy/repository.py`
- **.remove_all_for_tenant()** (2 connections) — `backend/om/tenancy/repository.py`
- **Session pinned to the global ``public`` schema. Use ONLY for PUBLIC_SCHEMA_TABLE** (1 connections) — `backend/om/tenancy/context.py`
- **Data access for the global ``user_tenant_mapping`` table (email -> tenant routin** (1 connections) — `backend/om/tenancy/repository.py`
- **Idempotently add an (email, tenant_id) mapping.** (1 connections) — `backend/om/tenancy/repository.py`
- **Remove a single mapping. Returns rows deleted.** (1 connections) — `backend/om/tenancy/repository.py`
- **Activate/deactivate every mapping for a tenant. Returns rows affected.** (1 connections) — `backend/om/tenancy/repository.py`
- **Deactivate all of a user's mappings and activate them on ``to_tenant``.** (1 connections) — `backend/om/tenancy/repository.py`
- **Repository over the global email->tenant mapping table.** (1 connections) — `backend/om/tenancy/repository.py`
- **Return the tenant the email is actively bound to, if any.** (1 connections) — `backend/om/tenancy/repository.py`
- **Login routing: return the active tenant, else adopt an invitation.          If** (1 connections) — `backend/om/tenancy/repository.py`
- **Distinct tenant ids that appear in the mapping table.** (1 connections) — `backend/om/tenancy/repository.py`
- **Map tenant_id -> (active_count, total_count).** (1 connections) — `backend/om/tenancy/repository.py`

## Relationships

- [[Community 884]] (4 shared connections)
- [[Community 1246]] (3 shared connections)
- [[User Roles & Agent Config]] (2 shared connections)
- [[Community 73]] (1 shared connections)
- [[Community 1066]] (1 shared connections)

## Source Files

- `backend/om/tenancy/context.py`
- `backend/om/tenancy/repository.py`

## Audit Trail

- EXTRACTED: 47 (63%)
- INFERRED: 28 (37%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*