# Community 1177

> 10 nodes · cohesion 0.20

## Key Concepts

- **schema.py** (5 connections) — `backend/om/tenancy/schema.py`
- **list_tenant_schemas()** (4 connections) — `backend/om/tenancy/migrations.py`
- **is_tenant_id()** (4 connections) — `backend/om/tenancy/schema.py`
- **is_safe_schema_name()** (3 connections) — `backend/om/tenancy/schema.py`
- **new_tenant_id()** (3 connections) — `backend/om/tenancy/schema.py`
- **Return every provisioned tenant schema name (excludes system + default schemas).** (1 connections) — `backend/om/tenancy/migrations.py`
- **Tenant identifier / Postgres schema-name rules.  A tenant id doubles as its Po** (1 connections) — `backend/om/tenancy/schema.py`
- **True if ``name`` is safe to interpolate as a Postgres schema identifier.** (1 connections) — `backend/om/tenancy/schema.py`
- **True if ``tenant_id`` has the strict provisioned-tenant shape.** (1 connections) — `backend/om/tenancy/schema.py`
- **Mint a fresh, well-formed tenant id.** (1 connections) — `backend/om/tenancy/schema.py`

## Relationships

- [[Community 718]] (2 shared connections)
- [[Community 73]] (1 shared connections)
- [[Community 1133]] (1 shared connections)
- [[Community 103]] (1 shared connections)
- [[Community 1066]] (1 shared connections)

## Source Files

- `backend/om/tenancy/migrations.py`
- `backend/om/tenancy/schema.py`

## Audit Trail

- EXTRACTED: 19 (79%)
- INFERRED: 5 (21%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*