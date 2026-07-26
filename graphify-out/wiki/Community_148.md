# Community 148

> 86 nodes · cohesion 0.03

## Key Concepts

- **configs.py** (94 connections) — `backend/shared_configs/configs.py`
- **DynamicTenantScheduler** (11 connections) — `backend/om/background/celery/apps/beat.py`
- **monitoring.py** (8 connections) — `backend/om/background/celery/apps/monitoring.py`
- **Any** (8 connections) — `backend/om/background/celery/apps/monitoring.py`
- **_get_search_filters()** (8 connections) — `backend/tests/external_dependency_unit/opensearch/test_assistant_knowledge_filter.py`
- **TestAssistantKnowledgeFilter** (8 connections) — `backend/tests/external_dependency_unit/opensearch/test_assistant_knowledge_filter.py`
- **._try_updating_schedule()** (7 connections) — `backend/om/background/celery/apps/beat.py`
- **_build_opensearch_index()** (7 connections) — `backend/om/kg/opensearch/opensearch_interactions.py`
- **._generate_schedule()** (6 connections) — `backend/om/background/celery/apps/beat.py`
- **Any** (6 connections) — `backend/om/background/celery/apps/beat.py`
- **_create_sync_engine()** (6 connections) — `backend/tests/integration/tests/migrations/conftest.py`
- **get_document_opensearch_contents()** (6 connections) — `backend/om/kg/opensearch/opensearch_interactions.py`
- **update_kg_chunks_opensearch_info()** (6 connections) — `backend/om/kg/opensearch/opensearch_interactions.py`
- **UUID** (5 connections) — `backend/tests/external_dependency_unit/opensearch/test_assistant_knowledge_filter.py`
- **conftest.py** (5 connections) — `backend/tests/integration/tests/migrations/conftest.py`
- **opensearch_interactions.py** (5 connections) — `backend/om/kg/opensearch/opensearch_interactions.py`
- **test_assistant_knowledge_filter.py** (5 connections) — `backend/tests/external_dependency_unit/opensearch/test_assistant_knowledge_filter.py`
- **beat_schedule.py** (5 connections) — `backend/om/background/celery/tasks/beat_schedule.py`
- **generate_cloud_tasks()** (5 connections) — `backend/om/background/celery/tasks/beat_schedule.py`
- **encode_string_batch()** (5 connections) — `backend/om/kg/utils/embeddings.py`
- **beat.py** (4 connections) — `backend/om/background/celery/apps/beat.py`
- **.__init__()** (4 connections) — `backend/om/background/celery/apps/beat.py`
- **on_beat_init()** (4 connections) — `backend/om/background/celery/apps/beat.py`
- **Any** (4 connections) — `backend/om/background/celery/tasks/beat_schedule.py`
- **document_index.py** (4 connections) — `backend/tests/integration/common_utils/document_index.py`
- *... and 61 more nodes in this community*

## Relationships

- [[Document Access & Indexing]] (13 shared connections)
- [[Community 119]] (10 shared connections)
- [[Community 73]] (9 shared connections)
- [[Community 85]] (6 shared connections)
- [[Document Indexing Adapter]] (4 shared connections)
- [[Community 161]] (4 shared connections)
- [[Community 61]] (3 shared connections)
- [[Backend Agent/API Test Fixtures]] (3 shared connections)
- [[Community 59]] (3 shared connections)
- [[Community 109]] (2 shared connections)
- [[Community 330]] (2 shared connections)
- [[Community 99]] (2 shared connections)

## Source Files

- `backend/alembic_tenants/versions/3b9f09038764_add_read_only_kg_user.py`
- `backend/om/background/celery/apps/beat.py`
- `backend/om/background/celery/apps/monitoring.py`
- `backend/om/background/celery/tasks/beat_schedule.py`
- `backend/om/connectors/models.py`
- `backend/om/kg/opensearch/opensearch_interactions.py`
- `backend/om/kg/utils/embeddings.py`
- `backend/om/tenancy/config.py`
- `backend/om/utils/tenant.py`
- `backend/shared_configs/configs.py`
- `backend/tests/external_dependency_unit/opensearch/test_assistant_knowledge_filter.py`
- `backend/tests/integration/common_utils/document_index.py`
- `backend/tests/integration/tests/migrations/conftest.py`

## Audit Trail

- EXTRACTED: 316 (90%)
- INFERRED: 34 (10%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*