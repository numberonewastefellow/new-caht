# Community 1009

> 13 nodes · cohesion 0.22

## Key Concepts

- **setup_test_tenants()** (8 connections) — `backend/tests/integration/multitenant_tests/syncing/test_search_permissions.py`
- **test_search_permissions.py** (6 connections) — `backend/tests/integration/multitenant_tests/syncing/test_search_permissions.py`
- **test_multi_tenant_access_control()** (3 connections) — `backend/tests/integration/multitenant_tests/syncing/test_search_permissions.py`
- **test_tenant1_can_access_own_documents()** (3 connections) — `backend/tests/integration/multitenant_tests/syncing/test_search_permissions.py`
- **test_tenant1_cannot_access_tenant2_documents()** (3 connections) — `backend/tests/integration/multitenant_tests/syncing/test_search_permissions.py`
- **test_tenant2_can_access_own_documents()** (3 connections) — `backend/tests/integration/multitenant_tests/syncing/test_search_permissions.py`
- **test_tenant2_cannot_access_tenant1_documents()** (3 connections) — `backend/tests/integration/multitenant_tests/syncing/test_search_permissions.py`
- **Test that Tenant 1 can access its own documents but not Tenant 2's.** (1 connections) — `backend/tests/integration/multitenant_tests/syncing/test_search_permissions.py`
- **Test that Tenant 2 can access its own documents but not Tenant 1's.** (1 connections) — `backend/tests/integration/multitenant_tests/syncing/test_search_permissions.py`
- **Test that Tenant 1 cannot access Tenant 2's documents.** (1 connections) — `backend/tests/integration/multitenant_tests/syncing/test_search_permissions.py`
- **Helper function to set up test tenants with documents and users.** (1 connections) — `backend/tests/integration/multitenant_tests/syncing/test_search_permissions.py`
- **Test that Tenant 2 cannot access Tenant 1's documents.** (1 connections) — `backend/tests/integration/multitenant_tests/syncing/test_search_permissions.py`
- **Legacy test for multi-tenant access control.** (1 connections) — `backend/tests/integration/multitenant_tests/syncing/test_search_permissions.py`

## Relationships

- [[Community 67]] (1 shared connections)

## Source Files

- `backend/tests/integration/multitenant_tests/syncing/test_search_permissions.py`

## Audit Trail

- EXTRACTED: 35 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*