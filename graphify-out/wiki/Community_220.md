# Community 220

> 60 nodes · cohesion 0.05

## Key Concepts

- **record_llm_response()** (25 connections) — `backend/om/tracing/llm_utils.py`
- **llm_generation_span()** (19 connections) — `backend/om/tracing/llm_utils.py`
- **record_llm_span_output()** (15 connections) — `backend/om/tracing/llm_utils.py`
- **process_memory_update()** (11 connections) — `backend/om/secondary_llm_flows/memory_update.py`
- **semantic_query_rephrase()** (11 connections) — `backend/om/secondary_llm_flows/query_expansion.py`
- **keyword_query_expansion()** (10 connections) — `backend/om/secondary_llm_flows/query_expansion.py`
- **generate_chat_session_name()** (8 connections) — `backend/om/secondary_llm_flows/chat_session_naming.py`
- **Any** (6 connections) — `backend/om/tracing/llm_utils.py`
- **GenerationSpanData** (6 connections) — `backend/om/tracing/llm_utils.py`
- **Span** (6 connections) — `backend/om/tracing/llm_utils.py`
- **query_expansion.py** (6 connections) — `backend/om/secondary_llm_flows/query_expansion.py`
- **_build_message_history()** (6 connections) — `backend/om/secondary_llm_flows/query_expansion.py`
- **LLM** (5 connections) — `backend/om/tracing/llm_utils.py`
- **expand_keywords()** (5 connections) — `backend/om/secondary_llm_flows/query_expansion.py`
- **llm_utils.py** (5 connections) — `backend/om/tracing/llm_utils.py`
- **memory_update.py** (4 connections) — `backend/om/secondary_llm_flows/memory_update.py`
- **_build_additional_context()** (4 connections) — `backend/om/secondary_llm_flows/query_expansion.py`
- **_build_usage_dict()** (4 connections) — `backend/om/tracing/llm_utils.py`
- **ChatMinimalTextMessage** (3 connections) — `backend/om/secondary_llm_flows/query_expansion.py`
- **LLM** (3 connections) — `backend/om/secondary_llm_flows/query_expansion.py`
- **_format_chat_history()** (3 connections) — `backend/om/secondary_llm_flows/memory_update.py`
- **_format_existing_memories()** (3 connections) — `backend/om/secondary_llm_flows/memory_update.py`
- **_format_user_basic_information()** (3 connections) — `backend/om/secondary_llm_flows/memory_update.py`
- **_clean_keyword_line()** (3 connections) — `backend/om/secondary_llm_flows/query_expansion.py`
- **build_llm_model_config()** (3 connections) — `backend/om/tracing/llm_utils.py`
- *... and 35 more nodes in this community*

## Relationships

- [[Community 65]] (12 shared connections)
- [[Community 86]] (11 shared connections)
- [[Community 133]] (7 shared connections)
- [[Community 232]] (6 shared connections)
- [[Community 419]] (6 shared connections)
- [[Community 140]] (4 shared connections)
- [[Community 468]] (2 shared connections)
- [[Community 185]] (2 shared connections)
- [[Community 851]] (2 shared connections)
- [[Community 213]] (1 shared connections)
- [[Community 62]] (1 shared connections)
- [[Agent Chat Packets & Citations]] (1 shared connections)

## Source Files

- `backend/om/secondary_llm_flows/chat_session_naming.py`
- `backend/om/secondary_llm_flows/memory_update.py`
- `backend/om/secondary_llm_flows/query_expansion.py`
- `backend/om/tracing/llm_utils.py`
- `backend/om/utils/text_processing.py`
- `backend/tests/external_dependency_unit/tracing/test_llm_span_recording.py`

## Audit Trail

- EXTRACTED: 151 (65%)
- INFERRED: 80 (35%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*