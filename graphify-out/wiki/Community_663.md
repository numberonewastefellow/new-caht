# Community 663

> 22 nodes · cohesion 0.13

## Key Concepts

- **MCPSessionManager** (10 connections) — `backend/om/tools/tool_implementations/mcp/mcp_client.py`
- **.get_or_create()** (10 connections) — `backend/om/tools/tool_implementations/mcp/mcp_client.py`
- **.call_tool()** (9 connections) — `backend/om/tools/tool_implementations/mcp/mcp_client.py`
- **._close_entry()** (6 connections) — `backend/om/tools/tool_implementations/mcp/mcp_client.py`
- **._start_session_loop()** (5 connections) — `backend/om/tools/tool_implementations/mcp/mcp_client.py`
- **.__init__()** (5 connections) — `backend/om/tools/tool_implementations/mcp/mcp_client.py`
- **_SessionEntry** (4 connections) — `backend/om/tools/tool_implementations/mcp/mcp_client.py`
- **.close_all()** (3 connections) — `backend/om/tools/tool_implementations/mcp/mcp_client.py`
- **.close_scope()** (3 connections) — `backend/om/tools/tool_implementations/mcp/mcp_client.py`
- **._key()** (3 connections) — `backend/om/tools/tool_implementations/mcp/mcp_client.py`
- **Event** (2 connections) — `backend/om/tools/tool_implementations/mcp/mcp_client.py`
- **Thread** (2 connections) — `backend/om/tools/tool_implementations/mcp/mcp_client.py`
- **AbstractEventLoop** (1 connections) — `backend/om/tools/tool_implementations/mcp/mcp_client.py`
- **.__init__()** (1 connections) — `backend/om/tools/tool_implementations/mcp/mcp_client.py`
- **Holds a live MCP session with its async resources.** (1 connections) — `backend/om/tools/tool_implementations/mcp/mcp_client.py`
- **Thread-safe pool of persistent MCP sessions keyed by (scope_id, server_url).** (1 connections) — `backend/om/tools/tool_implementations/mcp/mcp_client.py`
- **Runs in a dedicated daemon thread. Opens the async transport + session         a** (1 connections) — `backend/om/tools/tool_implementations/mcp/mcp_client.py`
- **Return a persistent session, creating one if needed.** (1 connections) — `backend/om/tools/tool_implementations/mcp/mcp_client.py`
- **Call a tool using a persistent session. Creates the session if needed.** (1 connections) — `backend/om/tools/tool_implementations/mcp/mcp_client.py`
- **Signal the session loop to stop (non-blocking).** (1 connections) — `backend/om/tools/tool_implementations/mcp/mcp_client.py`
- **Close all sessions for a given scope (called when agent step ends).** (1 connections) — `backend/om/tools/tool_implementations/mcp/mcp_client.py`
- **Close all sessions (for shutdown).** (1 connections) — `backend/om/tools/tool_implementations/mcp/mcp_client.py`

## Relationships

- [[Community 538]] (13 shared connections)
- [[Salesforce Connector]] (1 shared connections)

## Source Files

- `backend/om/tools/tool_implementations/mcp/mcp_client.py`

## Audit Trail

- EXTRACTED: 71 (99%)
- INFERRED: 1 (1%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*