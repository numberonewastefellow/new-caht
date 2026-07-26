# Community 718

> 20 nodes · cohesion 0.15

## Key Concepts

- **assert_tenant_id()** (10 connections) — `backend/om/tenancy/schema.py`
- **tenant_operation()** (8 connections) — `backend/om/tenancy/events.py`
- **drop_tenant_schema()** (6 connections) — `backend/om/tenancy/migrations.py`
- **deprovision_tenant()** (6 connections) — `backend/om/tenancy/provisioning.py`
- **.assign_user()** (6 connections) — `backend/om/tenancy/service.py`
- **emit_tenant_event()** (5 connections) — `backend/om/tenancy/events.py`
- **.deactivate_tenant()** (5 connections) — `backend/om/tenancy/service.py`
- **.delete_tenant()** (5 connections) — `backend/om/tenancy/service.py`
- **events.py** (4 connections) — `backend/om/tenancy/events.py`
- **TenantActionResponse** (3 connections) — `backend/om/tenancy/service.py`
- **Any** (2 connections) — `backend/om/tenancy/events.py`
- **Structured, OpenSearch-friendly event logging for tenancy operations (Standard 9** (1 connections) — `backend/om/tenancy/events.py`
- **Emit one structured tenancy log line. Never raises.** (1 connections) — `backend/om/tenancy/events.py`
- **Time an operation and emit a success/failure event automatically.      Usage::** (1 connections) — `backend/om/tenancy/events.py`
- **Drop a tenant's schema and everything in it. Strictly validated (never ``public`** (1 connections) — `backend/om/tenancy/migrations.py`
- **Permanently remove a tenant: drop its schema and every mapping row.      Stric** (1 connections) — `backend/om/tenancy/provisioning.py`
- **Raise ``ValueError`` unless ``tenant_id`` is a valid provisioned tenant id.** (1 connections) — `backend/om/tenancy/schema.py`
- **Route ``email`` to ``tenant_id``.          If the user already has an active m** (1 connections) — `backend/om/tenancy/service.py`
- **Drop a tenant's schema and all its mappings (blocking).** (1 connections) — `backend/om/tenancy/service.py`
- **Deactivate every mapping for a tenant without destroying its data.          Us** (1 connections) — `backend/om/tenancy/service.py`

## Relationships

- [[Community 1066]] (3 shared connections)
- [[Community 1133]] (3 shared connections)
- [[Community 1193]] (3 shared connections)
- [[Community 1177]] (2 shared connections)
- [[Community 106]] (1 shared connections)
- [[Community 73]] (1 shared connections)

## Source Files

- `backend/om/tenancy/events.py`
- `backend/om/tenancy/migrations.py`
- `backend/om/tenancy/provisioning.py`
- `backend/om/tenancy/schema.py`
- `backend/om/tenancy/service.py`

## Audit Trail

- EXTRACTED: 42 (61%)
- INFERRED: 27 (39%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*