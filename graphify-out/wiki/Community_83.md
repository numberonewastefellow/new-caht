# Community 83

> 136 nodes · cohesion 0.03

## Key Concepts

- **document.py** (67 connections) — `backend/om/db/document.py`
- **Session** (60 connections) — `backend/om/db/document.py`
- **DocumentMetadata** (35 connections) — `backend/om/document_index/document_metadata.py`
- **delete_documents_complete__no_commit()** (17 connections) — `backend/om/db/document.py`
- **document_by_cc_pair_cleanup_task()** (16 connections) — `backend/om/background/celery/tasks/shared/tasks.py`
- **DbDocument** (14 connections) — `backend/om/db/document.py`
- **.post_index()** (11 connections) — `backend/om/indexing/adapters/document_indexing_adapter.py`
- **datetime** (9 connections) — `backend/om/db/document.py`
- **get_accessible_documents_for_hierarchy_node_paginated()** (9 connections) — `backend/om/db/document.py`
- **Select** (8 connections) — `backend/om/db/document.py`
- **upsert_document_external_perms()** (8 connections) — `backend/om/db/document.py`
- **get_documents_for_cc_pair()** (7 connections) — `backend/om/db/document.py`
- **prepare_to_modify_documents()** (7 connections) — `backend/om/db/document.py`
- **upsert_document_by_connector_credential_pair()** (7 connections) — `backend/om/db/document.py`
- **upsert_document_external_perms__no_commit()** (7 connections) — `backend/om/db/document.py`
- **upsert_documents()** (7 connections) — `backend/om/db/document.py`
- **element_update_permissions()** (7 connections) — `backend/om/background/celery/tasks/doc_permission_syncing/tasks.py`
- **delete_all_documents_for_connector_credential_pair()** (6 connections) — `backend/om/db/document.py`
- **delete_document_by_connector_credential_pair__no_commit()** (6 connections) — `backend/om/db/document.py`
- **delete_documents_by_connector_credential_pair__no_commit()** (6 connections) — `backend/om/db/document.py`
- **get_document_kg_entities_and_relationships()** (6 connections) — `backend/om/db/document.py`
- **get_documents_by_ids()** (6 connections) — `backend/om/db/document.py`
- **get_documents_by_source()** (6 connections) — `backend/om/db/document.py`
- **get_unprocessed_kg_document_batch_for_connector()** (6 connections) — `backend/om/db/document.py`
- **mark_document_as_indexed_for_cc_pair__no_commit()** (6 connections) — `backend/om/db/document.py`
- *... and 111 more nodes in this community*

## Relationships

- [[Document External Access]] (17 shared connections)
- [[Community 102]] (16 shared connections)
- [[Community 69]] (9 shared connections)
- [[Community 178]] (8 shared connections)
- [[Community 120]] (6 shared connections)
- [[Community 85]] (5 shared connections)
- [[Community 130]] (5 shared connections)
- [[Document Indexing Adapter]] (4 shared connections)
- [[Community 61]] (4 shared connections)
- [[Community 217]] (4 shared connections)
- [[Backend Agent/API Test Fixtures]] (4 shared connections)
- [[Document Access & Indexing]] (3 shared connections)

## Source Files

- `backend/om/background/celery/tasks/doc_permission_syncing/tasks.py`
- `backend/om/background/celery/tasks/shared/tasks.py`
- `backend/om/db/document.py`
- `backend/om/db/utils.py`
- `backend/om/document_index/document_metadata.py`
- `backend/om/indexing/adapters/document_indexing_adapter.py`
- `backend/om/kg/opensearch/opensearch_interactions.py`

## Audit Trail

- EXTRACTED: 467 (74%)
- INFERRED: 164 (26%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*