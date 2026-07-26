# Community 256

> 54 nodes · cohesion 0.07

## Key Concepts

- **tasks.py** (22 connections) — `backend/om/background/celery/tasks/monitoring/tasks.py`
- **monitor_background_processes()** (12 connections) — `backend/om/background/celery/tasks/monitoring/tasks.py`
- **get_db_current_time()** (11 connections) — `backend/om/db/engine/time_utils.py`
- **_collect_connector_metrics()** (11 connections) — `backend/om/background/celery/tasks/monitoring/tasks.py`
- **Metric** (10 connections) — `backend/om/background/celery/tasks/monitoring/tasks.py`
- **Redis** (9 connections) — `backend/om/background/celery/tasks/monitoring/tasks.py`
- **_build_connector_final_metrics()** (9 connections) — `backend/om/background/celery/tasks/monitoring/tasks.py`
- **_collect_sync_metrics()** (9 connections) — `backend/om/background/celery/tasks/monitoring/tasks.py`
- **_build_connector_start_latency_metric()** (8 connections) — `backend/om/background/celery/tasks/monitoring/tasks.py`
- **Task** (7 connections) — `backend/om/background/celery/tasks/monitoring/tasks.py`
- **_has_metric_been_emitted()** (7 connections) — `backend/om/background/celery/tasks/monitoring/tasks.py`
- **monitor_celery_queues_helper()** (7 connections) — `backend/om/background/celery/tasks/monitoring/tasks.py`
- **get_old_index_attempts()** (6 connections) — `backend/om/background/indexing/index_attempt_utils.py`
- **_collect_queue_metrics()** (6 connections) — `backend/om/background/celery/tasks/monitoring/tasks.py`
- **monitor_process_memory()** (6 connections) — `backend/om/background/celery/tasks/monitoring/tasks.py`
- **emit_process_memory()** (5 connections) — `backend/om/background/celery/memory_monitoring.py`
- **build_job_id()** (5 connections) — `backend/om/background/celery/tasks/monitoring/tasks.py`
- **cleanup_index_attempts()** (4 connections) — `backend/om/background/indexing/index_attempt_utils.py`
- **_mark_metric_as_emitted()** (4 connections) — `backend/om/background/celery/tasks/monitoring/tasks.py`
- **is_running_in_container()** (4 connections) — `backend/om/utils/logger.py`
- **ConnectorCredentialPair** (3 connections) — `backend/om/background/celery/tasks/monitoring/tasks.py`
- **IndexAttempt** (3 connections) — `backend/om/background/celery/tasks/monitoring/tasks.py`
- **Session** (3 connections) — `backend/om/background/celery/tasks/monitoring/tasks.py`
- **cloud_monitor_celery_pidbox()** (3 connections) — `backend/om/background/celery/tasks/monitoring/tasks.py`
- **cloud_monitor_celery_queues()** (3 connections) — `backend/om/background/celery/tasks/monitoring/tasks.py`
- *... and 29 more nodes in this community*

## Relationships

- [[Community 70]] (7 shared connections)
- [[Document Indexing Adapter]] (5 shared connections)
- [[Community 99]] (3 shared connections)
- [[Community 59]] (3 shared connections)
- [[Community 291]] (2 shared connections)
- [[Connectors (Airtable/Asana)]] (1 shared connections)
- [[Community 522]] (1 shared connections)
- [[Community 106]] (1 shared connections)
- [[Community 73]] (1 shared connections)
- [[Community 148]] (1 shared connections)
- [[Community 161]] (1 shared connections)
- [[Community 85]] (1 shared connections)

## Source Files

- `backend/om/background/celery/memory_monitoring.py`
- `backend/om/background/celery/tasks/monitoring/tasks.py`
- `backend/om/background/indexing/index_attempt_utils.py`
- `backend/om/db/engine/time_utils.py`
- `backend/om/utils/logger.py`
- `phoenix/app/tests/utils/testServer.mjs`

## Audit Trail

- EXTRACTED: 187 (84%)
- INFERRED: 35 (16%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*