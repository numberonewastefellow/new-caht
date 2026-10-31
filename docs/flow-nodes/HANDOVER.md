# Flow nodes — HANDOVER (read this first)

Last updated: 2026-10-31. **Work now lives in the main checkout `D:/llm/danswer20022026` on branch
`main_multi_agent_stable`.** It was developed on `feature/flow-nodes` (worktree `D:/llm/danswer_flow_wt`, both now
removed) and merged locally in commit `3b2074ed3` (user's commits `88eb334e5` "flow-wise" + `e36f48d15`
"Create flowdev.bat"). **Not pushed.** Rules: commit only when the user asks; never push; explicit `git add`
paths (the repo is public); never run the alembic CLI. Other uncommitted work by the user/other agents lives in this
checkout too — touch only flow-nodes files.

Companion docs in this folder: `PROGRESS.md` (status + test stack), `DESIGN.md` (architecture),
`REFERENCE_STUDY.md` + `research/` (where ideas came from), `OPERATIONS.md` (sandbox settings).

## What the user asked for
Parallel branches, loops, Python code steps and webhook triggers for workflows (Langflow/n8n/Dify-level
flexibility), **easy to extend and upgradeable**, built step by step with readable, industry-standard code,
plus security hardening of the code sandbox. Old workflows must keep working.

## ▶ CURRENT STATUS — resume here
**Work from [TODO.md](TODO.md), top to bottom, one item at a time.** Details and evidence: [FIX_PLAN.md](FIX_PLAN.md). The table below is the summary per step.

| Step | What | Status |
|---|---|---|
| 1 | Steps use dedicated agents (save + run rule) | **Code done, uncommitted; verified on the main stack (below). OPEN: the user's look at the timeline and the Wizard.** |
| 2 | Safe saves, same errors in backend and frontend, `llm_decision` core fix | Done except the user's screen check of 2f. See below. |
| 3 | Container UI + full config editing (both editors) | Not started |
| 4 | Run display: fork/join in the trace and timeline | Not started |
| 5 | Webhook triggers in Pulse (P4) | Not started |
| 6 | Engine hardening (concurrency cap, cancel, retry, error kinds, loop, checkpoints) | Not started |
| 7 | Rollout readiness, review, docs, cleanup | Not started |

**User decisions for this plan (2026-10-31):** dedicated agents only (agent 0 and wrapper agents rejected at save and at
run); publishing a workflow grants access to its step agents; order = Steps 1–2, container UI, trace, webhooks, hardening.

**Step 1 as built:**
- `backend/om/workflows/nodes/agent.py`: `load_step_agent()` + `UnusableStepAgentError` are the one rule, used by
  `prepare_agent_step_v1` (save), `AgentToolCache` (run: the step FAILS) and `workflow_engine._build_agent_tools`
  (`llm_decision`: the step isn't offered to the orchestrator, and a warning is logged).
- A deleted agent now fails the run instead of being skipped (`fx_deleted_agent` in `ALLOWED_DIFFS`). Real DB: 0 of 277
  steps were on agent 0, a wrapper or a deleted agent.
- `AgentTool` no longer falls back to the first user in the DB (every workflow path passes the running user).
- Frontend: `lib/workflows/stepAgents.ts` (pickers), `validation.ts`, same error wording as the backend.
- Tests: `tests/unit/om/workflows/nodes/test_step_agents.py`, DB test cases, jest `stepAgents.test.ts` + `validation.test.ts`.
- Results: unit + pulse 391 (v2), goldens legacy 116, DB 28, jest 65, tsc clean, live smoke 21, code 15, parallel 10, loop 9
  (all on the former preview). Browser 16/23: the 7 failures were the chat run and its dependants, with the sandbox stopped.

**Step 1 verified on the main stack (2026-10-31), port 3000, real DB:**
| Check | Result | Script (in `D:/tmp`, `docker cp` into `virtualai-api_server-1:/tmp`; lost on API restart) |
|---|---|---|
| Sandbox: token required, no network, read-only root, uid 65532, code step, chat Python tool | 9/9; code step 0.17 s, `run_function` p50 171 ms | `main_sandbox_check.py` |
| Old data loads, read-only | 49 workflows, 284 steps, 0 problems; 114 paused: 66 of 67 sequential resumable, 1 restarts with what the user said, 47 `llm_decision` on their unchanged path | `main_dry_run.py` |
| Demo run through the API + agent-rule rejections | 22/22; 11.8 s; parallel step 3.7 s vs 5.9 s serial; pinned to version 1; temporary key removed | `main_demo_e2e.py` |
| Suites | unit + pulse 391, goldens legacy 116, jest 65; `tsc`: only the 2 known `dotenv` errors in Playwright configs | see FIX_PLAN "Verification" |
| User's chat runs of the demo | 3 runs, all `completed` | executions 510, 512, 513 of workflow 49 |

**Found while testing, not fixed:**
- The API logs `ERROR ... provider.py: No active trace ... Returning NoOpSpan` about once per agent call during demo runs (one run had none). Runs complete. It may mean LLM spans don't reach Phoenix/Langfuse for these steps. Cause not established, and not known whether it predates flow nodes. Look at it under Step 7 (observability).
- `dev.bat` has no `code-interpreter` shortcut, so `dev.bat build code-interpreter` silently does nothing. Use `docker compose -f docker-compose.yml -f docker-compose.dev-windows.yml build code-interpreter`, then `up -d --no-deps code-interpreter`; the executor image is `docker build -t om/python-executor-sci:latest -f code-interpreter\executor\Dockerfile code-interpreter\executor`.

**Step 2 as built (2026-10-31). Real-DB backup first: `D:/llm/backups/virtualai_postgres_before_flow_step2_20261031_095036.dump`.**
- **Core bug fixed: an `llm_decision` orchestrator never saw what its agents returned.** Results were stored as tool responses with no `tool_call_id`, and `construct_message_history` drops those, so the orchestrator delegated blind, repeated calls, and could imitate the JSON-text calls as its "final answer". The drop dates from 2026-02-18, so this affected every `llm_decision` run so far, not flow nodes. Fix: `om/workflows/orchestrator_history.py` stores real linked calls; old paused checkpoints upgrade on read; a call waiting for the user is removed on resume because resuming records it again.
  - Evidence: Customer Support Triage went from 6 calls and a raw-JSON answer to 1 call to Billing and a real answer. Patient Intake ran pause → reply → Triage → Diagnosis → Care Navigator. 48/48 real paused runs build a valid request (`D:/tmp/main_paused_history_check.py`). Cybercrime 5/5, Medical P1 pass (`D:/tmp/main_regression.sh`). Only `orchestrator_history` and the LLM-input history changed across 41 goldens.
  - Not yet run after this fix: the other 26 `llm_decision` workflows and the rest of their suites. If one fails, upgrade that workflow; no fallbacks (user's rule).
- **Saves:** one transaction with a row lock (`get_workflow_for_update`); a stale save is 409; the definition being replaced is snapshotted first, so old workflows keep a restorable "before" version. `save_workflow_update`, `_snapshot_current_definition`.
- **Rules:** duplicate `output_key` and reserved `loop` / `user_input` are refused on save. Frontend mirrors the backend: `lib/workflows/containerRules.ts`, `nodeConfigRules.ts`.
- **Version on `llm_decision` runs:** recorded for history. These runs still execute and resume on the live steps, not the pinned definition (follow-up in TODO).
- **Editors:** shared `StepOptionsSection`, `workflowLimits.ts`.

## Building / running — use `dev.bat` (`flowdev.bat` is retired)
**The user's decision, 2026-10-31: do NOT use `flowdev.bat` or the `flowdev` containers.** They existed for the separate
worktree. Everything now runs on the main stack (port 3000), `deployment\docker_compose\dev.bat`.

**State of the main stack (checked 2026-10-31 after the user's rebuild):**
- Migration `0002_workflow_nodes` applied to the real DB; 277/277 steps have a `node_key`; 48 workflows intact.
- API runs this code; `WORKFLOW_ENGINE_V2` is on by default; `CODE_INTERPRETER_API_TOKEN` is set on the API and sandbox.
- Demo created on the real DB: workflow 49 "Demo: Trip planner (code + parallel + loop)", wrapper agent 481, step agents
  478 "Demo: Travel researcher", 479 "Demo: Stay researcher", 480 "Demo: Day planner" (`D:/tmp/main_demo_seed.py`).
- `virtualai-code-interpreter-1` and the executor image are rebuilt: track H (auth, tenant binding, read-only sandbox) and the warm pool are live. Rollback image: `om/code-interpreter:pre-flow`.
- Host port of the code interpreter is now `127.0.0.1:8001` (the user's change; the Windows port proxy holds 8000).

**Testing on the main stack:** the `D:/tmp/flow_e2e_*.py` and browser scripts target the old preview. They create and
delete data, so don't point them at the real DB without asking the user.

## What was built — explained from the UI

On the main stack, `http://localhost:3000`:

| Where in the UI | What you can do now | Status |
|---|---|---|
| Admin → Workflows → **Edit** (Wizard), Step Type dropdown | Choose **Agent, Code, Condition**; Parallel/Loop also listed | Code step shows a Python box + inputs/outputs; Condition picks branch targets by step name. |
| Wizard / **Visual** builder | Steps inside a container show a badge "In <container> · branch N"; the container shows "Contains N steps" | **No control yet to put a step inside a Parallel/Loop** → containers can only be built via API/JSON today (gap #1). |
| Visual builder → **Utils** palette | Lists Code, Parallel, Loop, Condition (from the server catalog `GET /workflow/node-types`) | A new backend node type appears automatically. |
| **Versions** button (both editors) | History of every save, view a version, **restore** | Every save = immutable version; runs are pinned to the version they started on. |
| "Upgrade available" badge on a node | Opt-in upgrade of a node's config to a newer node version (diff preview) | e.g. old Condition v1 → v2. |
| Chat (agent "Demo: Trip planner…", workflow 49 on the main stack) | Ask "a 3 day trip to Goa" | The timeline shows "Code: Read the request" → "Parallel: Research in parallel" (2 branches at once) → "Loop: Plan each day" (1/3, 2/3, 3/3) → a formatted answer. |
| Admin → Pulse | Unchanged | Webhooks not built yet (gap #2). |

## Where the ideas came from (read before reviewing or extending)

**Research trail:**
1. Web survey of 11 platforms (2026-10-30): n8n, Langflow, Dify, Flowise, Zapier, Make, Power Automate/Copilot Studio, LangGraph, Activepieces, Windmill, Temporal (+ Sim Studio, Node-RED).
2. Code-level study of local clones.
3. Design deltas, approved by the user.

**Written up in** `D:/llm/danswer20022026/docs/flow-nodes/`:
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

**Docs, read first:** `D:/llm/danswer20022026/docs/flow-nodes/`
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

## Verification for the next session
Commands are in `PROGRESS.md` ("Test stack": unit, mypy) and FIX_PLAN.md ("Verification").

## Session log
- 2026-10-31 (later): sandbox service rebuilt on the main stack; Step 1 verified there (results above).
- 2026-10-31 (later): user rejected "just fix it" and asked for a design-vs-code analysis first; result + plan in
  `FIX_PLAN.md`. Step 1 built. User rebuilt the main stack with `dev.bat` and retired `flowdev.bat`. Demo created on the
  real DB. Found the main code-interpreter image was not rebuilt.
- 2026-10-31: user committed the branch (88eb334e5, e36f48d15); merged into `main_multi_agent_stable` (3b2074ed3, not pushed);
  worktree + branch removed; preview re-pointed at the main checkout; added `flowdev.bat`.
- 2026-10-30: research (web + code-level clones), P0 foundation, track H security, P1 code node (+P1b warm pool),
  P2 parallel, P3 loop, frontend P0, preview stack + browser smoke 21/21. Handover written mid-way through the
  "dedicated agents" fix.
