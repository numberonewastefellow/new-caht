# Chat Datetime & OAuth Tokens

> 415 nodes · cohesion 0.01

## Key Concepts

- **SearchToolConfig** (63 connections) — `backend/om/tools/tool_constructor.py`
- **create_test_user()** (62 connections) — `backend/tests/external_dependency_unit/conftest.py`
- **FileReaderTool** (59 connections) — `backend/om/tools/tool_implementations/file_reader/file_reader_tool.py`
- **OAuthTokenManager** (58 connections) — `backend/om/auth/oauth_token_manager.py`
- **stream_chat_message()** (56 connections) — `backend/om/chat/message_handler.py`
- **StreamingType** (52 connections) — `backend/om/server/query_and_chat/streaming_models.py`
- **ImageGenerationTool** (46 connections) — `backend/om/tools/tool_implementations/images/image_generation_tool.py`
- **construct_tools()** (46 connections) — `backend/om/tools/tool_constructor.py`
- **HttpRequestTool** (39 connections) — `backend/om/tools/tool_implementations/http_request/http_request_tool.py`
- **get_default_llm()** (36 connections) — `backend/om/llm/factory.py`
- **CustomToolConfig** (35 connections) — `backend/om/tools/tool_constructor.py`
- **FileReaderToolConfig** (35 connections) — `backend/om/tools/tool_constructor.py`
- **MCPTool** (33 connections) — `backend/om/tools/tool_implementations/mcp/mcp_tool.py`
- **Session** (29 connections) — `backend/tests/external_dependency_unit/tools/test_oauth_config_crud.py`
- **_create_test_oauth_config()** (29 connections) — `backend/tests/external_dependency_unit/tools/test_oauth_config_crud.py`
- **upsert_user_oauth_token()** (25 connections) — `backend/om/db/oauth_config.py`
- **Session** (21 connections) — `backend/tests/external_dependency_unit/tools/test_oauth_token_manager.py`
- **_create_test_oauth_config()** (21 connections) — `backend/tests/external_dependency_unit/tools/test_oauth_token_manager.py`
- **get_default_emitter()** (19 connections) — `backend/om/chat/emitter.py`
- **TestOAuthConfigCRUD** (19 connections) — `backend/tests/external_dependency_unit/tools/test_oauth_config_crud.py`
- **message_handler.py** (18 connections) — `backend/om/chat/message_handler.py`
- **Session** (17 connections) — `backend/om/chat/message_handler.py`
- **UUID** (16 connections) — `backend/om/chat/message_handler.py`
- **update_oauth_config()** (16 connections) — `backend/om/db/oauth_config.py`
- **.run()** (16 connections) — `backend/om/tools/tool_implementations/agent_tool.py`
- *... and 390 more nodes in this community*

## Relationships

- [[Agent Chat Packets & Citations]] (305 shared connections)
- [[User Roles & Agent Config]] (22 shared connections)
- [[Analytics & Usage Models (WS-H)]] (14 shared connections)
- [[Community 103]] (12 shared connections)
- [[Community 335]] (12 shared connections)
- [[Community 115]] (11 shared connections)
- [[MCP Server Integration]] (11 shared connections)
- [[Community 62]] (10 shared connections)
- [[Community 507]] (9 shared connections)
- [[Community 410]] (9 shared connections)
- [[Community 429]] (8 shared connections)
- [[Community 168]] (7 shared connections)

## Source Files

- `backend/om/auth/oauth_token_manager.py`
- `backend/om/chat/emitter.py`
- `backend/om/chat/message_handler.py`
- `backend/om/chat/models.py`
- `backend/om/db/mcp.py`
- `backend/om/db/oauth_config.py`
- `backend/om/llm/factory.py`
- `backend/om/server/features/oauth_config/api.py`
- `backend/om/server/features/user_oauth_token/api.py`
- `backend/om/server/query_and_chat/streaming_models.py`
- `backend/om/tools/tool_constructor.py`
- `backend/om/tools/tool_implementations/agent_tool.py`
- `backend/om/tools/tool_implementations/file_reader/file_reader_tool.py`
- `backend/om/tools/tool_implementations/http_request/http_request_tool.py`
- `backend/om/tools/tool_implementations/images/image_generation_tool.py`
- `backend/om/tools/tool_implementations/mcp/mcp_tool.py`
- `backend/tests/external_dependency_unit/answer/test_current_datetime_replacement.py`
- `backend/tests/external_dependency_unit/conftest.py`
- `backend/tests/external_dependency_unit/tools/test_mcp_passthrough_oauth.py`
- `backend/tests/external_dependency_unit/tools/test_oauth_config_crud.py`

## Audit Trail

- EXTRACTED: 1339 (52%)
- INFERRED: 1221 (48%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*