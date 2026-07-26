# Community 99

> 123 nodes · cohesion 0.03

## Key Concepts

- **index_attempt.py** (37 connections) — `backend/om/db/index_attempt.py`
- **Session** (36 connections) — `backend/om/db/index_attempt.py`
- **get_index_attempt()** (22 connections) — `backend/om/db/index_attempt.py`
- **IndexAttempt** (20 connections) — `backend/om/db/index_attempt.py`
- **optional_telemetry()** (18 connections) — `backend/om/utils/telemetry.py`
- **SimpleJob** (14 connections) — `backend/om/background/indexing/job_client.py`
- **docfetching_proxy_task()** (13 connections) — `backend/om/background/celery/tasks/docfetching/tasks.py`
- **docfetching_task()** (12 connections) — `backend/om/background/celery/tasks/docfetching/tasks.py`
- **SimpleJobClient** (12 connections) — `backend/om/background/indexing/job_client.py`
- **SimpleJobException** (12 connections) — `backend/om/background/indexing/job_client.py`
- **mark_attempt_failed()** (10 connections) — `backend/om/db/index_attempt.py`
- **Celery** (8 connections) — `backend/om/background/celery/tasks/docfetching/tasks.py`
- **Session** (8 connections) — `backend/om/db/indexing_coordination.py`
- **ConnectorIndexingLogBuilder** (8 connections) — `backend/om/background/celery/tasks/docfetching/tasks.py`
- **tasks.py** (8 connections) — `backend/om/background/celery/tasks/docfetching/tasks.py`
- **job_client.py** (8 connections) — `backend/om/background/indexing/job_client.py`
- **SimpleJobResult** (8 connections) — `backend/om/background/celery/tasks/docfetching/tasks.py`
- **Task** (7 connections) — `backend/om/background/celery/tasks/docfetching/tasks.py`
- **test_connector_deletion()** (7 connections) — `backend/tests/integration/tests/connector/test_connector_deletion.py`
- **create_index_attempt_error()** (7 connections) — `backend/om/db/index_attempt.py`
- **get_recent_attempts_for_cc_pair()** (7 connections) — `backend/om/db/index_attempt.py`
- **mark_attempt_canceled()** (7 connections) — `backend/om/db/index_attempt.py`
- **process_job_result()** (7 connections) — `backend/om/background/celery/tasks/docfetching/tasks.py`
- **validate_active_indexing_attempts()** (7 connections) — `backend/om/background/celery/tasks/docprocessing/tasks.py`
- **SimpleJob** (7 connections) — `backend/om/background/celery/tasks/docfetching/tasks.py`
- *... and 98 more nodes in this community*

## Relationships

- [[Document Indexing Adapter]] (38 shared connections)
- [[Community 144]] (11 shared connections)
- [[Community 120]] (10 shared connections)
- [[Community 70]] (9 shared connections)
- [[Community 85]] (8 shared connections)
- [[Community 161]] (7 shared connections)
- [[Backend Agent/API Test Fixtures]] (7 shared connections)
- [[Community 119]] (6 shared connections)
- [[Connector Checkpoint & Slim Docs]] (5 shared connections)
- [[Community 218]] (4 shared connections)
- [[Community 256]] (3 shared connections)
- [[Community 73]] (2 shared connections)

## Source Files

- `backend/om/background/celery/tasks/docfetching/tasks.py`
- `backend/om/background/celery/tasks/docprocessing/heartbeat.py`
- `backend/om/background/celery/tasks/docprocessing/tasks.py`
- `backend/om/background/indexing/job_client.py`
- `backend/om/db/index_attempt.py`
- `backend/om/db/indexing_coordination.py`
- `backend/om/utils/telemetry.py`
- `backend/tests/integration/tests/connector/test_connector_deletion.py`

## Audit Trail

- EXTRACTED: 406 (69%)
- INFERRED: 184 (31%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*