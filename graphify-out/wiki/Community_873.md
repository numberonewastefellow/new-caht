# Community 873

> 16 nodes · cohesion 0.17

## Key Concepts

- **cleanup_tenants.py** (9 connections) — `backend/scripts/tenant_cleanup/cleanup_tenants.py`
- **cleanup_tenant()** (7 connections) — `backend/scripts/tenant_cleanup/cleanup_tenants.py`
- **check_documents_deleted()** (4 connections) — `backend/scripts/tenant_cleanup/cleanup_tenants.py`
- **cleanup_control_plane()** (4 connections) — `backend/scripts/tenant_cleanup/cleanup_tenants.py`
- **drop_data_plane_schema()** (4 connections) — `backend/scripts/tenant_cleanup/cleanup_tenants.py`
- **get_tenant_index_name()** (3 connections) — `backend/scripts/tenant_cleanup/cleanup_tenants.py`
- **get_tenant_users()** (3 connections) — `backend/scripts/tenant_cleanup/cleanup_tenants.py`
- **main()** (2 connections) — `backend/scripts/tenant_cleanup/cleanup_tenants.py`
- **signal_handler()** (2 connections) — `backend/scripts/tenant_cleanup/cleanup_tenants.py`
- **Get list of user emails from the tenant's data plane schema.      Args:** (1 connections) — `backend/scripts/tenant_cleanup/cleanup_tenants.py`
- **Check if all documents and connector credential pairs have been deleted.      Ra** (1 connections) — `backend/scripts/tenant_cleanup/cleanup_tenants.py`
- **Drop the PostgreSQL schema for the given tenant by running script on pod.** (1 connections) — `backend/scripts/tenant_cleanup/cleanup_tenants.py`
- **Clean up control plane data (tenants table, subscription table, etc.)      Delet** (1 connections) — `backend/scripts/tenant_cleanup/cleanup_tenants.py`
- **Main cleanup function that orchestrates all cleanup steps.      Args:         te** (1 connections) — `backend/scripts/tenant_cleanup/cleanup_tenants.py`
- **Handle termination signals by killing active subprocess.** (1 connections) — `backend/scripts/tenant_cleanup/cleanup_tenants.py`
- **Get the default index name for the given tenant by running script on pod.** (1 connections) — `backend/scripts/tenant_cleanup/cleanup_tenants.py`

## Relationships

- [[Salesforce Connector]] (3 shared connections)
- [[Community 106]] (1 shared connections)
- [[Community 776]] (1 shared connections)

## Source Files

- `backend/scripts/tenant_cleanup/cleanup_tenants.py`

## Audit Trail

- EXTRACTED: 41 (91%)
- INFERRED: 4 (9%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*