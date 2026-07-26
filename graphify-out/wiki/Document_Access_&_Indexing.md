# Document Access & Indexing

> 276 nodes · cohesion 0.02

## Key Concepts

- **DocumentIndex** (156 connections) — `backend/om/document_index/interfaces_new.py`
- **DocumentAccess** (98 connections) — `backend/om/access/models.py`
- **TenantState** (86 connections) — `backend/om/document_index/interfaces_new.py`
- **DocumentSectionRequest** (78 connections) — `backend/om/document_index/interfaces_new.py`
- **IndexingMetadata** (68 connections) — `backend/om/document_index/interfaces_new.py`
- **QueryType** (67 connections) — `backend/om/context/search/enums.py`
- **DocumentInsertionRecord** (59 connections) — `backend/om/document_index/interfaces_new.py`
- **MetadataUpdateRequest** (55 connections) — `backend/om/document_index/interfaces_new.py`
- **DocumentChunk** (52 connections) — `backend/om/document_index/opensearch/schema.py`
- **OpenSearchDocumentIndex** (50 connections) — `backend/om/document_index/opensearch/opensearch_document_index.py`
- **DocumentChunkWithoutVectors** (48 connections) — `backend/om/document_index/opensearch/schema.py`
- **DocumentQuery** (48 connections) — `backend/om/document_index/opensearch/search.py`
- **DocumentSchema** (39 connections) — `backend/om/document_index/opensearch/schema.py`
- **KGUChunkUpdateRequest** (34 connections) — `backend/om/document_index/interfaces_new.py`
- **OpenSearchIndexPair** (34 connections) — `backend/om/document_index/opensearch/opensearch_document_index.py`
- **IndexFilters** (24 connections) — `backend/om/document_index/opensearch/opensearch_document_index.py`
- **DisabledDocumentIndex** (24 connections) — `backend/om/document_index/disabled.py`
- **InferenceChunk** (23 connections) — `backend/om/document_index/opensearch/opensearch_document_index.py`
- **interfaces_new.py** (20 connections) — `backend/om/document_index/interfaces_new.py`
- **Embedding** (17 connections) — `backend/om/document_index/opensearch/opensearch_document_index.py`
- **EmbeddingPrecision** (17 connections) — `backend/om/document_index/opensearch/opensearch_document_index.py`
- **ChunkCountNotFoundError** (17 connections) — `backend/om/document_index/opensearch/opensearch_document_index.py`
- **ChunkCountZeroError** (17 connections) — `backend/om/document_index/opensearch/opensearch_document_index.py`
- **DocMetadataAwareIndexChunk** (16 connections) — `backend/om/document_index/opensearch/opensearch_document_index.py`
- **DocumentChunkWithoutVectors** (16 connections) — `backend/om/document_index/opensearch/opensearch_document_index.py`
- *... and 251 more nodes in this community*

## Relationships

- [[Community 136]] (52 shared connections)
- [[Community 102]] (46 shared connections)
- [[Agent Chat Packets & Citations]] (45 shared connections)
- [[Community 69]] (38 shared connections)
- [[Community 444]] (22 shared connections)
- [[Community 257]] (17 shared connections)
- [[Community 85]] (16 shared connections)
- [[Community 204]] (15 shared connections)
- [[Community 123]] (14 shared connections)
- [[Community 148]] (13 shared connections)
- [[Analytics & Usage Models (WS-H)]] (10 shared connections)
- [[Community 349]] (10 shared connections)

## Source Files

- `backend/om/access/models.py`
- `backend/om/background/celery/tasks/shared/RetryDocumentIndex.py`
- `backend/om/context/search/enums.py`
- `backend/om/context/search/retrieval/search_runner.py`
- `backend/om/document_index/chunk_content_enrichment.py`
- `backend/om/document_index/disabled.py`
- `backend/om/document_index/factory.py`
- `backend/om/document_index/interfaces_new.py`
- `backend/om/document_index/opensearch/client.py`
- `backend/om/document_index/opensearch/opensearch_document_index.py`
- `backend/om/document_index/opensearch/schema.py`
- `backend/om/document_index/opensearch/search.py`
- `backend/om/document_index/opensearch/string_filtering.py`
- `backend/om/indexing/indexing_pipeline.py`
- `backend/om/indexing/vector_db_insertion.py`
- `backend/om/kg/opensearch/opensearch_interactions.py`
- `backend/om/tools/tool_implementations/search/search_utils.py`
- `backend/scripts/opensearch_smoke_test.py`
- `backend/tests/external_dependency_unit/opensearch/test_assistant_knowledge_filter.py`
- `backend/tests/external_dependency_unit/opensearch/test_kg_chunk_updates.py`

## Audit Trail

- EXTRACTED: 795 (36%)
- INFERRED: 1441 (64%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*