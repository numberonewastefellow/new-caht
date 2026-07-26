# Community 185

> 70 nodes · cohesion 0.05

## Key Concepts

- **test_compression.py** (21 connections) — `backend/tests/unit/om/chat/test_compression.py`
- **create_mock_message()** (19 connections) — `backend/tests/unit/om/chat/test_compression.py`
- **compress_chat_history()** (14 connections) — `backend/om/chat/compression.py`
- **generate_summary()** (13 connections) — `backend/om/chat/compression.py`
- **compression.py** (12 connections) — `backend/om/chat/compression.py`
- **_build_llm_messages_for_summarization()** (11 connections) — `backend/om/chat/compression.py`
- **get_messages_to_summarize()** (11 connections) — `backend/om/chat/compression.py`
- **find_summary_for_branch()** (8 connections) — `backend/om/chat/compression.py`
- **ChatMessage** (6 connections) — `backend/om/chat/compression.py`
- **get_compression_params()** (6 connections) — `backend/om/chat/compression.py`
- **CompressionParams** (5 connections) — `backend/om/chat/compression.py`
- **SummaryContent** (5 connections) — `backend/om/chat/compression.py`
- **calculate_total_history_tokens()** (4 connections) — `backend/om/chat/compression.py`
- **CompressionResult** (4 connections) — `backend/om/chat/compression.py`
- **test__build_llm_messages_for_summarization_assistant_messages()** (4 connections) — `backend/tests/unit/om/chat/test_compression.py`
- **test__build_llm_messages_for_summarization_skips_empty()** (4 connections) — `backend/tests/unit/om/chat/test_compression.py`
- **test__build_llm_messages_for_summarization_skips_tool_responses()** (4 connections) — `backend/tests/unit/om/chat/test_compression.py`
- **test__build_llm_messages_for_summarization_tool_calls()** (4 connections) — `backend/tests/unit/om/chat/test_compression.py`
- **test__build_llm_messages_for_summarization_user_messages()** (4 connections) — `backend/tests/unit/om/chat/test_compression.py`
- **test_cutoff_always_before_user_message()** (4 connections) — `backend/tests/unit/om/chat/test_compression.py`
- **test_empty_messages_filtered_out()** (4 connections) — `backend/tests/unit/om/chat/test_compression.py`
- **test_find_summary_for_branch_ignores_other_branch()** (4 connections) — `backend/tests/unit/om/chat/test_compression.py`
- **test_find_summary_for_branch_returns_matching_branch()** (4 connections) — `backend/tests/unit/om/chat/test_compression.py`
- **test_generate_summary_cutoff_marker_as_separate_message()** (4 connections) — `backend/tests/unit/om/chat/test_compression.py`
- **test_generate_summary_initial_system_prompt()** (4 connections) — `backend/tests/unit/om/chat/test_compression.py`
- *... and 45 more nodes in this community*

## Relationships

- [[Chat Datetime & OAuth Tokens]] (4 shared connections)
- [[Community 161]] (2 shared connections)
- [[Analytics & Usage Models (WS-H)]] (2 shared connections)
- [[Community 220]] (2 shared connections)
- [[Community 86]] (1 shared connections)
- [[Community 523]] (1 shared connections)
- [[Phoenix LDAP Auth Tests]] (1 shared connections)

## Source Files

- `backend/om/chat/compression.py`
- `backend/tests/unit/om/chat/test_compression.py`

## Audit Trail

- EXTRACTED: 205 (81%)
- INFERRED: 48 (19%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*