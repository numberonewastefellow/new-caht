# Workflow engine golden harness

Records exactly what the CURRENT workflow engine (`om/workflows/workflow_engine.py`)
does for every template workflow and for a set of edge-case fixtures, so a
refactored engine can be proven identical (or *intentionally* different).

No DB, no LLM, no MinIO, no network. Tests run in about 60s.

## Running

From Git Bash on the host. This mounts the worktree backend into a throwaway container:

```bash
export MSYS_NO_PATHCONV=1
docker run --rm -v "D:\llm\danswer_flow_wt\backend:/app" -w /app om/om-backend:latest \
  python -m pytest tests/unit/om/workflows/engine_golden -q -p no:cacheprovider
```

| Env var | Effect |
|---|---|
| `GOLDEN_UPDATE=1` | Regenerate every `golden/*.json` from the engine instead of comparing. This is refused unless `ENGINE_IMPL=legacy` (override with `GOLDEN_UPDATE_FORCE=1`). |
| `ENGINE_IMPL=legacy` (default) | Calls `om.workflows.workflow_engine.run_workflow`. Must match the goldens **exactly**. |
| `ENGINE_IMPL=v2` | Same entry point with `WORKFLOW_ENGINE_V2=true`. Skips until `om.workflows.sequential` exists. `ALLOWED_DIFFS` is applied. |

To regenerate one scenario, add `-k <name>` together with `GOLDEN_UPDATE=1`. Always review the
golden diff before you keep it.

## How it works

| File | Role |
|---|---|
| `fake_layer.py` | Fakes installed at module boundaries (see the table below) and the per-scenario `HarnessState`. |
| `builder.py` | Turns a template JSON or an inline dict into transient ORM `AgentWorkflow` / `AgentWorkflowStep` / `Agent` / `Tool` objects. Defaults go through `WorkflowCreate` / `WorkflowStepCreate`, then the `_add_step` column mapping. Ids: workflow `1`, steps `101+i` (`201+i` after an "edit"), agents `1001+n` (shared by name). |
| `recorder.py` | Runs each `RunSpec` of a `Scenario` through the selected engine and normalises the result to JSON. |
| `scenarios.py` | All scenarios and `ALLOWED_DIFFS`. |
| `engines.py` | The `ENGINE_IMPL` registry. |
| `test_engine_golden.py` | One parametrised test per scenario, plus checks that every template has a golden and that no golden is orphaned. |

### Patched boundaries

Patching is **by identity**. The source attribute and every alias of the same object in any
loaded `om.workflows.*` module are replaced. So helpers can move between modules inside
`om.workflows` without editing the harness.

| Patched | Source module | Replacement |
|---|---|---|
| `AgentTool.run` (class attribute) | `om.tools.tool_implementations.agent_tool` | `_fake_agent_run`. AgentTool **construction and properties are real**. |
| `run_llm_step` | `om.chat.llm_step` (+ aliases) | `fake_run_llm_step`, the scripted orchestrator |
| `get_llm_for_agent`, `get_default_llm`, `llm_from_provider`, `get_llm_token_counter` | `om.llm.factory` (+ aliases) | `FakeLLM` labels; the token counter is a word count |
| `fetch_llm_provider_view` | `om.db.llm` (+ aliases) | namespace with `.name` |
| `get_paused_execution` | `om.db.workflow` (+ aliases) | in-memory lookup |
| `save_checkpoint` | `om.db.workflow` (+ aliases) | recording wrapper around the **real** function |
| `persist_workflow_trace` | `om.workflows.trace_models` (+ aliases) | recording wrapper around the **real** function |
| `get_default_file_store` | `om.workflows.trace_models` | `InMemoryFileStore` |
| `db_session` argument | n/a | `FakeSession`: `add`/`get` for `WorkflowExecution` and `Agent`, no-op `commit`. `execute()` raises. |

The real `create_workflow_execution`, `update_workflow_execution`, `load_checkpoint`,
`load_workflow_trace`, `WorkflowTraceBuilder` and `evaluate_condition` all run.

### The fake agent

The fake agent emits real packets on `self.emitter`, which is the bus the engine polls:
- reasoning start/delta/done;
- when `has_tools`, a `fake_search` custom-tool group at `turn_index + 1`;
- `message_start` + 2 `message_delta` chunks;
- for scripted files, the same `document_files` group as `collect_pending_files`.

It then returns a real `ToolResponse` (`{"agent_output", "_file_ids", "_file_details"}`).

The default output is `"<output_key> result for: <task[:40]>"`. The agent script is keyed by
**step name** and lists the behaviour for each call:

| `kind` | Behaviour |
|---|---|
| `normal` | The default. |
| `needs_input` | `[NEEDS_INPUT] ...` question. |
| `error` | Raises. |
| `cancel_mid` | Waits until the bus is drained, sets the stop flag, then blocks. This makes the cancel point deterministic. |
| `raw` | Non-JSON response. |
| `empty` | Empty output. |

Optional keys: `output`, `files`, `sleep`.

### The fake orchestrator

A scripted list of decisions: `call`, `calls`, `tool` (raw / unknown name), `answer` or
`empty`, with optional `thinking` text and `reasoning`. The script position persists across
the runs of a scenario, so a resume continues the script. When the script is exhausted, the
orchestrator answers.

### What a golden records (per run)

| Field | Content |
|---|---|
| `packets` | Every packet: `type`, `placement` `[turn_index, tab_index, sub_turn_index]`, and all non-None fields. |
| `messages`, `final_answer` | Top-level message blocks and the last one. |
| `agent_calls` | The task each agent received (this is where `input_mapping` shows up), its placement, LLM label, `has_tools` and step overrides. |
| `orchestrator_calls` | Available tools and the history digest at each orchestrator call. |
| `checkpoints` | Every `save_checkpoint` call, **legacy field set only** (`LEGACY_CHECKPOINT_FIELDS`), so additive checkpoint fields don't churn the goldens. Orchestrator history is digested. |
| `final_step_outputs` | From the last checkpoint. |
| `trace_persists` | Ordered persist calls: message-key flag, status, node:status list. |
| `trace` | The final persisted trace JSON. |
| `executions` | Final state of every `WorkflowExecution` row. |

The normaliser replaces `started_at` / `ended_at` / `completed_at` with `<ts>`, and
`duration_ms` / `total_duration_ms` with `<ms>`. Everything else is deterministic.

## Scenarios

**Templates.** Every file in `tests/workflow_creator/workflows/*.json` (47) is run **forced into
sequential mode** as `golden/<stem>.json`. The 28 `llm_decision` templates are also run natively as
`golden/<stem>__llm_decision.json`, with the orchestrator calling each step's agent once in
`step_order` and then answering.
- The input is fixed.
- If a template has a `can_request_input` step, the first such step pauses once and a second run resumes it.
- Agents with `tool_names` (Office/MCP builders) "create" a `<output_key>.docx` / `.pptx` file.

**Fixtures (`fx_*`)**. See `description` / `covers` inside each golden.

| Fixture | Covers |
|---|---|
| `fx_router_true`, `fx_router_false` | Router branch skipping; router output `"true"` / `"false"` usable as `$route` |
| `fx_router_chain` | Router after router, router inside a skipped branch (never evaluated), router on an unresolved `$missing` (resolves to `""`, so `is_empty` is TRUE), unset router key left literal |
| `fx_router_skip_lost_on_resume` | Router + pause + resume (**bug**, see below) |
| `fx_hitl_pause_resume`, `fx_hitl_double_pause` | Pause, conversation-aware resume, accumulated clarification conversation |
| `fx_hitl_detection_modes` | `STATUS: COMPLETE` veto, `[NEEDS_INPUT]` ignored without `can_request_input`, heuristic pause |
| `fx_hitl_resume_after_edit`, `fx_hitl_resume_after_edit_insert_step` | Workflow saved while paused (steps recreated with new ids) |
| `fx_hitl_resume_legacy_checkpoint` | Old checkpoint without `clarification_conversation` (fallback resume) |
| `fx_hitl_resume_corrupted_checkpoint` | Unreadable checkpoint |
| `fx_stop_between_steps`, `fx_stop_mid_step` | Stop before a step / during a step |
| `fx_timeout_slow_step` | Timeout (`timeout_seconds=1`, step sleeps 1.1s) |
| `fx_step_error` | Agent raises |
| `fx_promote_output_with_files`, `fx_final_summary_files_dedup` | `promote_output`, step files in the default mapping, file de-dup (last writer wins) |
| `fx_is_terminal` | `is_terminal` |
| `fx_duplicate_output_key` | Two steps share an `output_key` (**bug**) |
| `fx_key_substring_collision` | `$research` vs `$research_notes` (**bug**) |
| `fx_input_mapping_forms` | `$user_input`, `$key.output`, `$key`, unknown ref, non-string values, default mapping |
| `fx_raw_and_empty_outputs` | Non-JSON and empty agent output |
| `fx_deleted_agent` | Deleted agent: step silently skipped |
| `fx_step_overrides` (+`__llm_decision`) | Step-level LLM/tool/prompt overrides in both modes |
| `fx_chat_files_trace` | Chat files: trace start node name and file names |
| `fx_llmd_basic` | Orchestrator thinking / reasoning / final answer |
| `fx_llmd_call_limit_and_unknown_tool` | `max_calls_per_agent` refusal, unknown tool, two tool calls in one cycle |
| `fx_llmd_pause_resume`, `fx_llmd_repause` | Direct re-call resume; re-pause; promote on re-call |
| `fx_llmd_resume_legacy_checkpoint` | Old-format checkpoint in llm_decision |
| `fx_llmd_max_steps_fallback`, `fx_llmd_promote_no_fallback`, `fx_llmd_empty_decision` | Fallback answer rules |
| `fx_llmd_stop_mid_step`, `fx_llmd_stop_between_steps`, `fx_llmd_timeout`, `fx_llmd_error` | Stop / timeout / error in llm_decision |

## Known current bugs captured by the goldens

These are recorded as-is. Fix them deliberately and add an `ALLOWED_DIFFS` entry.

1. **Timeout reports `completed`.** `fx_timeout_slow_step`, `fx_llmd_timeout`. The loop just
   `break`s. Sequential then emits the last output as the final answer; llm_decision emits the
   fallback.
2. **Router skip set is lost on resume.** `fx_router_skip_lost_on_resume`. `skip_step_orders` is
   a local variable, so the inactive-branch step ("Routine Handler") runs after resume.
3. **Completion is keyed by `output_key`.** `fx_duplicate_output_key`. `completed_step_ids` =
   steps whose `output_key` is in `step_outputs`. After step 0 writes `draft`, step 2 (also `draft`)
   counts as completed, so on resume "Second Draft" never runs. The value is also overwritten
   (last writer wins).
4. **`$key` substring collision.** `fx_key_substring_collision`. Plain `str.replace` in
   insertion order turns `$research_notes` into `<research output>_notes`.
5. **Sequential ignores step LLM and tool overrides.** `fx_step_overrides`. It uses
   `get_llm_for_agent(agent, user)` (agent-level LLM) and `has_tools=bool(agent.tools)` even with
   `tool_ids_override=[]`. llm_decision honours both. Prompt / token / doc-set overrides are passed
   in both modes.
6. **Editing a paused workflow breaks resume.** `fx_hitl_resume_after_edit*`. Step ids are
   recreated, so:
   - nothing matches `completed_step_ids` and the completed steps re-run;
   - `paused_at_step_id` matches nothing, so the paused step gets the normal mapping instead of the clarification task (the user's answer is lost).
7. **Corrupted-checkpoint resume.** `fx_hitl_resume_corrupted_checkpoint`.
   - The new execution's trace has **no start node**: the engine tries `load_workflow_trace(new_id)` instead of `set_start`.
   - The resume message becomes the user input.
   - The old row stays `failed` with its `paused_at_step_id` and checkpoint kept.
8. **Cancelled runs keep their checkpoint.** `fx_stop_*`. `update_workflow_execution` only
   finalises `completed` / `failed` / `timeout`. Sequential mid-step cancel also leaves the trace
   node `running` (llm_decision marks it `failed`).
9. **Errors emit no `stop` packet.** `fx_step_error`, `fx_llmd_error`. The exception propagates.
   The failing step's trace node stays `running` (both modes).
10. Router `true_steps` / `false_steps` only skip **forward**. A router inside a skipped branch is
    never evaluated, so its key stays unset (literal `$r4` in later mappings).

## ALLOWED_DIFFS

`scenarios.ALLOWED_DIFFS` maps a scenario name (glob) to a list of `(json_path_pattern, reason)`.
- Paths look like `runs[0].executions[0].status`.
- Patterns are globs where only `*` is special (it spans segments; brackets are literal).
- They are applied only when `ENGINE_IMPL != legacy`. Legacy must always match exactly.
- Active today: the timeout-status fix for `fx_timeout_slow_step` / `fx_llmd_timeout`.
- Commented candidates exist for the other planned fixes in `docs/flow-nodes/DESIGN.md`. Enable each one together with the engine change that introduces it.

## Seams a new engine must keep (or the harness must be extended)

- Sub-agents run through `AgentTool(...).run(placement, None, task=...)`, emitting on the
  `emitter` passed to the engine. The harness patches `AgentTool.run` on the class.
- The orchestrator calls `om.chat.llm_step.run_llm_step(emitter=..., history=..., tool_definitions=..., llm=..., placement=..., ...)`.
- LLMs come from `om.llm.factory` (`get_llm_for_agent`, `get_default_llm`, `llm_from_provider`,
  `get_llm_token_counter`) and `om.db.llm.fetch_llm_provider_view`.
- Persistence goes through the `om.db.workflow` helpers (`create_workflow_execution`,
  `update_workflow_execution`, `save_checkpoint`, `load_checkpoint`, `get_paused_execution`) with
  the given `db_session`.
  - `FakeSession` supports only `add` / `get` (WorkflowExecution, Agent) / `commit` / `flush`.
  - New DB access (e.g. workflow version rows) needs a fake added in `fake_layer.install()`.
- Traces go through `persist_workflow_trace` / `load_workflow_trace` (blob store via
  `trace_models.get_default_file_store`).
- Stop is read via the `is_connected` callable.
- Fakes are rebound in modules imported under `om.workflows.*` at install time. New modules
  elsewhere that import these names need to be added to `_SCAN_PREFIXES`.
- The builder sets the migration-0002 columns like the backfill (`node_key = "s<id>"`,
  `type_version = 1`, `version = schema_version = 1`) when they exist on the model.
