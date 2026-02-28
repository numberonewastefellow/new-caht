# Enterprise Agent Architecture Analysis

## Status: Analysis Document — Gaps Identified, Implementation Pending

---

## 1. Human-in-the-Loop: How Enterprise Frameworks Handle User Feedback

### Industry Patterns

| Pattern | Framework | Mechanism | Production Ready |
|---------|-----------|-----------|-----------------|
| **Interrupt/Resume** | LangGraph | `interrupt()` raises exception → runtime saves checkpoint → graph pauses. User responds via `Command(resume=value)`. Most granular — any node, any point. | Yes (Redis/Postgres checkpointer) |
| **Task-Boundary Webhooks** | CrewAI | Task completes → crew halts → webhook sent with execution_id. External system collects feedback → calls resume endpoint. Feedback injected as context. | Yes (webhook-based) |
| **Return of Control** | AWS Bedrock | Agent returns parameters + `invocationId` to caller. App does human review, sends result with same invocationId. Stateless, async-friendly. | Yes (platform-managed) |
| **Human Input Mode** | AutoGen/AG2 | `human_input_mode` = ALWAYS/TERMINATE/NEVER on agents. Blocks on stdin. | No (console-only) |
| **Guardrails** | OpenAI SDK | Input/output/tool guardrails can block execution. No mid-run pause/resume. | Partial |

**Critical insight**: None of them "wait" in a running thread. They all **stop execution completely, persist state to durable storage, and resume from checkpoint when user responds**. The thread/process is freed. This is essential for scale.

### Which Agents Can Request Input?

**Any agent, not just the first.** This is configurable per-step:

- **LangGraph**: Any node can call `interrupt()`. Multiple nodes can interrupt independently.
- **CrewAI**: Any task with `human_input=True` pauses the crew.
- **AWS Bedrock**: Any action group with `RETURN_CONTROL` pauses.

Example for Travel Planner:

| Step | Agent | Can Request Input | Why |
|------|-------|-------------------|-----|
| 1 | Details Collector | Yes | "What dates? How many travelers?" |
| 2 | Flight Finder | No | Works with given constraints |
| 3 | Hotel Finder | No | Works with given constraints |
| 4 | Activity Planner | Yes | "Found 12 activities — which interest you?" |
| 5 | Budget Calculator | No | Computes from available data |
| 6 | Itinerary Builder | Yes | "Here's the draft — any changes?" |

---

## 2. Memory Architecture: Enterprise Standard vs. Our Current State

### The Three Layers of Agent Memory

```
+-----------------------------------------------------------+
| Layer 3: LONG-TERM MEMORY (Cross-Session)                 |
| Semantic search, user preferences, entity facts           |
| Storage: Vector DB + Redis/Postgres                       |
| Examples: CrewAI Unified Memory, LangGraph Store          |
+-----------------------------------------------------------+
| Layer 2: WORKING MEMORY (Execution State / Checkpoints)   |
| Workflow context, step outputs, pause/resume state        |
| Storage: Redis (fast) or Postgres (durable)               |
| Examples: LangGraph Checkpointer, CrewAI crew state       |
+-----------------------------------------------------------+
| Layer 1: SHORT-TERM MEMORY (Conversation Context)         |
| Chat history, current session messages, token management  |
| Storage: Postgres (messages) + in-memory (token budget)   |
| Examples: All frameworks have this                        |
+-----------------------------------------------------------+
```

### Framework Comparison

| Feature | CrewAI | LangGraph | AutoGen | Our System |
|---------|--------|-----------|---------|------------|
| Short-term (chat history) | Yes | Yes | Yes | **Yes** |
| History compression | No | No | No | **Yes** (summarization) |
| Working memory (checkpoints) | File-based | Redis/Postgres | No | **No** |
| Execution pause/resume | Yes (webhooks) | Yes (interrupt) | No | **No** |
| Step output persistence | Task boundaries | Every super-step | No | **Post-execution only** |
| Long-term memory | Unified Memory (LanceDB) | Store (namespaced KV) | Teachability (vector DB) | **No** |
| Semantic search | Yes (composite scoring) | Yes (namespace queries) | Yes (vector similarity) | **No** |
| Cross-session context | Yes | Yes | Yes (memos) | **No** |
| User preferences | Yes (scoped memory) | Yes (user namespaces) | No | **Limited (10 items)** |
| State versioning | No | Yes (checkpoint history) | No | **No** |
| Crash recovery | Yes (crew rehydration) | Yes (checkpoint replay) | No | **No** |

### CrewAI Unified Memory (Current Best Practice)

```
Hierarchical Scopes:  /  →  /project/alpha  →  /agent/researcher
Composite Scoring:    0.4 * similarity + 0.3 * recency + 0.3 * importance
Deduplication:        Consolidates memories above 0.85 similarity threshold
Storage:              LanceDB (default), supports Pinecone, Chroma, etc.
Embedder:             OpenAI (default), supports Ollama, Azure, Cohere
```

### LangGraph Checkpointer (State Persistence Gold Standard)

```
Checkpoint saved at:  Every super-step (batch of parallel node executions)
Resume via:           thread_id (same = resume, new = fresh)
Performance (Redis):  GET: 2,950 ops/sec (0.34ms), LIST: 696 ops/sec (1.44ms)
Backends:             InMemory, SQLite, Postgres, Redis, CosmosDB
TTL support:          default_ttl + refresh_on_read
Serialization:        JsonPlusSerializer (msgpack-based), optional AES encryption
```

---

## 3. Our Current Architecture: What Exists

### What We HAVE (Layer 1: Short-term)

| Component | Storage | Details |
|-----------|---------|---------|
| Chat messages | PostgreSQL (`ChatMessage`) | Tree structure with branching, parent/child links |
| Chat sessions | PostgreSQL (`ChatSession`) | UUID-based, persona-linked |
| History compression | PostgreSQL | Progressive summarization when tokens exceed budget |
| Token management | In-memory | `construct_message_history()` — drops oldest first, preserves recent |
| User memories | PostgreSQL (`Memory`) | Max 10 per user, auto-evict oldest |
| Workflow execution log | PostgreSQL (`WorkflowExecution`) | `steps_executed` JSONB array (post-execution only) |
| Clarification flag | PostgreSQL (`ChatMessage.is_clarification`) | Used by Deep Research to skip clarification on resume |

### What We're MISSING

#### Missing: Layer 2 — Working Memory (Checkpoints)

| Gap | Impact | Enterprise Solution |
|-----|--------|-------------------|
| `WorkflowContext.step_outputs` is in-memory only | Crash = all context lost | LangGraph: checkpoint to Redis/Postgres at every step |
| No `paused_at_step` field on `WorkflowExecution` | Can't pause/resume workflows | LangGraph: `interrupt()` saves graph state |
| No `awaiting_user_input` flag | Can't detect paused workflows | CrewAI: webhook with execution_id |
| No checkpoint of partial execution | Can't resume after failure | LangGraph: replay from last checkpoint |
| Agent outputs truncated to 250 words for orchestrator | Orchestrator loses detail | LangGraph: full state in checkpoint, scoped views for nodes |

#### Missing: Layer 3 — Long-term Memory (Cross-Session)

| Gap | Impact | Enterprise Solution |
|-----|--------|-------------------|
| No semantic memory | Can't recall "user prefers window seats" across sessions | CrewAI: Unified Memory with composite scoring |
| No entity memory | Can't track facts about users/topics | CrewAI: entity extraction + vector storage |
| No cross-session workflow context | Each run starts fresh, no learning | LangGraph Store: namespaced KV with semantic search |
| No agent-specific memory | Agents can't remember past interactions | AutoGen Teachability: vector DB + memo persistence |
| Limited user preferences (10 items, text only) | No structured preference tracking | Redis Agent Memory Server: working + long-term tiers |

---

## 4. How Our Deep Research Handles Feedback (Reference Implementation)

Deep Research uses a **stop-and-restart** pattern, not true pause/resume:

```
1. User sends message (deep_research=true)
2. LLM decides: "Need clarification?"
   YES → Emit clarification as normal assistant message
       → Set ChatMessage.is_clarification = True in DB
       → Emit OverallStop packet
       → RETURN (execution stops completely, thread freed)
   NO  → Continue to research plan
3. User responds (normal chat message in same session)
4. Backend detects last assistant was is_clarification=True
   → skip_clarification=True
   → Starts fresh execution with full chat history (includes user's answer)
```

**Key properties:**
- No running thread waits — execution stops completely
- State is "persisted" via chat history (messages in DB)
- Resume is a fresh execution that reads history and skips completed phases
- Simple, works, but loses any in-memory computation state

---

## 5. Recommended Architecture for Enterprise-Grade Workflows

### Phase 1: Human-in-the-Loop (Highest Priority)

Add per-step `can_request_input` flag + checkpoint-based pause/resume:

**DB Changes:**
- `AgentWorkflowStep.can_request_input: bool` — configurable per step
- `WorkflowExecution.paused_at_step_id: int | null` — which step is paused
- `WorkflowExecution.checkpoint_data: JSONB` — serialized `WorkflowContext` (step_outputs + shared_data)

**Engine Changes:**
- After each step, if agent output contains clarification signal → save checkpoint → emit stop → return
- On next user message → detect paused execution → restore checkpoint → resume from paused step

**Streaming Changes:**
- New packet: `WorkflowPauseForInput` with `questions` field
- Frontend shows input form, user responds, triggers resume

### Phase 2: Execution Checkpoints (Crash Recovery)

Checkpoint `WorkflowContext` to DB after each step completes:

```python
# After each step completes:
update_workflow_execution(
    db_session, execution_id,
    checkpoint_data={
        "step_outputs": context.step_outputs,
        "shared_data": context.shared_data,
        "completed_steps": [s.id for s in completed],
        "next_step_index": i + 1,
    }
)
```

On crash recovery: load checkpoint, skip completed steps, resume.

### Phase 3: Long-term Memory (Cross-Session)

Two approaches by priority:

**3a. Structured Memory (simpler, use existing Postgres)**
- Extend `Memory` model: add `memory_type` (preference, entity, fact), `namespace`, `importance_score`
- Remove 10-item hard limit, add TTL-based eviction
- Include relevant memories in agent system prompts

**3b. Semantic Memory (requires vector DB)**
- Add pgvector extension to existing Postgres (or use Vespa which is already in the stack)
- Embed conversation summaries + extracted facts
- Retrieve relevant memories via similarity search before each agent call
- Similar to CrewAI's composite scoring: `0.4 * similarity + 0.3 * recency + 0.3 * importance`

---

## 6. Summary: Current State vs Enterprise Grade

```
                        CURRENT              ENTERPRISE TARGET
                        -------              -----------------
User Feedback:          None (one-way)  -->  Per-step interrupt/resume
State Persistence:      Post-execution  -->  Checkpoint after every step
Crash Recovery:         Lost context    -->  Resume from last checkpoint
Memory Scope:           Single session  -->  Cross-session semantic memory
Agent Collaboration:    250-word summary -> Full context with scoped views
User Preferences:       10 text items   -->  Structured + semantic + unlimited
Pause/Resume:           Not possible    -->  Any step can pause for input
```

---

## 7. Priority Order for Implementation

1. **Human-in-the-loop** (Phase 1) — Biggest UX gap. Users can't provide missing details.
2. **Execution checkpoints** (Phase 2) — Safety net for crashes + enables pause/resume.
3. **Long-term memory** (Phase 3) — Differentiator for enterprise. Agents learn from past sessions.

## 8. Files That Need Changes

| File | Phase | Change |
|------|-------|--------|
| `backend/onyx/db/models.py` | 1 | Add `can_request_input` to step, `paused_at_step_id` + `checkpoint_data` to execution |
| `backend/onyx/workflows/models.py` | 1 | Add checkpoint schemas, pause/resume request models |
| `backend/onyx/workflows/workflow_engine.py` | 1-2 | Checkpoint after each step, detect pause signal, resume logic |
| `backend/onyx/server/query_and_chat/streaming_models.py` | 1 | New `WorkflowPauseForInput` packet type |
| `backend/onyx/chat/process_message.py` | 1 | Detect paused workflow execution, route to resume |
| `backend/onyx/db/workflow.py` | 1-2 | CRUD for checkpoints, pause/resume state |
| `web/src/lib/workflows/interfaces.ts` | 1 | Add `can_request_input` to step interface |
| `web/src/refresh-pages/WorkflowEditorPage.tsx` | 1 | UI toggle for "Can Request Input" per step |
| Frontend chat components | 1 | Handle `WorkflowPauseForInput` packet, show input form |
| `backend/onyx/db/memory.py` | 3 | Extend memory model with types, namespaces, scoring |
