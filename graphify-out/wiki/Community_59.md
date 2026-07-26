# Community 59

> 162 nodes · cohesion 0.02

## Key Concepts

- **RedisConnectorPrune** (35 connections) — `backend/om/redis/redis_connector_prune.py`
- **RedisConnectorExternalGroupSync** (33 connections) — `backend/om/redis/redis_connector_ext_group_sync.py`
- **Any** (20 connections) — `backend/om/background/celery/apps/primary.py`
- **HubPeriodicTask** (15 connections) — `backend/om/background/celery/apps/primary.py`
- **tasks.py** (15 connections) — `backend/om/background/celery/tasks/pruning/tasks.py`
- **tasks.py** (14 connections) — `backend/om/background/celery/tasks/external_group_syncing/tasks.py`
- **check_for_pruning()** (14 connections) — `backend/om/background/celery/tasks/pruning/tasks.py`
- **RedisConnectorStop** (14 connections) — `backend/om/redis/redis_connector_stop.py`
- **check_for_external_group_sync()** (13 connections) — `backend/om/background/celery/tasks/external_group_syncing/tasks.py`
- **connector_pruning_generator_task()** (13 connections) — `backend/om/background/celery/tasks/pruning/tasks.py`
- **try_creating_prune_generator_task()** (13 connections) — `backend/om/background/celery/tasks/pruning/tasks.py`
- **RedisConnectorPrunePayload** (13 connections) — `backend/om/redis/redis_connector_prune.py`
- **format_error_for_logging()** (12 connections) — `backend/om/utils/logger.py`
- **primary.py** (11 connections) — `backend/om/background/celery/apps/primary.py`
- **Task** (11 connections) — `backend/om/background/celery/apps/primary.py`
- **Redis** (11 connections) — `backend/om/background/celery/tasks/pruning/tasks.py`
- **celery_redis.py** (11 connections) — `backend/om/background/celery/celery_redis.py`
- **try_creating_external_group_sync_task()** (11 connections) — `backend/om/background/celery/tasks/external_group_syncing/tasks.py`
- **PruneCallback** (10 connections) — `backend/om/background/celery/tasks/pruning/tasks.py`
- **RedisConnectorExternalGroupSyncPayload** (10 connections) — `backend/om/redis/redis_connector_ext_group_sync.py`
- **Redis** (9 connections) — `backend/om/background/celery/tasks/external_group_syncing/tasks.py`
- **celery_get_queue_length()** (9 connections) — `backend/om/background/celery/celery_redis.py`
- **connector_external_group_sync_generator_task()** (9 connections) — `backend/om/background/celery/tasks/external_group_syncing/tasks.py`
- **on_worker_init()** (8 connections) — `backend/om/background/celery/apps/primary.py`
- **Celery** (8 connections) — `backend/om/background/celery/tasks/external_group_syncing/tasks.py`
- *... and 137 more nodes in this community*

## Relationships

- [[Document Indexing Adapter]] (34 shared connections)
- [[Community 61]] (26 shared connections)
- [[Community 199]] (19 shared connections)
- [[Community 120]] (12 shared connections)
- [[Community 69]] (7 shared connections)
- [[Community 144]] (7 shared connections)
- [[Backend Agent/API Test Fixtures]] (6 shared connections)
- [[Community 320]] (5 shared connections)
- [[Connectors (Airtable/Asana)]] (4 shared connections)
- [[Community 601]] (4 shared connections)
- [[Community 148]] (3 shared connections)
- [[Community 119]] (3 shared connections)

## Source Files

- `backend/om/background/celery/apps/primary.py`
- `backend/om/background/celery/celery_redis.py`
- `backend/om/background/celery/celery_utils.py`
- `backend/om/background/celery/tasks/external_group_syncing/tasks.py`
- `backend/om/background/celery/tasks/pruning/tasks.py`
- `backend/om/redis/redis_connector.py`
- `backend/om/redis/redis_connector_ext_group_sync.py`
- `backend/om/redis/redis_connector_prune.py`
- `backend/om/redis/redis_connector_stop.py`
- `backend/om/server/utils.py`
- `backend/om/utils/logger.py`
- `backend/scripts/celery_purge_queue.py`

## Audit Trail

- EXTRACTED: 436 (64%)
- INFERRED: 249 (36%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*