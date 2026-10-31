# Flow nodes: design-vs-code analysis, then the proper fix plan (2026-10-31)

## Context
The user rejected the previous plan with: "before you fix analyze the design we have implemented, from where it taken and based on that understand what is required and what is missing … come to me again with proper fix."

So this plan does three things:
1. Traces each part of the design to its source: REFERENCE_STUDY deltas E/V/C/W, which came from graphon/Dify, LangGraph, n8n, Windmill, Activepieces and Langflow.
2. Checks the code against each item. Three read-only audits were run, and the key claims were spot-verified.
3. Turns the gaps into an ordered fix plan.

Rules:
- commit only when asked, and never push;
- explicit `git add` paths;
- never run the alembic CLI;
- one module at a time;
- no workarounds;
- dual-editor rule.

## TODO: build order (user's decision, 2026-10-31: "all one by one, write todo, implement and test it, check screenshot")
Publish this list as `docs/flow-nodes/TODO.md` and tick items as they finish. One item at a time; each is implemented, tested, then checked on screen before the next.

**Answer recorded:** the canvas is frontend work. Engine scheduling and the API contract don't change for it; only the run view needs small backend instrumentation. Parallel is drawn as a **box with lanes**.

| # | Item | Kind | Done when |
|---|---|---|---|
| 1 | Step 1 UI check (timeline, Wizard Next, save on workflow 49) | User check | User's screenshot or confirmation |
| 2a | Save: atomic, row lock, 409 on race (review finding 1) | Backend | DB tests reproduce and pass |
| 2b | Save: snapshot "before" version of pre-migration workflows (finding 2) | Backend | DB test: restore pre-edit definition |
| 2c | Reject duplicate `output_key`, reserve `loop`; test `llm_decision` rejects containers | Backend | Unit + DB tests |
| 2d | Pin `llm_decision` runs | Backend | Unit + goldens both engines |
| 2e | Shared validation mirrors the backend; router missing target is an error | Frontend | jest per rule |
| 2f | Editor parity (toggles, `max_calls_per_agent`) | Frontend | jest; screenshot |
| 3a | `research/04-container-ui.md` | Docs | Written, sources linked |
| 3b | Shared tree model and DFS order; replace BFS save; chain per block; fix router reorder | Frontend | jest round-trip, incl. workflow 49 payload unchanged |
| 3c | Container node kind, boxes with lanes, ELK layout | Frontend | jest; **screenshot of workflow 49** |
| 3d | Add steps into a lane, drag in/out, move between lanes; block cross-block edges | Frontend | jest; screenshot |
| 3e | Forms: branch labels, loop operator dropdown, code inputs/outputs | Frontend + small backend | jest; screenshot |
| 3f | Wizard: Run inside / Branch pickers, indent, safe reorder and delete | Frontend | jest; screenshot |
| 3g | Build parallel + loop from the UI in each editor, save, reload, run; nested combinations | End to end | Runs complete; nesting tests added |
| 4 | Run view: trace fields, loop trace, packet branch fields, persist `step_type`, grouped timeline | Backend + frontend | Tests; screenshot of a demo run |
| 5 | Webhooks in Pulse (W1–W5) | Full stack | Tests in PROGRESS "Webhooks"; screenshot |
| 6 | Engine hardening | Backend | Each with tests; goldens green |
| 7 | Rollout readiness, review, docs | Mixed | Section "Step 7" |

**Testing setup:**
- Backend code is bind-mounted, so `dev.bat restart api background` picks it up; Pulse uses `dev.bat build pulse`. Web changes need `dev.bat build web`, which I run; it restarts only the web container.
- DB tests keep using the `flow_dev` database (env file `D:/tmp/flowdev.env`), never the real DB; the `flowdev` containers stay retired.
- Screenshots: no test login exists on the real DB and none will be created, so at each screen check I ask the user for a screenshot.
- Live checks on the real DB use the throwaway-key pattern of `D:/tmp/main_demo_e2e.py`.
- Migration `0003` (item 5) applies to the real DB when the API restarts: ask the user to take a backup first.

## DONE: Step 1 verified on the main stack (2026-10-31)
The user rebuilt with `dev.bat` and asked to continue testing. `flowdev.bat` is retired; everything runs on port 3000. Results are in HANDOVER. Only item 1 in the TODO above remains.

**Checked just now (read-only):**
- Migration `0002` is applied; demo workflow 49 is loaded in the Visual Builder with the dedicated agents.
- `om/python-executor-sci:latest` is rebuilt. **`om/code-interpreter:local` is still 3 months old**: its logs show `/v1/run_function` 404, so the hardening and warm pool aren't live.
- Workflow 49 has 0 executions, so the chat run has not been tested on this stack.

**Test order (each must pass before the next):**
1. **Rebuild the sandbox service**, the two lines the user didn't get to, from `deployment/docker_compose`:
   `docker compose -f docker-compose.yml -f docker-compose.dev-windows.yml build code-interpreter`, then `... up -d --no-deps code-interpreter`.
   Touches only that container. The old image stays tagged `pre-flow` if the user tagged it; if not, tag it first.
2. **Sandbox check** (`D:/tmp/main_sandbox_check.py` in the API container, no DB access):
   - `run_function` supported, ~0.15 s;
   - a call without the token is rejected (401);
   - no network and a read-only filesystem inside the sandbox;
   - the normal chat Python tool path (`/v1/execute`) still works.
3. **Old workflows still load, read-only** (new `D:/tmp/main_dry_run.py`, writes nothing; this is the Step 7 dry-run report, done early because the real DB is now migrated). For all workflows:
   - loads through `graph_from_workflow`;
   - step order unchanged;
   - every node type and version is known;
   - all agent steps pass `load_step_agent`;
   - every paused execution's checkpoint maps to node keys.
4. **Demo end to end through the real API:**
   - mint a temporary admin API key, `POST` a chat run of workflow 49 with "a 3 day trip to Goa", then delete the key in a `finally`;
   - checks: execution `completed`, pinned to a version; steps in order; 2 branches ran concurrently; 3 loop iterations; final answer holds the "Trip plan" sections; sandbox log shows `run_function` 200.
   - Leaves one execution and one chat session on the real DB (same as a manual run). It creates no other data and uses live LLM calls.
5. **Rejections through the real API**, same temporary key: saving a step on agent 0 and on a wrapper agent both return 400 with the right message. Nothing is created.
6. **Backend and web suites again:** unit + pulse, goldens on both engines, `tsc`, jest.
7. **The user checks in the browser** (no test login exists on the real DB, and none will be created):
   - chat with "Demo: Trip planner": timeline labels and the formatted answer;
   - `/admin/workflows/edit/49`: click Next, no "needs an agent" error;
   - save with no changes: no error.

**Then:** record results in HANDOVER, mark Step 1 done. Step 2 starts only after this. The review's save fixes (findings 1 and 2) still await the user's decision.

**Screenshot evidence for Step 3 (not fixed now, no scope jump):** on the canvas, parallel branches are one chain (Travel → "then #4" → Stay), which contradicts how they run; the "Pipeline Mode: agents run one after another" legend is wrong for them; edges route across nodes with looped stubs at the handles; the workflow title is cut off.

## A. Design origin → what the code does

**Backend engine:** sources are REFERENCE_STUDY E1–E9 (graphon dispatcher, LangGraph and Langflow).

| # | From | Required by design | Code today | Status |
|---|---|---|---|---|
| E1 | graphon "containers yield their worker" | One bounded pool **per run** (`WORKFLOW_MAX_CONCURRENCY`); nested containers scheduled by the coordinator | Pool per parallel step (`branches.py:196`); a loop inside a branch runs **on the branch thread** (`blocks.py:61` → `loop.py:160`); no run-wide or global cap | Partial |
| E2 | LangGraph stream queue | One queue, turn range per branch | Done (`branches.py:48,146,230`) | ✅ |
| E3 | LangGraph `apply_writes` | Ordered merge; **reject duplicate `output_key` at save** | Merge ✅. **The backend never rejects duplicates** (`saving.py:123-129` checks keys and orders only); only the browser does (`validation.ts:173`) | Partial, real bug |
| E4 | graphon error modes, LangGraph cancel | `fail_fast` / `continue` / `drop_failed`; cancel between LLM and tool turns | Only `fail` and `continue`; `fail` waits for all branches; cancel is checked only between nodes; a loop inside a branch drops the cancel event (`loop.py:232-246`) | Partial |
| E5 | LangGraph pending writes | Progress saved per branch inside a container | Deliberately not built; DESIGN v1 re-runs the container | Changed on purpose |
| E6 | LangGraph "async" durability | Throttled checkpoints | A commit after every node (`state.py:290`) | Missing (latency) |
| E7 | graphon loop + ExecutionLimits | Break checked before and after each round; explicit break; global step budget | Checked before only; no break, no budget; items beyond `max_iterations` dropped silently | Partial |
| E8 | n8n `executionOrder` | `schema_version=2`: safe tokenizer and `$key.output.<path>` for agents | Column only; nothing branches on it (`inputs.py:16-65`) | Missing |
| E8b | graphon runtime_state | Checkpoint v1→v2 migrated when read | Done (`state.py:178-248`) | ✅ |
| E9 | graphon pitfall | Retry/backoff inside the branch thread | No retry anywhere | Missing |
| C1/C2 | Dify, graphon limits, n8n runner | Nonce harness, strict output validation | Done | ✅ |
| C3 | dify-sandbox | 5 s default / 30 s max; fixed error kinds | Timeouts ✅; one free-text `CodeNodeError`, prints and trace discarded (`code.py:276-289`) | Partial |
| C5 | dify-sandbox | Backend per-tenant + global semaphore | None in the backend | Missing |
| V1 | Windmill, Activepieces | **Every** run is pinned to a version | Only v2 sequential runs; **`llm_decision` (29 live workflows) and Pulse runs of them never pin** (`workflow_engine.py:1283-1299`) | Partial |
| V2 | Activepieces migrations | Lazy N→N+1 chain | Machinery present, chain empty | Partial (fine for now) |
| V3 | n8n VersionedNodeType | Opt-in upgrade, diff, audit, revert, `breaking` flag | Preview + revert ✅; breaking returns 409 instead of a flag; no audit event | Partial |
| Save rules | DESIGN "Save rules (v1)" | Depth, size, no parallel-in-parallel, no pause in children, router same block, `llm_decision` rejects containers | All present (`saving.py:132-182`); the `llm_decision` rejection has no test | ✅ (test gap) |
| Migration item 6 | PROGRESS plan | Live-DB dry-run report script | Not written | Missing |

**Agent steps** (the bug the user hit). There is no reference design for this; it was a frontend convention.

| Facts (verified) | Evidence |
|---|---|
| Agent 0 = built-in "Assistant", public, tools set **globally** by admins via `PATCH /admin/default-assistant`; its chat-only special handling doesn't apply in a step | `constants.py:68`, `0001_om_baseline.sql:7504`, `agent_tool.py:300-317` |
| A wrapper agent (`workflow_id` set) has no tools or prompt. As a step it **silently becomes an empty LLM call**; there is no recursion guard | `db/workflow.py:213-280`, `agent_tools.py:56-92` |
| The rule came from Visual Builder commit `35afee21a "agentic ui"` (2026-03-07), unexplained. The old Wizard blocked 0 only because 0 was its placeholder. The backend never enforced it, but `stepAgents.ts` claims it does | git history |
| Step agents are loaded with **no access check** at run time. `AgentTool` falls back to the **first user in the DB** when there is no user | `agent_tools.py:59`, `agent_tool.py:260-265` |
| All 47 templates create dedicated agents by name; the main DB has 0 steps on agent 0 or wrappers; only my `D:/tmp` demo and E2E scripts use agent 0 | `config.py:242-275`, HANDOVER |
| Reference pattern (Dify agent_v2): validate the referenced agent **at save and again at run**; sub-workflow calls are a separate node with a depth guard (Dify `WORKFLOW_CALL_MAX_DEPTH`, n8n `callerPolicy`) | `dify/api/core/workflow/…/validators.py`, `binding_resolver.py`; `n8n/packages/workflow/src/interfaces.ts:4171` |

**Frontend editors:** the design is DESIGN "Containers" plus the dual-editor rule.

| Required | Code today |
|---|---|
| Build containers (put a step into parallel/loop, pick a branch) | **Neither editor can.** The Wizard shows a note (`WorkflowEditorPage.tsx:325-338`). Visual Builder: badges only, a grid layout, sequential mode chains every step in one line, so branches *look* serial (`graphUtils.ts:173-183,385-518`) |
| Edit all config | The schema form can't edit parallel `branches` (labels), code `inputs` / `outputs` (stuck at defaults), or loop `operator` (free text) (`configSchema.ts:175-188`) |
| Structure-safe editing | Wizard up/down can move a child **above its container**; deleting a container **orphans its children** in both editors (`WorkflowEditorPage.tsx:932-937`, `useWorkflowGraph.ts:170-180`) |
| Frontend and backend give the same errors | The frontend misses all container rules, loop `items`/condition required, code output/input names and `main`, and router missing targets (silently dropped, `validation.ts:70-72`). The backend misses agent 0, wrappers and duplicate `output_key` |
| Editors match each other | Terminal / Show as Message / Can Request Input are only in the Visual agent panel; `max_calls_per_agent` max is 20 vs 10 |
| Run display shows fork/join | Timeline: parallel header only, branches not grouped. Trace: the loop writes no trace node, and there are no fork/join edges (`trace_models.py:72-92`) |

**Webhooks (P4):** the design is W1–W5. Nothing is built. Reusable pieces:
- SCIM token helpers (`scim/auth.py:57-131`);
- `EncryptedString`;
- Pulse's commit-then-enqueue runner, owner access re-check and rate limits;
- `PulseRun.trigger`;
- the `PUBLIC_ENDPOINT_SPECS` allowlist.

To build: model and migration, `POST /hooks/{token}` doing the cheapest checks first, dedup, listen mode, `{{payload.x}}`, and UI.

## B. Fix plan, in order. Each step is finished and tested before the next, one module at a time.
**User decisions (2026-10-31):**
- Steps use **dedicated agents only**: agent 0 and wrapper agents are rejected at save and at run.
- **Publishing grants access** to step agents; only the "first user in DB" fallback is fixed.
- Order: Steps 1–2, then container UI, then trace, then webhooks, then hardening.

### Step 1: agent-step rule, properly (backend is the source of truth)
1. `backend/om/workflows/nodes/agent.py`: a single function `step_agent_problem(agent) -> str | None` that returns a problem for:
   - missing or deleted;
   - `agent.id == DEFAULT_AGENT_ID` (`om/configs/constants.py`);
   - `agent.workflow_id is not None`.

   `prepare_agent_step_v1` raises `StepSaveError` with that message. Fix the wrong comment at line 89.
2. The same function at run time in `AgentToolCache._build` (`nodes/agent_tools.py`): the step **fails** with that message instead of being silently skipped, so old rows and restored versions surface clearly.
3. Run-time access (**user decision: publishing grants access**): no new per-runner check. Replace the "first user in DB" fallback in `agent_tool.py:260-265` with the workflow owner. If there is still no user, the step fails with a clear error. Log the fallback.
4. Frontend: fix the `stepAgents.ts` doc comment; error texts identical to the backend's.
5. Tests:
   - unit cases for the rule function, the save hook and the run hook;
   - DB test fixture uses a dedicated agent, plus rejection tests (0, wrapper);
   - jest `stepAgents.test.ts` and `validation.test.ts` (null / 0 / wrapper / dedicated).
6. Live data:
   - the seed script creates dedicated "Demo: …" agents and re-seeds workflow 76;
   - the `flow_e2e_*.py` scripts stop using agent 0;
   - re-run them;
   - browser test: the Wizard passes step 2 on workflow 76.

### Step 2: protect saves, and make the backend and frontend give the same errors
0. **Save fixes from `REVIEW_88eb334e5.md`:**
   - Finding 1: `SELECT … FOR UPDATE` in `saving.save_workflow_update`, compare `expected_version` after taking the lock, one transaction for steps + version row (`db/workflow.py:140` commits today), leftover IntegrityError → 409.
   - Finding 2: pin the current graph **before** applying an edit when the workflow has no version row, and `next = max(latest, workflow.version) + 1` (`versioning.py:47`).
   - Findings 1 and 2 were static review; reproduce each in a test first.
1. Backend `saving.py`: reject duplicate `output_key` (E3), and add the missing `llm_decision`-rejects-containers test. Confirm no live workflow has duplicates before enforcing it (0 on the last count).
2. Pin `llm_decision` runs to a version (V1): call `pin_workflow_version` in `workflow_engine.py`'s `llm_decision` path (`versioning.py`).
3. Frontend `validation.ts` mirrors the backend rules:
   - container rules;
   - loop required fields;
   - code input and output names;
   - router missing target becomes an error.

   Both editors use it. Add jest for each rule.
4. Editor parity: Terminal / Message / Request-input toggles for every type in the Visual panel; a shared `max_calls_per_agent` limit, as a constant in `lib/workflows`.

### Step 3: container UI and full config editing (biggest user-visible gap)
1. **Research notes first:** `research/04-container-ui.md`.
   - Surveyed 2026-10-31 (web summaries, no screenshots): Sim Studio (Apache) is the closest model: Parallel and Loop boxes, parent link on each node, parents sorted first. Dify (ideas only): Loop/Iteration boxes on one canvas, flat nodes with container tags, edges only within a scope, ELK. Flowise, n8n, Langflow, Power Automate as comparison.
   - Add the UI folders to the sparse clones and read Sim and Flowise directly: Dify `web/app/components/workflow/nodes/{iteration,loop,_base}/`, plus `web/app/components/workflow/utils/elk-layout.ts`.
   - React Flow sub-flows: `parentId`, `extent:"parent"`, `expandParent`, parents before children.
2. **Shared model** in `lib/workflows/editorModel.ts` and `serializer.ts`:
   - save walks the container tree instead of the BFS in `graphUtils.ts:318-377`; `step_order` is depth-first; this also fixes the router reorder (`[R, x, x2, y]`);
   - chain edges per `(parent_key, branch_index)`, including Finish (`graphUtils.ts:173-183,207`);
   - new nodes take their container from where they're dropped (`editorModel.ts:184` hardcodes null), and `onConnect` refuses cross-block edges;
   - move-into / out-of container and change-branch helpers;
   - delete-container removes or unparents children (user-visible choice);
   - reorder keeps children after their container;
   - lane removal renumbers `branch_index`; empty lanes show a clear error before the server's 400.
3. **Config fields** in `components/workflows/`, shared by both editors:
   - parallel branch-labels editor;
   - code inputs (name → `$reference` picker) and outputs (name + type) editors;
   - loop operator dropdown reusing `CONDITION_OPERATORS` (`RouterConfigPanel.tsx:92`);
   - backend, small: validate loop `operator` at save (`loop.py:92-107`; an unknown one makes `while` run zero times), enum hint via `json_schema_extra` keeping the `str` type, unique branch labels (duplicates overwrite each other, `parallel.py:178`).
4. **Wizard:**
   - "Run inside" and "Branch" pickers;
   - children indented under their container;
   - safe reorder and delete.
5. **Visual Builder:**
   - Parallel (**box with lanes, user's decision**) and Loop (box with one lane, `branch_index=0`) as React Flow parent nodes with a `container` kind; `isStepNode` must exclude lane nodes (`types.ts:84-86`);
   - drag in or out sets `parent_key`/`branch_index`;
   - **ELK layout instead of dagre** (React Flow's docs list an open dagre sub-flow issue; Dify uses ELK); neither is installed yet;
   - the sequential chain no longer links siblings across branches;
   - exempt each lane's first child from the disconnected check (`graphUtils.ts:551-553`); correct the "Pipeline Mode" legend.
6. **Tests:**
   - jest round-trip with containers in both editors, plus the delete and reorder cases;
   - browser: build parallel + loop from the UI in each editor, then save, reload and run.

### Step 4: run display (fork/join)
Backend instrumentation, not scheduling; no migration, because traces are JSON blobs.
- Trace: a `parent_key` / `branch_index` / iteration field on `TraceNode`, a loop trace node, fork/join edges, real timestamps from `BufferedTrace` (`trace_models.py:286,327`), keep branches that never finished (`parallel.py:156-158`).
- Packets: optional branch and iteration fields on `WorkflowStepStart` (`streaming_models.py:380-386`); persist `step_type` so a reloaded chat keeps its labels (`message_handler.py:518-523`, `session_loading.py:99-103`).
- Timeline: group the branch rows under the parallel step. Trace graph: layout beyond a single chain (`WorkflowTraceGraphBody.tsx:121`).
- Tests. Goldens will need a reviewed update for the new optional packet fields.

### Step 5: webhook triggers in Pulse (P4)
Follow W1–W5, reusing the pieces listed in section A.
1. Migration `0003_pulse_webhooks`.
2. Public `POST /hooks/{token}` doing the cheapest checks first, with HMAC over the raw body.
3. Dedup (202 with the original run id), then 429.
4. Listen mode.
5. `{{payload.x}}` templates.
6. UI in ScheduleModal.
7. Tests, as listed in PROGRESS "Webhooks".

### Step 6: engine hardening (design deltas not yet built)
- **Run-wide and global concurrency cap (E1, C5):**
  - `WORKFLOW_MAX_CONCURRENCY` setting;
  - backend semaphore around the code sandbox and branch workers.
- **Cancel (E4):**
  - pass the branch cancel event into loops and agents;
  - `fail` stops waiting on the first error;
  - add `drop_failed`.
- **Retry (E9):** retry per node with backoff on the worker thread (`retry` in the node config; agent and code only; default 0, so nothing changes).
- **Code error kinds (C3):** `error_kind` field, keep the capped print log.
- **Loop (E7):**
  - check after each iteration;
  - warn when `max_iterations` truncates the list;
  - a global step budget.
- **Throttled checkpoints (E6).**
- Each item gets its own tests, and the goldens must stay green.

### Step 7: rollout readiness
- **Dry-run report script** (read-only, run against `flow_dev`).
- Template JSONs for code, parallel and loop.
- A live regression of the medical, discussion and one gov-dept suite on v2.
- Multi-agent review, then `graphify update .`.
- Docs: HANDOVER, PROGRESS and DESIGN. Fix the stale lines, and record E5, E8 and V2 as deliberately deferred with a reason.
- Main-stack rollout checklist for the user.
- Test-stack cleanup when the user says.

**Deferred, with reasons recorded in DESIGN:**
- E5 container progress: containers never pause, so v1 re-runs the container.
- E8 `schema_version=2` tokenizer: it changes old behaviour and needs its own "Upgrade workflow" UX.
- gVisor.

## Verification (every step)
- **Backend:**
  - unit `tests/unit/om/workflows` in `om/om-backend:latest`, with `backend/` mounted;
  - goldens with `ENGINE_IMPL=v2` and `ENGINE_IMPL=legacy`;
  - DB tests on `flow_dev`;
  - mypy on the changed modules.
- **Web:** `npx tsc --noEmit` and `npx jest src/lib/workflows src/components/workflows src/components/workflow-builder`.
- **Live:** on the main stack, as described under "Testing setup" in the TODO section. No `flowdev.bat`.
