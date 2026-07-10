# Workflow System — Copilot Studio / Foundry-Inspired Features

> **Status:** Design / planning document for review. No code has been written yet. Scope is *explanation +
> design* so the features can be reviewed and prioritized before implementation.

## Context

We researched Microsoft **Copilot Studio**, **Foundry Agent Service**, and **M365 Copilot prebuilt agents**, and
want to bring their strengths into this repo's multi-agent workflow engine. This document explains, for each
feature: **what it is**, **how it works in our architecture**, **a concrete example**, the **files it touches**,
and **open design decisions**.

## Prior-Art Audit — read this first

A sweep of the repo's own design docs showed that **two of these five features are already built**, and **F1
already has a better, file-level plan**. The repo's docs predate this one and are authoritative.

| Feature | Prior analysis? | Where | Real status |
|---|---|---|---|
| **F1** Parallel | **Yes — extensive** | `backend/onyx/workflows/PARALLEL_EXECUTION.md` (+ `LIMITATIONS.md` §2, `PERFORMANCE.md` §4 / Tier-3) | NOT IMPLEMENTED; **design complete — build that, not F1 below** |
| **F2** Triggers | **No — blank spot** | only "Event Based connectors" in `connectors/README.md`, marked *"not used… future design purposes"* (ingestion, not workflow triggering) | NOT IMPLEMENTED, NOT ANALYZED |
| **F3** Connected agents | Yes | `MULTI_AGENT_IMPLEMENTATION_PLAN.md` §4a | **Primitive IMPLEMENTED** (`agent_tool.py`); only builder UX + cycle guard missing |
| **F4** Gallery | Barely | one bullet "Workflow templates / marketplace", `MULTI_AGENT_IMPLEMENTATION_PLAN.md` Phase 4 | NOT IMPLEMENTED |
| **F5** External data | Yes | `MULTI_AGENT_IMPLEMENTATION_PLAN.md` §5.5; `backend/onyx/mcp_server/README.md`; `docs/folder-connector.md` | **Tool/MCP mechanism IMPLEMENTED**; only live mail/DB tools undesigned |

**Net: F2 and F4 are the only features where new design work adds real value.**

### Stale-doc warnings (these docs contradict shipped code — trust the code)

- `backend/onyx/workflows/PAUSE_RESUME_DESIGN.md` says *"Design Complete — Implementation Pending"* and that resume
  is broken. But `workflows/models.py:246-269` already has `WorkflowCheckpoint` with `clarification_conversation`
  and `paused_agent_original_task` — the exact redesign it proposes. **Shipped.**
- `backend/onyx/workflows/PROMOTE_OUTPUT_DESIGN.md` says *"NOT IMPLEMENTED — research only."* But `promote_output`
  is a live field on `WorkflowStepCreate` and is used in workflow templates. **Shipped.**
- `MULTI_AGENT_IMPLEMENTATION_PLAN.md`'s comparison table claims fan-out/fan-in = "Yes". **Wrong.** The Deep
  Research primitive exists; the workflow-engine feature does not. `PARALLEL_EXECUTION.md` is correct.

### What we already have (baseline — do not rebuild)

- **Orchestration engine:** `backend/onyx/workflows/workflow_engine.py` — `run_workflow_sequential()` and `run_workflow_llm_decision()`.
- **Modes today:** `OrchestrationMode = Literal["sequential", "llm_decision"]`; `StepType = Literal["agent", "conditional_router"]` (`backend/onyx/workflows/models.py:14-17`).
- **A2A primitive:** `AgentTool` wraps any Persona as a callable tool (`backend/onyx/tools/tool_implementations/agent_tool.py`); a finished workflow becomes a reusable Persona via `create_or_update_workflow_persona()` (`backend/onyx/db/workflow.py`).
- **Tools & templates:** MCP tool integration plus 36 JSON workflow templates in `backend/tests/workflow_creator/workflows/` deployed by `create_workflows.py`.
- **Visual builder:** `web/src/components/workflow-builder/` (React Flow; Agent / Conditional Router / Orchestrator / Finish nodes).
- **HITL:** pause/resume via `WorkflowCheckpoint` (`backend/onyx/workflows/models.py:246`).
- **Step model:** already supports `input_mapping`, `output_key`, `is_terminal`, and per-step overrides.

### Cross-cutting constraints (from `CLAUDE.md`)

- **Dual-editor rule:** any new workflow field must be reflected in **both** editors — the Wizard (`web/src/refresh-pages/WorkflowEditorPage.tsx`) and the Visual Builder (`web/src/components/workflow-builder/*`).
- **Migrations:** new DB columns need an Alembic migration, but **never run alembic directly** — the backend applies pending migrations on restart.
- **Theming:** accent colors via CSS variables only; no hardcoded colors in any new gallery/node UI.
- **Graph:** after code changes, run `graphify update .` to refresh the knowledge graph.

ORM models live in `backend/onyx/db/models.py` (`AgentWorkflow`, `AgentWorkflowStep`, `WorkflowExecution`); Pydantic
create/response schemas in `backend/onyx/workflows/models.py`. New fields go in **both** plus a migration.

---

## F1 — Parallel Fan-Out / Fan-In Orchestration

> ⚠️ **SUPERSEDED — do not build the design below.**
> `backend/onyx/workflows/PARALLEL_EXECUTION.md` is the source of truth. It is better engineered: a flat nullable
> `parallel_group` **integer column** on `agent_workflow_step` (steps sharing a non-null group run concurrently;
> `NULL` = sequential, fully backward compatible), thread-per-agent with per-thread DB sessions, and a shared
> `step_outputs` dict under a lock. Sequential mode only. **No separate join step is needed** — a normal downstream
> sequential step reads each parallel output via `input_mapping`. The section below is retained only as context for
> where the idea came from.

### What it is

Today every step runs one-at-a-time. Foundry's concurrent / Magentic-One pattern lets independent agents run **in
parallel**, then a **join** step aggregates their outputs — the classic "fan-out → fan-in".

### How it works (design)

Add a `parallel_group` **step type** (preferred over a new top-level mode, so it composes inside existing
sequential/llm_decision workflows):

- New `StepType` value `"parallel_group"` in `models.py:17`.
- A parallel-group step holds a list of child agent steps that share the same upstream input and run concurrently.
  The engine runs the children with `asyncio.gather` / a thread pool (the engine already runs a background emitter
  thread — `_stream_agent_packets()`), then a **join** writes a dict of child outputs into the context under the
  group's `output_key`.
- **Join strategies:** `concat` (default — label + concatenate child outputs) or `reduce` (a designated agent
  summarizes the children). The reduce agent receives `input_mapping` referencing each child's `output_key`.
- Concurrency cap and per-child timeout reuse the existing `max_calls_per_agent` / `timeout_seconds` settings.

### Example (template JSON)

```json
{
  "step_name": "Multi-Lens Review",
  "step_type": "parallel_group",
  "step_order": 1,
  "output_key": "reviews",
  "join_strategy": "reduce",
  "children": [
    { "step_name": "Security Reviewer",    "persona_name": "WF Security", "output_key": "sec" },
    { "step_name": "Performance Reviewer", "persona_name": "WF Perf",     "output_key": "perf" },
    { "step_name": "Style Reviewer",       "persona_name": "WF Style",    "output_key": "style" }
  ],
  "join_step": {
    "step_name": "Lead Reviewer",
    "persona_name": "WF Lead Reviewer",
    "input_mapping": { "Security": "$sec", "Performance": "$perf", "Style": "$style" }
  }
}
```

Result: the 3 reviewers run at once (~1× latency instead of 3×), then Lead Reviewer merges their findings.

### Touch points

- `backend/onyx/workflows/workflow_engine.py` — new branch to execute a parallel group + join.
- `backend/onyx/workflows/models.py` — `StepType` value + child/join schema.
- `backend/onyx/db/models.py` — store children / join config.
- `web/src/components/workflow-builder/` — new `ParallelGroupNode.tsx`, `graphUtils.ts`, `NodeConfigPanel.tsx`, side-by-side `autoLayout()`.

### Open design decisions

- **Child storage:** nested rows on one step (JSONB) vs. real `AgentWorkflowStep` rows linked by a new
  `parent_step_id`. Real rows reuse per-step overrides/tools/HITL and existing trace nodes; JSONB is simpler but
  duplicates logic. **Recommendation: real rows + `parent_step_id`.**
- **HITL inside a branch:** simplest first version = children cannot pause (only the join can). Document the limit.

---

## F2 — Event Triggers (Autonomous Workflows)

### What it is

Today a workflow only starts from a chat message (`WorkflowRunRequest.message`). Copilot Studio's flagship is
agents that **act on events**: a schedule (cron), an inbound webhook, or a new email/record. The workflow runs
unattended and delivers output to a sink (chat session, notification, or webhook callback).

### How it works (design)

- New `WorkflowTrigger` model: `{ workflow_id, trigger_type: "schedule"|"webhook"|"email", config (JSONB), enabled, last_fired_at }`.
  - schedule → `{ "cron": "0 9 * * 1" }`
  - webhook → generated `{ "url_token": "..." }`
  - email → `{ "address": "wf+123@..." }`
- **Schedule:** register with the existing background scheduler (Celery beat is already used by the Onyx backend)
  → enqueue a workflow execution with a synthesized `message` from the trigger payload.
- **Webhook:** new public endpoint `POST /workflow/trigger/{url_token}` in
  `backend/onyx/server/features/workflow/api.py` → validate token → start the workflow with the request body as input.
- Execution reuses the **existing** `run_workflow()` path; only the *entry point* and *output sink* are new.
- **Output sinks:** write to a chat session (current behavior), POST to a callback URL, or fire an in-app
  notification (`PushNotification` infra).

### Example

> "Every Monday 9am, run *Research & Report Generator* on 'competitor news this week' and post the report to chat
> session X." → a `schedule` trigger with `{ "cron": "0 9 * * 1", "message": "competitor news this week" }`.

### Touch points

- New `WorkflowTrigger` table + Alembic migration.
- Scheduler registration (Celery beat).
- `backend/onyx/server/features/workflow/api.py` — webhook route.
- New triggers UI tab.

### Open design decisions

- **Run-as identity:** autonomous runs need an identity (workflow owner? service principal?) — affects tool/knowledge access.
- **Webhook security:** signed tokens, rotation, rate limiting.
- **Recommendation:** ship **schedule-only first** to de-risk; add webhook next. Largest of the four (new infra + security surface).

---

## F3 — Connected Agents as First-Class Builder Nodes (A2A UX)

> ✅ **The backend primitive is ALREADY IMPLEMENTED.** `MULTI_AGENT_IMPLEMENTATION_PLAN.md` §4a specifies
> `AgentTool` (`backend/onyx/tools/tool_implementations/agent_tool.py`), and `PERFORMANCE.md` cites optimizations
> and bug fixes *inside* that file — i.e. it is live code, not a proposal. **Remaining work is only:** (a) the
> visual-builder UX below, and (b) a nesting/cycle guard (flagged at ~70% confidence in the plan; arbitrary
> agent→agent recursion and circular-delegation prevention are not yet designed).

### What it is

Foundry "connected agents": an agent can call **another agent as a tool** and delegate sub-tasks. We already have
the backend primitive (`AgentTool`); today it's only wired up via `llm_decision` mode at the orchestrator level.
F3 surfaces it in the **visual builder** so a user can attach "Agent-as-Tool" to any agent node — no JSON, no
separate orchestrator.

### How it works (design)

- `AgentTool.tool_definition()` already exposes a persona as an OpenAI-style function. We let an agent step
  declare `connected_agent_ids: list[int]` (personas/workflows it may call).
- At construction (`tool_constructor.construct_tools()`), for each connected id we build an `AgentTool` and add it
  to that step's tool list — so the parent agent's normal LLM loop can call it on demand.
- **Builder UX:** `NodeConfigPanel` gets a "Connected agents" picker (reuses the existing persona selector). A
  dashed edge renders parent → connected agent to visualize delegation.
- **Depth guard:** cap nesting (e.g. 2) + reuse `max_calls_per_agent` to prevent runaway A2A recursion.

### Example

A "Travel Planner" agent node with connected agents `[Flight Finder, Hotel Finder, Visa Checker]`. When the user
asks to plan a trip, the planner autonomously calls Flight Finder and Hotel Finder as tools, reads their results,
and composes the itinerary — all within one agent step, decided by the LLM rather than a fixed sequence.

### Touch points

- `backend/onyx/db/models.py` + `backend/onyx/workflows/models.py` — add `connected_agent_ids` to the step.
- `backend/onyx/tools/tool_constructor.py` — wire AgentTools (reuse `agent_tool.py` as-is).
- `web/src/components/workflow-builder/` — `types.ts`, `NodeConfigPanel.tsx`, `graphUtils.ts` (dashed edges).

> Mostly UX + plumbing; the backend execution primitive already exists → **lowest backend risk**.

---

## F4 — Prebuilt Agent / Workflow Gallery (UI)

### What it is

Copilot Studio / M365's "explore prebuilt agents" discovery. We have **36 ready templates** in
`backend/tests/workflow_creator/workflows/`, but they're only deployable via a Python CLI. F4 turns them into a
browsable in-app gallery with categories, descriptions, starter messages, and one-click deploy.

### How it works (design)

Templates already carry `name`, `description`, `icon_name`, `orchestration_mode`, and (in richer ones)
`starter_messages` — everything needed for cards. Two sourcing options:

1. **Live workflows already in DB** (`is_public=true`): the list endpoint exists; the gallery just renders them
   with category facets + starter messages. **Lowest effort — recommended first.**
2. **Template catalog:** expose the JSON files as a read-only catalog + a `POST /workflow/from-template` deploy
   action (server-side equivalent of `create_workflows.py`'s `_resolve_steps()` persona auto-create).

Add a lightweight `category` label (derive from existing `labels` / `icon_name`, e.g. Research, Code, Data,
Medical, Finance, Business) for filtering. "Use template" clones into the user's workspace and opens it in the editor.

### Example

Gallery grid with cards for *Research & Report Generator*, *Universal Problem Solver*, *Medical Diagnosis Panel*,
*Code Review*, *Travel Planner*… Filter chips: Research / Code / Data / Medical / Finance. Click a card → see its
starter messages → "Use this workflow" → opens in the Wizard/Visual builder ready to run.

### Touch points

- New gallery page under `web/` (reuse the existing workflow list data layer in `web/src/lib/workflows/`), a card
  component, and category facets.
- Backend: optional `from-template` endpoint if we want the file-based catalog.

> **Easiest visible win, frontend-led.**

---

## F5 — Agent ↔ Connector Connectivity (live external data)

> ✅ **The agent→tool/MCP mechanism is ALREADY IMPLEMENTED.** `MULTI_AGENT_IMPLEMENTATION_PLAN.md` §5.5 states:
> *"a workflow agent inherits ALL of its persona's tools — built-in, custom, and MCP. No special handling needed."*
> All tool types are presented to the LLM identically as function definitions via `construct_tools()`. Onyx also
> **hosts its own MCP server** (`backend/onyx/mcp_server/README.md`, FastMCP on port 8090), and filesystem
> ingestion is "functionally complete" per `docs/folder-connector.md`.
>
> **So the generic extension path already works.** The genuine gap is narrower than first stated: there are no
> **live mail or database tools**, and **no SQL/database connector exists at all**. The `ImapMailTool` recipe below
> is still the right first step, and the connector-reuse analysis still holds.

### The problem

Workflow agents are usually *configured* with only `SearchTool` / web search, so they *feel* limited — but the
framework is not the limit. The repo has a rich tool framework (`backend/onyx/tools/built_in_tools.py`):
`SearchTool`, `WebSearchTool`, `OpenURLTool`, `PythonTool`, `FileReaderTool`, `HttpRequestTool`,
`ImageGenerationTool`, `MemoryTool`, plus `CustomTool` (OpenAPI) and `MCPTool`. What's missing is **live external
data access** (run SQL now, read this folder now, fetch the latest mail now).

### Can we reuse the `connectors/` folder? — Analysis

- There are **60+ connectors** in `backend/onyx/connectors/` (Gmail, IMAP, SharePoint, Google Drive, S3,
  Confluence, Jira, Slack, Salesforce, …) but they are **batch indexers**, not live tools: they implement
  `LoadConnector`/`PollConnector`/`CheckpointedConnector` (`connectors/interfaces.py`) and **yield whole
  `Document` batches into the Vespa index via Celery** (`background/celery/tasks/docfetching`).
- They have **no `query()`/`search()`/`execute()` interface** and there are **zero SQL/database connectors**
  (only `phoenix/scripts/ddl` helpers and Airtable-via-API).
- **But** connectors help agents two ways: (a) **indirectly today** — anything a connector has indexed is already
  queryable via `SearchTool`; (b) their **client/SDK code + credential infra are reusable** when building a live tool.

**Verdict:** don't call connectors directly from agents (architecture mismatch). **Reuse the connector's
low-level client + parsing helpers + the encrypted `Credential` storage, and write a thin new `Tool`** that
provides the live query interface connectors lack.

### Worked example — wire the IMAP mail connector into an agent (the "simple one")

IMAP is the simplest case: plain username/password (no OAuth), and the connector already exposes reusable
module-level primitives in `backend/onyx/connectors/imap/connector.py`:

- `_get_mail_client()` → logs into `imaplib.IMAP4_SSL` from `{imap_username, imap_password}`
- `_fetch_email_ids_in_mailbox(client, mailbox, start, end)` → IMAP `SEARCH` with a date range
- `_fetch_email(client, email_id)` + `_convert_email_headers_and_body_into_document(...)` → parse to text

The connector's own `__main__` block (lines 444-484) already demonstrates instantiating it with
`OnyxStaticCredentialsProvider` — a ready-made PoC path.

**Recipe (Approach A — reuse the connector, minimal new code):**

1. **Credentials:** reuse the encrypted `Credential` table (`source=DocumentSource.IMAP`) via
   `OnyxDBCredentialsProvider`, or `OnyxStaticCredentialsProvider` for a quick PoC.
2. **New tool class** `ImapMailTool(Tool)` in `backend/onyx/tools/tool_implementations/mail/imap_mail_tool.py`:
   - `tool_definition()` → exposes `search_mail(query, since_days, mailbox?)` as an OpenAI function.
   - `run()` → calls the connector's `_get_mail_client` / `_fetch_email_ids_in_mailbox` / `_fetch_email`, returns
     top-N emails as `ToolResponse.llm_facing_response`. No IMAP re-implementation.
3. **Register** (mirrors every other built-in tool):
   - add `ImapMailTool` to `BUILT_IN_TOOL_MAP` in `built_in_tools.py`;
   - Alembic migration seeding a `Tool` row with `in_code_tool_id="ImapMailTool"`;
   - add an instantiation branch in `tool_constructor.py` → `construct_tools()`.
4. **Attach** the tool to a workflow persona (tool selector) → the agent can live-search mail mid-workflow.

**Reuse map:** ✅ connector IMAP client + email parsing + `Credential` encryption/storage · ❌ NOT the checkpoint /
Celery / `Document`-batch machinery (that is indexing, not live query).

**Contrast — MCP alternative:** an MCP server would *not* reuse connector code (you'd reimplement IMAP in the
server). Use MCP for sources with **no existing connector** (e.g. databases) or when you want process isolation;
use Approach A when you want to **reuse an existing connector**.

### Generalizing beyond IMAP

- **Mail (Gmail/Outlook):** same recipe; Gmail/Graph add OAuth → reuse the connector's OAuth credential flow.
- **Filesystem / object store (S3, SharePoint, Drive):** reuse those connectors' clients behind a
  `list_files` / `read_file` tool.
- **Databases (Postgres/Oracle/MySQL):** **no connector exists** → build a new read-only `SqlQueryTool`
  (SQLAlchemy) or a Database MCP server; reuse only the `Credential` storage.

### Touch points

- New tool file under `backend/onyx/tools/tool_implementations/<source>/`, `built_in_tools.py`,
  `tool_constructor.py`, one Alembic migration, and the persona/workflow tool-selector UI.

---

## Recommended Build Order

| # | Feature | Why this order | Effort / risk |
|---|---------|----------------|---------------|
| 1 | **F5 — IMAP mail tool (PoC)** | Smallest end-to-end proof an agent can use a connector live; reuses existing code | Low |
| 2 | **F4 — Gallery** | Frontend-only, immediate value; a real gap | Low |
| 3 | **F3 — Connected agents (UX only)** | Backend primitive already built; only builder UX + cycle guard remain | Low backend |
| 4 | **F1 — Parallel execution** | **Build `PARALLEL_EXECUTION.md`, not this doc's F1.** Engine extension; real latency win | Medium, contained |
| 5 | **F2 — Triggers** | The one unanalyzed feature. New infra + security; schedule-first, webhook later | Highest |

F5 is the recommended **first PoC** for data connectivity: it proves the connector-reuse pattern with one small
new tool file + registration, then the same recipe generalizes to filesystem/object-store and (via a new
`SqlQueryTool` or MCP) databases. Each feature is independently shippable.

**Caveats from the audit:** F1's design here is superseded by `PARALLEL_EXECUTION.md`. F3 and F5 are far smaller
than their sections imply, because their backend primitives already ship. **F2 and F4 are the only features
needing genuinely new design work** — F2's design now lives in `backend/onyx/workflows/EVENT_TRIGGERS.md`.

Note that F1 (per `PARALLEL_EXECUTION.md`) touches only the **Wizard** editor in its own plan; per `CLAUDE.md`'s
dual-editor rule it must also update the **Visual Builder**.

## Verification (per feature, when implemented)

- **F5:** seed an IMAP `Credential`, attach `ImapMailTool` to a persona, run a workflow asking it to "find emails
  about X from the last 7 days," confirm the agent calls `search_mail` and returns real messages (visible in the
  trace / packets). Sanity-check the connector's `__main__` block first for live IMAP access.
- **F1:** deploy a parallel template via `create_workflows.py`, run it, confirm children execute concurrently
  (overlapping timestamps in `steps_executed`) and the join aggregates; check the trace graph renders branches.
- **F2:** create a schedule trigger, confirm a run is enqueued and output lands in the chosen sink.
- **F3:** build an agent with connected agents in the visual builder, run it, confirm the parent calls the
  sub-agents as tools (visible in the trace / packets).
- **F4:** open the gallery, filter by category, deploy a template, confirm it opens runnable in the editor.

## Next Step

Review this document. When a feature (recommended start: **F5 — IMAP mail tool PoC**) is approved for build, it
will be converted into a step-by-step implementation plan with exact file edits — **no code will be written until
then.**
