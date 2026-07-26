# MCP Server Integration

> 167 nodes · cohesion 0.03

## Key Concepts

- **api.py** (50 connections) — `backend/om/server/features/mcp/api.py`
- **Session** (27 connections) — `backend/om/server/features/mcp/api.py`
- **mcp.py** (26 connections) — `backend/om/db/mcp.py`
- **User** (25 connections) — `backend/om/server/features/mcp/api.py`
- **Session** (22 connections) — `backend/om/db/mcp.py`
- **get_mcp_server_by_id()** (21 connections) — `backend/om/db/mcp.py`
- **_upsert_mcp_server()** (20 connections) — `backend/om/server/features/mcp/api.py`
- **_connect_oauth()** (19 connections) — `backend/om/server/features/mcp/api.py`
- **_list_mcp_tools_by_id()** (19 connections) — `backend/om/server/features/mcp/api.py`
- **update_mcp_server__no_commit()** (16 connections) — `backend/om/db/mcp.py`
- **_db_mcp_server_to_api_mcp_server()** (15 connections) — `backend/om/server/features/mcp/api.py`
- **_ensure_mcp_server_owner_or_admin()** (14 connections) — `backend/om/server/features/mcp/api.py`
- **save_user_credentials()** (14 connections) — `backend/om/server/features/mcp/api.py`
- **extract_connection_data()** (13 connections) — `backend/om/db/mcp.py`
- **get_mcp_server_tools_snapshots()** (12 connections) — `backend/om/server/features/mcp/api.py`
- **process_oauth_callback()** (12 connections) — `backend/om/server/features/mcp/api.py`
- **get_mcp_server_db_tools()** (11 connections) — `backend/om/server/features/mcp/api.py`
- **OmTokenStorage** (11 connections) — `backend/om/server/features/mcp/api.py`
- **update_mcp_server_simple()** (11 connections) — `backend/om/server/features/mcp/api.py`
- **update_mcp_server_with_tools()** (11 connections) — `backend/om/server/features/mcp/api.py`
- **update_connection_config()** (10 connections) — `backend/om/db/mcp.py`
- **delete_mcp_server_admin()** (10 connections) — `backend/om/server/features/mcp/api.py`
- **MCPConnectionConfig** (9 connections) — `backend/om/db/mcp.py`
- **MCPServer** (9 connections) — `backend/om/db/mcp.py`
- **get_user_connection_config()** (9 connections) — `backend/om/db/mcp.py`
- *... and 142 more nodes in this community*

## Relationships

- [[User Roles & Agent Config]] (42 shared connections)
- [[Community 103]] (17 shared connections)
- [[Chat Datetime & OAuth Tokens]] (11 shared connections)
- [[Community 168]] (6 shared connections)
- [[Backend Agent/API Test Fixtures]] (4 shared connections)
- [[Community 72]] (3 shared connections)
- [[Community 69]] (3 shared connections)
- [[Analytics & Usage Models (WS-H)]] (3 shared connections)
- [[Community 106]] (1 shared connections)
- [[Community 538]] (1 shared connections)
- [[Community 549]] (1 shared connections)

## Source Files

- `backend/om/db/mcp.py`
- `backend/om/db/tools.py`
- `backend/om/server/features/mcp/api.py`
- `phoenix/tutorials/mcp/tracing_between_mcp_client_and_server/client.py`

## Audit Trail

- EXTRACTED: 668 (79%)
- INFERRED: 182 (21%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*