# Flow nodes — HANDOVER (read this first)

Last updated: 2026-10-30. Worktree `D:/llm/danswer_flow_wt`, branch `feature/flow-nodes` (off `main_multi_agent_stable`).
**Nothing is committed** (user rule: commit only when asked; never push; explicit `git add` paths — the repo is public).
Never touch the main checkout `D:/llm/danswer20022026` or the `virtualai-*` stack. Never run the alembic CLI.

Companion docs in this folder: `PROGRESS.md` (status + test stack), `DESIGN.md` (architecture),
`REFERENCE_STUDY.md` + `research/` (where ideas came from), `OPERATIONS.md` (sandbox settings).

## What the user asked for
Parallel branches, loops, Python code steps and webhook triggers for workflows (Langflow/n8n/Dify-level
flexibility), **easy to extend and upgradeable**, built step by step with readable, industry-standard code,
plus security hardening of the code sandbox. Old workflows must keep working.

## ▶ IN PROGRESS when this handover was written — resume here
**Task: "workflow steps use dedicated agents" (fixes the error the user hit in the Wizard).**
The user opened `/admin/workflows/edit/76` on the preview, clicked Next, and got
`"Getting there" needs an agent` (×3). Cause: demo workflow 76 uses agent **0** (the default "Assistant"); the
frontend validation used `!step.agent_id` (0 is falsy) and the old Wizard used `0` as its placeholder value.
Product convention (Visual Builder since 2026-03 "agentic ui"): steps use **dedicated** agents — never the default
Assistant (id 0) nor a workflow wrapper agent (`agent.workflow_id` set). Main DB has 0 steps violating this.
The user said: **no workarounds — proper implementation.**

Done so far (uncompiled/untested yet):
- `web/src/lib/workflows/stepAgents.ts` (new): `selectableStepAgents()`, `isSelectableStepAgent()`, `DEFAULT_ASSISTANT_AGENT_ID`.
- Used by `components/workflow-builder/AgentSidebar.tsx`, `NodeConfigPanel.tsx`, and the Wizard `refresh-pages/WorkflowEditorPage.tsx`.
- Wizard agent `<select>`: placeholder `value=""`, value `step.agent_id ?? ""`, onChange `"" → null`, else `Number(v)`.
- `lib/workflows/validation.ts`: `agent_id == null` → "needs an agent"; `agent_id === 0` → "uses the default Assistant; choose a dedicated agent".

Remaining for this task:
1. Backend rule in `backend/om/workflows/nodes/agent.py::prepare_agent_step_v1`: reject agent 0 and wrapper agents
   (`agent.workflow_id is not None`) with clear messages; unit + DB tests
   (`tests/external_dependency_unit/workflow/test_workflow_saving_db.py` — its `agent_id` fixture must exclude id 0).
2. Jest: add cases to `web/src/lib/workflows/validation.test.ts` (null vs 0 vs dedicated) and a `stepAgents` test; run
   `npx tsc --noEmit` and `npx jest src/lib/workflows src/components/workflows src/components/workflow-builder`.
3. Re-seed the demo (workflow 76 in `flow_dev`) with dedicated agents (`D:/tmp/flow_preview_seed.py` uses agent 0;
   pick/create named agents) and switch the live E2E scripts (`D:/tmp/flow_e2e_*.py`) off agent 0.
4. Rebuild the preview web image (`docker build -t om/om-web-server:flowdev web`), recreate `flow_web`, re-run
   `python D:/tmp/flow_preview_browser.py` and add a check that the Wizard passes step 2 for workflow 76.

## Then continue with (in order)
1. Write `research/00-platform-survey.md` (the 11-platform web survey; summary table below is the seed).
2. **Container UI** — users can't yet put a step inside Parallel/Loop from either editor (see "How the next session
   should research a remaining feature" below; research notes first, then design, then code).
3. **Webhook triggers in Pulse (P4).**
4. Multi-agent review (correctness / security / UX), fixes, `graphify update .`, docs, test-stack cleanup.
5. Commit only when the user asks.

## What was built — explained from the UI

**Preview** at `http://localhost:3091` (log in with your own account; DB `flow_dev` is a clone of the main DB):

| Where in the UI | What you can do now | Status |
|---|---|---|
| Admin → Workflows → **Edit** (Wizard), Step Type dropdown | Choose **Agent, Code, Condition**; Parallel/Loop also listed | Code step shows a Python box + inputs/outputs; Condition picks branch targets by step name. |
| Wizard / **Visual** builder | Steps inside a container show a badge "In <container> · branch N"; the container shows "Contains N steps" | **No control yet to put a step inside a Parallel/Loop** → containers can only be built via API/JSON today (gap #1). |
| Visual builder → **Utils** palette | Lists Code, Parallel, Loop, Condition (from the server catalog `GET /workflow/node-types`) | A new backend node type appears automatically. |
| **Versions** button (both editors) | History of every save, view a version, **restore** | Every save = immutable version; runs are pinned to the version they started on. |
| "Upgrade available" badge on a node | Opt-in upgrade of a node's config to a newer node version (diff preview) | e.g. old Condition v1 → v2. |
| Chat (agent "Demo: Trip planner…", workflow 76) | Ask "a 3 day trip to Goa" | The timeline shows "Code: Read the request" → "Parallel: Research in parallel" (2 branches at once) → "Loop: Plan each day" (1/3, 2/3, 3/3) → a formatted answer. |
| Admin → Pulse | Unchanged | Webhooks not built yet (gap #2). |

## Where the ideas came from (read before reviewing or extending)

**Research trail:**
1. Web survey of 11 platforms (2026-10-30): n8n, Langflow, Dify, Flowise, Zapier, Make, Power Automate/Copilot Studio, LangGraph, Activepieces, Windmill, Temporal (+ Sim Studio, Node-RED).
2. Code-level study of local clones.
3. Design deltas, approved by the user.

**Written up in** `D:/llm/danswer_flow_wt/docs/flow-nodes/`:
- `REFERENCE_STUDY.md`: summary + every design delta E1–E9, V1–V3, C1–C5, W1–W5, each with its source.
- `research/01-engines.md`: parallel / loop / checkpoint.
- `research/02-sandboxes.md`: code execution + our sandbox gap analysis.
- `research/03-webhooks-versioning.md`.
- **Missing:** the web-survey summary (platform table below) is not yet in the repo. Next session: write it to `research/00-platform-survey.md`.

**Local source clones** (read-only, untrusted, never build or run): `D:/llm/reference-frameworks/`
- Sparse checkouts, so add more folders with `MSYS_NO_PATHCONV=1 git -C D:/llm/reference-frameworks/<repo> sparse-checkout add "/<path>/"` (Git Bash rewrites `/paths` unless `MSYS_NO_PATHCONV=1`).
- **Licences / clean-room rule:**
  - Read for ideas only, never copy code: **n8n** (Sustainable Use), **Windmill** (AGPL), **Dify main** (modified Apache).
  - Reference allowed (credit any pattern): **graphon** (Dify's engine, Apache-2.0), **LangGraph** (MIT), **Langflow** (MIT), **Activepieces** (MIT core), **dify-sandbox** (Apache).

### Feature → inspiration → where to look

| Our feature (file) | Main inspiration | What we took | What we avoided | Source to read |
|---|---|---|---|---|
| **Node-type registry + versions** (`nodes/base.py`, `registry.py`, `builtin.py`) | n8n `typeVersion`; Activepieces pinned piece versions + flow-version migrations; graphon (type, version) registry | Every node pinned to a version; old versions stay registered; opt-in upgrade functions; unknown version = hard error | Silent auto-upgrade; Langflow swapping code at build time | `n8n/packages/workflow/src/versioned-node-type.ts`, `interfaces.ts` (typeVersion); `activepieces/packages/server/api/src/app/flows/flow-version/migrations/`, `activepieces/brain/knowledge/decisions/000005-freeze-piece-versions-in-the-flow-bundle-manifest.md`, `activepieces/docs/build-pieces/piece-reference/piece-versioning.mdx`; `graphon/src/graphon/nodes/base/node.py`; `dify/api/core/workflow/node_factory.py` |
| **Workflow versions + pinned runs** (`versioning.py`, `agent_workflow_version`) | Windmill immutable hashed versions; Temporal pinned runs; Activepieces locked flow versions | Content-hash snapshot per save; runs and resume use the pinned definition; restore | Draft/publish UX (user chose history only) | `windmill/backend/windmill-api/src/jobs.rs` (`run/fv`, `run/h`); `activepieces/packages/server/api/src/app/flows/` |
| **Engine coordinator** (`sequential.py`, `blocks.py`) | graphon dispatcher; LangGraph supersteps | One coordinator thread owns DB, trace and checkpoints; runners only run nodes | Retry sleep on the coordinator (graphon pitfall) | `graphon/src/graphon/engine/` (`dispatcher.py`, `worker/worker_pool.py`, `scheduler.py`, `ARCHITECTURE.md`); `langgraph/libs/langgraph/langgraph/pregel/` (`main.py`, `_runner.py`, `_executor.py`, `_loop.py`) |
| **Parallel container** (`branches.py`, `nodes/parallel.py`) | graphon iteration window; LangGraph ordered merge + `max_concurrency`; n8n Merge (wait-all); Windmill branch-all; Sim/Flowise containers | Bounded pool, sliding window; per-branch isolated state; merge in declared order; error modes; first-success join | n8n's single-threaded "parallel"; graphon last-write-wins; Langflow's per-layer barrier | `graphon/src/graphon/engine/container_handler/builtin/iteration.py`; `langgraph/.../pregel/_algo.py` (`apply_writes`), `channels/named_barrier_value.py`, `channels/binop.py`; `n8n/packages/nodes-base/nodes/Merge/`, `n8n/packages/core/src/execution-engine/workflow-execute.ts` |
| **Loop container** (`nodes/loop.py`) | Dify/graphon Iteration + Loop nodes; Flowise Loop (max count); Power Automate "Until" caps; Langflow `max_iterations` guard | Container (not a back-edge); mandatory `max_iterations`; `$loop.item/index/previous`; per-iteration fresh scope; collect list/last | n8n back-edge loops (hard to resume, no cap) | `graphon/src/graphon/engine/container_handler/builtin/loop.py`, `graphon/src/graphon/nodes/loop/entities.py`; `n8n/packages/nodes-base/nodes/SplitInBatches/`; `langflow/src/lfx/src/lfx/graph/graph/base.py`, `runnable_vertices_manager.py` |
| **Code step** (`nodes/code.py`, `code_harness.py`) | Dify code node (`main(**inputs) -> dict`, declared outputs, graphon limits); n8n task runners (result via separate channel, print capture); dify-sandbox seccomp | Out-of-process sandbox; base64 source; nonce result frame; strict output validation; fail closed | Langflow in-process exec (CVE-2025-3248); Flowise NodeVM fallback; Dify's static result tag | `graphon/src/graphon/nodes/code/code_node.py`, `limits.py`; `dify/api/core/helper/code_executor/` (`template_transformer.py`); `n8n/packages/@n8n/task-runner-python/` (`task_executor.py`, `task_analyzer.py`, `import_validation.py`); `dify-sandbox/internal/core/runner/python/`, `internal/core/lib/python/add_seccomp.go` |
| **Sandbox hardening + warm pool** (`code-interpreter/`) | Windmill nsjail limits; dify-sandbox workers/queue; Activepieces warm engine + fresh isolate | Token auth, tenant binding, admission limits, read-only rootfs, no network; single-use pre-started containers | Windmill "dedicated workers" outside the jail (speed over safety) | `windmill/backend/windmill-worker/nsjail/`, `windmill-worker/src/python_executor.rs`; `dify-sandbox/conf/`, `internal/middleware/`; `activepieces/packages/server/engine/src/lib/core/code/`, `activepieces/docs/install/architecture/sandboxing.mdx` |
| **Webhooks in Pulse** (planned, P4) | n8n test vs live webhooks; Windmill scoped tokens + raw body; Activepieces `/sync` + handshake; Dify typed payload → variables; Standard Webhooks HMAC | Cheap checks first, HMAC over raw bytes, Listen test mode, `{{payload.x}}`, dedup (none of the refs do it), 429 | Parsing the body before verifying (Windmill, Activepieces); Langflow's uncapped, non-durable body | `n8n/packages/cli/src/webhooks/` (`live-webhooks.ts`, `test-webhooks.ts`, `webhook-request-handler.ts`), `n8n/packages/nodes-base/nodes/Webhook/`; `windmill/backend/windmill-api/src/triggers/http/handler.rs`; `activepieces/packages/server/api/src/app/webhooks/`; `dify/api/controllers/trigger/webhook.py`, `dify/api/services/trigger/webhook_service.py`; `langflow/src/backend/base/langflow/api/v1/endpoints.py` |

**Web-only findings** (no clone) to keep in mind:
- **Zapier:** paths run sequentially (10 branches × 3 levels); loop cap 500; Code step on Lambda with a 1 s – 2 min tier.
- **Make:** a router with a fallback route; no merge node.
- **Power Automate:** parallel branches joined via `runAfter`; Apply-to-each up to 50 concurrent; Until defaults to 60 (max 5000).
- **Sim Studio:** Parallel / Loop container blocks with results in order.
- **Temporal:** `patched()` and worker-versioning pinned / auto-upgrade.
- **Flowise:** NodeVM sandbox-escape CVEs.

### How the next session should research a remaining feature
- **Container UI** (Wizard + Visual Builder):
  - Read how Dify/Flowise/Sim render Iteration/Loop/Parallel as boxes on the canvas. Dify's web UI is not cloned yet: add `/web/app/components/workflow/nodes/iteration/`, `/web/app/components/workflow/nodes/loop/` and `/web/app/components/workflow/nodes/_base/` to the dify sparse checkout.
  - n8n canvas: add `/packages/frontend/editor-ui/src/components/canvas/` (check the actual path with `git ls-tree`).
  - React Flow sub-flows: `parentId`, `extent: "parent"`, group nodes.
  - Our current editor: `web/src/components/workflow-builder/` + `web/src/lib/workflows/serializer.ts`.
- **Webhooks:** the source paths in the table row above, plus `research/03-webhooks-versioning.md`, plus Pulse code (`backend/om/pulse/`, `backend/om/server/features/pulse/`, `backend/om/db/pulse.py`), plus the SCIM token pattern (`backend/om/server/scim/auth.py`).
- **Process:** before coding each feature, write a short "research notes" section into `docs/flow-nodes/research/` (what each reference does, what we adopt or avoid), then design, then implement step by step with tests.

## How it is built (for the review)

**Docs, read first:** `D:/llm/danswer_flow_wt/docs/flow-nodes/`
- `PROGRESS.md`: status per phase, test results, test stack.
- `DESIGN.md`: architecture, versioning, containers.
- `REFERENCE_STUDY.md` + `research/01-03`: what we adopted from Dify/graphon, LangGraph, n8n, Windmill and Activepieces.
- `OPERATIONS.md`: sandbox security settings, the run_function warm pool.

**Backend** `backend/om/workflows/`:
- **Node registry:**
  - `nodes/base.py`: `NodeTypeSpec` with runner, config model, capabilities, `prepare_step`, `present_output`, `upgrade_from_previous`.
  - `nodes/registry.py`: strict lookup by (type, version), upgrade chain, catalog.
  - `nodes/builtin.py`: the single place where node types are registered.
- **Node types (one module each):** `nodes/agent.py`, `router.py` (v1 + v2), `code.py` + `code_harness.py`, `parallel.py`, `loop.py`, `agent_tools.py`.
- **Engine:**
  - `sequential.py`: the coordinator (run lifecycle).
  - `blocks.py`: `run_block`, which dispatches through the registry.
  - `branches.py`: parallel branches in threads. Each branch gets an isolated `ScopedRunContext` and a `BufferedTrace`, results are merged in branch order, and the coordinator is the only writer to the DB and trace.
  - `state.py`: RunState, checkpoint v2, resume.
  - `graph.py`: immutable graph, definition JSON, content hash.
  - `inputs.py`: `resolve_reference` for `$step.output.path` and `$loop.item`.
  - `workflow_engine.py::run_workflow` dispatches on `WORKFLOW_ENGINE_V2` (default on; the legacy path is kept for one release).
- **Saving:** `saving.py` (validation via the registry, container rules, optimistic `expected_version`, restore); `versioning.py` (pin by content hash).
- **DB:**
  - `om/db/workflow.py`: upsert steps by `node_key`, `_link_parents`.
  - `om/db/workflow_version.py`.
  - Migration `alembic/versions/0002_workflow_nodes.py` (additive).
- **API:** `om/server/features/workflow/api.py`: node-types catalog/upgrade, versions list/get/restore, new step fields.
- **Sandbox:**
  - `code-interpreter/code-interpreter/app/`: auth token, tenant binding, hardening, `/v1/run_function` + warm pool.
  - Client: `backend/om/tools/tool_implementations/python/code_interpreter_client.py`.

**Frontend** `web/src/`:
- `lib/workflows/{nodeRegistry,useNodeTypes,serializer,editorModel,routerConfig,validation,configSchema,trace}.ts`
- `components/workflows/` (SchemaConfigForm, upgrade + version dialogs)
- `components/workflow-builder/nodeUi.tsx` + Generic/Router/Step panels + `NodeBadges.tsx`
- `refresh-pages/WorkflowEditorPage.tsx` (Wizard)
- `app/app/message/.../workflow/WorkflowStepRenderer.tsx` (timeline labels)

**Tests (all green at handover):**
- Backend unit: `tests/unit/om/workflows/` (374), including `nodes/test_*.py`.
- Golden old-vs-new engine: `tests/unit/om/workflows/engine_golden/` (116; run with `ENGINE_IMPL=v2` or `legacy`).
- DB: `tests/external_dependency_unit/workflow/test_workflow_saving_db.py` (19) and `test_code_node_sandbox.py` (7).
- Live E2E scripts (run inside `flowdev-flow_api-1`): `D:/tmp/flow_api_smoke.py` (19), `flow_e2e_code.py` (15), `flow_e2e_parallel.py` (10), `flow_e2e_loop.py` (9).
- Browser: `D:/tmp/flow_preview_browser.py` (21; Playwright, Chrome 1194).
- Web: jest `src/lib/workflows src/components/workflows src/components/workflow-builder` (61), tsc 0 errors.
- Migration-safety suite (snapshot recaptured).

**Test stack (isolated):**
- **flow_api** on 8091 and **flow_web** on 3091 (`deployment/docker_compose/docker-compose.flow-dev.yml`, project `flowdev`, env `D:/tmp/flowdev.env`).
- Sandbox `flowdev-code-interpreter` (image `om/code-interpreter:flowtest-p1b`, executor `om/python-executor-sci:flowtest`, token in `D:/tmp/flowdev_ci_token.txt`).
- DB `flow_dev`.
- Test admin login in `D:/tmp/flow_preview_login.json`.

## Next steps, in order (after approval)

1. **Fix the agent-id-0 bug** (Wizard select + validation + jest). Also swap the demo's agents to a named agent, so the demo is clearer.
2. **Write `docs/flow-nodes/HANDOVER.md`** in the worktree: a copy of the "explained from the UI", "where the ideas came from" and "how it is built" sections above. Write `research/00-platform-survey.md` (the 11-platform web survey). Update `PROGRESS.md`. Save a memory pointer to HANDOVER.md.
3. **Container UI** (gap #1), so users can build parallel/loop without JSON:
   - **Wizard:** each step gets a "Run inside" dropdown (top level or a Parallel/Loop step) plus a "Branch" dropdown (parallel only). Children render indented under their container. The Parallel/Loop config form gets proper fields (branch labels list; loop mode/items/condition/max/collect). Code inputs/outputs editors replace the "edit via JSON" note.
   - **Visual builder:** Parallel/Loop render as React Flow group nodes (`parentId`, `extent:"parent"`). Drag a node into or out of a group to set `parent_key`, and a branch lane sets `branch_index`. Use a layered layout (dagre) instead of the grid.
   - Both go through the shared `serializer.ts` and `validation.ts` (dual-editor rule).
   - **Tests:** jest (serializer/validation round-trip with containers); browser test that builds the demo from the UI in both editors, saves, reloads and runs.
4. **Webhook triggers in Pulse (P4)**, as designed in DESIGN.md / REFERENCE_STUDY W1–W5:
   - migration `0003_pulse_webhooks`;
   - public `POST /hooks/{token}` (cheap checks first, HMAC over the raw body, dedup, 429, size cap);
   - Listen test mode; `{{payload.x}}` templates;
   - a Webhooks tab in Pulse;
   - tests.
5. **Multi-agent review** (correctness, security, UX) of the whole branch, then fixes, `graphify update .`, final docs, and cleanup of the test stack.
6. **Commit** only when the user asks (local branch commits; never push).

## Verification for the next session
- Re-run the suites listed above (commands in `PROGRESS.md` → "Test stack").
- The browser test must also cover:
  - editing workflow 76 in the Wizard past step 2 without errors (agent 0);
  - building a parallel + loop workflow from the UI.


## Session log
- 2026-10-30: research (web + code-level clones), P0 foundation, track H security, P1 code node (+P1b warm pool),
  P2 parallel, P3 loop, frontend P0, preview stack + browser smoke 21/21. Handover written mid-way through the
  "dedicated agents" fix.
