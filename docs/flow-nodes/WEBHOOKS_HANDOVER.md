# Webhook triggers in Pulse: handover for the implementing agent

**Your task:** TODO item 5. Let an external system start a workflow through Pulse with an HTTP call, securely. This is one self-contained feature; the rest of the flow-nodes work is being done in parallel by another agent.

## Read first
1. `docs/flow-nodes/REFERENCE_STUDY.md`, deltas **W1–W5**: the design decisions, with sources.
2. `docs/flow-nodes/research/03-webhooks-versioning.md`: how n8n, Windmill, Activepieces, Dify and Langflow do it. n8n, Windmill and Dify main are clean-room: ideas only, never copy code. Local clones are in `D:/llm/reference-frameworks/`, read-only.
3. `docs/flow-nodes/PROGRESS.md`, "Test plan": the webhook test cases.
4. `AGENTS.md` and `CLAUDE.md` at the repo root.

## Hard rules
These protect the user's real data and the parallel work.

- **Work in your own git worktree, branched from `074b8ec6b` or later.** Don't edit the main checkout `D:/llm/danswer20022026`.
- **Never start, stop, restart or rebuild the main stack** (`virtualai-*`, port 3000). No `dev.bat`. The main stack bind-mounts the main checkout and applies pending migrations when it starts, so a migration file reaching that checkout would run on the **real database**.
- **Never run the alembic CLI**, anywhere. Migrations apply when a backend starts.
- **Test only on a new scratch database of your own**, for example a clone named `flow_webhooks`. Not the real database, and not `flow_dev`, which the other agent's tests use. Never drop anything you didn't create.
- **Don't use `flowdev.bat`** or the `flowdev` containers: retired by the user.
- **Commit only if the user asks. Never push.** The repo is public: explicit `git add` paths only, never `-A`.
- **No secrets** in files, logs or output. Throwaway API keys must be removed afterwards.
- **No workarounds or fallbacks.** Implement it properly.
- **Keep LLM use minimal.** Test webhook logic without LLM calls, using a fake run or a code-only workflow. One small live run at the end is enough.
- **Stay in scope:** Pulse and webhooks only. If something outside looks wrong, report it rather than changing it.

## The design, in short
Details and reasons are in W1–W5.

**W1. Public `POST /hooks/{token}`, cheapest checks first:**
1. method;
2. token shape (404, no DB);
3. `Content-Length` and a hard 1 MB streaming cap (413);
4. tenant from the token;
5. Redis rate limit per IP and per token (429 with `Retry-After`);
6. hashed lookup with a short cache (uniform 404);
7. Standard Webhooks HMAC over the **raw bytes**, ±5 min, against every `v1,` signature (401);
8. **only then** parse JSON, with depth and key limits.

**W2. Tokens:** `whk_<tenant>.<secret>`, stored as SHA-256, last 4 characters shown, two active hashes during rotation. The HMAC secret is encrypted, not hashed.

**W3. Duplicates and bursts:** a duplicate returns 202 with the original run id. Bursts queue up to N pending runs, then 429. Don't reuse run-now's 409.

**W4. Listen mode:** `POST /hooks/test/{token}` works only while the owner has Listen open (Redis TTL 120–300 s), otherwise 409. It captures the payload **without running** and never consumes production dedup keys.

**W5. Payload in the input:** `{{payload.a.b}}` is substituted as a length-capped string, **never re-expanded**, inside a delimited untrusted block. Authorization, Cookie and signature headers are stripped before storing. Tokens are redacted from access logs. No CORS. Owner access is re-checked when the run starts.

## What already exists: reuse it
| Need | Reuse | Where |
|---|---|---|
| Token generate, hash, last 4, tenant parse, constant-time compare | SCIM token helpers: copy the pattern with a `whk_` prefix | `backend/om/server/scim/auth.py:57-131` |
| Encrypted secret | `EncryptedString` | `backend/om/db/models.py:124` |
| Starting a run reliably | Commit first, then enqueue; `enqueue_pulse_run` | `backend/om/pulse/scheduler.py`, `dispatch.py:13` |
| Running it | The whole runner: access re-check, rate limits, chat session, watchdog | `backend/om/pulse/runner.py`, `access.py:64-102` |
| Run bookkeeping | `PulseRun.trigger`; the slot unique index covers only `trigger='scheduled'` | `backend/om/db/models.py:5207,5246-5253`, `backend/om/db/pulse.py` |
| Input templating | `render_input_message` | `backend/om/pulse/timing.py:490` |
| Public route allowlist | `PUBLIC_ENDPOINT_SPECS` | `backend/om/server/auth_check.py:16` |
| UI | `sections/schedules/*`, `ScheduleModal`, `refresh-pages/SchedulesPage.tsx`, `lib/schedules/api.ts` | `web/src/` |

Line numbers are from an audit on 2026-10-31; check them.

## What to build
1. Webhook model, and `PulseRun.dedup_key` with a partial unique index where `trigger='webhook'`. Migration `0004_pulse_triggers`, following `0002_workflow_nodes`. Not additive: it restructures the Pulse tables (see `docs/scheduled-workflows/DESIGN.md`, "Triggers").
2. The public endpoint (W1), dedup and burst handling (W3), listen mode (W4), payload mapping (W5).
3. Admin API: create, rotate, revoke, listen.
4. UI: a Webhooks tab in Pulse (Schedules | Webhooks), show-once token, rotate, Listen / Send test event.

Keep it in small modules, following the surrounding style.

## Tests required
Valid and invalid HMAC, replay window, dedup, 429, size cap, uniform 404, cross-tenant token, runs as owner, admin view. Plus unit and DB tests on your scratch database, migration upgrade and downgrade, `tsc`, and jest for the UI.

**Verify the goal, not just the status code:** the workflow actually receives the payload, and an untrusted payload can't inject into the prompt or re-expand.

Web testing notes: `tsc` works (ignore the 2 `dotenv` errors), and jest works; local `next build` and lint are broken on this machine.

## Finished means
- All of the above passes, in your worktree.
- You report: what was built, test results, how to run them, anything not verified, and anything you couldn't do.
- **You don't merge.** The other agent reviews your work, takes a fresh backup of the real database, merges, and asks the user to check the screen.

Keep a dated progress log at the bottom of this file, in your worktree, so the work can be resumed.

## Progress log

- **2026-10-31, setup.** Worktree `D:/llm/danswer-webhooks`, branch `feature/pulse-webhooks` from 074b8ec6b. Scratch DB `flow_webhooks` (clone of the real DB, schedules disabled), Redis 6/7/8. Stack and scripts in `D:/tmp/webhooks/` (not in git): `compose.yml` (project `webhooks`), `pytest.sh` (refuses any DB but `flow_webhooks`), `it.env` and `webhooks.env` (secrets, never print them). Design changed with the user's approval: full plan in `C:/Users/Pandu/.claude/plans/reivew-code-from-this-distributed-cat.md`. The migration is `0004_pulse_triggers`, not `0003_pulse_webhooks`, and it isn't additive.
- **2026-10-31, could not reach the other agent.** Its session refuses cross-session messages. For whoever merges: (1) the body of the legacy `apply_input_mapping` in `workflows/inputs.py` becomes single pass; (2) `pulse_schedule` splits into `pulse_trigger` + `pulse_schedule` + `pulse_webhook`, `pulse_run.schedule_id` -> `trigger_id`, `pulse_run.trigger` -> `fired_by`, `chat_session.pulse_schedule_id` -> `pulse_trigger_id`.
- **2026-10-31, step 1 backend (trigger refactor, no webhook code).** Unit + engine_golden 167 passed; real-DB scheduler 15 passed; new down/up migration test on the clone's real rows passed; live API, worker and scheduler: 17 passed + 1 skipped with a code-only workflow, plus the 3 tests that need an assistant reply passed with a one-agent workflow (210 tokens). Found, not changed: a workflow ending in a code step leaves the chat's assistant message empty, so `output_preview` is empty too.
- **2026-10-31, steps 1b-5 backend.** `PulseWebhook`, intake (12 steps), verifiers, payload rendering, limits, listen, own queue and worker, admin switch, management API. Single-pass `apply_input_mapping`, proven same as the old algorithm by a 3000-case comparison when values contain no `$`. Tests: `test_webhook_core.py` (unit), `test_pulse_webhooks_db.py` and `test_pulse_webhook_tenants.py` (real DB, races, a real second schema), `test_pulse_webhooks_api.py` (27 attacks over real HTTP through nginx; no LLM). Bugs the tests caught: ORM refuses to compare encrypted values on rotate; `pipeline`/list Redis commands aren't tenant-prefixed; nginx error log prints the URL.
- **2026-10-31, step 6-7.** UI built and checked: browser walkthrough 34/34 through real nginx, screenshots read by eye in light and dark. One live LLM run with an injection payload: injection ignored, `$internal_note` stayed literal, other step's output not leaked, 102 tokens. Final code: backend unit + workflows 489 passed, DB 38 passed, jest 748 passed. 7 jest failures in `CustomForm.test.tsx` also fail on the main checkout without this work (not caused here, not changed). Helm chart not updated (open item). Independent review pending.
- **2026-10-31, independent review and final gate.** Review found no auth bypass. Fixed: revoke and pause now stop queued runs (`policy.py`); pause, revoke or delete between locate and accept gives 404 and no run; test events have the size limit; rate-limited webhook runs fail visibly and notify; wider credential-header stripping; Sentry events scrubbed; signed webhooks can't use an unsigned header for dedup; an unreadable admin switch gives 503 rather than reopening; schedule stats exclude webhook runs; delete locks parent first; `updated_at` on child-only writes; UI cache and Listen fixes; admin revoke asks first. Accepted, documented: tenant cap can overshoot slightly; rendered values stay in chat history.
- **Final results.** Backend unit + workflows 491, real DB 45, live attacks 30 through nginx, existing Pulse live 20 + 1 skipped, browser 38/38, signatures verified by the official `standardwebhooks` library, zero raw tokens in API, worker and nginx logs and `/metrics`. jest: only `CustomForm.test.tsx` (7) fails alone, and it fails the same on the main checkout. `AzureOnboardingForm` failed once in a full run under load and passes alone.
- **Not exercised:** the rate-limited-run path in the runner (needs a rate-limit policy); a real multi-tenant deployment (cross-tenant used a real second schema with the flag patched); `.prod` and `.no-letsencrypt` nginx templates and prod compose files (same edits, not started); Sentry scrubbing against a real Sentry (unit test only); `pulse_entrypoint.sh` inside a rebuilt image (a copy was mounted).
- **Merge notes.** (1) `0003_user_ui_preferences` now exists in the main checkout and is applied to the real DB. Re-parent this branch's migration onto it and rename it `0004_pulse_triggers`, or the backend won't start with two heads. (2) `db/models.py` overlaps with that work. (3) Stop `pulse_scheduler` and `pulse_worker` for the upgrade; recreate nginx; start `pulse_webhook_worker`; rebuild web and Pulse images; then `graphify update .`. (4) Helm chart still needs the worker and nginx limits.
- **Rerun:** `D:/tmp/webhooks/reset_scratch.sh`, then `D:/tmp/webhooks/pytest.sh <path> -q -p no:cacheprovider`. Browser: `make_login.py`, `browser_check.py`. Live LLM: `live_llm_check.py`.

- **2026-10-31, visual builder crash (React #310).** Opening an existing workflow in the visual builder crashed: `selectedSteps` in `WorkflowVisualBuilderPage.tsx` called `useMemo` after the loading `return`. It came in with `074b8ec6b`, so it isn't webhook code. Moved above the return, in the same place as the main checkout's uncommitted version, so that hunk should merge cleanly. `ScheduledRunBanner.tsx` had the same mistake (not reachable, because `AppPage` guards it); its null check now follows the hooks. The main checkout still has the banner issue. New test: `components/workflow-builder/WorkflowVisualBuilderPage.test.tsx`. jest only runs tests under `src/app`, `src/components` and `src/lib`, so a test in `refresh-pages` is never picked up. Lint doesn't run on this machine and `tsc` can't see this kind of bug, so nothing catches it automatically.
- **2026-10-31, admin pages and worker health.** New Features has a Webhook triggers card with setup steps and (i) help; Platform Services has a Pulse Webhook Worker card. `/api/admin/pulse/health` gained `pulse_workers_alive` and a `webhooks` section, because it said nothing about webhooks and a stopped worker looked healthy. Workers publish Redis presence keys (`om/pulse/worker_presence.py`), withdrawn when shutdown starts. Fixed a bug found on the way: the healthcheck glob missed `om_k8s_pulsewebhook_readiness.txt`, so `pulse_webhook_worker` would have stayed unhealthy; the scratch stack hid it by disabling healthchecks. **Merge note:** `Dockerfile.pulse` is a layer over the backend image, so rebuild backend first, then Pulse, with `OM_BACKEND_IMAGE` set; building Pulse alone keeps the old code and `workers_alive` stays 0. **Found, not changed:** `/api/metrics` is public through nginx; each API process keeps its own counters; React #418 in dark mode on admin pages; the comment in `on_worker_shutdown` about cold shutdown is wrong (Celery's `terminate()` doesn't send that signal, so the reaper handles those runs).
