# Agent Chat Packets & Citations

> 509 nodes · cohesion 0.02

## Key Concepts

- **Placement** (353 connections) — `backend/om/server/query_and_chat/placement.py`
- **Packet** (336 connections) — `backend/om/server/query_and_chat/streaming_models.py`
- **Emitter** (258 connections) — `backend/om/chat/emitter.py`
- **ChatStateContainer** (178 connections) — `backend/om/chat/chat_state.py`
- **CitationInfo** (128 connections) — `backend/om/server/query_and_chat/streaming_models.py`
- **AgentResponseDelta** (117 connections) — `backend/om/server/query_and_chat/streaming_models.py`
- **DynamicCitationProcessor** (116 connections) — `backend/om/chat/citation_processor.py`
- **AgentResponseStart** (112 connections) — `backend/om/server/query_and_chat/streaming_models.py`
- **PythonTool** (110 connections) — `backend/om/tools/tool_implementations/python/python_tool.py`
- **SearchTool** (105 connections) — `backend/om/tools/tool_implementations/search/search_tool.py`
- **WebSearchTool** (90 connections) — `backend/om/tools/tool_implementations/web_search/web_search_tool.py`
- **SectionEnd** (83 connections) — `backend/om/server/query_and_chat/streaming_models.py`
- **OpenURLTool** (79 connections) — `backend/om/tools/tool_implementations/open_url/open_url_tool.py`
- **CitationMapping** (78 connections) — `backend/om/chat/citation_processor.py`
- **OverallStop** (68 connections) — `backend/om/server/query_and_chat/streaming_models.py`
- **Packet** (55 connections) — `backend/om/server/query_and_chat/session_loading.py`
- **streaming_models.py** (53 connections) — `backend/om/server/query_and_chat/streaming_models.py`
- **MemoryTool** (52 connections) — `backend/om/tools/tool_implementations/memory/memory_tool.py`
- **ReasoningDelta** (51 connections) — `backend/om/server/query_and_chat/streaming_models.py`
- **CitationMode** (48 connections) — `backend/om/chat/citation_processor.py`
- **ReasoningStart** (47 connections) — `backend/om/server/query_and_chat/streaming_models.py`
- **SearchToolDocumentsDelta** (46 connections) — `backend/om/server/query_and_chat/streaming_models.py`
- **SearchDoc** (45 connections) — `backend/om/server/query_and_chat/session_loading.py`
- **CitationInfo** (44 connections) — `backend/om/server/query_and_chat/session_loading.py`
- **GeneratedImage** (44 connections) — `backend/om/server/query_and_chat/session_loading.py`
- *... and 484 more nodes in this community*

## Relationships

- [[Chat Datetime & OAuth Tokens]] (305 shared connections)
- [[Analytics & Usage Models (WS-H)]] (204 shared connections)
- [[Community 115]] (85 shared connections)
- [[Community 62]] (78 shared connections)
- [[Community 323]] (58 shared connections)
- [[Community 94]] (51 shared connections)
- [[Document Access & Indexing]] (45 shared connections)
- [[Community 580]] (37 shared connections)
- [[Community 65]] (34 shared connections)
- [[Community 95]] (33 shared connections)
- [[Community 82]] (30 shared connections)
- [[Community 275]] (23 shared connections)

## Source Files

- `backend/om/chat/chat_state.py`
- `backend/om/chat/citation_processor.py`
- `backend/om/chat/citation_utils.py`
- `backend/om/chat/emitter.py`
- `backend/om/chat/llm_loop.py`
- `backend/om/chat/llm_step.py`
- `backend/om/chat/prompt_utils.py`
- `backend/om/context/search/models.py`
- `backend/om/context/search/utils.py`
- `backend/om/deep_research/dr_loop.py`
- `backend/om/deep_research/dr_mock_tools.py`
- `backend/om/file_store/utils.py`
- `backend/om/server/query_and_chat/placement.py`
- `backend/om/server/query_and_chat/session_loading.py`
- `backend/om/server/query_and_chat/streaming_models.py`
- `backend/om/server/query_and_chat/streaming_utils.py`
- `backend/om/tools/fake_tools/research_agent.py`
- `backend/om/tools/tool_implementations/agent_tool.py`
- `backend/om/tools/tool_implementations/custom/custom_tool.py`
- `backend/om/tools/tool_implementations/file_reader/file_reader_tool.py`

## Audit Trail

- EXTRACTED: 1524 (21%)
- INFERRED: 5803 (79%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*