# Flow nodes: TODO

**Where we are:** everything through item 4 is built, self-reviewed, tested in a real browser and live on port 3000. Webhooks (5) is with another agent (branch `feature/pulse-webhooks`). **Item 6 is deferred by the user (2026-10-31).** **Final review done 2026-11-01; findings below are not fixed: the user asked for review only.** The webhook work (5) is in this checkout, and the other agent is testing it.

Work top to bottom, one item at a time: implement, test, check on screen, tick, add a progress line. Why each item exists: [FIX_PLAN.md](FIX_PLAN.md) (evidence) and the plan review in the progress log below.

**Rules:**
- Commit only when the user asks; never push; explicit `git add` paths; never run the alembic CLI; keep both editors in sync.
- **No workarounds (user, 2026-10-31):** if an existing workflow fails, upgrade that workflow; don't add fallbacks. Back up first; backups are in `D:/llm/backups/`.
- Keep it simple, in small modules.
- **Verify the goal, not just `completed`:** read what agents actually received and answered. A completed run can still be wrong.

**Testing setup:**
- Main stack with `dev.bat`. `flowdev.bat` and the `flowdev` containers are retired.
- Backend code is bind-mounted: `dev.bat restart api background`. Pulse: `dev.bat build pulse`. Web: `dev.bat build web`.
- DB tests use the `flow_dev` database (env file `D:/tmp/flowdev.env`), never the real DB. Point the sandbox tests at `CODE_INTERPRETER_BASE_URL=http://code-interpreter:8000` with the token from `.env`.
- Live checks use throwaway keys, scripts in `D:/tmp`: `main_agent_flow.py`, `main_demo_e2e.py`, `main_saves_e2e.py`, `main_regression.sh`.
- Screen checks: no test login exists on the real DB, so ask the user for a screenshot.

## Done

| # | Item | Verified by |
|---|---|---|
| 1.0 | Steps use dedicated agents (save + run) | Unit, DB, live API; user's checks |
| 2a | Saves are atomic, row lock, 409 on a race | DB tests reproduced the bug first; 5 runs of the concurrency test |
| 2b | Old workflows keep a restorable "before" version | DB tests; live restore |
| 2c | Duplicate and reserved output keys refused; `llm_decision` refuses containers | Unit, DB, live API; 47 templates and the real DB have none |
| 2d | `llm_decision` runs record their version | DB tests; live runs |
| 2e | Frontend validation mirrors the backend | jest per rule |
| 2f | Editor parity: shared step options and limits | jest; user's checks |
| 2g | **Core fix:** the `llm_decision` orchestrator now sees its agents' results | Real pipeline tests; 48/48 paused runs valid; live runs; Cybercrime 5/5; Medical P1 |
| 2h | Orchestrator limits hidden in Sequential mode, both editors | jest. On screen at the next check |
| 2j | Version snapshots include workflow-level settings; restore brings them back | DB tests; unit + goldens on both engines |
| 3a | Research notes: `research/04-container-ui.md` | Sources linked |
| 3b | Tree model and depth-first save; chain per block; router reorder fixed | jest, including the demo's payload unchanged |
| 3h | Safe references on new workflows (`schema_version` 2): `$loop.item.title` reads the field, values never re-expand, bad references refused on save. Existing workflows unchanged until upgraded | Unit; DB; live: an agent received exactly the field; goldens unchanged |
| 3g (API) | Nesting works: loop in parallel, loop in loop, condition in a branch, nested fields | `tests/workflow_creator/test_container_nesting.py`, no LLM calls |
| 3i | Upgraded `02_code_review.json` to parallel reviewers (live, version 3 of workflow 2). Medical P2's guard-rail corrected: the patient has HbA1c 7.8 and diabetes, so consulting the Endocrinologist is right. `create_workflows.py` now deploys new node types | Live run read: summarizer got both reviews. **Medical P2 not re-run, to save tokens** |
| 3j | Demo rebuilt as `44_trip_planner_demo.json` (live, workflow 49): destination chosen first, then parallel research, outline, one call per day | The user's 6-day question: 6 distinct days, all three researchers on the same place |

## To do

| Done | # | Item | Kind | Done when |
|---|---|---|---|---|
| [x] | 3c | Show containers: boxes with lanes, children inside, recursive layout, correct legend. Browser-tested; the user saw it on screen too | Frontend | Done 2026-10-31 |
| [x] | 3d | Edit structure: Run inside / Branch pickers, add into a lane, drag in/out (joins where dropped), refuse cross-block edges, Delete key, keep-steps removal. Browser-tested | Frontend | Done 2026-10-31 |
| [x] | 3e | Forms: branch names, loop settings by mode, code inputs/outputs. Browser-tested | Frontend + small backend | Done 2026-10-31 |
| [x] | 3f | Wizard: children indented, safe reorder and delete, Next no longer saves by itself. Browser-tested | Frontend | Done 2026-10-31 |
| [x] | 3g | Built parallel + loop on screen, saved, reloaded; the same definition ran on the real backend with real agents (Paris, then Rome) | End to end | Done 2026-10-31 |
| [x] | 4 | Run view: scope on steps, fork/join and real times in the trace, a trace node for loops, labels kept after reload. Browser-tested on a saved chat; the user's real run 571 read and correct | Backend + frontend | Done 2026-10-31 |
| [x] | 3k | Agent steps can declare an expected output (JSON schema): the provider enforces it where the model supports that, small mistakes are repaired, the reply is validated, one retry sends the error back, then the step fails clearly. Both editors. The save check refuses fields a step doesn't declare. Demo moved to it (version 5). Live runs and browser-tested | Full stack | Done 2026-11-01 |
| [ ] | 5 | Webhooks in Pulse (W1–W5). **Handed to another agent by the user, 2026-10-31**, in its own worktree and scratch DB; brief: [WEBHOOKS_HANDOVER.md](WEBHOOKS_HANDOVER.md). Left for this track: review its work, back up the real DB, merge, user's screen check | Full stack | Reviewed, merged, screenshot |
| [ ] | 6 | **Deferred by the user, 2026-10-31: develop later.** Engine hardening, in order: cancel + fail-fast + timeout; budgets + concurrency; retry; sandbox admission + code errors; opt-in router upgrade. A loop must not silently drop items beyond `max_iterations`: say so in the output and the trace. Decide whether `llm_decision` runs on the pinned definition | Backend | Each with tests; goldens green |
| [ ] | 7 | Dry-run script in the repo, template JSONs, multi-agent review, `graphify update .`, docs (`research/00-platform-survey.md`, DESIGN, HANDOVER), remove `flowdev.bat` and the flow-dev compose file, drop `flow_dev` only if the user agrees. Look at the `No active trace` log errors | Mixed | Checklist done; rollout notes for the user |

**Not scheduled; the user decides at the end:** durable runs and crash resume, idempotency for side-effecting tools, cost budgets per tenant, approvals inside containers, OpenTelemetry, audit and RBAC, draft/publish, PII retention. See `REVIEW_88eb334e5.md`.

## Local HTTPS, 2026-11-01: live on https://localhost

`dev.bat` turns it on when `deployment/data/sslcerts/ssl.crt` exists (`setup-local-https.bat` creates it); `.env` has `WEB_DOMAIN=https://localhost`. How to use it and go back: `deployment/docker_compose/README-windows-dev.md`. Files: `docker-compose.local-https.yml`, `deployment/data/nginx/app.conf.template.local-https`. Backup: `D:/llm/backups/virtualai_postgres_before_local_https_20261101_125229.dump`.

**Always start through `dev.bat`, or add `-f docker-compose.local-https.yml`:** compose without it gives nginx the HTTP config and no port 443.

**Tested on the live stack:** the certificate is trusted by Windows; `http://localhost:3000` redirects; no HSTS; plain `http://nginx:8088` works from the Docker network; webhook URLs are `https://localhost/api/hooks/...`; file upload and a demo chat work (919 events over 19 s, trace opens); `main_trace_check` 11/11, `main_nesting_e2e` 28/28, `main_saves_e2e` 11/11. From the LAN address only 80, 443 and 3000 are open; from this machine all ports still work.

**Earlier, on a separate nginx:** tokens redacted in logs, oversized webhook body 413, spoofed `X-Forwarded-For` ignored, a real browser saw no plain HTTP or mixed content.

**Open:**
- `Secure` login cookie: needs the user's sign-in. The code sets it from `WEB_DOMAIN`.
- Registered OAuth redirect URLs need changing to `https://localhost/...`.
- IIS on this PC listens on IPv6 port 80, so `http://localhost/` shows its welcome page. Port 3000, `127.0.0.1` and HTTPS aren't affected.
- Docker Desktop shows every published-port caller as `172.19.0.1`, so here all webhook callers still share one rate-limit bucket. The `.prod` templates still hop through port 80: that review finding stays open.
- Not from HTTPS: knowledge file deletes are stuck, 35 files since 2026-10-24, plus `https-test.txt` from this test. The lightweight worker in `backend/supervisord.conf` (used here, `USE_LIGHTWEIGHT_BACKGROUND_WORKER=true`) has no `user_file_delete` in its queue list, so nothing processes these deletes. Not fixed.

## Final review, 2026-11-01: not fixed, the user decides

Three independent reviewers. "Reproduced" means I ran it; "read" means traced in the code.

**Flow nodes**

| Sev | Finding | Where | Checked |
|---|---|---|---|
| High | The citation processor strips `[n]` from agent replies: `{"ids":[1, 2]}` becomes `{"ids":}`, "section [2]" loses the number. Free-text steps too | `agent_tool.py`, `llm_step.py` | Reproduced |
| High | A schema that isn't strict-compatible (bare `array`, open nested object, `anyOf`) passes save, then the LLM call fails on every run | `output_contract.py` | Reproduced |
| High | A reply cut off by the token limit can pass: `{"days":["a","b","Day thr` becomes a shorter valid list; `finish_reason` is never read | `output_contract.py` | Reproduced |
| High | A schema is accepted on `schema_version` 1 workflows, where `$s.output.status` in a router reads as empty and takes the wrong branch | `nodes/agent.py`, `saving.py` | Read |
| Med | A failed run loses all its step records on reload: `save_chat_turn` is skipped when the run raises | `message_handler.py:503`, `sequential.py:137` | Read |
| Med | The retry re-runs the whole agent, so a tool that changes something runs twice; retry files are dropped | `nodes/agent.py` | Read |
| Med | With `on_branch_error: continue`, a failed branch's output reads as empty to later steps | `state.py` | Read |
| Med | A loop keeps only the last iteration's files | `nodes/loop.py:298` | Read |
| Med | Changing a step's agent clears its overrides in the Visual Builder but not in the Wizard | `WorkflowEditorPage.tsx:409` | Read |
| Med | Optional schema fields become required under strict mode; without `required`, `{"day":[1]}` passes on models without enforcement | `output_contract.py` | Partly reproduced |
| Low | Delete key removes a box and its steps with no confirmation; only top-level `$step.output` fields are checked on save; schema box loses a custom schema on Text → JSON; legacy engine ignores `output_schema` | Various | Read |

**Webhooks (owned by the other agent)**

| Sev | Finding | Where | Checked |
|---|---|---|---|
| High | Behind TLS, every caller shares one rate-limit bucket (`127.0.0.1`), so anyone sending 301 requests a minute blocks all webhooks | `nginx/app.conf.template.prod`, `limits.py` | Read |
| Med | The TLS nginx block doesn't redact tokens in its logs; Helm has no redaction | `nginx/app.conf.template.prod` | Read |
| Med | An admin can rewrite `input_message` on another user's webhook, which then runs with the owner's access (rotation is owner-only, this isn't) | `webhook_api.py:418` | Read |
| Med | Payload text can steer an agent with all the workflow's tools; `<untrusted_data>` is the only defence | `runner.py`, `payload.py` | Read |
| Med | Reaching the owner's rate limit counts as failures, which auto-pauses the webhook | `runner.py:301` | Read |
| Med | A resend after a skipped or failed run returns "duplicate" and nothing runs | `pulse_webhook.py:283` | Read |
| Med | Webhook runs never expire while the worker is down, and old events all run when it returns | `scheduler.py` | Read |
| Med | Owner isn't notified when a webhook is disabled at run time; one user can use up the tenant's run cap | `runner.py:284`, `pulse_webhook.py:288` | Read |
| Med | Helm has no worker for the `pulse_webhook` queue | `helm/.../pulse-worker.yaml` | Reviewer's report |
| Low | Replay of signed requests when dedup is off; `ENCRYPTION_KEY_SECRET` unset stores signing secrets in plaintext (true here); dev compose exposes port 8080 on all interfaces; `test_url` never shown in the UI; `prod-no-letsencrypt` compose names a template that doesn't exist; no migration lock timeout | Various | Partly read |

**Item 7 so far:** `No active trace` fix written, 3 tests pass, not deployed. Dry-run script in the repo: 0 problems in 48 templates, 49 workflows, 289 steps, 123 paused runs. `flowdev.bat` and its compose file removed, and unused code removed, with the user's OK. Docs not updated.

## Open after the self-review (2026-10-31)

Not fixed; each goes with the item named, or the user decides.

| Open point | Where it goes |
|---|---|
| The chat's model picker doesn't reach workflow steps; each step uses its agent's own model | The user: later, not this release |
| `input_mapping` is stored as JSONB, which reorders keys: the outline agent gets `where they stay` before `chosen destination`, not the authored order | Needs its own look |
| Expected output on `llm_decision` steps; refused on save for now | Later |
| A cut-off reply can still pass if it fits the schema, so schemas should use rules like `minItems` | Note for authors |
| A follow-up message in a workflow chat starts a new run with only that message: after "plan india…", "i'm planning from UAE" (run 596) lost India and the 6 days | Design question, the user decides |
| A branch abandoned by `first_success` leaves no trace node | Item 6 (cancel) |
| The container trace stays "running" if the client disconnects mid-step (cancel and failure paths are closed) | Item 6 (cancel) |
| Whole trace rewritten about 3× per `llm_decision` step; checkpoints rewrite all outputs each step. Grows with run size, not noticeable at today's sizes | Item 6 (budgets), only if a real run shows it |
| `selectedSteps` recomputes on every drag tick while a step is selected | Only if dragging feels slow |
| Adding or removing a branch still lays out the whole canvas and rebuilds its edges (typing no longer does) | Only if it bothers someone |
| React hydration error #418 on every admin page in dark mode, also pages this work didn't touch; cause not found | Separate from flow nodes; the user decides |
| Input Mapping on the agent panel is two levels deep (Advanced tab, then Advanced toggle) | Usability, the user decides |
| A new Visual Builder workflow starts in LLM Decision, where Parallel, Loop and Code aren't offered | Usability, the user decides |
| The chat timeline says "10 agents" when it counts code steps too (the list page now says steps) | Small, with item 7 |
| Browser checks live in `D:/tmp/ui`, not the repo; a real-backend fake API isn't a substitute for the first real login | Item 7: decide whether to add them to the repo |
| Nothing calls `fitView` after a box grows, so it can end up partly off screen (a saved workflow does now open fitted) | Only if it bothers someone |
| Could not verify: all agents at their call limit sends `tools=[]` while history holds tool calls; extended-thinking replays | Item 6 |
| `No active trace` log errors not investigated | Item 7 |
| Medical P2 guard-rail not re-run since its test changed (costs LLM tokens) | User decides |
| `llm_decision` runs and resumes on the live steps, not the pinned definition | Item 6 (decide) |
| A loop silently stops at `max_iterations` | Item 6 |
| Dry-run script still at `D:/tmp/main_dry_run.py`; `research/00-platform-survey.md` missing; `DESIGN.md` not updated for schema 2, settings, scope; `flowdev.bat` not removed | Item 7 |

## Progress log

- **2026-11-02, disconnected steps are kept but skipped (uncommitted; live and browser test wait for a rebuild).** A cut line used to block saving with `"X" is not connected`, because a workflow is saved as an ordered list and lines are redrawn from it. Now a top-level step no line from Start reaches is saved with `disabled` (migration `0008_workflow_step_disabled`) and doesn't run. Like n8n's disabled nodes. **Backend:** `WorkflowGraph.runnable()` for the sequential engine; `runnable_workflow_steps()` for the legacy and LLM Decision engines, the wrapper agent's description and a webhook's tool list; versions keep disabled steps, and write the flag only when true, so existing hashes don't change. Save refuses: every step disconnected; a running step that reads, or a condition that leads to, a disconnected one; a disconnected step inside a container. **Visual Builder:** `disconnectedStepIds()` (reachable from Start, through router lines too) sets the flag on save; on load running steps chain from Start, disconnected ones stay linked to each other; greyed nodes with a "Not connected — won't run" badge and a banner listing them, none blocking. **Wizard:** a "Skip this step" switch. **Show as Message:** not required on the last step (the engine already shows the last step's answer); both editors note when an earlier step's message hides it (`lib/workflows/finalAnswer.ts`); END tooltip says which answer the chat shows. **Tested:** backend 686 (workflows + Pulse, 19 new, no golden changes); frontend editor suites 241 (new `disconnectedSteps.test.tsx`, `finalAnswer.test.ts`), full jest 857/864 with the 7 failures all in `CustomForm.test.tsx` (LLM provider form, not touched); tsc clean apart from the known dotenv noise. **Not yet:** live run on a copy of workflow 79 (cut, run, reconnect, reload) and the browser check of both editors.
- **2026-11-02, HITL works from the toggle alone.** A step with "Can Request Input" on now gets a short "Asking the user" section added to its system prompt at run time (`INPUT_REQUEST_GUIDANCE`, `with_input_guidance` in `om/workflows/hitl.py`; applied in `AgentTool._run_agent`). Skipped when the prompt already mentions `[NEEDS_INPUT]`, so the 50 of 52 live HITL steps that have it keep the same prompt. It doesn't ask for `STATUS: COMPLETE`: nothing removes that from replies, and it shows in 27 of the last 286 saved answers. Toggle text updated in both editors. **Tested:** 11 new unit tests, all workflow unit tests and goldens pass with no golden changed. Live on temporary copies of workflow 79, chat path, committed code plus this change on an isolated port: no FIR given paused 3 of 3 with the marker hidden, replying continued through all 5 steps, a full FIR didn't pause 2 of 2, toggle off didn't pause. Before this, 15 of 15 runs didn't pause. **Accepted by the user:** workflow 48 has an active schedule, HITL on and no marker, so its scheduled runs may start stopping at "needs input"; not tested. **Open:** a finished answer with a line like "What should I do next?" can still pause by mistake (existing heuristic); `STATUS: COMPLETE` shows in answers; a dedicated "ask user" tool is the next step if the marker proves unreliable.
- **2026-11-01, 3k done.** Real workflow, 6 runs: India, UAE snow and Japan twice each, all completed with the right day counts (6, 6, 7), read. The user's own chat runs 591 and 596 completed too. Measured on the real bad replies from runs 584 and 586, enforcement off: old array prompt 0/10 on the first try, schema stated in the task 10/10, retry with the error 10/10; new object prompt 10/10; API-enforced schema 10/10 on run 584's input. An agent with a tool and a schema completes. Real backend, no LLM: refused bad schema, pausing step, LLM Decision and undeclared field; a schema survives settings saves and comes back on restore, 8/8. Browser: output format 21/21, run view 11/11, editors 83/84 (the #418 error). Unit 593, goldens 116 unchanged, DB 57, web 217. The browser check caught one bug: the validator didn't run the rules on agent steps; fixed. Backup: `D:/llm/backups/virtualai_postgres_before_output_contract_20261101_003917.dump`. One temp key was left by a deploy interrupted partway; removed.
- **2026-11-01, 3k, expected output.** `om/workflows/output_contract.py`; the schema is stored in the agent step's `config` column, no migration, and left out when empty, so existing definitions keep their hash: all 116 goldens unchanged. `json_repair` (new dependency, images need a rebuild) returned `""` on both real failures, so it's one layer, not the fix. `om/chat/llm_step.py` now passes `structured_response_format` where it had a TODO.
- **2026-10-31, tested in a real browser at the user's request.** Headless Chromium on the real web image, isolated network, fake API serving captured responses of the real workflow. A scratch API on `flow_dev` was refused by the permission system as a shared-resource change, so nothing there ran. Saves went to the fake; the definition built on screen was then created and run on the real backend with a temp key and removed. Results on the final image: editors 83/84, item 4 11/11; the one failure is hydration error #418, on all admin pages in dark mode. Real backend, no LLM: trace 11/11, nesting 28/28, saves 11/11. Run from the UI's definition: 5/5. **Found and fixed:** a step dragged out of a box always landed last (now where dropped); **Wizard: after any edit, Next on step 2 saved and left without showing step 3** (older bug: one DOM button changing type mid-click); saved workflows opened zoomed in on Start; trace minimap empty and zoom buttons white in dark mode; list page showing `Agent #null` for code steps. Migration `0003` (other work stream) was applied by someone else's restart at 09:47 UTC.
- **2026-10-31, self-review.** Two independent reviews, each claim checked against the code. **Fixed in the editors:** Visual Builder crash on load (a hook after an early return); moving a step into a box keeps options the server refuses; Add/rename of code inputs could overwrite data; typing in box settings rebuilt the canvas and brought back deleted edges; branch-name fallback text while typing; new Code/Parallel steps missing their defaults; changing the type of a box with steps; Delete key skipping the tree rules; layout using too-small sizes; a drop on a box's header left the box; multi-select drag; hidden limits still validated in Sequential. **Fixed in the backend:** a later agent's pause reusing an earlier agent's task; persisted output mixing up parallel branches; references to steps that didn't run failing or passing inconsistently; router conditions ignoring paths (schema 2); save check not matching how settings are read (`$500` in a code input, `items` reading its own body, `$loop.foo`); a paused step that's gone losing the user's reply; re-pause exceeding `max_calls_per_agent`; a run pinning a stale definition; new workflow saved in pieces; metadata saves failing on old workflows (my regression); `first_success` + `fail` depending on timing; a loop inside a losing branch still spending LLM calls; save checks running in `llm_decision`, where order isn't fixed. **Optimized:** `graph_from_workflow` 2 instead of up to 4 per save; no deep copy of the context per while check; no canvas rebuild per keystroke. **Measured, no change needed:** Wizard placement at 100 steps, 2.4 ms per keystroke. Two goldens regenerated (`fx_llmd_repause`, `fx_llmd_resume_legacy_checkpoint`), intended changes only.
- **2026-10-31, item 4.** Instrumentation only; scheduling unchanged. `scope`/`depth` on `WorkflowStepStart` and `TraceNode`, set in `blocks.run_block`. The trace builder forks and joins (`begin_branch`, `end_branch`, `join_branches`). Live, code steps only: 11/11. Goldens unchanged: both new fields are omitted when empty. Known limit: a branch abandoned by `first_success` still leaves no trace node.
- **2026-10-31, 3e–3j.** A real lesson from reading the demo's output: all checks passed while the researchers disagreed (Georgia, Switzerland, Lapland), because parallel steps can't see each other and the destination was open. Fixed in the workflow's order, not the engine; checks now test coherence. Goldens keep the old Code Review in `engine_golden/frozen_templates/`. Found on the way: `create_workflows.py` silently dropped steps without an agent; it now raises.
- **2026-10-31, webhooks handed over.** User assigned item 5 to another agent; brief in `WEBHOOKS_HANDOVER.md`. User committed the work so far as `074b8ec6b` (not pushed).
- **2026-10-31, 3d + 3f.** `stepTree.ts`: `moveStep`, `removeStep`, `reorderInBlock`. `containerLanes.ts`: lanes and allowed places. `StepPlacementFields.tsx` used by both editors. Canvas: drop into a lane, drag in and out, lines stay within a block. Not exercised in a real browser by me; jest and types only.
- **2026-10-31, demo check.** User's 6-day trip gave 2 days. Trace read (execution 556): the demo's toy first step built `["Day 1", "Day 2"]`; the loop and the LLM did what they were told. Added 3j. Answered why the two orchestrator limits are hidden in Sequential mode: 0 uses in the Sequential engine; values stay saved. User confirmed they show on LLM Decision workflows.
- **2026-10-31, 3c.** `containerLayout.ts` (recursive, pure), `ContainerNode.tsx`, a `container` editor kind. Workflows without containers keep the old grid. Web rebuilt and API restarted, so 2h and 2j are live too.
- **2026-10-31, old workflows.** User: don't test all old workflows with LLM calls (tokens); pick a couple, upgrade their JSON and test those. Bulk run stopped. Results before stopping: Medical P3 and P4 pass. Medical P2 fails a guard-rail: the orchestrator also consulted the Endocrinologist, which the test forbids for this patient. Not retested; goes with the `22_medical_diagnosis.json` upgrade in 3i. Discussion and later suites did not run.
- **2026-10-31, plan review.** Added 2h (limits mislead in Sequential mode, from the user's screenshot), 2i (the core fix changed 29 workflows), 2j (the orchestrator prompt isn't versioned), 3h (references in loops). Dropped ELK for a small recursive layout: our graph is a tree of chains, ELK is async, and this adds no dependency. No lane nodes. Item 6 reordered by risk.
- **2026-10-31.** User validated the Wizard, Visual panel and Customer Support Triage. 2f confirmed.
- **2026-10-31.** Step 2 built. Found and fixed the `llm_decision` core bug. Real DB backed up first: `D:/llm/backups/virtualai_postgres_before_flow_step2_20261031_095036.dump`. Details in HANDOVER.
