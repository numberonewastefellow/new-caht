# Flow nodes — design

Status: P0 design, 2026-10-30. Background: [REFERENCE_STUDY.md](REFERENCE_STUDY.md). Status tracking: [PROGRESS.md](PROGRESS.md).

## Goals

- Add **parallel**, **loop** and **code** nodes, plus **webhook** triggers (in Pulse).
- **Extensible:** a new node type is one module (config model + runner) registered in one place.
- **Upgradeable:** saved workflows keep the node versions they were saved with. Upgrades are explicit and can be reverted. Every run is pinned to the workflow version it started on.
- **Backward compatible:** the 48 live workflows and 102 paused runs behave exactly as they do today. This is proven by the golden harness in `backend/tests/unit/om/workflows/engine_golden/`.

## Backend architecture (`backend/om/workflows/`)

```
nodes/                 one module per node type, holding all of its versions
  base.py              NodeTypeSpec, NodeCapabilities, NodeRunner protocol, StepOutcome/StepStatus
  registry.py          NodeTypeRegistry: register / get(type, version) / latest / upgrade chain / catalog
  builtin.py           registers the built-in node types explicitly; get_node_registry()
  agent.py             "agent" v1: config model, legacy-column loader, runner
  agent_tools.py       per-run AgentTool cache (honours step LLM/tool overrides)
  router.py            "conditional_router" v1 (step-order targets, deprecated) + v2 (node-key targets) + upgrade
graph.py               WorkflowNode / WorkflowGraph (immutable, pydantic), definition <-> graph
state.py               RunState, TurnCursor, ResumePoint, RunContext (checkpoints, progress), restore_run_state()
sequential.py          the v2 sequential coordinator: run lifecycle + _run_block() dispatch via the registry
agent_streaming.py     stream a sub-agent's packets live (shared with llm_decision)
hitl.py                clarification detection + resume task (shared)
inputs.py              input mapping + file collection (shared)
workflow_engine.py     run_workflow() entry point; legacy sequential path kept behind WORKFLOW_ENGINE_V2
```

**Responsibilities:**

- **Coordinator** (`sequential.py`) is the only thread that touches the DB, the trace and checkpoints. This is graphon's dispatcher rule. It walks the graph, asks the registry for each node's runner and yields packets.
- **Runner** (one per node type and version) handles one node, inside a `RunContext`. It returns a `StepOutcome`: `completed`, `paused`, `cancelled`, `terminal` or `failed`, plus the output and any skip set. Runners never commit to the DB directly; they go through `RunState`.
- **Registry** maps `(type, version)` to a spec. An unknown type or version is a hard error, never a silent fallback. Old versions stay registered for as long as a saved row uses them.
- **Graph** is plain data built from a workflow *definition* (a JSON document), so it is thread-safe and can be snapshotted. Live runs and resumed runs both build from a definition:
  - a live run serializes the ORM rows into a definition;
  - a resumed run loads the definition of the version it is pinned to.

### Node type contract

```python
NodeTypeSpec(
    type="agent", version=1,
    label="Agent", category="core", description="...",
    config_model=AgentStepConfigV1,      # pydantic; JSON schema drives the editor form
    runner=AgentRunnerV1(),              # implements NodeRunner.run(node, ctx) -> Generator[Packet, None, StepOutcome]
    capabilities=NodeCapabilities(modes={"sequential", "llm_decision"}, can_pause=True),
    upgrade_from_previous=None,          # callable(config_prev, UpgradeContext) -> config_this
    load_legacy=load_agent_legacy_v1,    # optional: build config from legacy ORM columns
    deprecated=False,
)
```

## Versioning

| Level | Field | Meaning |
|---|---|---|
| Node | `agent_workflow_step.type_version` | Which spec version this node runs with. Pinned until the user upgrades it. |
| Workflow semantics | `agent_workflow.schema_version` | Engine-level behaviour switches. 1 = today's behaviour (e.g. legacy `$key` substitution); 2 = safe tokenizer and `$key.output.<path>`. |
| Workflow content | `agent_workflow.version` + `agent_workflow_version` rows | Immutable snapshot per save (definition JSON, content hash, author). Used for history, diff, revert and pinning. |
| Run | `workflow_execution.workflow_version_id` | The definition a run started on. Resume uses it. |
| Checkpoint | `WorkflowCheckpoint.checkpoint_version` | 1 = legacy (`completed_step_ids`); 2 = `completed_keys`, `skipped_keys`, `output_order`, `paused_node_key`. v1 is read via the step-id→key map in the pinned definition. |

**How changes happen:**
- **Structural** workflow-document migrations run lazily in memory on read and are written back only on save. Each is a pure, idempotent N→N+1 function, tested with fixtures.
- **Behavioural** node upgrades are opt-in. A spec may define `upgrade_from_previous`; a spec without one is marked *breaking*. The UI shows a diff, the change is audited, and it can be reverted by restoring a previous workflow version.
- **Version rows** are created when a workflow is saved, and lazily for a workflow that has none yet (on its first run after the upgrade). If the hash is unchanged, no new row is written.

## Data model changes (migration `0002_workflow_nodes`)

The migration is additive only.

- `agent_workflow_step`:
  - new columns: `node_key` (text, not null, backfilled `'s' || id`, unique per workflow), `type_version` (int, not null, default 1), `config` (jsonb, null), `parent_step_id` (self-FK, null, cascade), `branch_index` (int, null);
  - all legacy columns stay.
- `agent_workflow`: new columns `version` (int, not null, default 1) and `schema_version` (int, not null, default 1).
- New table `agent_workflow_version`: `id`, `workflow_id` (FK, cascade), `version`, `schema_version`, `content_hash`, `definition` (jsonb), `created_by_id` (FK user, set null), `created_at`; unique `(workflow_id, version)`.
- `workflow_execution`: new column `workflow_version_id` (FK, set null, null).

## Saving

- `update_workflow` upserts steps by `node_key` instead of deleting and recreating them, so step ids stay stable.
- Each save bumps `version` and writes a version row.
- An optional `expected_version` on update gives optimistic concurrency: if it doesn't match, the API returns 409.

## API contract (P0)

**Step create/update:**
- New optional fields: `node_key` (the server generates `n_<8 hex>` when absent), `type_version` (defaults to latest), `config` (for node types whose spec has no legacy loader).
- Agent v1 and router v1/v2 keep their current top-level fields, so old clients keep working.
- P2 adds `parent_key` and `branch_index`.

**Step response:** adds `node_key`, `type_version`, `config`, `latest_type_version`, `upgrade_available`.

**Workflow response:** adds `version` and `schema_version`. Update accepts `expected_version`.

**New endpoints:**
- `GET  /workflow/node-types`: the catalog (type, versions, label, category, description, JSON schema, capabilities, deprecated, has_upgrade). Declared before `/{workflow_id}`.
- `POST /workflow/node-types/{type}/upgrade` `{from_version, config, context}` returns `{to_version, config, breaking}`.
- `GET  /workflow/{id}/versions`, `GET /workflow/{id}/versions/{n}`, `POST /workflow/{id}/versions/{n}/restore`.

## Containers (P2 parallel, P3 loop)

**Model**
- A child step has `parent_step_id` (the API sends `parent_key`, the parent's node key) and a `branch_index`.
- The graph exposes the top-level nodes and, for each container, its branches. A branch is an ordered list of child nodes.
- `step_order` stays globally unique, in depth-first order: children come after their parent.

**Save rules (v1)**
- A parent must be a container type, at most 3 levels deep, with at most 100 nodes per workflow.
- A `parallel` container cannot be nested in another `parallel`, which avoids nested thread pools.
- Children may not have `can_request_input`, `promote_output` or `is_terminal`, so a container never pauses midway.
- A router's targets must be in the router's own block (same parent and branch).

**Execution: coordinator + branch workers**
- The main generator thread is the only coordinator: it does all DB writes, checkpoints, trace persistence and yields.
- Each branch runs `_run_block(branch_nodes, branch_ctx)` in a worker thread, on a pool sized `min(branches, max_concurrency)` and filled as a sliding window.
- Each branch's `ScopedRunContext` (shared with loop iterations) holds:
  - a deep copy of the context, so branches can't see each other's writes;
  - its own `RunState` and turn range;
  - its own `Emitter`, DB session (`get_session_with_current_tenant`) and `AgentToolCache`;
  - a buffered trace;
  - no-op checkpoint and persist calls (`RunContext.save_checkpoint` / `persist_progress` / `persist_trace` are overridden).
- Packets are sent as `(branch, packet)` on one shared queue, plus a done sentinel. The coordinator blocks on `get(timeout=0.05)` and checks for stop.
- **Placement:** branch *i* uses turns starting at `base + i * BRANCH_TURN_STRIDE`, so each branch's step groups (and its sub-agents' tool groups) never collide with other branches. After the join, the cursor moves past the highest turn used.
- **Join:**
  - The join waits for all branches (`wait_all`), or until the first branch succeeds (`first_success`).
  - It then merges each branch's outputs, files, `steps_executed` and buffered trace into the main run **in declared branch order**. The result doesn't depend on which branch finished first.
  - The container's output is JSON `{branch_label: last output of that branch}`.
- **Errors:** `on_branch_error` is either `fail` (the run fails with the first error) or `continue` (the failed branch is reported as `{"error": ...}`).
- **Cancel:** a per-run `threading.Event`, checked by branches between nodes. Agent threads are never killed (Python can't); they wind down.
- **Checkpointing:** the container checkpoints once, when it completes. Containers never pause, so a crashed run re-runs the container (v1).

## Engine rules preserved from the legacy sequential path

All of these are checked against the golden files:

- Packet sequence and placement arithmetic: step start, deltas, end, section end, and pause = +1/+2/+3, promote = +1.
- HITL detection and the conversation-aware resume.
- The router's skip-forward semantics.
- `promote_output`, the final summary from the last output, and file de-duplication.
- Trace calls and their order.

Intentional fixes are listed in the harness's `ALLOWED_DIFFS`:

- a timeout now reports `failed`;
- sequential mode now honours step LLM and tool overrides;
- the router skip set is restored on resume;
- completion is keyed by `node_key` instead of `output_key`.
