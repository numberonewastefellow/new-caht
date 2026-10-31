# Flow nodes: parallel, loops, code nodes, webhook triggers. Progress tracker

> **Current plan and step status: [FIX_PLAN.md](FIX_PLAN.md) + the status table in [HANDOVER.md](HANDOVER.md).** The sections below are per-phase history.

> **New session? Read [HANDOVER.md](HANDOVER.md) first** — it has the in-progress task, what was built (UI + code), where the ideas came from (framework source paths) and the next steps.

> **Read this first in every new session. Update it at the end of every session.**
> Approved plan: `C:/Users/Pandu/.claude/plans/witty-orbiting-bunny.md`. Design and decisions go in `DESIGN.md`; code-level research goes in `REFERENCE_STUDY.md`.

## Ground rules
- **Where:** main checkout `D:/llm/danswer20022026`, branch `main_multi_agent_stable` (developed on `feature/flow-nodes` from fe6a6b054; merged locally in 3b2074ed3 on 2026-10-31, not pushed; worktree + branch removed).
- **Git:** local commits only, NEVER push. Use explicit `git add <paths>` because the repo is public.
- **Run on the main stack with `dev.bat`.** `flowdev.bat` and the `flowdev` containers are retired (user's decision, 2026-10-31). Don't start or stop the main stack without asking.
- **Migrations:** the chain is `0001_om_baseline → 0002_workflow_nodes → 0003_user_ui_preferences → 0004_pulse_triggers`. Never run the alembic CLI.
- **Dual-editor rule:** Wizard and Visual Builder change together, through one shared registry and serializer.
- **Reference clones:** `D:/llm/reference-frameworks/`. Read only, untrusted, never built.
  - n8n, Windmill and Dify are clean-room only: no code is copied from them.

## User decisions (2026-10-30)
- Containers (Parallel and Loop nodes holding child steps), not the `parallel_group` integer.
- New branch and worktree.
- Code nodes are Python-only in v1, on the existing code-interpreter sandbox.
- Webhooks live in Pulse: tabs Schedules | Webhooks.
- Build foundation first: R → P0 → P1 code → P2 parallel → P3 loop, with P4 webhooks alongside after P0.
- Do a code-level reference study (LangGraph, Dify + dify-sandbox, n8n, Windmill, Activepieces, Langflow) before coding.

## Working rules from the user (2026-10-30)
- Code must be **readable, extensible and industry standard**: small single-purpose modules, typed Pydantic models and type hints, one interface per node type, matching the surrounding style.
- **Implement step by step.** Finish and test one module before moving on. **Don't jump between modules by mistake.**
- P0 backend order: registry → graph → state → runners → engine coordinator → DB/migration/save → API → frontend.
- Parallel agents only on clearly separate modules. H covers only the code-interpreter and its client; the golden harness only adds tests.

## User decisions after the reference study (2026-10-30)
- **Security is part of this work.** Hardening track **H**, the code-interpreter fixes, ships with this feature.
  - Reuse the existing API-key code (`om/auth/api_key.py`: `secrets.token_urlsafe` generator, SHA-256 hash, constant-time compare, Bearer parsing) for the service token.
  - Our DB API keys themselves can't be used: the code-interpreter has no DB, and those keys are user identities.
  - The token is `CODE_INTERPRETER_API_TOKEN`, shared by the backend and the service. The service **fails closed** (rejects `/v1/*`) when no token is set, unless `CODE_INTERPRETER_ALLOW_UNAUTHENTICATED=true` (dev only).
  - The backend sends `X-OM-Tenant`. Sessions and files are bound to the tenant, and the global file listing is removed.
- **Engine style: Dify / graphon** (Apache-2.0, so it can be studied directly; credit it when a pattern is adopted).
  - One coordinator (dispatcher) thread.
  - A bounded worker pool with a sliding window.
  - Containers give up their worker slot while their children run.
  - Fix graphon's known weaknesses using LangGraph and other references: no retry sleep on the coordinator; deterministic ordered merge instead of last-write-wins; reject duplicate keys.
- **Version history only.** Every save creates an immutable version and every run pins one. No draft/publish step.
- **Code node speed:** yes, P1b. Add `run_function` and a warm pool of single-use containers.

## Status
| Phase | Status |
|---|---|
| R: reference study | **DONE. Design deltas are with the user for decisions.** Write-up: `REFERENCE_STUDY.md` + `research/01..03`. Deltas: E1–E9 (engine), V1–V3 (versioning), C1–C5 (code), W1–W5 (webhooks), plus new hardening track H |
| H: code-interpreter hardening | ✅ DONE (agent). Bearer token (`CODE_INTERPRETER_API_TOKEN`, fail-closed 503, dev override), `X-OM-Tenant` binding, global file listing removed, worker/queue limiter. Docker: read-only, uid 65532, 128 MB workspace, `--cpus`. K8s: SA token off, seccomp RuntimeDefault, ro rootfs, deny-all egress NetworkPolicy, stdin EOF fix. Compose: token passed to all services, port bound to 127.0.0.1, `dev.bat` generates the token. Lean executor image (2.81 → 2.0 GB). Tests: interpreter 85/85 (29 security), live E2E 26/26, client 12/12; pre-existing failures identical to HEAD. Docs: `OPERATIONS.md`. **Breaking on deploy: all services must share the token.** Deferred: gVisor, custom seccomp profile, parent helm chart render. Pre-existing: `import cv2` needs libGL; worktree `entrypoint.sh` has CRLF. |
| P0: foundation (registry, engine runners, node_key, pinning, shared serializer) | IN PROGRESS. Done: ✅ 1 registry (`nodes/base.py`, `nodes/registry.py`, 17 tests); ✅ 2 data model (ORM + `0002_workflow_nodes`, applied to `flow_dev` via the API start command: 277/277 steps backfilled, main DB untouched); ✅ 3 graph (`graph.py`, 12 tests); ✅ 4 state (`state.py`: RunState/TurnCursor/RunContext/restore_run_state, checkpoint v2 fields, 13 tests); ✅ 5 runners (`nodes/agent.py`, `nodes/router.py` v1+v2+upgrade, `nodes/agent_tools.py`, `nodes/builtin.py`; shared helpers moved to `agent_streaming.py`/`hitl.py`/`inputs.py`; 14 tests; 56 total); ✅ 6 coordinator (`sequential.py`; `run_workflow()` dispatches on `WORKFLOW_ENGINE_V2` (default on; app_configs); helpers moved out of `workflow_engine.py` with aliases, legacy path unchanged). **Golden harness: legacy 116/116, v2 116/116**: 111 identical, 5 intentional fixes in `ALLOWED_DIFFS` (timeout status, step overrides, router skip on resume, duplicate output_key, edit-while-paused restarts with everything the user said). Unit 153/153. ✅ 7 save/versions: `db/workflow.py` upsert by node_key (stable ids, temp re-order); `db/workflow_version.py`; `workflows/versioning.py` (pin by content hash with savepoint retry; resume uses the pinned definition); `workflows/saving.py` (registry-driven `prepare_steps` via per-type `prepare_step` hooks, mode checks, optimistic `expected_version`, restore); router v2 accepts legacy `condition` and mirrors it for the legacy engine. DB tests 12/12 on `flow_dev` (caught the agent-id-0 bug). Unit 269/269, goldens legacy+v2 116/116. ✅ 8 API (`server/features/workflow/api.py`): create/update via `saving.py` (400 invalid, 409 stale `expected_version`); step responses gain `node_key`/`type_version`/`latest_type_version`/`upgrade_available`/`config`; workflow `version`/`schema_version`; `GET /workflow/node-types`, `POST /workflow/node-types/{type}/upgrade`, `GET /workflow/{id}/versions[/{n}]`, `POST /admin/workflow/{id}/versions/{n}/restore`. Fixed pre-existing: `WorkflowExecutionResponse.chat_session_id` was typed int (it's a UUID) and `StepExecutionRecord` ids are now nullable. Live API smoke on flowdev 19/19 (`D:/tmp/flow_api_smoke.py`, mints and removes a temporary admin key). Migration-safety 34/34 (snapshot recaptured: +16 modules, none removed). mypy clean on new modules (4 errors in legacy `workflow_engine.py` code are pre-existing and identical on main). ✅ 9 frontend (agent): `web/src/lib/workflows/{nodeRegistry,useNodeTypes,serializer,editorModel,routerConfig,validation,configSchema,trace}.ts`, `components/workflows/{SchemaConfigForm,upgrade dialog,version history}`, Visual Builder `nodeUi.tsx` + Generic/Router/Step config panels + badges, Wizard on the shared serializer (bug 2 fixed), router edges → node keys (bug 1 fixed), `expected_version`, Versions modal, trace fallback node. tsc 0 errors, jest 61/61 new (7 pre-existing slow-typing timeouts in CustomForm.test unrelated). NOT yet browser-tested; containers shown as badges (group-node UI pending). |
| P1: code node | 🔶 P1a DONE: `nodes/code.py` (`code` v1: config with code/inputs/outputs/timeout 1-30s; save validates with `ast.parse` only and never executes; runner resolves `$step.output.path` inputs via `inputs.resolve_reference`); `nodes/code_harness.py` (base64 source, stdout saved before user code, prints captured, single nonce frame; graphon-style output validation); generic trace `step` node (`TraceNode.node_type`); switch `WORKFLOW_CODE_NODE_ENABLED`; fails closed without a sandbox. Tests: unit 130/130 (harness runs in a subprocess: forgery, template injection, NaN, SystemExit), real hardened sandbox 7/7 (`tests/external_dependency_unit/workflow/test_code_node_sandbox.py`: network blocked, read-only fs, time limit), API E2E 15/15 incl. a live LLM agent → code step (`D:/tmp/flow_e2e_code.py`). Goldens regenerated for the trace schema addition only (proved: 113 files differ only by `node_type: null`); legacy+v2 116/116. ✅ P1b (agent): `POST /v1/run_function` (fresh hardened single-use sandbox; optional out-of-band result file) + Docker warm pool (`RUN_FUNCTION_POOL_MIN/MAX/TTL_SEC/ENABLED`; destroy after use, refill, TTL, orphan cleanup, cold fallback); configurable `PYTHON_EXECUTOR_DOCKER_TAG`; client `run_function()` + `RunFunctionUnsupportedError`; K8s answers 501. 71 service tests, 24 client tests, live isolation checks. **Latency: warm p50 123 ms (real harness ~180 ms) vs /v1/execute ~780 ms.** The code node now uses run_function and falls back to execute (unit 22/22, real sandbox 7/7 in 4.8 s vs 8.9 s, E2E 15/15). |
| P2: parallel container | 🔶 BACKEND DONE. Steps: (0) trace persistence moved onto `RunContext.persist_trace` (branch contexts no-op it); (1) graph containers: `WorkflowNode.parent_key/branch_index`, `top_level()`, `branches()`, `depth()`, structural validation; (2) saving: `parent_key`/`branch_index` in payload/response, generic container rules in `saving._check_containers` (parent must be `is_container`, depth ≤3, ≤100 steps, no pause/promote/terminal inside), router targets same block, DB `_link_parents` (kept children detached before deleting a container, so no cascade loss); (3) `blocks.py` (run_block, shared) + `branches.py` (BranchRunContext isolation: deep-copied context, own session/emitter/agent cache, no sandbox session, BufferedTrace replayed at join; bounded pool; one event queue; coordinator-only DB/trace; per-branch turn range `BRANCH_TURN_STRIDE`; ordered merge; cancel event); (4) `nodes/parallel.py` (`parallel` v1: branches/labels, join wait_all|first_success, on_branch_error fail|continue, max_concurrency; output JSON {label: last output}; no parallel-in-parallel). Tests: unit 15/15 stable ×4 (concurrency, cap, order, isolation, errors, first_success, cancel, trace replay); DB 19/19 incl container save rules; LIVE E2E 10/10 (`D:/tmp/flow_e2e_parallel.py`: 2 code branches + live LLM agent branch ran concurrently, parallel step ≈ slowest branch); unit total 351, goldens v2 116/116, mypy clean. NEXT: container UI (React Flow group nodes) after the frontend P0 step; trace fork/join edges. |
| P3: loop container | 🔶 BACKEND DONE (unit). `nodes/loop.py` (`loop` v1: for_each over a $reference JSON list or lines | while (router condition operators, checked before each iteration); mandatory max_iterations ≤50; collect list|last; `$loop.item/index/previous` as typed `RunState.variables` for code steps and as text for agent mappings; each iteration is a fresh `ScopedRunContext` on the coordinator thread; iteration marker rows; the last iteration's body outputs are merged). Resolver accepts `$name.<path>`. Fixed: scoped states now inherit the run's `started_at` (the workflow timeout was measured per branch). Unit 17/17; total unit 370, goldens v2 116/116, mypy clean (4 pre-existing legacy errors). LIVE E2E 9/9 (`D:/tmp/flow_e2e_loop.py`: for_each with code + live agent body over 3 items, per-iteration items correct, results collected; while stops by index; collect last). NEXT: container UI. |
| P4: webhooks in Pulse | not started |

## Old workflows: migration plan
**Live data snapshot** (main DB, read-only count, 2026-10-30):
- 48 workflows, 277 steps;
- **0 router steps**;
- 0 duplicate `output_key`s;
- 29 `llm_decision` workflows;
- 476 executions, of which **102 are `paused`**.

The 47 template JSONs contain no routers either.

**Decision: no forced rewrite of old workflows. An additive DB migration plus a lazy, versioned upgrade.**
1. **Migration `0002_workflow_nodes`** (automatic on backend start) only adds and backfills:
   - `node_key = 's' || id`, `type_version = 1`, `config = NULL`, `parent_step_id = NULL`;
   - `AgentWorkflow.version = 1`, `schema_version = 1`;
   - nullable snapshot columns on `workflow_execution`.

   Old rows keep every legacy column. The `agent` v1 and `router` v1 node specs read them through `load_config`.
2. **Behaviour pinned by `schema_version = 1`.** Old workflows keep their exact current semantics, including the old `$key` substitution.
   - New or explicitly upgraded workflows get `schema_version = 2`: safe tokenizer and `$key.output.<path>`.
   - An "Upgrade workflow" button shows what changes before applying it.
3. **Routers:** v1 configs (`true_steps`/`false_steps` as step orders) are converted to `node_key`s by a migrate function when the workflow is saved or upgraded.
   - The live DB has 0 routers, so this is low risk, but the converter is covered by tests.
4. **Paused runs (102):** checkpoint v1 is read through an id-to-key map, so existing paused runs can still be resumed after the upgrade.
   - Runs paused before the migration have no definition snapshot. They resume against the current definition, the same as today.
   - If their step ids are gone, they fail with a clear "workflow changed since this run paused" message instead of silently running wrong steps.
5. **llm_decision workflows (29):** untouched apart from new save-time validation. Containers are rejected in this mode.
6. **Dry-run report** before rollout: a script loads every live workflow through the new graph builder and writes a report. For each workflow it checks:
   - it loads;
   - its step order is identical;
   - it re-serializes with no changes;
   - its paused checkpoints map to keys.

   It writes nothing. It runs against a cloned DB.

## Test plan: old and new workflows
**Old workflows (backward-compatibility gate; P0 cannot merge until all pass):**
- **Golden packet streams:**
  - every one of the 47 templates is run through the OLD engine and the NEW engine with a fake AgentTool, a fixed seed and canned outputs;
  - the packet sequence must be identical: type, placement, step order, final answer, files.
  - Bug fixes that intentionally change behaviour (e.g. sequential overrides) are listed as allowed differences.
- **Extra fixtures for paths no template exercises:**
  - router true/false and nested skips;
  - HITL pause → resume, and pause → edit workflow → resume;
  - stop/cancel;
  - timeout (must now report failed);
  - `promote_output`, `is_terminal`, duplicate `output_key`.
- **Live-DB dry run:** the migration-report script above, run against a clone of the real DB (48 workflows, 102 paused checkpoints).
- **Migration tests:** `0002` upgrade and downgrade on a baseline DB, plus the migration-safety snapshot suite.
- **Editor round-trip:** for each template, the snapshot is loaded into both the Visual Builder and the Wizard serializer, then saved. The payload must be identical (jest), which catches the lost-override and router-renumber bugs.
- **Live regression on the test stack:**
  - Travel Planner, Medical Diagnosis, Discussion Panel (HITL) and one `llm_decision` workflow;
  - selected existing suites (`test_medical_diagnosis.py`, `test_discussion_workflow.py`, one gov-dept `test_<dept>.py`).

**New workflows (per phase):**
- **Unit:**
  - registry and versioning: unknown version rejected, migrate chain, upgrade flag;
  - each runner with fake agents.
- **Engine scenarios:**
  - parallel: wait-all, first-success, branch error fail/continue, cancel mid-branch, concurrency limit, packet tabs, deterministic merge order;
  - loop: for-each, while, max-iterations cap, collect list/last, `$loop.*` variables;
  - code node: harness spoofing, timeout, out of memory, bad output type, fail-closed with no sandbox.
- **API:**
  - save/validate rules: containers rejected in `llm_decision`, nesting depth limit, `can_request_input` not allowed inside containers;
  - catalog and migrate endpoints.
- **Webhooks:**
  - valid and invalid HMAC, replay window, dedup, 429, size cap, uniform 404, cross-tenant token, runs as owner, admin view.
- **Template JSONs** for each new node type (e.g. Travel Planner with parallel Flight + Hotel, a for-each research loop, a code transform), deployed with `create_workflows.py` and run in chat.
- **Browser (Playwright):** build in both editors → save → reload → run → timeline and trace show the branches/iterations correctly.

## ⚠️ Existing security findings (pre-existing, outside this feature; reported to the user, not fixed)
- **The code-interpreter API has no auth on `/v1/*`.** `GET /v1/files` lists every tenant's files, and session ids aren't bound to a tenant.
- **`docker-compose.dev-windows.yml` publishes it on `0.0.0.0:8000`**, so anyone on the LAN can call it. That includes running code (inside the network-less sandbox) and listing or reading files.
- **K8s executor pods have unrestricted egress**, and they have no seccomp profile and no read-only root filesystem.
- Details are in `research/02-sandboxes.md`. The proposed fix is a service token plus tenant binding, and binding the port to 127.0.0.1. This is the user's decision: either a separate hardening track or part of P1.

## Test stack (isolated) — RETIRED, kept for history
- DB `flow_dev`: a clone of the main DB in `virtualai-relational_db-1`.
- Env file: `D:/tmp/flowdev.env` (NOT in git; Redis DBs 5/13/14).
- Start (applies migrations to `flow_dev` only):
  `FLOWDEV_ENV_FILE=D:/tmp/flowdev.env docker compose -p flowdev -f deployment/docker_compose/docker-compose.flow-dev.yml up -d`
  It listens on `127.0.0.1:8091`.
- Unit tests: `docker run --rm -v "D:\llm\danswer20022026\backend:/app" -w /app om/om-backend:latest python -m pytest <path> -q -p no:cacheprovider` (Git Bash: `MSYS_NO_PATHCONV=1`).
- mypy: add `-v "D:\tmp\flow_mypy_cache:/mypycache"` and run `python -m mypy <paths> --cache-dir /mypycache --follow-imports=silent --ignore-missing-imports`.
- **Cleanup when done:** `docker compose -p flowdev ... down`, then `dropdb flow_dev`.

## Test sandbox (isolated) — RETIRED, kept for history
- Container `flowdev-code-interpreter` (image `om/code-interpreter:flowtest`, executor `om/python-executor-sci-flowtest:latest` = hardened image retagged so the main `om/python-executor-sci:latest` is untouched), on network `virtualai_default`.
- Token in `D:/tmp/flowdev_ci_token.txt` (not in git); `D:/tmp/flowdev.env` points the flow API at it.
- **Cleanup when done:** `docker rm -f flowdev-code-interpreter`, `docker rmi om/python-executor-sci-flowtest:latest`.

## Preview UI (isolated) — RETIRED, kept for history
- `http://localhost:3091`: web from this branch (`om/om-web-server:flowdev`), compose service `flow_web` (`OVERRIDE_API_PRODUCTION=true`, `INTERNAL_URL=http://flow_api:8080`).
- Login: your own account works (flow_dev is a copy of your DB). Test admin creds are in `D:/tmp/flow_preview_login.json` (not in git).
- Demo workflow #76 "Demo: Trip planner (code + parallel + loop)" (wrapper agent 487).
- Browser smoke: `python D:/tmp/flow_preview_browser.py` (Playwright, screenshots in `D:/tmp/flow_preview_shots/`).
- Findings: the editors, palette (Code/Parallel/Loop/Condition), Versions and wizard code editor work, and the chat run executes live. Fixed: timeline labelled non-agent steps "Agent" (`WorkflowStepRenderer.workflowStepLabel`), and the `WorkflowStepStart` TS type lacked `step_type`.
- Browser smoke **21/21** (login, list, visual, palette, Versions, wizard, live chat run of demo #76 to completion, timeline labels, final answer). Fixed: the final answer showed raw JSON for code/parallel/loop outputs; nodes now declare `NodeTypeSpec.present_output` (`present_json_output`: a single string field is shown as text, otherwise formatted JSON). Unit 374, goldens v2 116/116.

## Session log
- **2026-10-30:** plan approved; worktree created; live-DB migration sizing done; reference clones started.
