# Community 69

> 149 nodes · cohesion 0.02

## Key Concepts

- **get_redis_client()** (77 connections) — `backend/om/redis/redis_pool.py`
- **DocumentBatchPrepareContext** (41 connections) — `backend/om/indexing/indexing_pipeline.py`
- **KnowledgeFileIndexingAdapter** (15 connections) — `backend/om/indexing/adapters/user_file_indexing_adapter.py`
- **try_creating_docfetching_task()** (14 connections) — `backend/om/background/celery/tasks/docfetching/task_creation_utils.py`
- **models.py** (13 connections) — `backend/om/indexing/models.py`
- **tasks.py** (13 connections) — `backend/om/background/celery/tasks/user_file_processing/tasks.py`
- **_create_test_cc_pair()** (12 connections) — `backend/tests/external_dependency_unit/celery/test_docfetching_priority.py`
- **process_single_user_file_delete()** (12 connections) — `backend/om/background/celery/tasks/user_file_processing/tasks.py`
- **_process_user_file_with_indexing()** (11 connections) — `backend/om/background/celery/tasks/user_file_processing/tasks.py`
- **Task** (10 connections) — `backend/om/background/celery/tasks/user_file_processing/tasks.py`
- **.test_priority_based_on_last_successful_index_time()** (10 connections) — `backend/tests/external_dependency_unit/celery/test_docfetching_priority.py`
- **process_single_user_file_project_sync()** (10 connections) — `backend/om/background/celery/tasks/user_file_processing/tasks.py`
- **.build_metadata_aware_chunks()** (9 connections) — `backend/om/indexing/adapters/document_indexing_adapter.py`
- **.build_metadata_aware_chunks()** (9 connections) — `backend/om/indexing/adapters/user_file_indexing_adapter.py`
- **UUID** (9 connections) — `backend/om/background/celery/tasks/user_file_processing/tasks.py`
- **.test_lock_released_after_successful_task_creation()** (9 connections) — `backend/tests/external_dependency_unit/celery/test_docfetching_priority.py`
- **.test_no_task_created_when_deleting()** (9 connections) — `backend/tests/external_dependency_unit/celery/test_docfetching_priority.py`
- **.test_redis_lock_prevents_concurrent_task_creation()** (9 connections) — `backend/tests/external_dependency_unit/celery/test_docfetching_priority.py`
- **ChunkEmbedding** (9 connections) — `backend/om/indexing/models.py`
- **process_single_user_file()** (9 connections) — `backend/om/background/celery/tasks/user_file_processing/tasks.py`
- **_process_user_file_without_vector_db()** (9 connections) — `backend/om/background/celery/tasks/user_file_processing/tasks.py`
- **Session** (8 connections) — `backend/tests/external_dependency_unit/celery/test_docfetching_priority.py`
- **_create_test_connector()** (8 connections) — `backend/tests/external_dependency_unit/celery/test_docfetching_priority.py`
- **_create_test_credential()** (8 connections) — `backend/tests/external_dependency_unit/celery/test_docfetching_priority.py`
- **_create_test_search_settings()** (8 connections) — `backend/tests/external_dependency_unit/celery/test_docfetching_priority.py`
- *... and 124 more nodes in this community*

## Relationships

- [[Document Access & Indexing]] (38 shared connections)
- [[Document Indexing Adapter]] (20 shared connections)
- [[Community 61]] (13 shared connections)
- [[Community 83]] (9 shared connections)
- [[Community 102]] (8 shared connections)
- [[Analytics & Usage Models (WS-H)]] (7 shared connections)
- [[Community 161]] (7 shared connections)
- [[Community 59]] (7 shared connections)
- [[Backend Agent/API Test Fixtures]] (6 shared connections)
- [[Community 85]] (6 shared connections)
- [[Community 332]] (4 shared connections)
- [[Community 73]] (4 shared connections)

## Source Files

- `backend/om/background/celery/tasks/docfetching/task_creation_utils.py`
- `backend/om/background/celery/tasks/shared/tasks.py`
- `backend/om/background/celery/tasks/user_file_processing/tasks.py`
- `backend/om/db/knowledge_file.py`
- `backend/om/indexing/adapters/document_indexing_adapter.py`
- `backend/om/indexing/adapters/user_file_indexing_adapter.py`
- `backend/om/indexing/indexing_pipeline.py`
- `backend/om/indexing/models.py`
- `backend/om/key_value_store/store.py`
- `backend/om/redis/redis_pool.py`
- `backend/om/utils/supervisord_watchdog.py`
- `backend/tests/external_dependency_unit/celery/test_docfetching_priority.py`

## Audit Trail

- EXTRACTED: 452 (62%)
- INFERRED: 273 (38%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*