# Community 85

> 136 nodes · cohesion 0.03

## Key Concepts

- **get_current_search_settings()** (47 connections) — `backend/om/db/search_settings.py`
- **get_all_document_indices()** (20 connections) — `backend/om/document_index/factory.py`
- **search_settings.py** (18 connections) — `backend/om/db/search_settings.py`
- **setup_onyx()** (18 connections) — `backend/om/setup.py`
- **get_active_search_settings()** (17 connections) — `backend/om/db/search_settings.py`
- **check_and_perform_index_swap()** (15 connections) — `backend/om/db/swap_index.py`
- **_perform_index_swap()** (15 connections) — `backend/om/db/swap_index.py`
- **get_default_document_index()** (14 connections) — `backend/om/document_index/factory.py`
- **Session** (13 connections) — `backend/om/db/search_settings.py`
- **reset.py** (13 connections) — `backend/tests/integration/common_utils/reset.py`
- **search_settings.py** (13 connections) — `backend/om/server/manage/search_settings.py`
- **get_secondary_search_settings()** (12 connections) — `backend/om/db/search_settings.py`
- **ensure_full_deployment_setup()** (11 connections) — `backend/tests/external_dependency_unit/full_setup.py`
- **setup_postgres()** (11 connections) — `backend/om/setup.py`
- **User** (10 connections) — `backend/om/server/manage/search_settings.py`
- **reset_document_index_multitenant()** (10 connections) — `backend/tests/integration/common_utils/reset.py`
- **reset_postgres()** (10 connections) — `backend/tests/integration/common_utils/reset.py`
- **get_document_info()** (10 connections) — `backend/om/server/documents/document.py`
- **set_new_search_settings()** (10 connections) — `backend/om/server/manage/search_settings.py`
- **setup.py** (10 connections) — `backend/om/setup.py`
- **update_default_multipass_indexing()** (10 connections) — `backend/om/setup.py`
- **Session** (9 connections) — `backend/om/server/manage/search_settings.py`
- **reset_document_index()** (9 connections) — `backend/tests/integration/common_utils/reset.py`
- **get_chunk_info()** (9 connections) — `backend/om/server/documents/document.py`
- **update_saved_search_settings()** (9 connections) — `backend/om/server/manage/search_settings.py`
- *... and 111 more nodes in this community*

## Relationships

- [[Document Access & Indexing]] (16 shared connections)
- [[Document Indexing Adapter]] (10 shared connections)
- [[Community 120]] (10 shared connections)
- [[Salesforce Connector]] (9 shared connections)
- [[Backend Agent/API Test Fixtures]] (8 shared connections)
- [[Community 99]] (8 shared connections)
- [[Community 102]] (8 shared connections)
- [[Community 107]] (8 shared connections)
- [[Community 73]] (6 shared connections)
- [[Community 148]] (6 shared connections)
- [[Community 69]] (6 shared connections)
- [[Community 161]] (6 shared connections)

## Source Files

- `backend/om/context/search/preprocessing/access_filters.py`
- `backend/om/db/deletion_attempt.py`
- `backend/om/db/document.py`
- `backend/om/db/search_settings.py`
- `backend/om/db/swap_index.py`
- `backend/om/document_index/document_index_utils.py`
- `backend/om/document_index/factory.py`
- `backend/om/server/documents/document.py`
- `backend/om/server/manage/search_settings.py`
- `backend/om/setup.py`
- `backend/tests/external_dependency_unit/full_setup.py`
- `backend/tests/integration/common_utils/reset.py`
- `backend/tests/integration/common_utils/timeout.py`
- `backend/tests/integration/conftest.py`
- `backend/tests/integration/tests/migrations/test_assistant_consolidation_migration.py`
- `backend/tests/integration/tests/no_vectordb/conftest.py`

## Audit Trail

- EXTRACTED: 451 (65%)
- INFERRED: 245 (35%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*