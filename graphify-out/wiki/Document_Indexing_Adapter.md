# Document Indexing Adapter

> 189 nodes · cohesion 0.02

## Key Concepts

- **RedisConnector** (92 connections) — `backend/om/redis/redis_connector.py`
- **EmbeddingModel** (70 connections) — `backend/om/natural_language_processing/search_nlp_models.py`
- **IndexingCoordination** (64 connections) — `backend/om/db/indexing_coordination.py`
- **DefaultIndexingEmbedder** (51 connections) — `backend/om/indexing/embedder.py`
- **OmRuntime** (51 connections) — `backend/om/server/runtime/onyx_runtime.py`
- **DocumentBatchStorage** (45 connections) — `backend/om/file_store/document_batch_storage.py`
- **DocumentIndexingBatchAdapter** (32 connections) — `backend/om/indexing/adapters/document_indexing_adapter.py`
- **tasks.py** (28 connections) — `backend/om/background/celery/tasks/docprocessing/tasks.py`
- **docprocessing_task()** (20 connections) — `backend/om/background/celery/tasks/docprocessing/tasks.py`
- **IndexAttemptError** (19 connections) — `backend/om/db/index_attempt.py`
- **CoordinationStatus** (19 connections) — `backend/om/db/indexing_coordination.py`
- **Task** (18 connections) — `backend/om/background/celery/tasks/docprocessing/tasks.py`
- **check_indexing_completion()** (16 connections) — `backend/om/background/celery/tasks/docprocessing/tasks.py`
- **FileStoreDocumentBatchStorage** (15 connections) — `backend/om/file_store/document_batch_storage.py`
- **upsert_ingestion_doc()** (15 connections) — `backend/om/server/onyx_api/ingestion.py`
- **Session** (14 connections) — `backend/om/background/celery/tasks/docprocessing/tasks.py`
- **ConnectorIndexingLogBuilder** (13 connections) — `backend/om/background/celery/tasks/docprocessing/tasks.py`
- **DocumentProcessingBatch** (13 connections) — `backend/om/background/celery/tasks/docprocessing/tasks.py`
- **_kickoff_indexing_tasks()** (13 connections) — `backend/om/background/celery/tasks/docprocessing/tasks.py`
- **monitor_indexing_attempt_progress()** (13 connections) — `backend/om/background/celery/tasks/docprocessing/tasks.py`
- **Celery** (12 connections) — `backend/om/background/celery/tasks/docprocessing/tasks.py`
- **ConnectorFailure** (12 connections) — `backend/om/background/celery/tasks/docprocessing/tasks.py`
- **Redis** (12 connections) — `backend/om/background/celery/tasks/docprocessing/tasks.py`
- **RedisLock** (12 connections) — `backend/om/background/celery/tasks/docprocessing/tasks.py`
- **Any** (11 connections) — `backend/om/background/celery/tasks/docprocessing/tasks.py`
- *... and 164 more nodes in this community*

## Relationships

- [[Community 99]] (38 shared connections)
- [[Community 59]] (34 shared connections)
- [[Community 161]] (32 shared connections)
- [[Community 144]] (24 shared connections)
- [[Community 69]] (20 shared connections)
- [[Community 199]] (20 shared connections)
- [[Community 120]] (19 shared connections)
- [[Community 70]] (16 shared connections)
- [[Document External Access]] (15 shared connections)
- [[Community 102]] (15 shared connections)
- [[Community 109]] (14 shared connections)
- [[Community 130]] (11 shared connections)

## Source Files

- `backend/om/background/celery/tasks/docprocessing/tasks.py`
- `backend/om/background/celery/tasks/docprocessing/utils.py`
- `backend/om/db/index_attempt.py`
- `backend/om/db/indexing_coordination.py`
- `backend/om/file_store/document_batch_storage.py`
- `backend/om/indexing/adapters/document_indexing_adapter.py`
- `backend/om/indexing/embedder.py`
- `backend/om/natural_language_processing/search_nlp_models.py`
- `backend/om/redis/redis_connector.py`
- `backend/om/redis/redis_connector_utils.py`
- `backend/om/server/onyx_api/ingestion.py`
- `backend/om/server/runtime/onyx_runtime.py`
- `backend/tests/unit/om/indexing/conftest.py`

## Audit Trail

- EXTRACTED: 540 (45%)
- INFERRED: 649 (55%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*