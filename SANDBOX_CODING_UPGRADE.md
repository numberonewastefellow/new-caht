# Sandbox / Coding-Agent Upgrade — Execution Spec

> Execution-ready implementation guide for a follow-up agent. Three independent tracks.
> Within each track, the numbered order is mandatory. All file paths are repo-relative
> (branch `rename_onyx_to_om`; package is `om`, not `onyx`).
>
> **Ground rules:** never run `alembic upgrade/downgrade` manually (migrations apply on backend
> restart). Do not commit unless asked. Each step is independently shippable + verifiable against
> the live server (`http://localhost:3000`, containers `virtualai-*`). Verify with the existing
> harness `backend/tests/workflow_creator/test_sandbox_persistence.py`.
>
> **Provenance:** produced 2026-07-18 from a graphify-oriented exploration of the current code.
> Line anchors are approximate (`~Lnnn`) — confirm with a quick read/grep before editing, as line
> numbers drift.

## Current state (baseline)

- Coding = `PythonTool` → FastAPI microservice `code-interpreter/code-interpreter/`. Snippets only.
- Persistent per-chat sandbox already works: `ChatSession.sandbox_session_id`, lazy-created,
  Docker-only, reaped 30min idle / 24h. (Verified passing via `test_sandbox_persistence.py`.)
- Pipeline: user code writes a file → executor tars `/workspace` → service diffs vs inputs →
  `WorkspaceFile(file_id)` → `PythonTool.run` downloads → Onyx file store →
  `build_full_frontend_file_url` → emits `PythonToolFile` inside `PythonToolDelta`.
- Frontend `web/src/app/app/message/messageComponents/timeline/renderers/code/PythonToolRenderer.tsx`
  **accumulates** stdout/stderr/files across many deltas → emitting more deltas/files needs no FE change.
- Separate unused-for-coding substrate: Onyx Craft `Sandbox` (per-user persistent pod).

---

## TRACK A — Code Interpreter polish (do first: highest ROI, lowest risk)

Reuses the workspace-snapshot → file-store → `PythonToolFile` pipeline. No FE change for A1–A2.

### A1. Auto figure capture *(smallest, ship first)*

Today charts surface only if user code calls `plt.savefig(...)`. Auto-save open matplotlib figures
after each cell. **No-op when matplotlib isn't imported** (never import pyplot ourselves).

Shared capture logic:

```python
def _capture_figures(workspace_dir, start_counter):
    import sys
    mpl = sys.modules.get("matplotlib")
    if mpl is None:
        return start_counter
    plt = sys.modules.get("matplotlib.pyplot")
    if plt is None:
        return start_counter
    n = start_counter
    for num in plt.get_fignums():
        try:
            fig = plt.figure(num)
            fig.savefig(f"{workspace_dir}/figure_{n}.png", dpi=150, bbox_inches="tight")
            plt.close(fig)
            n += 1
        except Exception:
            pass
    return n
```

- **Session (persistent kernel):** `code-interpreter/code-interpreter/app/services/_kernel.py` — add a
  module-level monotonic `_FIG_COUNTER`; call `_capture_figures("/workspace", _FIG_COUNTER)` in a
  `finally` around the exec (inside the existing `redirect_stdout/redirect_stderr` block, right after
  `_exec_single_mode`, ~L81-88), before building the response dict. Monotonic counter is required so
  cell 2's figure doesn't overwrite cell 1's (fignums reset after `close`).
- **Ephemeral:** `code-interpreter/code-interpreter/app/services/executor_docker.py`
  `_create_tar_archive` (~L135-190) — append an epilogue to the generated `__main__.py` that inlines
  the helper and calls it (dir `/workspace`, start 1). Top-level append runs after user code even on
  `last_line_interactive=False` and after an uncaught exception.
- Known v1 limitation: user calling `savefig` but not `close` yields a duplicate `figure_N.png`; accept.

**Verify:** `code-interpreter/tests/integration_tests/session_tests/test_chart_generation.py` +
new ephemeral case: (a) `plt.plot([1,2,3])` no savefig → `files` has `figure_1.png`; (b) `print("hi")`
no matplotlib → no `figure_*`; (c) two-cell session → `figure_1.png` + `figure_2.png`. Backend E2E:
add **message 4** to `test_sandbox_persistence.py` drawing a chart without savefig, assert `msg4["files"]` non-empty.

### A2. Live streaming stdout/stderr

Service already streams for ephemeral (`routes.execute_stream` ~L215,
`DockerExecutor.execute_python_streaming` ~L480). Missing: client method, `PythonTool` consumption,
and a **session** streaming path.

- **Client:** `backend/om/tools/tool_implementations/python/code_interpreter_client.py` — add
  `execute_stream(...) -> Iterator[event]` mirroring `execute` (L61-93): POST `/v1/execute/stream`
  with `stream=True`, parse SSE frames (`event:`/`data:`, blank-line separated), yield typed
  `output` chunk / `result` (carries `list[WorkspaceFile]`) / `error`. Pass `session_id` through.
- **`PythonTool.run`:** `backend/om/tools/tool_implementations/python/python_tool.py` — refactor
  `_execute_with_self_heal`/`_execute_with_retry` (~L266, ~L345) into a streaming variant: consume
  `execute_stream`, emit an incremental `PythonToolDelta(stdout=chunk)` per chunk (FE joins
  automatically), accumulate full stdout/stderr locally (needed for self-heal prompt +
  `LlmPythonExecutionResult`), on final event capture exit_code/timed_out/files → feed the unchanged
  download loop (~L575-639). **Avoid double-render:** set a `streamed` flag so the terminal emit
  (~L661-671) sends only `files` + self-heal note (not the already-streamed text). Fall back to
  blocking `execute` if the stream route is unavailable; keep `_is_retriable_error` (~L249) and the
  deadline/budget machinery (~L374-453) untouched.
- **Session streaming (hard part):** kernel emits one JSON per cell today
  (`_kernel.py` ~L92-99). Gate a stream mode behind `{"code":..., "stream": true}`:
  - `_kernel.py`: replace `redirect_stdout(StringIO)` with a line-buffered writer whose `.write(s)`
    does `sys.__stdout__.write(json.dumps({"t":"out","d":s})+"\n"); flush()` (+ `"t":"err"` twin);
    after exec + figure capture emit `{"t":"result","exit_code":...,"duration_ms":...}`.
  - `session_manager.py`: add `execute_in_session_streaming(...)` — write request, loop
    `_read_line_with_timeout` (~L434) yielding a chunk per `out`/`err` until `result` (timeout →
    restart kernel as today ~L283-293), then `_extract_workspace_snapshot` (~L363). Hold
    `state._lock` (~L252) for the whole cell; deadline per-cell not per-line.
  - `routes.py`: `execute_stream` (~L215) has no session branch today — add one driving
    `execute_in_session_streaming`, translating chunks/result like the ephemeral loop (~L235-244)
    with `_save_workspace_files`. Pure message framing over the existing pipe — security unchanged.

**Verify:** `tests/integration_tests/test_streaming.py` + new `session_tests/test_streaming_session.py`
(print→sleep→print → multiple `output` frames before `result`; final carries files). Backend:
`test_sandbox_persistence.py::send_message` already collects multiple `python_tool_delta` (~L133-142)
— assert a long print yields >1 stdout delta and self-heal still recovers a broken snippet.

### A3. Rich outputs (`display()`, inline images, plotly/HTML)

Capture IPython-style rich reprs → emit as `/workspace` artifacts (.png/.html) so they ride the
existing `PythonToolFile` pipeline (PNGs render inline; HTML = safe download link for v1).

- **`_kernel.py`:** inject a `display(obj)` into `user_globals` (~L55) that duck-types a MIME bundle
  with a monotonic `display_{n}` counter: `_repr_html_()` (pandas Styler, plotly `to_html`) → `.html`;
  `_repr_png_()`/raw PNG bytes/PIL `Image.save` → `.png`; matplotlib `Figure` → reuse A1 savefig; else
  `repr(obj)` → stdout. Route the last-expression value (`_exec_single_mode` ~L43-46) through the same
  resolver. All writes try/except; import no rich lib (duck-typing only) → zero change when unused.
  Ephemeral parity: same helper in the A1 epilogue.
- **A3b (optional, product-gated) inline HTML/plotly:** add optional `mime`/`inline_html` to
  `PythonToolFile` in `backend/om/server/query_and_chat/streaming_models.py` (~L247) (or a new
  `PythonToolRichOutput` packet); mirror in `web/src/app/app/services/streamingModels.ts` (~L154,
  `PacketType` ~L24, `PythonToolObj` union ~L341); add an `.html` branch to `PythonToolRenderer.tsx`
  (~L218-231) rendering a **sandboxed** `<iframe srcDoc sandbox="allow-scripts">` (no `allow-same-origin`).
  Skip for v1.

**Verify:** `session_tests/test_rich_output.py`: `display(df.head())`→`.html`; plotly→`.html` with
`<div`; `display(PIL_image)`→`.png`; `display("plain")`→stdout only. Backend: add a `display()`
message to `test_sandbox_persistence.py`, assert a `.png` with a `file_id`.

### Track A critical files

- `code-interpreter/code-interpreter/app/services/_kernel.py` (A1b, A2 protocol, A3)
- `code-interpreter/code-interpreter/app/services/session_manager.py` (A2 session streaming)
- `code-interpreter/code-interpreter/app/services/executor_docker.py` (A1a, A3 epilogue)
- `backend/om/tools/tool_implementations/python/code_interpreter_client.py` (A2 client)
- `backend/om/tools/tool_implementations/python/python_tool.py` (A2 consume stream)
- `code-interpreter/code-interpreter/app/api/routes.py`, `.../models/schemas.py` (A2 session branch, `stream` field)

---

## TRACK B — Real codebase-editing agent (largest effort)

**Design decision:** reuse the Craft `Sandbox` **pod** as substrate; drive it with new first-class
Onyx `Tool`s that call `SandboxManager` directly. **Do NOT route through opencode/ACP** (that's a
competing autonomous agent, awkward to nest in a workflow). The code-interpreter microservice is the
wrong substrate (ephemeral, `--network none`, no git, no persistent repo).

The pod already runs arbitrary shell internally via
`k8s_stream(connect_get_namespaced_pod_exec, ..., container="sandbox", command=["/bin/sh","-c",script])`
(~15 call sites in `kubernetes_sandbox_manager.py`, e.g. `list_directory` ~L2019, `read_file` ~L2149),
has a persistent per-user writable `/workspace/sessions`, snapshots, and hardened isolation (non-root
uid 1000, cap-drop ALL, seccomp RuntimeDefault). The generic exec is **not** on the `SandboxManager`
ABC — exposing it is the one primitive that unlocks everything.

### B0. Foundation — `exec_command` primitive *(gates all of Track B)*

- `backend/om/server/features/build/sandbox/base.py` — add to the ABC:
  `exec_command(sandbox_id, session_id, command: list[str], cwd: str, timeout, env) -> ExecResult`
  (define `ExecResult(stdout, stderr, exit_code)` in `sandbox/models.py`), plus
  `ensure_code_workspace(sandbox_id, scope_id)` (mkdir `-p /workspace/code/{scope_id}`).
- `backend/om/server/features/build/sandbox/kubernetes/kubernetes_sandbox_manager.py` — extract the
  `k8s_stream` exec pattern into one `_exec(container, argv)` helper. **Capture exit code via a
  sentinel** (`; echo "__EXIT__$?"`) because `k8s_stream` swallows exit status; parse + strip it.
- `backend/om/server/features/build/sandbox/local/local_sandbox_manager.py` — implement via
  `subprocess.run(cwd=..., timeout=...)`.
- Repos live under a new writable `/workspace/code/{scope_id}`; `scope_id` = `chat_session_id`
  (hash for non-UUID synthetic workflow scopes, cf. `python_tool.py` ~L218-241).
- **De-risk first:** `exec_command(["bash","-lc","git --version; rg --version"])` against image
  `onyxdotapp/sandbox:v0.1.5`. If missing → edit the sandbox Dockerfile (`.../kubernetes/docker/`) +
  rebuild/publish — the **largest non-code chunk**, gates B1–B4.

**Verify:** unit mirror of `.../local/test_manager.py` (~L207): `exec_command` runs `echo hi` (exit 0)
and `false` (exit 1).

### B1. Read-only agent (Read + Grep + Terminal)

New dir `backend/om/tools/tool_implementations/codebase/` with a `CodebaseToolMixin` that resolves the
sandbox (`get_sandbox_by_user_id` → ensure provisioned/healthy via
`backend/om/server/features/build/session/manager.py` ~L470-590 → `ensure_code_workspace`) and holds
`exec_command` plumbing. Each tool follows the `Tool[TOverride]` pattern
(`backend/om/tools/interface.py`): `id/name/description/tool_definition/emit_start/run/is_available`.

| Tool / `in_code_tool_id` | file | params | impl |
|---|---|---|---|
| `RepoReadTool` | `codebase/repo_read_tool.py` | `path`, `start_line?`, `end_line?` | `SandboxManager.read_file`; numbered lines |
| `CodeSearchTool` | `codebase/code_search_tool.py` | `pattern`, `glob?`, `path?` | `exec_command(["rg","-n",...])` (fallback `grep -rn`) |
| `TerminalTool` | `codebase/terminal_tool.py` | `command` | `exec_command(["/bin/bash","-lc",command], cwd, timeout)`; stream stdout deltas |

Register each in `backend/om/tools/built_in_tools.py` `BUILT_IN_TOOL_MAP` (~L38) + an `elif` branch in
`backend/om/tools/tool_constructor.py` (~L151-301, near the PythonTool branch ~L251), receiving
`user`, `db_session`, `chat_session_id`, `emitter`. Add an alembic migration seeding the tool rows
(model on `backend/alembic/versions/c7e9f4a3b2d1_add_python_tool.py`). Streaming: reuse
`PythonToolStart`/`PythonToolDelta` packets or add lightweight `TerminalToolStart/Delta`.
Repo ingestion = `git clone <url> /workspace/code/{scope}/<repo>` via `TerminalTool` (egress open).
Private repos: reuse user OAuth token already threaded into `construct_tools` (~L137-139) or a
per-persona secret.

**Verify:** attach the 3 tools to a scratch persona; live chat: clone a small public repo, grep a
symbol, read the file; confirm ToolCall rows persist and the workspace survives a 2nd message.

### B2. File edit/write

`codebase/file_edit_tool.py` — `FileEditTool`: params `path` + (`old_string`/`new_string` **or**
unified `diff`); write via `exec_command` heredoc or `git apply`. Gate write tools behind
`allowed_tool_ids` (`tool_constructor.py` ~L148) so read-only can ship first. Register + migration as B1.
**Verify:** agent edits a file → `git diff` shows change → re-read confirms → run repo tests, observe pass/fail.

### B3. Git operations (+ optional PR)

`codebase/git_tool.py` — `GitTool`: `operation` (status/diff/branch/commit/log) + args via
`exec_command(["git",...], cwd=repo)`; optional PR via `gh` if a token is configured. Register + migration.
**Verify:** branch → commit → `git log`/`git diff`; with `gh` + token, open a draft PR on a throwaway repo.

### B4. Coding-agent workflow/persona

`backend/tests/workflow_creator/workflows/21_codebase_agent.json`, modeled on
`20_universal_problem_solver.json`: Explore (Read+Search+Terminal read-only) → Plan → Edit
(FileEdit+Terminal) → Verify (Terminal build/test) → Iterate (loop on failing tests, cf. PythonTool
self-heal) → Summarize/Commit (Git). Optionally callable from workflow 20's orchestrator via `AgentTool`.
**Verify:** run end-to-end on a seeded bug (reuse workflow 20's starter bug); confirm **real file
changes + passing tests**, not a markdown diff.

### Track B security

Path confinement under `/workspace/code/{scope}` (reuse `_sanitize_path`/`shlex.quote` from the K8s
manager ~L2001-2006); hard timeout + output cap (`_truncate_output`, `python_tool.py` ~L73) on
Terminal, staying under `tool_runner`'s 600s cap; add a `NetworkPolicy` egress allowlist (pod egress
is currently open — pure K8s change); gate write ops behind `allowed_tool_ids`; call
`update_sandbox_heartbeat` on tool use so the reaper doesn't kill an active coding session.

### Track B risks

Sandbox image contents (git/rg/toolchains) — biggest; exit-code capture through `k8s_stream`;
concurrency on one shared per-user pod (parallel steps stomping git state — may need per-step
subdirs/locks); larger blast radius than the `--network none` Python sandbox.

### Track B critical files

- `backend/om/server/features/build/sandbox/base.py` (ABC: `exec_command`, `ensure_code_workspace`)
- `backend/om/server/features/build/sandbox/kubernetes/kubernetes_sandbox_manager.py` (`_exec` + impl)
- `backend/om/server/features/build/sandbox/local/local_sandbox_manager.py` (subprocess impl)
- `backend/om/tools/tool_constructor.py` (~L251 register branches), `backend/om/tools/built_in_tools.py` (~L38)
- `backend/om/tools/tool_implementations/python/python_tool.py` (reference pattern for run/streaming/self-heal)

---

## TRACK C — Workflow-engine gaps (nested delegation + parallelism)

**Concurrency model (decides everything):** the engine is **NOT asyncio**. It's a synchronous
generator that offloads each agent to an OS **thread** and streams packets through a per-agent
`queue.Queue` `Emitter` bus. Evidence: `Emitter.emit` = `self.bus.put(packet)`
(`backend/om/chat/emitter.py` ~L9-13); `AgentTool.run` is sync with `for cycle in range(max_cycles)`
(`agent_tool.py` ~L379, never awaits); `_stream_agent_packets` runs `run_in_background(_run_agent)`
then polls `emitter.bus.get(timeout=0.05)` yielding packets until `not thread.is_alive()`
(`workflow_engine.py` ~L298-359); `run_in_background` = `TimeoutThread` + `contextvars.copy_context()`
(`backend/om/utils/threadpool_concurrency.py` ~L506-517). **Parallelism = thread-based, one
Emitter/bus per branch + a multiplexer generator. Do NOT introduce asyncio** (would require rewriting
`AgentTool.run` and every tool).

**Guardrail-first: ship inert caps + plumbing before any behavior change.** Nesting (C1-C4) and
parallelism (C5-C7) are independent; within each, order is mandatory.

### C1. Delegation budget on `AgentTool` (inert)

`agent_tool.py` `__init__` (~L118-163): add `delegation_depth=0`, `max_delegation_depth=0`,
`delegation_breadth=0`; store on `self`. No behavioral use. Verify: existing tests green.

### C2. Hard-cap constants + blocked response

`agent_tool.py` top (near `AGENT_TOOL_RESPONSE_ID` ~L32): `_MAX_DELEGATION_DEPTH_HARD_CAP = 2`,
`_MAX_DELEGATION_BREADTH_HARD_CAP = 4`. Effective = `min(config, hard cap)`. Emit a "delegation
blocked" tool response when exceeded. Verify: assert on the constant → runaway recursion impossible.

### C3. Gated sub-agent build in `construct_tools` (off by default)

`tool_constructor.py` (`construct_tools` signature ~L111-123; return site ~L481): add params
`sub_agent_persona_ids=None`, `delegation_depth=0`, `max_delegation_depth=0`, `delegation_breadth=0`.
Only if `sub_agent_persona_ids and delegation_depth < min(max_delegation_depth, HARD_CAP)`: **lazily
`from om.tools.tool_implementations.agent_tool import AgentTool` inside the block** (mirrors the
existing lazy import at `agent_tool.py` ~L283 → no module-level cycle), load each allowed sub-persona
(cap at breadth/hard cap), append an `AgentTool(...)` under a synthetic negative `tool_dict` key
(avoid colliding with real `db_tool_model.id`). Exclude `persona.id` from its own allow-list.
Existing callers (`process_message.py` ~L891, `research_agent.py` ~L762) pass nothing → identical
behavior. Verify: `construct_tools(..., sub_agent_persona_ids=[p2.id], max_delegation_depth=1)` yields
a `delegate_to_p2` tool; without params → none.

### C4. `AgentTool.run` opt-in + budget propagation → nesting live (bounded)

`agent_tool.py` `run()` `construct_tools(...)` call (~L282-297): pass
`sub_agent_persona_ids=self._resolve_allowed_sub_personas()` + the depth/breadth budget. The generic
dispatch at ~L470 (`matched_tool.run(...)`) runs a nested `AgentTool` with no special-casing —
recursion "just works" once present + depth-gated. Child `max_cycles = max(4, parent//2)` via
`max_cycles_override`. **Allow-list MVP:** any other persona in the same workflow (no migration);
follow-up = `AgentWorkflowStep.sub_agent_persona_ids` PGJSONB column (models.py ~L5109-5119) +
migration + Pydantic + CRUD. Nested `AgentTool` shares the parent `emitter` → nested packets stream
live; optional `depth`/`parent_step_id` on `WorkflowStepStart` for UI indentation. Verify: new
external-dep test — A delegates to leaf B, assert B's output nested under A, and a deep/self-ref
config stops at the hard cap (bounded threads).

### C5. Parallel multi-tool-call execution (`LIMITATIONS.md` §3)

`workflow_engine.py` `run_workflow_llm_decision` tool-call loop (~L2096-2469): when
`len(tool_calls) > 1` **and** none target a `can_request_input` step (see C7), run each on its own
`Emitter(queue.Queue())` + thread (`run_in_background`), `Placement(turn_index=base+i, tab_index=i)`,
and **multiplex** (round-robin `bus.get(timeout=0.05)` across all buses, track completion via
`thread.is_alive()`, final drain — `_stream_agent_packets` generalized to N buses). Merge outputs
into `msg_history` in **deterministic tool_call order** (not completion order). **Per-thread DB
sessions** via `get_session_with_current_tenant()` (contextvars already copied). Error isolation:
each branch captures its own exception (pattern ~L300-302); one failing → "Tool error"
`TOOL_CALL_RESPONSE`, others continue; abort only if all fail. Checkpoint/trace writes on the main
thread after join. Reuse `run_functions_tuples_in_parallel`/`parallel_yield`/`ThreadSafeDict`
(`threadpool_concurrency.py` ~L284, ~L537, ~L39). Verify: prompt inducing two independent
delegations → both outputs, deterministic order, wall-clock < sum of durations.

### C6. (Optional) `parallel_group` fan-out for the sequential engine

`run_workflow_sequential` (~L581+); add nullable `AgentWorkflowStep.parallel_group: int` (models.py
~L5067) + migration + `workflows/models.py` + `db/workflow.py` + TS interfaces + editor UI (both
editors per CLAUDE.md dual-editor rule). Implement `_group_steps()` + `_run_parallel_group()` reusing
the C5 multiplexer; NULL group = unchanged. **First fix the stale `onyx`→`om` paths in
`backend/om/workflows/PARALLEL_EXECUTION.md`** (existing design doc for this).

### C7. HITL guard (ship with C5)

A parallel group may **not** contain a `can_request_input` step — enforce at build/validation and in
the C5 predicate (HITL steps always run sequentially). Rationale: current pause `return`s from the
generator (~L2394) and serializes one paused step; pausing one of N live branches needs quiescing
siblings — out of scope. Verify: existing pause/resume test green; a workflow mixing a HITL step +
a parallel group pauses correctly and the group runs as a batch.

### Track C critical files

- `backend/om/workflows/workflow_engine.py` (orchestrator loop ~L2096-2469, `_stream_agent_packets`
  ~L298-359, `_build_agent_tools` ~L446, dispatch ~L2630)
- `backend/om/tools/tool_implementations/agent_tool.py` (`__init__` ~L118, `run`/`construct_tools`
  call ~L282-297, generic dispatch ~L416-523)
- `backend/om/tools/tool_constructor.py` (`construct_tools` ~L111, return ~L481 — lazy-import AgentTool)
- `backend/om/utils/threadpool_concurrency.py` (parallel building blocks)
- `backend/om/db/models.py` (`AgentWorkflowStep` ~L5067) + `backend/om/workflows/PARALLEL_EXECUTION.md`
- Tests: `backend/tests/external_dependency_unit/workflow/test_workflow_multi_agent.py`,
  `backend/tests/workflow_creator/test_coding_workflows.py`

---

## Recommended overall sequencing

1. **A1** auto figure capture — days, isolated, immediate UX win.
2. **A2–A3** streaming + rich outputs — visible ADA parity.
3. **C1–C5, C7** nesting guardrails + parallelism — unblocks richer workflows, low blast radius.
4. **B0 spike** (image + exec de-risk) early, then **B1→B4** read-only → write → git → workflow.

Tracks are independent and can be split across people. Caps always ship before enablement (esp. Track C).

---

## Appendix — Before/After on a real interaction (user-visible payoff)

Reference case: a multi-agent (6-agent) answer to *"learn pandas data wrangling… show real
examples"* that printed a pivot table and saved `sales_by_region.png`. Observed **today**: whole
response appears at once after ~69s ("Python execution completed"); DataFrame/pivot shown as
monospace text; chart rendered inline **only because** the code called `plt.savefig(...)`; the 6
agents ran sequentially.

| Aspect | Today | After (track) |
|---|---|---|
| Output timing | all at once after ~69s | streams live as it runs (**A2**) |
| DataFrame / pivot display | monospace `to_string()` text | styled HTML table (**A3**) |
| Charts | static PNG, needs explicit `savefig` | inline even without savefig; interactive plotly option (**A1 / A3**) |
| Multi-agent latency | sequential | independent agents run concurrently (**C5**) |
| Repo editing | n/a for this task | n/a — Track B only applies when editing a codebase |

**Takeaway for prioritization:** on ordinary code-interpreter/data-analysis chats like this, the
*felt* improvement is **A2 (streaming) + A3 (rich tables/interactive charts)**, with **C5** shrinking
multi-agent wall-clock. **A1** is a robustness fix (visible only when the model forgets `savefig` /
uses `plt.show()`), and **Track B** produces no change unless the user asks the agent to modify a repo.
This reinforces the sequencing above: ship A first.

---

## TODO (deferred) — Live agent-prose + reasoning streaming in workflows

**Why:** In multi-agent workflows each sub-agent's answer currently appears as a **block** and its
reasoning is **hidden** — by design, not a bug. The engine streams sub-agent `message_delta`/
`reasoning_delta` to the bus, but `_stream_agent_packets` drops them via `_AGENT_SUPPRESS_TYPES`
(`backend/om/workflows/workflow_engine.py:93-101,325`) and re-emits each agent's whole answer as one
`WorkflowStepDelta` (`:1117-1121, :2396-2399, :1907`); the frontend `WorkflowStepRenderer` joins
those into a block. (PythonTool stdout is NOT suppressed → A2 streaming already works live here.)
Goal: token-by-token prose + live "thinking" in workflows, like normal chat. Independent of A1/A2
(workflow-engine + workflow-renderer change; Track-C-adjacent).

**Phase 1 — live prose (recommended: translate, don't merely un-suppress):**
- `workflow_engine.py` `_stream_agent_packets` (~L298-359): instead of dropping sub-agent
  `message_delta`, translate each chunk into an incremental `WorkflowStepDelta(content=chunk)` tagged
  with the current step's placement and yield it live. The frontend `WorkflowStepRenderer` already
  joins `WorkflowStepDelta.content` + passes `isStreaming`
  (`web/src/app/app/message/messageComponents/timeline/renderers/workflow/WorkflowStepRenderer.tsx:41-72`),
  so this streams with **little/no frontend change**.
- **Avoid duplication:** the engine also emits one big `WorkflowStepDelta(content=full_agent_output)`
  at step end (`:1117-1121, :2396-2399, :1907`). With live chunks, either (a) drop that final content
  emit, or (b) keep it authoritative and have the renderer REPLACE the accumulated chunks with the
  final content on `WorkflowStepEnd`. **Recommend (b)** — stream for responsiveness, reconcile to
  `agent_output` on complete (robust when `agent_output` ≠ raw message text).
- Keep `agent_output` parsing (`agent_tool.py:561-574`) for orchestration/msg_history **unchanged** —
  UI-only change; the LLM transcript is unaffected.

**Phase 2 — live reasoning:**
- Add a workflow reasoning packet (e.g. `WorkflowStepReasoningDelta`) or forward `reasoning_delta`
  tagged to the step placement; drop `reasoning_*` from the suppress set. Render a **collapsible**
  "Thinking" sub-block inside `WorkflowStepRenderer` (mirror normal chat's reasoning renderer);
  collapsed/off by default (many agents = noise).

**Risks/decisions:** streamed-vs-final duplication (pick reconcile strategy b); parallel agents
(Track C) interleaving — `placement`/`tab_index` already separate groups; token volume/perf — apply
rAF batching (same as A2 deferred item); msg_history unaffected.

**Files:** `backend/om/workflows/workflow_engine.py` (`_stream_agent_packets`, the 3 block re-emit
sites, `_AGENT_SUPPRESS_TYPES` L93-101), `backend/om/server/query_and_chat/streaming_models.py`
(optional `WorkflowStepReasoningDelta`), `web/.../workflow/WorkflowStepRenderer.tsx` (+ `streamingModels.ts`).

**Verify:** run a multi-agent workflow → each agent's prose fills token-by-token; reasoning shows
live (phase 2); final text matches `agent_output`; no duplication; PythonTool stdout still streams
(A2 unaffected).
