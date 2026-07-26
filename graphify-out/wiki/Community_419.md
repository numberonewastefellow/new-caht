# Community 419

> 36 nodes · cohesion 0.08

## Key Concepts

- **demonstrate()** (14 connections) — `backend/tests/search_baseline/demo_reranking_layers.py`
- **select_sections_for_expansion()** (10 connections) — `backend/om/secondary_llm_flows/document_filter.py`
- **test_search_tool_layer.py** (9 connections) — `backend/tests/search_baseline/test_search_tool_layer.py`
- **classify_section_relevance()** (8 connections) — `backend/om/secondary_llm_flows/document_filter.py`
- **select_chunks_for_relevance()** (8 connections) — `backend/om/secondary_llm_flows/document_filter.py`
- **_chunk()** (7 connections) — `backend/tests/search_baseline/test_search_tool_layer.py`
- **combine_retrieval_results()** (6 connections) — `backend/om/context/search/retrieval/search_runner.py`
- **_retrieve()** (6 connections) — `backend/tests/search_baseline/demo_reranking_layers.py`
- **demo_reranking_layers.py** (5 connections) — `backend/tests/search_baseline/demo_reranking_layers.py`
- **main()** (5 connections) — `backend/tests/search_baseline/demo_reranking_layers.py`
- **test_llm_section_selection_plumbing()** (5 connections) — `backend/tests/search_baseline/test_search_tool_layer.py`
- **document_filter.py** (4 connections) — `backend/om/secondary_llm_flows/document_filter.py`
- **InferenceChunk** (3 connections) — `backend/tests/search_baseline/demo_reranking_layers.py`
- **Session** (3 connections) — `backend/tests/search_baseline/demo_reranking_layers.py`
- **_fmt()** (3 connections) — `backend/tests/search_baseline/demo_reranking_layers.py`
- **test_combine_dedups_and_sorts_by_score()** (3 connections) — `backend/tests/search_baseline/test_search_tool_layer.py`
- **test_combine_keeps_higher_score_on_duplicate()** (3 connections) — `backend/tests/search_baseline/test_search_tool_layer.py`
- **test_select_chunks_for_relevance_window()** (3 connections) — `backend/tests/search_baseline/test_search_tool_layer.py`
- **test_select_chunks_single()** (3 connections) — `backend/tests/search_baseline/test_search_tool_layer.py`
- **InferenceSection** (2 connections) — `backend/om/secondary_llm_flows/document_filter.py`
- **LLM** (2 connections) — `backend/om/secondary_llm_flows/document_filter.py`
- **LLM** (2 connections) — `backend/tests/search_baseline/demo_reranking_layers.py`
- **test_combine_handles_empty_sets()** (2 connections) — `backend/tests/search_baseline/test_search_tool_layer.py`
- **test_no_cross_encoder_rerank_columns()** (2 connections) — `backend/tests/search_baseline/test_search_tool_layer.py`
- **InferenceChunk** (1 connections) — `backend/om/secondary_llm_flows/document_filter.py`
- *... and 11 more nodes in this community*

## Relationships

- [[Community 220]] (6 shared connections)
- [[Document Access & Indexing]] (5 shared connections)
- [[Community 119]] (3 shared connections)
- [[Community 204]] (2 shared connections)
- [[Chat Datetime & OAuth Tokens]] (2 shared connections)
- [[Agent Chat Packets & Citations]] (2 shared connections)
- [[Community 257]] (1 shared connections)
- [[Community 1449]] (1 shared connections)
- [[Backend Agent/API Test Fixtures]] (1 shared connections)
- [[Community 106]] (1 shared connections)

## Source Files

- `backend/om/context/search/retrieval/search_runner.py`
- `backend/om/secondary_llm_flows/document_filter.py`
- `backend/tests/search_baseline/demo_reranking_layers.py`
- `backend/tests/search_baseline/test_search_tool_layer.py`

## Audit Trail

- EXTRACTED: 94 (72%)
- INFERRED: 36 (28%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*