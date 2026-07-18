# Multi-Agent Sequential Orchestration System - Implementation Plan

> **Date**: 2026-02-25 (updated)
> **Status**: Review pending
> **Goal**: Build a multi-agent/assistant system where agents run sequentially based on LLM decisions (similar to LangFlow)

---

## Verdict: FEASIBLE — Architecture Already Has Strong Foundations

The existing Deep Research system (`backend/om/deep_research/`) already implements a multi-agent pattern with an orchestrator LLM that spawns and coordinates sub-agents. The core primitives needed are already in place.

---

## 0. Confidence Assessment & Existing Proof

### The Deep Research System Is Already a Working Multi-Agent Coordinator

The codebase already has a production-proven orchestrator → sub-agent pattern. Here's the exact flow from the code:

```
[dr_loop.py:427]  for cycle in range(max_orchestrator_cycles):   # up to 8 cycles
                       │
                       ▼
[dr_loop.py:503]  Orchestrator LLM decides what to do next
                  tools: research_agent, think_tool, generate_report
                  tool_choice = REQUIRED  ← LLM MUST pick an agent/action
                       │
                       ├── calls "research_agent" with a task string
                       │    └── [research_agent.py] spawns INDEPENDENT sub-agent
                       │        - Has its OWN LLM loop (run_llm_step)
                       │        - Has its OWN tools (WebSearch, OpenURL, Search)
                       │        - Runs up to 30 minutes per agent
                       │        - Returns intermediate report back to orchestrator
                       │
                       ├── calls "think_tool" — orchestrator reasons about results
                       │
                       └── calls "generate_report" — produces final synthesis
```

**Key code reference** (`dr_loop.py:506-509`):
```python
tool_definitions=get_orchestrator_tools(
    include_think_tool=not is_reasoning_model
),
tool_choice=ToolChoiceOptions.REQUIRED,  # LLM MUST pick an agent/action
```

The orchestrator LLM is **forced to pick a tool** — meaning it must decide which agent to call next. This is exactly the LangFlow routing pattern.

### Confidence Breakdown

| Aspect | Confidence | Reason |
|--------|-----------|--------|
| Orchestrator → Agent routing | **95%** | Already working in Deep Research. Just needs generalization. |
| Agent runs its own full LLM loop | **95%** | `research_agent.py` already does this with `run_llm_step()` |
| Output passes between agents | **90%** | DR already passes intermediate reports back to orchestrator via chat history |
| Multiple agent personas with different configs | **85%** | Each Persona already has independent LLM/tools/knowledge. Need to wire them into workflow. |
| Streaming per-agent sections | **90%** | Placement system (turn_index, tab_index) already handles multi-section output |
| Sequential mode | **95%** | Simplest case — just a loop over agents |
| LLM-decision mode | **85%** | Proven pattern, needs generalization from 1 agent type to N agent types |

### Lower Confidence Areas (New Work Required)

| Aspect | Confidence | Risk |
|--------|-----------|------|
| Context passing between diverse agents | **70%** | DR only passes text. Different agent types may need structured data (JSON, files, etc.) |
| Agent failure mid-chain recovery | **65%** | DR has timeout handling, but graceful partial-result recovery across arbitrary agents is new |
| Token budget management across N agents | **60%** | With N agents each having their own LLM loop, total token usage can explode. Need budget controls. |
| Circular/infinite loop prevention | **70%** | Need visited-agent tracking. DR avoids this by design (linear cycles), but generic orchestration could loop. |

### Comparison with LangFlow

| Feature | LangFlow | Our System (Proposed) | Gap |
|---------|----------|----------------------|-----|
| Visual node editor | Yes (React Flow) | No (list-based first) | UI only, not architectural |
| LLM-based routing | Yes | **Yes (already works in DR)** | None |
| Sequential chains | Yes | **Yes (trivial to build)** | None |
| Agent has own tools | Yes | **Yes (Persona has M2M tools)** | None |
| Agent has own LLM | Yes | **Yes (Persona has llm_model_override)** | None |
| Agent has own knowledge | Yes | **Yes (Persona has document_sets)** | None |
| Streaming output | Partial | **Yes (Emitter + Placement)** | We're ahead |
| Conditional branching | Yes | Not yet, Phase 3 | Future work |
| Parallel fan-out/fan-in | Yes | **Yes (DR already does parallel research agents)** | Minor generalization |

### What We're Actually Building

The multi-agent system is essentially:
1. **Generalize** `dr_loop.py` from "1 type of sub-agent (researcher)" → "N types of sub-agents (any Persona)"
2. **Generalize** `dr_mock_tools.py` from "hardcoded research_agent tool" → "dynamic AgentTool per Persona"
3. **Add DB tables** so workflows are configurable instead of hardcoded
4. **Add API endpoints** to create/run workflows

The orchestration pattern itself is **production-proven**. The new challenge is context management between diverse agents.

---

## 0.5 Craft System Analysis — How It Compares

### What Craft Is

**Craft is NOT a multi-agent orchestrator.** It's a **single autonomous coding agent** (OpenCode CLI) running in an isolated sandbox. There is no agent-to-agent coordination.

```
User Message → SessionManager → SandboxManager → OpenCode Agent → Stream back
                                                       │
                                                  Single agent with:
                                                  - Its OWN LLM loop (internal to OpenCode)
                                                  - Its OWN tools (bash, edit, read, glob, grep)
                                                  - Extended thinking enabled
                                                  - Access to knowledge files
                                                  - Runs until task complete
```

### Craft Architecture at a Glance

| Component | Details |
|-----------|---------|
| **Agent** | OpenCode CLI — communicates via ACP (Agent Communication Protocol, JSON-RPC 2.0 over stdin/stdout) |
| **LLM Loop** | Internal to OpenCode, NOT the VertualAI `llm_loop.py` — completely separate |
| **Sandbox** | Isolated workspace per user (local filesystem or Kubernetes pod) |
| **Streaming** | SSE (Server-Sent Events) with ACP event types, NOT the VertualAI Packet/Emitter system |
| **Tools** | File operations, bash commands, web access, MCP servers — NOT the VertualAI Tool system |
| **State** | Stateful sessions with artifacts, snapshots, restore — NOT stateless chat turns |
| **DB** | Separate tables: `BuildSession`, `BuildMessage`, `Sandbox` — NOT `ChatSession`/`ChatMessage` |

### Key Backend Files

| File | Role |
|------|------|
| `backend/om/server/features/build/api/api.py` | Main API router, rate limiting, webapp proxy |
| `backend/om/server/features/build/api/messages_api.py` | Message send endpoint, SSE streaming |
| `backend/om/server/features/build/session/manager.py` | Session lifecycle, agent invocation, streaming state |
| `backend/om/server/features/build/sandbox/base.py` | Abstract SandboxManager interface |
| `backend/om/server/features/build/sandbox/local/` | Filesystem-based sandbox (dev) |
| `backend/om/server/features/build/sandbox/kubernetes/` | Pod-based sandbox (prod) |
| `backend/om/server/features/build/sandbox/util/opencode_config.py` | LLM & tool config generation |
| `backend/om/server/features/build/sandbox/util/agent_instructions.py` | AGENTS.md generation per session |
| `backend/om/server/features/build/AGENTS.template.md` | Agent instruction template |
| `backend/om/server/features/build/configs.py` | Environment variables, feature flags |

### Key Frontend Files

| File | Role |
|------|------|
| `web/src/app/craft/v1/page.tsx` | Main page — two-panel layout (chat + output) |
| `web/src/app/craft/hooks/useBuildStreaming.ts` | SSE stream parsing + FIFO state updates |
| `web/src/app/craft/hooks/useBuildSessionStore.ts` | Zustand store — session state + pre-provisioning |
| `web/src/app/craft/hooks/useBuildSessionController.ts` | URL → session lifecycle management |
| `web/src/app/craft/components/ChatPanel.tsx` | Message history + input bar |
| `web/src/app/craft/components/OutputPanel.tsx` | Tabbed preview (webapp iframe) / files / artifacts |
| `web/src/app/craft/components/ToolCallPill.tsx` | Expandable tool call display with diffs |

### Execution Flow

```
1. User visits /craft/v1
   └── Frontend pre-provisions sandbox in background (ensurePreProvisionedSession)

2. User sends message
   └── POST /api/build/sessions/{id}/send-message → SSE StreamingResponse

3. SessionManager._stream_cli_agent_response()
   ├── Gets user's sandbox (local dir or K8s pod)
   ├── Sends message to OpenCode via ACP (stdin/stdout or kubectl exec)
   └── Streams ACP events back:
       ├── AgentMessageChunk  → text content
       ├── AgentThoughtChunk  → reasoning (collapsible)
       ├── ToolCallStart      → tool invocation began
       ├── ToolCallProgress   → tool result (saved on completion)
       ├── AgentPlanUpdate    → task list / plan
       └── PromptResponse     → agent finished

4. Frontend renders FIFO stream items
   └── Output panel auto-refreshes when /web/ files change (live webapp preview)

5. At stream end, all accumulated state saved to DB
```

### Craft vs Chat vs Our Proposed Multi-Agent System

| Aspect | VertualAI Chat | Craft | Our Multi-Agent (Proposed) |
|--------|-----------|-------|---------------------------|
| **Agent count** | 1 persona per session | 1 OpenCode agent per sandbox | N personas coordinated by orchestrator |
| **LLM loop** | `llm_loop.py` (VertualAI) | OpenCode internal (separate) | `llm_loop.py` (reuse VertualAI) |
| **Tool system** | VertualAI Tool interface | OpenCode tools (bash, edit, etc.) | VertualAI Tool interface (reuse) |
| **Orchestration** | None (single agent) | None (single agent) | LLM-decision or sequential |
| **Agent coordination** | N/A | N/A | Orchestrator routes between agents |
| **Output type** | Text + citations | Code + apps + artifacts | Text + any agent capability |
| **Streaming** | Packet/Emitter system | SSE/ACP events | Packet/Emitter (reuse) |
| **State** | Stateless turns | Stateful sandbox sessions | Workflow execution context |
| **Isolation** | None | Full sandbox (local/K8s) | None (runs in VertualAI process) |

### Is Craft Agent-Based Orchestration?

**No.** Craft is a **single-agent-with-tools** pattern:
- One OpenCode agent makes ALL decisions autonomously
- The agent has its own internal LLM loop (not VertualAI's)
- SessionManager just manages lifecycle — it does NOT route between agents
- Tool calls (bash, edit, read) are sequential decisions by the same agent
- No multi-agent coordination, no orchestrator, no agent handoffs

**The "intelligence" is entirely inside OpenCode**, not in the backend. The backend's role is:
- Session/sandbox lifecycle management
- Streaming event accumulation and persistence
- Rate limiting and access control
- File/knowledge provisioning

### What We Can Learn From Craft For Multi-Agent

1. **SSE streaming pattern** — Craft's FIFO streaming of tool calls + text + thinking is a good UX model for showing multi-agent progress
2. **Session state management** — The `BuildStreamingState` accumulator pattern could inform workflow execution state tracking
3. **Sandbox isolation** — If future agents need code execution, Craft's sandbox infrastructure is reusable
4. **Agent instructions template** — `AGENTS.template.md` per-session personalization pattern is useful for per-step agent context injection

---

## 1. Current Architecture Assets (What Already Exists)

### Orchestrator-Agent Pattern (Deep Research)
| File | Role |
|------|------|
| `backend/om/deep_research/dr_loop.py` | Orchestrator LLM loop that decides what to do next |
| `backend/om/tools/fake_tools/research_agent.py` | Sub-agents with their own LLM loops |
| `backend/om/deep_research/dr_mock_tools.py` | "Fake tools" that act as agent-routing decisions |

**Pattern**: `Orchestrator LLM → decides tool/agent → spawns agent → collects output → decides next step`

### Agentic LLM Loop
| File | Role |
|------|------|
| `backend/om/chat/llm_loop.py` | Reusable agentic loop (LLM call → tool calls → repeat) |
| `backend/om/chat/llm_step.py` | Single LLM step with tool call extraction |
| `backend/om/chat/process_message.py` | Entry point for chat processing |

Already supports multi-turn, tool calling, streaming, citations.

### Tool System
| File | Role |
|------|------|
| `backend/om/tools/interface.py` | Abstract `Tool` base class |
| `backend/om/tools/tool_runner.py` | Parallel tool execution with timeouts |
| `backend/om/tools/tool_constructor.py` | Builds tool instances from DB models |

8+ built-in tools + custom OpenAPI + MCP tools. Tools are M2M linked to Personas.

### Persona (Agent) System
| File | Role |
|------|------|
| `backend/om/db/models.py:3255` | Persona model with system_prompt, tools, LLM config |
| `backend/om/db/persona.py` | Persona CRUD (1346 lines) |
| `backend/om/server/features/persona/api.py` | API endpoints |

Each Persona is independently configurable (own LLM, own tools, own knowledge sources).

### Streaming Infrastructure
| File | Role |
|------|------|
| `backend/om/server/query_and_chat/streaming_models.py` | Packet-based streaming |
| `backend/om/chat/emitter.py` | Queue-based decoupled emission |
| `backend/om/server/query_and_chat/placement.py` | Multi-section output (turn_index, tab_index) |

---

## 2. Orchestration Modes

### Mode 1: LLM Decision (Most LangFlow-like) ⭐ Primary
```
User Query → Orchestrator LLM → decides → Agent A → output →
  Orchestrator LLM → decides → Agent B → output →
  Orchestrator LLM → decides → Final Answer
```
- Orchestrator LLM sees all available agents as "tools"
- Decides which agent to call and what task to give it
- Can loop, skip agents, or call the same agent multiple times
- **Already proven pattern** in the Deep Research system

### Mode 2: Sequential (Simpler)
```
User Query → Agent A → output → Agent B → output → Agent C → Final Output
```
- Fixed order, no LLM routing needed
- Previous agent's output becomes next agent's input
- Cheaper (no orchestrator LLM calls)

### Mode 3: Conditional (Advanced, future)
```
User Query → Agent A → output →
  IF condition → Agent B
  ELSE → Agent C
```
- Rules-based routing (output contains keyword, confidence score, etc.)

---

## 3. Database Schema Changes

### New Table: `agent_workflow`
```sql
CREATE TABLE agent_workflow (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    description TEXT,
    user_id UUID REFERENCES "user"(id) ON DELETE CASCADE,

    -- Orchestration config
    orchestration_mode VARCHAR NOT NULL DEFAULT 'llm_decision',
        -- 'llm_decision' | 'sequential' | 'conditional'
    orchestrator_prompt TEXT,
        -- System prompt for the routing LLM (only for llm_decision mode)
    orchestrator_llm_provider VARCHAR,
    orchestrator_llm_model VARCHAR,
    max_steps INTEGER DEFAULT 10,
    timeout_seconds INTEGER DEFAULT 1800,  -- 30 min default

    -- Metadata
    is_public BOOLEAN DEFAULT TRUE,
    is_visible BOOLEAN DEFAULT TRUE,
    deleted BOOLEAN DEFAULT FALSE,
    icon_name VARCHAR,
    uploaded_image_id VARCHAR,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### New Table: `agent_workflow_step`
```sql
CREATE TABLE agent_workflow_step (
    id SERIAL PRIMARY KEY,
    workflow_id INTEGER REFERENCES agent_workflow(id) ON DELETE CASCADE,
    persona_id INTEGER REFERENCES persona(id) ON DELETE CASCADE,
        -- The agent to run at this step

    step_order INTEGER NOT NULL,          -- For sequential mode ordering
    step_name VARCHAR NOT NULL,           -- Human-readable label
    step_description TEXT,                -- What this step does

    input_mapping JSONB DEFAULT '{}',
        -- How to feed previous step output as input
        -- e.g. {"context": "$step_1.output", "query": "$user_input"}
    output_key VARCHAR DEFAULT 'output',
        -- Name for this step's output in the context dict

    condition JSONB,
        -- Optional, for conditional routing
        -- e.g. {"field": "$step_1.output", "contains": "technical", "goto": "step_3"}

    is_terminal BOOLEAN DEFAULT FALSE,    -- Whether this step ends the workflow

    UNIQUE(workflow_id, step_order)
);
```

### New Table: `workflow_execution` (for tracking/debugging)
```sql
CREATE TABLE workflow_execution (
    id SERIAL PRIMARY KEY,
    workflow_id INTEGER REFERENCES agent_workflow(id),
    chat_session_id INTEGER REFERENCES chat_session(id),
    user_id UUID REFERENCES "user"(id),

    status VARCHAR DEFAULT 'running',  -- 'running' | 'completed' | 'failed' | 'timeout'
    steps_executed JSONB DEFAULT '[]',
        -- [{step_id, persona_id, input, output, duration_ms, tokens_used}]
    total_tokens INTEGER DEFAULT 0,
    total_duration_ms INTEGER DEFAULT 0,

    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);
```

---

## 4. Backend Implementation

### 4a. Agent-as-Tool Adapter
**New file**: `backend/om/tools/tool_implementations/agent_tool.py`

```python
class AgentTool(Tool):
    """Wraps an existing Persona as a callable tool for the orchestrator LLM."""

    def __init__(self, persona: Persona, db_session: Session):
        self.persona = persona
        self.db_session = db_session

    @property
    def name(self) -> str:
        return f"call_agent_{self.persona.id}"

    @property
    def description(self) -> str:
        return f"Delegate to '{self.persona.name}': {self.persona.description}"

    def tool_definition(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task": {
                            "type": "string",
                            "description": "The task/query to delegate to this agent"
                        }
                    },
                    "required": ["task"]
                }
            }
        }

    def run(self, placement, override_kwargs, **llm_kwargs):
        """Run the persona's full LLM loop — same pattern as research_agent.py"""
        llm = get_llm_for_persona(self.persona, self.db_session)
        tools = construct_tools(self.persona, self.db_session)
        # Reuse existing llm_loop
        result = run_llm_loop(llm, tools, context, emitter)
        return ToolResponse(result)
```

Follows the exact pattern of `dr_mock_tools.py` `RESEARCH_AGENT_TOOL_DESCRIPTION` but generalized.

### 4b. Workflow Engine
**New file**: `backend/om/workflows/workflow_engine.py`

```python
def run_workflow(workflow, user_message, emitter, db_session):
    steps = load_workflow_steps(workflow)
    context = {"user_input": user_message}

    if workflow.orchestration_mode == "llm_decision":
        # === LLM-driven routing (mirrors dr_loop.py) ===
        orchestrator_llm = get_llm(workflow.orchestrator_config)
        # Present each agent as a callable tool
        agent_tools = [AgentTool(step.persona, db_session) for step in steps]

        for cycle in range(workflow.max_steps):
            result = run_llm_step(
                orchestrator_llm, context,
                tools=agent_tools,
                system_prompt=workflow.orchestrator_prompt
            )

            if result.has_tool_call:
                agent_persona = resolve_persona(result.tool_call)
                agent_output = run_agent_step(agent_persona, context, emitter)
                context[step.output_key] = agent_output
            else:
                # Orchestrator produced final answer
                emit_final_response(result, emitter)
                break

    elif workflow.orchestration_mode == "sequential":
        # === Fixed order execution ===
        for step in sorted(steps, key=lambda s: s.step_order):
            input_text = apply_input_mapping(step.input_mapping, context)
            agent_output = run_agent_step(step.persona, input_text, emitter)
            context[step.output_key] = agent_output


def run_agent_step(persona, context, emitter):
    """Run a single agent — reuses existing llm_loop.py infrastructure"""
    llm = get_llm_for_persona(persona)
    tools = construct_tools(persona)
    return run_llm_loop(llm, tools, context, emitter)
```

### 4c. API Endpoints
**New file**: `backend/om/server/features/workflow/api.py`

```
POST   /api/workflow              - Create workflow
PATCH  /api/workflow/{id}         - Update workflow
DELETE /api/workflow/{id}         - Delete workflow
GET    /api/workflow/{id}         - Get workflow details
GET    /api/workflows             - List workflows
POST   /api/workflow/{id}/run     - Execute workflow (streaming response)
```

### 4d. New Streaming Packets
Add to `streaming_models.py`:
```python
class WorkflowStepStart(Packet):    # Agent X started
class WorkflowStepDelta(Packet):    # Agent X streaming output
class WorkflowStepEnd(Packet):      # Agent X finished
class WorkflowOrchestratorThinking(Packet):  # Orchestrator deciding next step
```

---

## 5. Frontend Implementation

### Phase 1: List-Based Editor (Recommended first)
Similar to existing `AgentEditorPage.tsx` 3-step wizard:

**Step 1 - Workflow Identity**: Name, description, orchestration mode
**Step 2 - Add Agents**: Sortable list of agent steps
  - Each step: select existing Persona + configure input mapping
  - Drag to reorder (for sequential mode)
**Step 3 - Orchestrator Config** (only for LLM-decision mode):
  - Select orchestrator LLM model
  - Custom orchestrator prompt
  - Max steps, timeout settings

### Phase 2: Visual Graph Editor (Future, LangFlow-like)
- Node-based canvas using React Flow / xyflow library
- Drag agents from sidebar onto canvas
- Connect outputs to inputs with edges
- Visual debugging (highlight active node during execution)

### Execution View
- Multi-section streaming (reuse existing Placement system)
- Each agent's output in its own collapsible section
- Show orchestrator decisions between sections
- Real-time progress indicator

---

## 5.5 How MCP Tools & OpenAPI Custom Tools Work (Current System)

### Answer: Yes, the LLM Decides Everything

All tools — built-in, MCP, and OpenAPI custom — are presented to the LLM in the **exact same way** as OpenAI-format function definitions. The LLM autonomously decides which tools to call. There is no hardcoded routing.

### The Unified Tool Flow

```
                          construct_tools()
                    (tool_constructor.py:108-461)
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                     │
    Built-in Tools      OpenAPI Custom Tools      MCP Tools
    (SearchTool,        (CustomTool from          (MCPTool from
     WebSearchTool,      openapi_schema)           mcp_server)
     ImageGenTool, ...)
          │                    │                     │
          └────────────────────┼────────────────────┘
                               │
                    tool.tool_definition()
                    (all return same format)
                               │
                               ▼
              ┌────────────────────────────────┐
              │  OpenAI Function Call Format:   │
              │  {                              │
              │    "type": "function",          │
              │    "function": {                │
              │      "name": "tool_name",       │
              │      "description": "...",      │
              │      "parameters": { JSON }     │
              │    }                            │
              │  }                              │
              └────────────────────────────────┘
                               │
                    Passed to LLM as:
                    tool_definitions=[...all tools...]
                    tool_choice=AUTO
                               │
                               ▼
              ┌────────────────────────────────┐
              │  LLM DECIDES which to call:    │
              │  Returns tool_calls with       │
              │  name + arguments              │
              └────────────────────────────────┘
                               │
                    run_tool_calls()
                    (tool_runner.py)
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                     │
    Built-in: runs       Custom: HTTP request     MCP: JSON-RPC
    internal logic       to external API          to MCP server
          │                    │                     │
          └────────────────────┼────────────────────┘
                               │
                    ToolResponse → back to LLM
                    (added to chat history as ToolMessage)
                               │
                    LLM continues reasoning...
```

### Key Code Path (llm_loop.py:793-802)

```python
# ALL tool types are treated identically by the LLM loop:
tool_defs = [tool.tool_definition() for tool in final_tools]  # line 793

llm_step_result, has_reasoned = run_llm_step(
    ...
    tool_definitions=tool_defs,     # Flat list of ALL tools
    tool_choice=tool_choice,        # AUTO — LLM decides freely
    ...
)
```

The LLM sees a flat list of function definitions. It has NO idea whether a tool is built-in, custom HTTP, or MCP. It just picks based on name + description + parameter schema.

### How OpenAPI Custom Tools Work

**Configuration**: Admin provides an OpenAPI 3.x JSON schema.

**Storage**: `Tool.openapi_schema` (JSONB column in `tool` table)

**Parsing** (`openapi_parsing.py`):
```
OpenAPI Schema → openapi_to_method_specs() → List[MethodSpec]
                                                    │
Each MethodSpec becomes a separate tool:            │
  - name = operationId                              │
  - description = summary                           │
  - parameters = path params + query params + requestBody
```

**Execution** (`custom_tool.py:146-241`):
```python
def run(self, placement, override_kwargs, **llm_kwargs):
    # 1. Extract path params, query params, request body from LLM args
    # 2. Build URL: base_url + path + query string
    # 3. Make HTTP request with auth headers
    response = requests.request(method, url, json=request_body, headers=self.headers)
    # 4. Parse response (JSON, CSV, image)
    # 5. Return ToolResponse with llm_facing_response (JSON string)
```

**Auth Options**:
- Custom headers (static, set by admin)
- Per-tool OAuth (OAuth2 flow, token stored in DB)
- Passthrough auth (user's login OAuth token)

### How MCP Tools Work

**Configuration**: Admin registers an MCP server URL + transport + auth.

**Discovery** (`mcp_client.py`):
```
Admin triggers discovery → MCP client connects to server →
  session.initialize() → session.list_tools() →
  Returns list of tools with name, description, inputSchema →
  Saved as Tool records with mcp_input_schema + mcp_server_id
```

**Execution** (`mcp_tool.py:108-289`):
```python
def run(self, placement, override_kwargs, **llm_kwargs):
    # 1. Build auth headers (admin config, per-user config, or OAuth token)
    # 2. Open MCP client session (Streamable HTTP or SSE transport)
    # 3. session.initialize() → session.call_tool(name, arguments)
    # 4. Process result (text, JSON, images, embedded resources)
    # 5. Return ToolResponse
```

**Auth Options**:
- None (public MCP server)
- API Token (admin-set or per-user)
- OAuth (per-user OAuth flow)
- Pass-through OAuth (user's login token)

**Transport**:
- `STREAMABLE_HTTP` — HTTP POST with JSON-RPC
- `SSE` — Server-Sent Events stream

### How Tool Construction Works for a Persona

`construct_tools()` in `tool_constructor.py:108-461` iterates `persona.tools` and routes by type:

```python
for db_tool_model in persona.tools:
    if db_tool_model.in_code_tool_id:
        # BUILT-IN: SearchTool, WebSearchTool, ImageGenTool, etc.
        tool_cls = get_built_in_tool_by_id(db_tool_model.in_code_tool_id)
        # ... instantiate with specific config per tool type

    elif db_tool_model.openapi_schema:
        # CUSTOM: Parse OpenAPI → build HTTP-calling tools
        tools = build_custom_tools_from_openapi_schema_and_headers(
            openapi_schema=db_tool_model.openapi_schema,
            custom_headers=db_tool_model.custom_headers,
            user_oauth_token=oauth_token,
        )

    elif db_tool_model.mcp_server_id:
        # MCP: Connect to MCP server, create MCPTool instances
        mcp_server = get_mcp_server_by_id(db_tool_model.mcp_server_id)
        mcp_tool = MCPTool(
            mcp_server=mcp_server,
            tool_name=saved_tool.name,
            tool_definition=saved_tool.mcp_input_schema,
            connection_config=connection_config,
        )
```

### What This Means for Multi-Agent Workflows

**Current state is already good.** Since all tools use the same `Tool` interface and return `ToolResponse`, a workflow agent inherits ALL of its persona's tools — built-in, custom, and MCP. No special handling needed.

When Agent A runs in a workflow step:
1. `construct_tools(agent_a.persona)` builds all its tools (Search + MCP + Custom)
2. LLM sees all tools as flat function definitions
3. LLM calls whichever tools it needs
4. Results flow back normally via ToolResponse
5. Agent A's final output passes to Agent B (or back to orchestrator)

### SOTA Comparison: What's Missing vs Best-in-Class

| Feature | Current System | SOTA (LangGraph, CrewAI, AutoGen) | Gap & Recommendation |
|---------|---------------|----------------------------------|---------------------|
| **LLM decides tool calls** | Yes (tool_choice=AUTO) | Yes | None |
| **Parallel tool execution** | Yes (ThreadPoolExecutor) | Yes | None |
| **Tool retry on failure** | Partial (error → LLM sees error, can retry) | Explicit retry policies | Could add configurable retry count per tool |
| **Tool result validation** | None (raw response passed to LLM) | Schema validation, guardrails | Could add JSON schema validation for tool outputs |
| **Tool timeout per-tool** | Global 10min default | Per-tool configurable | Could add `timeout_seconds` to Tool model |
| **Structured output between agents** | Text only (JSON as string) | Typed schemas (Pydantic models) | Add structured output format spec per workflow step |
| **Tool approval / human-in-the-loop** | None | Yes (LangGraph interrupts) | Could add approval gates before sensitive tools |
| **Dynamic tool loading** | MCP discovery only | Runtime tool registration | Already strong with MCP |
| **Tool cost tracking** | Token counting exists | Per-tool cost attribution | Could extend `ToolCall.tool_call_tokens` |
| **Agent memory across workflow** | None between agents | Shared memory/state | Add shared context dict in workflow engine |

### Recommended SOTA Improvements for Multi-Agent

1. **Structured Inter-Agent Communication**: Instead of passing raw text between agents, define a `WorkflowContext` schema:
   ```python
   class WorkflowContext(BaseModel):
       user_input: str
       step_outputs: dict[str, StepOutput]  # step_name → output
       shared_documents: list[SearchDoc]     # shared citations
       shared_files: list[str]               # shared file IDs
   ```

2. **Tool Result Validation**: Add optional output schema per tool to validate before passing to LLM:
   ```python
   class Tool:
       def output_schema(self) -> dict | None:  # JSON Schema
           return None  # Override per tool
   ```

3. **Human-in-the-Loop Gates**: Add approval checkpoints in workflow:
   ```python
   class AgentWorkflowStep:
       requires_approval: bool = False  # Pause and wait for user OK
   ```

4. **Shared Memory Across Agents**: Reuse the existing `MemoryTool` pattern:
   ```python
   # Each agent in workflow gets access to shared workflow memory
   workflow_memory = WorkflowMemory()
   # Agent A writes: workflow_memory.set("customer_type", "enterprise")
   # Agent B reads: workflow_memory.get("customer_type")
   ```

---

## 6. Example Use Cases

### Research + Summarize + Translate (Sequential)
1. **Researcher Agent**: Has SearchTool + WebSearchTool, searches for info
2. **Summarizer Agent**: Has custom prompt for concise summaries
3. **Translator Agent**: Has custom prompt for translation to target language

### Customer Support Triage (LLM Decision)
- **Classifier Agent**: Determines query type
- **Technical Support Agent**: Has tech knowledge base
- **Billing Support Agent**: Has billing docs
- Orchestrator routes based on classification output

### Content Pipeline (Sequential)
1. **Draft Writer**: Creates initial content
2. **Editor Agent**: Reviews and improves quality
3. **SEO Optimizer**: Adds keywords and formatting

---

## 7. Implementation Phases

### Phase 1 — Core Engine (Week 1-2)
- [ ] Alembic migration for `agent_workflow`, `agent_workflow_step`, `workflow_execution`
- [ ] `AgentTool` adapter class
- [ ] Workflow engine (`run_workflow` with sequential + llm_decision modes)
- [ ] Workflow DB CRUD operations
- [ ] API endpoints (CRUD + streaming execution)
- [ ] New streaming packet types

### Phase 2 — Frontend Editor (Week 2-3)
- [ ] Workflow list page
- [ ] Workflow editor (list-based, sortable steps)
- [ ] Agent selector component (pick from existing Personas)
- [ ] Orchestration mode configuration
- [ ] Input mapping UI

### Phase 3 — Execution & Monitoring (Week 3-4)
- [ ] Workflow execution view with per-agent streaming sections
- [ ] Orchestrator decision visualization
- [ ] Execution history & debugging view
- [ ] Cost/token tracking per step

### Phase 4 — Advanced Features (Future)
- [ ] Visual graph editor (React Flow)
- [ ] Conditional routing mode
- [ ] Workflow templates / marketplace
- [ ] Parallel agent execution (fan-out / fan-in)
- [ ] Agent output validation / guardrails between steps

---

## 8. Key Files to Modify

| File | Change |
|------|--------|
| `backend/om/db/models.py` | Add AgentWorkflow, AgentWorkflowStep, WorkflowExecution models |
| `backend/om/server/manage.py` | Register new API router |
| `backend/om/chat/process_message.py` | Add workflow execution entry point |
| `backend/om/server/query_and_chat/streaming_models.py` | Add workflow packet types |
| `web/src/app/admin/` | Add workflow admin pages |
| `web/src/refresh-pages/` | Add WorkflowEditorPage |

### New Files to Create
| File | Purpose |
|------|---------|
| `backend/om/workflows/__init__.py` | New module |
| `backend/om/workflows/workflow_engine.py` | Core orchestration engine |
| `backend/om/workflows/models.py` | Pydantic schemas |
| `backend/om/db/workflow.py` | DB CRUD operations |
| `backend/om/server/features/workflow/api.py` | API endpoints |
| `backend/om/tools/tool_implementations/agent_tool.py` | Agent-as-Tool adapter |
| `web/src/refresh-pages/WorkflowEditorPage.tsx` | Frontend editor |
| `web/src/refresh-pages/WorkflowListPage.tsx` | Frontend list |

---

## 9. Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Token explosion (orchestrator + multiple agents) | `max_steps` limit, `timeout_seconds`, token budget per step |
| Circular agent calls | Visited-agent tracking set, max depth limit |
| Context loss between agents | Explicit context passing via `input_mapping` JSON |
| Latency (sequential agents add up) | Streaming per-agent, parallel where possible |
| Cost (multiple LLM calls per query) | Cost tracking in `workflow_execution`, budget limits |
| Agent failure mid-workflow | Graceful error handling, partial result return |

---

## 10. Verification Plan

1. **Unit tests**: Workflow engine with mock LLMs and mock agent personas
2. **Integration test**: 3-agent sequential workflow, verify output flows correctly
3. **LLM-decision test**: Workflow with orchestrator, verify correct agent routing
4. **Streaming test**: Frontend receives per-agent streaming sections properly
5. **Timeout test**: Verify `max_steps` and `timeout_seconds` limits enforced
6. **Error test**: Agent failure mid-workflow returns partial results gracefully
