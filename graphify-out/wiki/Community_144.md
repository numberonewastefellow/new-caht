# Community 144

> 88 nodes · cohesion 0.04

## Key Concepts

- **connector_document_extraction()** (33 connections) — `backend/om/background/indexing/run_docfetching.py`
- **HierarchyNodeCacheEntry** (30 connections) — `backend/om/redis/redis_hierarchy.py`
- **MemoryTracer** (20 connections) — `backend/om/background/indexing/memory_tracer.py`
- **run_docfetching.py** (15 connections) — `backend/om/background/indexing/run_docfetching.py`
- **Celery** (13 connections) — `backend/om/background/indexing/run_docfetching.py`
- **datetime** (11 connections) — `backend/om/background/indexing/run_docfetching.py`
- **IndexAttempt** (11 connections) — `backend/om/background/indexing/run_docfetching.py`
- **IndexingHeartbeatInterface** (11 connections) — `backend/om/background/indexing/run_docfetching.py`
- **Session** (11 connections) — `backend/om/background/indexing/run_docfetching.py`
- **ConnectorFailure** (10 connections) — `backend/om/background/indexing/run_docfetching.py`
- **Document** (10 connections) — `backend/om/background/indexing/run_docfetching.py`
- **DocumentBatchStorage** (10 connections) — `backend/om/background/indexing/run_docfetching.py`
- **IndexModelStatus** (10 connections) — `backend/om/background/indexing/run_docfetching.py`
- **OmCeleryPriority** (10 connections) — `backend/om/background/indexing/run_docfetching.py`
- **ConnectorRunner** (10 connections) — `backend/om/background/indexing/run_docfetching.py`
- **HierarchyConnector** (10 connections) — `backend/om/connectors/interfaces.py`
- **check_for_hierarchy_fetching()** (9 connections) — `backend/om/background/celery/tasks/hierarchyfetching/tasks.py`
- **checkpointing_utils.py** (9 connections) — `backend/om/background/indexing/checkpointing_utils.py`
- **get_latest_valid_checkpoint()** (9 connections) — `backend/om/background/indexing/checkpointing_utils.py`
- **_check_connector_and_attempt_status()** (9 connections) — `backend/om/background/indexing/run_docfetching.py`
- **_get_connector_runner()** (9 connections) — `backend/om/background/indexing/run_docfetching.py`
- **tasks.py** (8 connections) — `backend/om/background/celery/tasks/hierarchyfetching/tasks.py`
- **_run_hierarchy_extraction()** (8 connections) — `backend/om/background/celery/tasks/hierarchyfetching/tasks.py`
- **_try_creating_hierarchy_fetching_task()** (8 connections) — `backend/om/background/celery/tasks/hierarchyfetching/tasks.py`
- **save_checkpoint()** (8 connections) — `backend/om/background/indexing/checkpointing_utils.py`
- *... and 63 more nodes in this community*

## Relationships

- [[Connectors (Airtable/Asana)]] (25 shared connections)
- [[Document Indexing Adapter]] (24 shared connections)
- [[Connector Checkpoint & Slim Docs]] (22 shared connections)
- [[Document External Access]] (14 shared connections)
- [[Connector Indexing Types]] (12 shared connections)
- [[Community 99]] (11 shared connections)
- [[Salesforce Connector]] (7 shared connections)
- [[Community 351]] (7 shared connections)
- [[Community 59]] (7 shared connections)
- [[Community 120]] (6 shared connections)
- [[Backend Agent/API Test Fixtures]] (4 shared connections)
- [[Community 69]] (3 shared connections)

## Source Files

- `backend/om/background/celery/tasks/hierarchyfetching/tasks.py`
- `backend/om/background/indexing/checkpointing_utils.py`
- `backend/om/background/indexing/memory_tracer.py`
- `backend/om/background/indexing/run_docfetching.py`
- `backend/om/connectors/interfaces.py`
- `backend/om/connectors/models.py`
- `backend/om/redis/redis_hierarchy.py`
- `backend/om/utils/object_size_check.py`

## Audit Trail

- EXTRACTED: 248 (53%)
- INFERRED: 219 (47%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*