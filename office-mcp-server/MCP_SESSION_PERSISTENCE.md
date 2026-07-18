# MCP Session Persistence: Problem Statement & Enterprise SOTA Analysis

## Problem Statement

### What's Broken

VirtualAI's MCP client creates a **new session for every tool call**. This breaks any MCP server that maintains **in-memory state across tool calls** — including the PPT MCP Server, which holds `Presentation` objects in memory per session.

**The call chain today:**

```
Agent LLM says: call create_presentation()
  -> MCPTool.run()
    -> call_mcp_tool()
      -> streamablehttp_client()          # new connection
        -> ClientSession()                # new session
          -> session.initialize()         # server assigns session ID "abc123"
          -> session.call_tool(...)       # presentation created in memory
        <- session exits                  # session "abc123" destroyed
      <- connection closed

Agent LLM says: call add_slide()
  -> MCPTool.run()
    -> call_mcp_tool()
      -> streamablehttp_client()          # NEW connection
        -> ClientSession()                # NEW session
          -> session.initialize()         # server assigns NEW session ID "def456"
          -> session.call_tool(...)       # ERROR: no presentation in this session
        <- session exits
      <- connection closed
```

The presentation created in session `abc123` is gone by the time `add_slide` runs in session `def456`. The PPT MCP Server returns success for `create_presentation`, but the in-memory `Presentation` object is garbage-collected when the session closes.

### Impact

- **PPT Builder agent** calls tools successfully but produces **no output file** — each tool call starts fresh
- The server logs show 1 `CallToolRequest` per session (3 sessions for 3 tool calls), confirming sessions are not reused
- The `auto_generate_presentation` tool works as a single-call workaround, but loses the fine-grained multi-tool pipeline (charts, tables, custom formatting)
- **Any stateful MCP server** will have this problem — not just PowerPoint

### Root Cause (Code)

```
backend/om/tools/tool_implementations/mcp/mcp_client.py

  call_mcp_tool()                           # line 246
    -> _call_mcp_client_function_sync()     # line 179
      -> _create_mcp_client_function_runner()  # line 122
        -> async with streamablehttp_client(server_url):   # line 144
            async with ClientSession(read, write):         # line 158
              await function(session)                      # one-shot

  No mechanism to reuse sessions across multiple call_mcp_tool() invocations.
```

The `streamablehttp_client` and `ClientSession` are both `async with` context managers — they open, execute one function, and close. There is no session pool, no session ID tracking, and no way to persist a session across multiple synchronous `MCPTool.run()` calls from the agent's LLM loop.

---

## How Enterprise Platforms Solve This

### 1. MCP Protocol Specification (Official)

The [MCP Specification (2025-11-25)](https://modelcontextprotocol.io/specification/2025-11-25) explicitly supports stateful sessions:

- Server assigns a `Mcp-Session-Id` header during initialization
- Client **MUST** include this header on all subsequent requests
- Session affinity is required — all requests with the same session ID must route to the same server instance
- Sessions can be terminated explicitly via `DELETE /mcp`

**Key insight**: The protocol was designed for multi-tool sessions. Our client implementation ignores this by creating disposable sessions.

### 2. LangChain / LangGraph MCP Adapters

[langchain-mcp-adapters](https://github.com/langchain-ai/langchain-mcp-adapters) provides two modes:

| Mode | How It Works | Use Case |
|------|-------------|----------|
| **Stateless** (default) | `MultiServerMCPClient.get_tools()` — each tool invocation creates a fresh session | Simple tools (search, calculator) |
| **Persistent** | `client.session()` — returns a long-lived `ClientSession` that stays open | Stateful servers (file editors, PowerPoint, databases) |

```python
# LangChain persistent session pattern
async with client.session("ppt-server") as session:
    tools = session.get_tools()
    # All tool calls reuse the same session
    agent = create_react_agent(model, tools)
    await agent.ainvoke({"messages": [...]})
    # Session stays open throughout the agent's entire LLM loop
```

**Key insight**: The client manages session lifecycle at the agent scope — session opens when the agent starts, closes when the agent finishes.

### 3. Microsoft Agent Framework (AutoGen + Semantic Kernel)

[Microsoft Agent Framework](https://learn.microsoft.com/en-us/agent-framework/overview/) provides:

- **Session-based state management** — agent sessions track state across tool calls
- **MCP client integration** — supports stdio, HTTP streaming, and WebSocket connections
- **Middleware pipeline** — interceptors can modify requests, add session headers, implement retries
- **Graph-based orchestration** — explicit multi-agent workflows with typed edges

Their MCP integration maintains a session context per agent execution scope, with automatic cleanup when the agent step completes.

### 4. OpenAI Agents SDK

[OpenAI Agents SDK Sessions](https://openai.github.io/openai-agents-python/sessions/) provides:

- `Session` objects that persist state between `session.run()` calls
- Multiple storage backends: SQLite, Redis, SQLAlchemy, Dapr, OpenAI-hosted
- The session is the memory container — tool results carry forward automatically
- Thread-scoped checkpoints for rollback on failure

```python
# OpenAI SDK pattern
session = SQLiteSession(db_path="sessions.db")
session.run("Create a presentation about AI")
# Tool calls within this run share session state
session.run("Add a chart to slide 3")
# Previous state (the presentation) is still available
```

### 5. AWS Bedrock AgentCore

[AWS Bedrock AgentCore](https://repost.aws/questions/QU-YbedQP2Qj6QwqR5EnuELQ/) takes a different approach:

- MCP servers **must be stateless** between HTTP requests (no process-local RAM)
- State is externalized to DynamoDB, S3, Redis, or AgentCore Memory
- This enables horizontal scaling but requires servers to be session-aware

**Key insight**: The alternative to client-managed sessions is server-side state externalization — but this requires the MCP server itself to support it.

### 6. FastMCP / Prefect

[FastMCP](https://github.com/PrefectHQ/fastmcp) addresses this directly:

- `StreamableHttpTransport` was creating new sessions per connection ([Issue #2790](https://github.com/PrefectHQ/fastmcp/issues/2790))
- Fix: Transport reuses existing sessions by tracking `mcp-session-id` headers
- Client maintains a `session_id` → `transport` mapping for connection reuse

---

## Enterprise Architecture Patterns (Ranked)

### Pattern A: Client-Side Session Pool (Recommended)

```
┌─────────────────────────────────────────────────────┐
│                 Agent Execution Scope                │
│                                                     │
│  ┌──────────────────────────────────────────────┐   │
│  │          MCP Session Manager                  │   │
│  │                                              │   │
│  │  sessions: {                                 │   │
│  │    "scope_123::server_A": ClientSession_1,   │   │
│  │    "scope_123::server_B": ClientSession_2,   │   │
│  │  }                                           │   │
│  └──────────┬──────────────────┬────────────────┘   │
│             │                  │                     │
│    ┌────────┴────────┐  ┌─────┴──────────┐          │
│    │  Tool Call #1   │  │  Tool Call #2   │          │
│    │  create_pres()  │  │  add_slide()    │          │
│    │  session = pool │  │  session = pool │ (same!)  │
│    └─────────────────┘  └────────────────┘          │
│                                                     │
│  On scope exit: close all sessions                  │
└─────────────────────────────────────────────────────┘
```

**How it works:**
1. When an agent step begins, a `scope_id` is assigned (e.g., `workflow_step_{step_id}`)
2. First MCP tool call: session manager creates a new `ClientSession`, stores it keyed by `(scope_id, server_url)`
3. Subsequent tool calls: session manager returns the existing `ClientSession`
4. When the agent step finishes: session manager closes all sessions for that scope
5. Safety: TTL on sessions (5 min) to auto-close abandoned sessions

**Pros:** Minimal server changes, works with any MCP server, session lifecycle matches agent lifecycle
**Cons:** Async context management complexity (must keep event loop alive)

**Used by:** LangChain MCP Adapters (persistent mode), Microsoft Agent Framework

### Pattern B: Server-Side State Externalization

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Tool Call 1 │     │  Tool Call 2 │     │  Tool Call 3 │
│  (session A) │     │  (session B) │     │  (session C) │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                    │
       └────────────┬───────┴────────────────────┘
                    │
              ┌─────┴─────┐
              │   Redis    │  state_key = "pres_user_123"
              │            │  value = serialized Presentation
              └────────────┘
```

**How it works:**
1. MCP server stores state in Redis/DynamoDB keyed by a `state_key` passed as a tool argument
2. Each tool call loads state, operates on it, saves it back
3. Client doesn't need session persistence — any session can access the state

**Pros:** Horizontally scalable, survives server restarts, works with stateless clients
**Cons:** Requires MCP server modification, serialization overhead, storage dependency

**Used by:** AWS Bedrock AgentCore, production-grade MCP deployments

### Pattern C: Single-Call Aggregation (Workaround)

```
┌──────────────────────────────────────────┐
│  Agent LLM                               │
│                                          │
│  Instead of:                             │
│    call create_presentation()            │
│    call add_slide(layout="title")        │
│    call add_slide(layout="content")      │
│    call save_presentation()              │
│                                          │
│  Do this:                                │
│    call auto_generate_presentation({     │
│      topic: "...",                        │
│      slides: [{...}, {...}],             │
│      output_path: "..."                  │
│    })                                    │
│                                          │
└──────────────────────────────────────────┘
```

**How it works:**
1. Use a single "do-everything" tool that handles the full workflow internally
2. All state is local to that one tool call — no cross-session state needed

**Pros:** No infrastructure changes, works today
**Cons:** Loses fine-grained control, can't handle iterative refinement, limits the LLM's ability to adapt

**Used by:** Simple integrations, quick workarounds

---

## Recommended Implementation: Pattern A (Client-Side Session Pool)

This is the enterprise-grade approach used by LangChain, Microsoft, and the MCP specification itself. It requires changes to 4-5 files in the Onyx backend with no changes to the MCP server.

### Why Pattern A

1. **Protocol-compliant**: Uses `Mcp-Session-Id` as designed by the MCP specification
2. **Zero server changes**: Works with any MCP server (PPT, databases, file editors, etc.)
3. **Scoped lifecycle**: Session lives exactly as long as the agent step — no leaks, no orphans
4. **Backward compatible**: Without a `scope_id`, existing behavior is preserved (new session per call)
5. **Already proven**: LangChain's persistent session mode and Microsoft Agent Framework both use this pattern

### Files to Change

| File | Change | Lines |
|------|--------|-------|
| `mcp_client.py` | Add `MCPSessionManager` class with get/create/close | ~80 new |
| `mcp_client.py` | Modify `call_mcp_tool()` to accept `session_scope_id` | ~10 modified |
| `mcp_tool.py` | Accept `session_scope_id` in constructor, pass to `call_mcp_tool()` | ~5 modified |
| `tool_constructor.py` | Pass `chat_session_id` to `MCPTool()` constructor | ~3 modified |
| `agent_tool.py` | Pass scope ID when constructing tools; cleanup on exit | ~8 modified |

### The Async Challenge

The `streamablehttp_client` is an `async with` context manager. To keep it alive across multiple synchronous `call_mcp_tool()` calls:

1. Start a **dedicated event loop thread** for the session manager
2. `streamablehttp_client` and `ClientSession` contexts run on that loop and stay open
3. Synchronous `call_mcp_tool()` submits work to that loop via `asyncio.run_coroutine_threadsafe()`
4. On scope close: exit the async contexts on that loop, then optionally shut down the loop

This is the same pattern used by LangChain's `MultiServerMCPClient` for persistent sessions and by the MCP Python SDK's own test infrastructure.

---

## References

- [MCP Specification (2025-11-25)](https://modelcontextprotocol.io/specification/2025-11-25) — Official protocol spec with session lifecycle
- [MCP Transports: Streamable HTTP](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports) — Session ID header requirements
- [LangChain MCP Adapters: Session Management](https://deepwiki.com/langchain-ai/langchain-mcp-adapters/3-session-management-and-transport) — Stateless vs persistent modes
- [FastMCP Issue #2790: Session persistence](https://github.com/PrefectHQ/fastmcp/issues/2790) — Same problem in FastMCP
- [LiteLLM Issue #20242: MCP session ID persistence](https://github.com/BerriAI/litellm/issues/20242) — Same problem in LiteLLM
- [MCP Python SDK Issue #713: Multi server lifespan](https://github.com/modelcontextprotocol/python-sdk/issues/713) — Session lifecycle management
- [MCP TypeScript SDK Issue #852: Missing session reuse](https://github.com/modelcontextprotocol/typescript-sdk/issues/852) — Browser client session reuse bug
- [Microsoft Agent Framework](https://learn.microsoft.com/en-us/agent-framework/overview/) — Enterprise MCP integration with session state
- [OpenAI Agents SDK: Sessions](https://openai.github.io/openai-agents-python/sessions/) — Session persistence patterns
- [AWS Bedrock AgentCore: Session State](https://repost.aws/questions/QU-YbedQP2Qj6QwqR5EnuELQ/) — Stateless server + external state pattern
- [MCP Session Affinity with NGINX Plus](https://community.f5.com/kb/technicalarticles/mcp-session-affinity-with-f5-nginx-plus/341961) — Load balancing with sticky sessions
- [How to Load Balance Streamable MCP Servers](https://thenewstack.io/scaling-ai-interactions-how-to-load-balance-streamable-mcp/) — HAProxy session persistence
- [MCP Server Best Practices 2026](https://www.cdata.com/blog/mcp-server-best-practices-2026) — Enterprise deployment patterns
- [AI Agent Orchestration Patterns (Azure)](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/ai-agent-design-patterns) — Microsoft's agent design patterns
