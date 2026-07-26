# Community 199

> 64 nodes · cohesion 0.06

## Key Concepts

- **RedisConnectorPermissionSync** (38 connections) — `backend/om/redis/redis_connector_doc_perm_sync.py`
- **LoggerContextVars** (23 connections) — `backend/om/utils/logger.py`
- **connector_permission_sync_generator_task()** (19 connections) — `backend/om/background/celery/tasks/doc_permission_syncing/tasks.py`
- **tasks.py** (18 connections) — `backend/om/background/celery/tasks/doc_permission_syncing/tasks.py`
- **RedisConnectorPermissionSyncPayload** (16 connections) — `backend/om/redis/redis_connector_doc_perm_sync.py`
- **Redis** (14 connections) — `backend/om/background/celery/tasks/doc_permission_syncing/tasks.py`
- **PermissionSyncCallback** (14 connections) — `backend/om/background/celery/tasks/doc_permission_syncing/tasks.py`
- **RedisConnector** (13 connections) — `backend/om/background/celery/tasks/doc_permission_syncing/tasks.py`
- **check_for_doc_permissions_sync()** (12 connections) — `backend/om/background/celery/tasks/doc_permission_syncing/tasks.py`
- **try_creating_permissions_sync_task()** (12 connections) — `backend/om/background/celery/tasks/doc_permission_syncing/tasks.py`
- **Celery** (10 connections) — `backend/om/background/celery/tasks/doc_permission_syncing/tasks.py`
- **RedisLock** (10 connections) — `backend/om/background/celery/tasks/doc_permission_syncing/tasks.py`
- **Task** (10 connections) — `backend/om/background/celery/tasks/doc_permission_syncing/tasks.py`
- **ConnectorCredentialPair** (9 connections) — `backend/om/background/celery/tasks/doc_permission_syncing/tasks.py`
- **ElementExternalAccess** (9 connections) — `backend/om/background/celery/tasks/doc_permission_syncing/tasks.py`
- **Session** (9 connections) — `backend/om/background/celery/tasks/doc_permission_syncing/tasks.py`
- **monitor_ccpair_permissions_taskset()** (8 connections) — `backend/om/background/celery/tasks/doc_permission_syncing/tasks.py`
- **validate_permission_sync_fences()** (8 connections) — `backend/om/background/celery/tasks/doc_permission_syncing/tasks.py`
- **validate_permission_sync_fence()** (6 connections) — `backend/om/background/celery/tasks/doc_permission_syncing/tasks.py`
- **.update_db()** (6 connections) — `backend/om/redis/redis_connector_doc_perm_sync.py`
- **Redis** (5 connections) — `backend/om/redis/redis_connector_doc_perm_sync.py`
- **_fail_doc_permission_sync_attempt()** (5 connections) — `backend/om/background/celery/tasks/doc_permission_syncing/tasks.py`
- **_is_external_doc_permissions_sync_due()** (5 connections) — `backend/om/background/celery/tasks/doc_permission_syncing/tasks.py`
- **PermissionSyncResult** (5 connections) — `backend/om/redis/redis_connector_doc_perm_sync.py`
- **.__init__()** (4 connections) — `backend/om/background/celery/tasks/doc_permission_syncing/tasks.py`
- *... and 39 more nodes in this community*

## Relationships

- [[Document External Access]] (27 shared connections)
- [[Document Indexing Adapter]] (20 shared connections)
- [[Community 59]] (19 shared connections)
- [[Community 61]] (13 shared connections)
- [[Community 70]] (9 shared connections)
- [[Backend Agent/API Test Fixtures]] (4 shared connections)
- [[Community 218]] (3 shared connections)
- [[Community 83]] (2 shared connections)
- [[Community 120]] (2 shared connections)
- [[Community 69]] (2 shared connections)
- [[Community 143]] (2 shared connections)
- [[Community 403]] (2 shared connections)

## Source Files

- `backend/om/background/celery/tasks/doc_permission_syncing/tasks.py`
- `backend/om/redis/redis_connector_doc_perm_sync.py`
- `backend/om/utils/logger.py`

## Audit Trail

- EXTRACTED: 182 (53%)
- INFERRED: 164 (47%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*