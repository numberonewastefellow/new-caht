# Community 62

> 161 nodes · cohesion 0.03

## Key Concepts

- **CodeInterpreterClient** (63 connections) — `backend/om/tools/tool_implementations/python/code_interpreter_client.py`
- **chat.py** (34 connections) — `backend/om/db/chat.py`
- **Session** (31 connections) — `backend/om/db/chat.py`
- **chat_backend.py** (29 connections) — `backend/om/server/query_and_chat/chat_backend.py`
- **User** (24 connections) — `backend/om/server/query_and_chat/chat_backend.py`
- **UUID** (23 connections) — `backend/om/db/chat.py`
- **Session** (22 connections) — `backend/om/server/query_and_chat/chat_backend.py`
- **handle_send_chat_message()** (16 connections) — `backend/om/server/query_and_chat/chat_backend.py`
- **get_chat_session_by_id()** (15 connections) — `backend/om/db/chat.py`
- **rename_chat_session()** (15 connections) — `backend/om/server/query_and_chat/chat_backend.py`
- **SearchDocKey** (14 connections) — `backend/om/chat/chat_state.py`
- **save_chat_turn()** (14 connections) — `backend/om/chat/save_chat.py`
- **ChatMessage** (12 connections) — `backend/om/db/chat.py`
- **create_new_chat_message()** (12 connections) — `backend/om/db/chat.py`
- **get_chat_session()** (12 connections) — `backend/om/server/query_and_chat/chat_backend.py`
- **duplicate_chat_session_for_user_from_slack()** (11 connections) — `backend/om/db/chat.py`
- **execute_code_in_chat()** (11 connections) — `backend/om/server/query_and_chat/chat_backend.py`
- **ChatSession** (10 connections) — `backend/om/db/chat.py`
- **get_chat_message()** (10 connections) — `backend/om/db/chat.py`
- **fetch_chat_file()** (10 connections) — `backend/om/server/query_and_chat/chat_backend.py`
- **DBSearchDoc** (9 connections) — `backend/om/db/chat.py`
- **UUID** (9 connections) — `backend/om/server/query_and_chat/chat_backend.py`
- **_create_and_link_tool_calls()** (9 connections) — `backend/om/chat/save_chat.py`
- **get_or_create_root_message()** (9 connections) — `backend/om/db/chat.py`
- **get_available_context_tokens_for_session()** (9 connections) — `backend/om/server/query_and_chat/chat_backend.py`
- *... and 136 more nodes in this community*

## Relationships

- [[Agent Chat Packets & Citations]] (78 shared connections)
- [[User Roles & Agent Config]] (32 shared connections)
- [[Chat Datetime & OAuth Tokens]] (10 shared connections)
- [[Community 103]] (10 shared connections)
- [[Community 323]] (10 shared connections)
- [[Community 372]] (6 shared connections)
- [[Community 291]] (5 shared connections)
- [[Analytics & Usage Models (WS-H)]] (5 shared connections)
- [[Community 332]] (3 shared connections)
- [[Community 458]] (3 shared connections)
- [[Community 580]] (3 shared connections)
- [[Community 161]] (3 shared connections)

## Source Files

- `backend/om/chat/chat_processing_checker.py`
- `backend/om/chat/chat_state.py`
- `backend/om/chat/chat_utils.py`
- `backend/om/chat/save_chat.py`
- `backend/om/db/chat.py`
- `backend/om/db/chat_search.py`
- `backend/om/server/query_and_chat/chat_backend.py`
- `backend/om/tools/tool_implementations/python/code_interpreter_client.py`

## Audit Trail

- EXTRACTED: 631 (67%)
- INFERRED: 311 (33%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*