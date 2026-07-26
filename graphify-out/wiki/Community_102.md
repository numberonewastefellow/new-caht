# Community 102

> 122 nodes · cohesion 0.04

## Key Concepts

- **Chunker** (43 connections) — `backend/om/indexing/chunker.py`
- **IndexingEmbedder** (24 connections) — `backend/om/indexing/embedder.py`
- **LLMRateLimitError** (21 connections) — `backend/om/llm/multi_llm.py`
- **indexing_pipeline.py** (18 connections) — `backend/om/indexing/indexing_pipeline.py`
- **IndexingPipelineResult** (17 connections) — `backend/om/indexing/indexing_pipeline.py`
- **run_indexing_pipeline()** (17 connections) — `backend/om/indexing/indexing_pipeline.py`
- **Document** (16 connections) — `backend/om/indexing/indexing_pipeline.py`
- **TextSection** (16 connections) — `backend/tests/unit/om/indexing/test_indexing_pipeline.py`
- **index_doc_batch()** (16 connections) — `backend/om/indexing/indexing_pipeline.py`
- **index_doc_batch_prepare()** (13 connections) — `backend/om/indexing/indexing_pipeline.py`
- **LLM** (12 connections) — `backend/om/indexing/indexing_pipeline.py`
- **filter_documents()** (12 connections) — `backend/om/indexing/indexing_pipeline.py`
- **process_image_sections()** (12 connections) — `backend/om/indexing/indexing_pipeline.py`
- **test_indexing_pipeline.py** (12 connections) — `backend/tests/unit/om/indexing/test_indexing_pipeline.py`
- **create_test_document()** (12 connections) — `backend/tests/unit/om/indexing/test_indexing_pipeline.py`
- **._chunk_document_with_sections()** (11 connections) — `backend/om/indexing/chunker.py`
- **index_doc_batch_with_handler()** (11 connections) — `backend/om/indexing/indexing_pipeline.py`
- **test_indexing_pipeline_uses_updated_contextual_rag_settings()** (11 connections) — `backend/tests/external_dependency_unit/search_settings/test_search_settings.py`
- **BaseTokenizer** (10 connections) — `backend/om/indexing/indexing_pipeline.py`
- **DocAwareChunk** (10 connections) — `backend/om/indexing/indexing_pipeline.py`
- **DocumentIndex** (10 connections) — `backend/om/indexing/indexing_pipeline.py`
- **IndexAttemptMetadata** (10 connections) — `backend/om/indexing/indexing_pipeline.py`
- **Session** (10 connections) — `backend/om/indexing/indexing_pipeline.py`
- **Chunker** (10 connections) — `backend/om/indexing/indexing_pipeline.py`
- **embed_chunks_with_failure_handling()** (10 connections) — `backend/om/indexing/embedder.py`
- *... and 97 more nodes in this community*

## Relationships

- [[Document Access & Indexing]] (46 shared connections)
- [[Community 83]] (16 shared connections)
- [[Document Indexing Adapter]] (15 shared connections)
- [[Community 130]] (11 shared connections)
- [[Document External Access]] (9 shared connections)
- [[Community 65]] (8 shared connections)
- [[Community 69]] (8 shared connections)
- [[Community 85]] (8 shared connections)
- [[Community 107]] (5 shared connections)
- [[Community 133]] (3 shared connections)
- [[Salesforce Connector]] (3 shared connections)
- [[Community 523]] (3 shared connections)

## Source Files

- `backend/om/connectors/cross_connector_utils/miscellaneous_utils.py`
- `backend/om/document_index/chunk_content_enrichment.py`
- `backend/om/indexing/chunker.py`
- `backend/om/indexing/embedder.py`
- `backend/om/indexing/indexing_pipeline.py`
- `backend/om/llm/multi_llm.py`
- `backend/tests/external_dependency_unit/search_settings/test_search_settings.py`
- `backend/tests/unit/om/indexing/test_chunker.py`
- `backend/tests/unit/om/indexing/test_indexing_pipeline.py`

## Audit Trail

- EXTRACTED: 453 (62%)
- INFERRED: 279 (38%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*