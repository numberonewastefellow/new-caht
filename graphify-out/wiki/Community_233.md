# Community 233

> 57 nodes · cohesion 0.05

## Key Concepts

- **no_bastion_cleanup_utils.py** (11 connections) — `backend/scripts/tenant_cleanup/no_bastion_cleanup_utils.py`
- **no_bastion_cleanup_tenants.py** (10 connections) — `backend/scripts/tenant_cleanup/no_bastion_cleanup_tenants.py`
- **cleanup_tenant()** (7 connections) — `backend/scripts/tenant_cleanup/no_bastion_cleanup_tenants.py`
- **no_bastion_analyze_tenants.py** (6 connections) — `backend/scripts/tenant_cleanup/no_bastion_analyze_tenants.py`
- **main()** (6 connections) — `backend/scripts/tenant_cleanup/no_bastion_analyze_tenants.py`
- **find_background_pod()** (6 connections) — `backend/scripts/tenant_cleanup/no_bastion_cleanup_utils.py`
- **mark_tenant_connectors_for_deletion()** (6 connections) — `backend/scripts/tenant_cleanup/no_bastion_mark_connectors.py`
- **safe_print()** (6 connections) — `backend/scripts/tenant_cleanup/no_bastion_mark_connectors.py`
- **TenantNotFoundInControlPlaneError** (5 connections) — `backend/scripts/tenant_cleanup/no_bastion_cleanup_utils.py`
- **run_connector_deletion()** (5 connections) — `backend/scripts/tenant_cleanup/no_bastion_mark_connectors.py`
- **Any** (4 connections) — `backend/scripts/tenant_cleanup/no_bastion_analyze_tenants.py`
- **analyze_tenants()** (4 connections) — `backend/scripts/tenant_cleanup/no_bastion_analyze_tenants.py`
- **collect_control_plane_data_from_pod()** (4 connections) — `backend/scripts/tenant_cleanup/no_bastion_analyze_tenants.py`
- **collect_tenant_data()** (4 connections) — `backend/scripts/tenant_cleanup/no_bastion_analyze_tenants.py`
- **find_recent_tenant_data()** (4 connections) — `backend/scripts/tenant_cleanup/no_bastion_analyze_tenants.py`
- **check_documents_deleted()** (4 connections) — `backend/scripts/tenant_cleanup/no_bastion_cleanup_tenants.py`
- **cleanup_control_plane()** (4 connections) — `backend/scripts/tenant_cleanup/no_bastion_cleanup_tenants.py`
- **drop_data_plane_schema()** (4 connections) — `backend/scripts/tenant_cleanup/no_bastion_cleanup_tenants.py`
- **main()** (4 connections) — `backend/scripts/tenant_cleanup/no_bastion_cleanup_tenants.py`
- **execute_control_plane_delete()** (4 connections) — `backend/scripts/tenant_cleanup/no_bastion_cleanup_utils.py`
- **execute_control_plane_query_from_pod()** (4 connections) — `backend/scripts/tenant_cleanup/no_bastion_cleanup_utils.py`
- **get_tenant_status()** (4 connections) — `backend/scripts/tenant_cleanup/no_bastion_cleanup_utils.py`
- **no_bastion_mark_connectors.py** (4 connections) — `backend/scripts/tenant_cleanup/no_bastion_mark_connectors.py`
- **main()** (4 connections) — `backend/scripts/tenant_cleanup/no_bastion_mark_connectors.py`
- **get_tenant_index_name()** (3 connections) — `backend/scripts/tenant_cleanup/no_bastion_cleanup_tenants.py`
- *... and 32 more nodes in this community*

## Relationships

- [[Salesforce Connector]] (7 shared connections)
- [[Community 106]] (3 shared connections)
- [[Community 260]] (1 shared connections)

## Source Files

- `backend/scripts/tenant_cleanup/no_bastion_analyze_tenants.py`
- `backend/scripts/tenant_cleanup/no_bastion_cleanup_tenants.py`
- `backend/scripts/tenant_cleanup/no_bastion_cleanup_utils.py`
- `backend/scripts/tenant_cleanup/no_bastion_mark_connectors.py`

## Audit Trail

- EXTRACTED: 152 (90%)
- INFERRED: 17 (10%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*