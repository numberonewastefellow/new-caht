# Community 61

> 161 nodes · cohesion 0.02

## Key Concepts

- **Any** (28 connections) — `backend/om/background/celery/apps/app_base.py`
- **RedisDocumentSet** (26 connections) — `backend/om/redis/redis_document_set.py`
- **RedisTeam** (26 connections) — `backend/om/redis/redis_team.py`
- **RetryDocumentIndex** (23 connections) — `backend/om/background/celery/tasks/shared/RetryDocumentIndex.py`
- **app_base.py** (22 connections) — `backend/om/background/celery/apps/app_base.py`
- **RedisObjectHelper** (19 connections) — `backend/om/redis/redis_object_helper.py`
- **LivenessProbe** (17 connections) — `backend/om/background/celery/apps/app_base.py`
- **TenantAwareTask** (16 connections) — `backend/om/background/celery/apps/app_base.py`
- **TenantContextFilter** (16 connections) — `backend/om/background/celery/apps/app_base.py`
- **check_for_document_index_sync_task()** (15 connections) — `backend/om/background/celery/tasks/document_index/tasks.py`
- **insert_sync_record()** (14 connections) — `backend/om/db/sync_record.py`
- **ColoredFormatter** (14 connections) — `backend/om/utils/logger.py`
- **LogRecord** (13 connections) — `backend/om/background/celery/apps/app_base.py`
- **update_sync_record_status()** (12 connections) — `backend/om/db/sync_record.py`
- **tasks.py** (11 connections) — `backend/om/background/celery/tasks/document_index/tasks.py`
- **monitor_team_taskset()** (11 connections) — `backend/om/background/celery/tasks/document_index/tasks.py`
- **PlainFormatter** (11 connections) — `backend/om/utils/logger.py`
- **CeleryTaskColoredFormatter** (10 connections) — `backend/om/background/celery/apps/task_formatters.py`
- **CeleryTaskPlainFormatter** (10 connections) — `backend/om/background/celery/apps/task_formatters.py`
- **Worker** (10 connections) — `backend/om/background/celery/apps/primary.py`
- **Redis** (10 connections) — `backend/om/background/celery/tasks/document_index/tasks.py`
- **document_sync.py** (10 connections) — `backend/om/background/celery/tasks/document_index/document_sync.py`
- **try_generate_stale_document_sync_tasks()** (10 connections) — `backend/om/background/celery/tasks/document_index/document_sync.py`
- **try_generate_document_set_sync_tasks()** (10 connections) — `backend/om/background/celery/tasks/document_index/tasks.py`
- **try_generate_team_sync_tasks()** (10 connections) — `backend/om/background/celery/tasks/document_index/tasks.py`
- *... and 136 more nodes in this community*

## Relationships

- [[Community 59]] (26 shared connections)
- [[Community 199]] (13 shared connections)
- [[Community 69]] (13 shared connections)
- [[Community 120]] (9 shared connections)
- [[Document Access & Indexing]] (9 shared connections)
- [[Community 210]] (7 shared connections)
- [[Document Indexing Adapter]] (6 shared connections)
- [[Community 276]] (6 shared connections)
- [[Community 291]] (5 shared connections)
- [[Community 83]] (4 shared connections)
- [[Community 148]] (3 shared connections)
- [[Connectors (Airtable/Asana)]] (2 shared connections)

## Source Files

- `backend/om/background/celery/apps/app_base.py`
- `backend/om/background/celery/apps/primary.py`
- `backend/om/background/celery/apps/task_formatters.py`
- `backend/om/background/celery/celery_utils.py`
- `backend/om/background/celery/tasks/document_index/document_sync.py`
- `backend/om/background/celery/tasks/document_index/tasks.py`
- `backend/om/background/celery/tasks/shared/RetryDocumentIndex.py`
- `backend/om/db/sync_record.py`
- `backend/om/db/team.py`
- `backend/om/redis/redis_document_set.py`
- `backend/om/redis/redis_object_helper.py`
- `backend/om/redis/redis_team.py`
- `backend/om/utils/logger.py`

## Audit Trail

- EXTRACTED: 469 (63%)
- INFERRED: 281 (37%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*