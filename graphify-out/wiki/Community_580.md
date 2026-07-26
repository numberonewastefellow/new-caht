# Community 580

> 26 nodes · cohesion 0.12

## Key Concepts

- **translate_assistant_message_to_packets()** (25 connections) — `backend/om/server/query_and_chat/session_loading.py`
- **session_loading.py** (14 connections) — `backend/om/server/query_and_chat/session_loading.py`
- **TestCreateMemoryPackets** (11 connections) — `backend/tests/unit/tools/test_memory_tool_packets.py`
- **create_memory_packets()** (6 connections) — `backend/om/server/query_and_chat/session_loading.py`
- **create_fetch_packets()** (5 connections) — `backend/om/server/query_and_chat/session_loading.py`
- **create_message_packets()** (5 connections) — `backend/om/server/query_and_chat/session_loading.py`
- **create_python_tool_packets()** (5 connections) — `backend/om/server/query_and_chat/session_loading.py`
- **create_search_packets()** (5 connections) — `backend/om/server/query_and_chat/session_loading.py`
- **_create_workflow_step_packets()** (5 connections) — `backend/om/server/query_and_chat/session_loading.py`
- **create_citation_packets()** (4 connections) — `backend/om/server/query_and_chat/session_loading.py`
- **create_file_reader_packets()** (4 connections) — `backend/om/server/query_and_chat/session_loading.py`
- **create_image_generation_packets()** (4 connections) — `backend/om/server/query_and_chat/session_loading.py`
- **create_research_agent_packets()** (4 connections) — `backend/om/server/query_and_chat/session_loading.py`
- **citation_utils.py** (3 connections) — `backend/om/chat/citation_utils.py`
- **extract_citation_order_from_text()** (3 connections) — `backend/om/chat/citation_utils.py`
- **create_custom_tool_packets()** (3 connections) — `backend/om/server/query_and_chat/session_loading.py`
- **create_reasoning_packets()** (3 connections) — `backend/om/server/query_and_chat/session_loading.py`
- **.test_placement_is_set_correctly()** (2 connections) — `backend/tests/unit/tools/test_memory_tool_packets.py`
- **.test_produces_start_delta_end_for_add()** (2 connections) — `backend/tests/unit/tools/test_memory_tool_packets.py`
- **.test_produces_start_delta_end_for_update()** (2 connections) — `backend/tests/unit/tools/test_memory_tool_packets.py`
- **Extract citation numbers from text in order of first appearance.      Parses cit** (1 connections) — `backend/om/chat/citation_utils.py`
- **Reconstruct PythonTool packets from stored ToolCall data for history reload.** (1 connections) — `backend/om/server/query_and_chat/session_loading.py`
- **Recreate FileReaderStart + FileReaderResult + SectionEnd from the stored     JSO** (1 connections) — `backend/om/server/query_and_chat/session_loading.py`
- **Create packets for research agent tool calls.     This recreates the packet stru** (1 connections) — `backend/om/server/query_and_chat/session_loading.py`
- **Translates an assistant message and tool calls to packet format.     It needs to** (1 connections) — `backend/om/server/query_and_chat/session_loading.py`
- *... and 1 more nodes in this community*

## Relationships

- [[Agent Chat Packets & Citations]] (37 shared connections)
- [[Community 62]] (3 shared connections)
- [[Community 171]] (1 shared connections)
- [[Community 106]] (1 shared connections)
- [[Community 168]] (1 shared connections)

## Source Files

- `backend/om/chat/citation_utils.py`
- `backend/om/server/query_and_chat/session_loading.py`
- `backend/tests/unit/tools/test_memory_tool_packets.py`

## Audit Trail

- EXTRACTED: 101 (83%)
- INFERRED: 20 (17%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*