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
1. Webhook model, and `PulseRun.dedup_key` with a partial unique index where `trigger='webhook'`. Migration `0003_pulse_webhooks`: additive, following `0002_workflow_nodes`.
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
