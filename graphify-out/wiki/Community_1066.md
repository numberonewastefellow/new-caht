# Community 1066

> 12 nodes · cohesion 0.20

## Key Concepts

- **provision_tenant()** (10 connections) — `backend/om/tenancy/provisioning.py`
- **provisioning.py** (7 connections) — `backend/om/tenancy/provisioning.py`
- **_seed_default_setup()** (5 connections) — `backend/om/tenancy/provisioning.py`
- **_provision_on_demand()** (4 connections) — `backend/om/tenancy/provisioning.py`
- **get_login_tenant_id()** (3 connections) — `backend/om/tenancy/provisioning.py`
- **get_or_provision_tenant()** (2 connections) — `backend/om/tenancy/provisioning.py`
- **Billing-free, on-demand tenant provisioning (clean-room).  This replaces the O** (1 connections) — `backend/om/tenancy/provisioning.py`
- **Resolve the tenant for ``email`` at login, provisioning one on first sight.** (1 connections) — `backend/om/tenancy/provisioning.py`
- **Resolve the tenant an email should authenticate into — **without** provisioning.** (1 connections) — `backend/om/tenancy/provisioning.py`
- **Run per-tenant runtime setup inside the freshly-migrated tenant schema.      T** (1 connections) — `backend/om/tenancy/provisioning.py`
- **Create a brand-new tenant and route ``admin_email`` to it. Returns the tenant id** (1 connections) — `backend/om/tenancy/provisioning.py`
- **Serialize concurrent first-logins for one email behind a Postgres advisory lock.** (1 connections) — `backend/om/tenancy/provisioning.py`

## Relationships

- [[Community 718]] (3 shared connections)
- [[Community 1133]] (2 shared connections)
- [[Community 143]] (1 shared connections)
- [[Community 635]] (1 shared connections)
- [[Community 1177]] (1 shared connections)
- [[Community 1193]] (1 shared connections)
- [[Community 85]] (1 shared connections)
- [[Community 884]] (1 shared connections)

## Source Files

- `backend/om/tenancy/provisioning.py`

## Audit Trail

- EXTRACTED: 27 (73%)
- INFERRED: 10 (27%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*