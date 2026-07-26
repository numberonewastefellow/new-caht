# Community 1133

> 10 nodes · cohesion 0.24

## Key Concepts

- **migrations.py** (7 connections) — `backend/om/tenancy/migrations.py`
- **_build_alembic_config()** (5 connections) — `backend/om/tenancy/migrations.py`
- **create_tenant_schema()** (5 connections) — `backend/om/tenancy/migrations.py`
- **run_migrations_for_schema()** (5 connections) — `backend/om/tenancy/migrations.py`
- **run_migrations_for_all_tenants()** (3 connections) — `backend/om/tenancy/migrations.py`
- **Config** (1 connections) — `backend/om/tenancy/migrations.py`
- **Per-tenant schema lifecycle + Alembic migration runner (clean-room).  Schema-p** (1 connections) — `backend/om/tenancy/migrations.py`
- **Create the tenant's schema if absent. Returns True if it was created.      Val** (1 connections) — `backend/om/tenancy/migrations.py`
- **Apply the full migration chain to a single tenant schema.** (1 connections) — `backend/om/tenancy/migrations.py`
- **Apply the migration chain to every tenant schema (and the default schema).** (1 connections) — `backend/om/tenancy/migrations.py`

## Relationships

- [[Community 718]] (3 shared connections)
- [[Community 73]] (2 shared connections)
- [[Community 1066]] (2 shared connections)
- [[Community 1177]] (1 shared connections)

## Source Files

- `backend/om/tenancy/migrations.py`

## Audit Trail

- EXTRACTED: 24 (80%)
- INFERRED: 6 (20%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*