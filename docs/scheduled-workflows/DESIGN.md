# Plan — **Pulse**: scheduled workflows engine (n8n-style)

## Context
We have multi-agent workflows (JSON in `backend/tests/workflow_creator/workflows/`, engine in
`backend/om/workflows/workflow_engine.py`), but they only run interactively inside an HTTP/SSE chat request.
The user wants n8n/OpenClaw-style scheduled workflows:
- pick any workflow and schedule it (cron / interval / once);
- it runs headless in the background, repeatedly, collecting information;
- results are saved to the DB;
- every run shows up as a chat session in history;
- schedules are managed from the UI.

The bar is enterprise grade: low latency, HA (no double-fire, no single point of failure), horizontally
scalable, and easy to use.

**Pulse** is the brand, the same way Cortex is the brand for inference and embeddings.

We work in the isolated worktree `D:/llm/danswer_sched_wt`, on branch `feature/scheduled-workflows` (off
`main_multi_agent_stable` @ eb6902e66). Another agent is refactoring the main checkout. The tracker is
`docs/scheduled-workflows/PROGRESS.md`; a new session resumes from it.

**How the plan was made:**
- 3 research agents: a SOTA survey, a backend map and a frontend map.
- 2 adversarial reviewers: one on reliability/HA, one on UX/simplicity. They found 5 critical and 6 high
  defects in the draft; all fixes are folded in below.

## Framework, inspiration, footprint
- **Engine:** built on our existing **Postgres + Celery + Redis**.
  - We do not embed n8n, Airflow, Temporal or Hatchet. Each of those would be a separate server running
    *beside* our workflow engine, not inside it.
- **What we borrow (pattern only, no code):** n8n's newer durable scheduler (2.45+), which Airflow's HA
  scheduler also uses:
  - schedules are DB rows;
  - a ticker claims due rows with `SELECT … FOR UPDATE SKIP LOCKED` plus an advisory lock (plain Postgres
    SQL, no dependency), so N replicas never double-fire;
  - runs execute on a scalable worker queue.
- **UX inspiration:**
  - n8n Schedule Trigger: frequency presets, timezone, next-runs preview.
  - OpenClaw cron: each run is its own session; interrupted runs are never replayed; auto-pause after
    repeated failures.
- **Other ideas borrowed:**
  - Temporal: skip-on-overlap.
  - Dagster: a run key, `UNIQUE(schedule_id, scheduled_for)`.
  - Inngest: jitter, and the DST warning that a run can fire 0, 1 or 2 times.
- **Rejected:**
  - Celery beat entries per schedule, or RedBeat: single instance; our beat diffs by task name only; Redis is
    not durable; RedBeat fails over in 25 minutes.
  - APScheduler 4: still alpha.
  - Temporal / Hatchet: a new stateful cluster.
- **New package:** `croniter==6.2.4` only. It is small, pure Python, MIT-licensed and maintained by
  pallets-eco. It computes next/previous fire times for a cron expression in a timezone and validates
  expressions. `tzdata` is already pinned. The frontend needs no new packages.
- **Maintenance:** low. Everything stays in our stack. There is no new server to operate, upgrade, back up or
  monitor.

## Packaging (follows existing patterns)
- **Code:** `backend/om/pulse/` (domain package, like `om/workflows/`):
  - `timing.py`: cron/interval/once, tz/DST, jitter, misfire, templating (pure functions)
  - `scheduler.py`: ticker loop + claim/outbox/reaper/retention
  - `runner.py`: headless executor
  - `notifications.py`
- **Celery:** `om/background/celery/apps/pulse_worker.py` + `configs/pulse_worker.py` +
  `versioned_apps/pulse_worker.py` shim + `tasks/pulse/tasks.py`. These mirror the existing light/heavy apps
  and use `TenantAwareTask`.
- **DB layer:** `om/db/pulse.py` (CRUD).
  - Sessions follow existing patterns: `get_session_with_current_tenant()` / `get_session_with_tenant()`,
    and `SqlEngine.init_engine(...)` at process start, sized to concurrency.
- **API:** `om/server/features/pulse/api.py` + `models.py`, registered in `om/main.py`.
- **Requirements:** `backend/requirements/pulse.txt` (`croniter==6.2.4`).
  - `backend/Dockerfile` COPYs and installs it next to `default.txt`/`ee.txt` (Dockerfile:73-74 pattern),
    because the api_server needs it for `next_run_at` and the preview.
  - Also listed in `combined.txt`.
- **Dockerfile:** `backend/Dockerfile.pulse` is a thin image `FROM ${OM_BACKEND_IMAGE:-om/om-backend:latest}`.
  - Adds `scripts/pulse_entrypoint.sh` (role = scheduler | worker), a healthcheck and labels.
  - Tagged `om/pulse:local`, like `om/cortex:local`.
  - Future Pulse-only packages go here.
- **Compose:** `docker-compose.yml`, `docker-compose.dev-windows.yml` (+ other variants that define
  `background`).
  - **`pulse_scheduler`**:
    - runs `python -m om.pulse.scheduler`, a 5s loop with **2 replicas** by default (HA, safe by design);
    - tiny CPU/RAM footprint;
    - healthcheck = a heartbeat file mtime.
  - **`pulse_worker`**:
    - runs `celery -A om.background.celery.versioned_apps.pulse_worker worker -Q pulse --pool=threads
      --concurrency=${PULSE_WORKER_CONCURRENCY:-4} --prefetch-multiplier=1`;
    - `stop_grace_period: 1900s` (≥ the 1800s workflow max, so a deploy doesn't kill runs);
    - scale with `--scale pulse_worker=N`.
  - Both get the same env block as `background` (DB, Redis, OpenSearch, S3, Cortex, Phoenix, plus
    `CODE_INTERPRETER_BASE_URL`), plus `PULSE_*` settings.
  - Dev-windows mounts are the same as `background`: `../../backend/{om,ee,shared_configs,alembic,
    alembic_tenants}`, `E:/temp/vert/pulse_logs:/var/log/om`, `E:/temp/vert/file-system:/app/file-system`,
    `E:/test_folder_data`.
- **Helm:** `pulse-scheduler.yaml` (Deployment, replicas 2) and `pulse-worker.yaml` + `-hpa.yaml` +
  `-scaledobject.yaml` (KEDA on queue depth), cloned from the `celery-worker-light*` templates; plus
  `values.yaml` entries.
- **Env (`PULSE_*`):**

  | Variable | Default | Notes |
  |---|---|---|
  | `PULSE_TICK_SECONDS` | 5 | |
  | `PULSE_MIN_INTERVAL_SECONDS` | 300 | tests use 60 |
  | `PULSE_MAX_SCHEDULES_PER_USER` | 20 | |
  | `PULSE_TENANT_MAX_CONCURRENT_RUNS` | 8 | |
  | `PULSE_MISFIRE_GRACE_SECONDS` | 300 | |
  | `PULSE_MAX_CONSECUTIVE_FAILURES` | 5 | |
  | `PULSE_DEFAULT_RETENTION` | 50 | |
  | `PULSE_WORKER_CONCURRENCY` | 4 | |

  All are documented in `env.template`.

## Architecture
```
UI /app/schedules  (+ Schedule button on workflow cards) ──REST──► api_server /pulse/*
                                                                       │ writes rows, computes next_run_at
Postgres: pulse_schedule(next_run_at) · pulse_run(UNIQUE sched,for) · chat_session.pulse_schedule_id
      ▲ every 5s: pg_try_advisory_xact_lock + FOR UPDATE SKIP LOCKED → INSERT run ON CONFLICT DO NOTHING
pulse_scheduler ×2 (HA) ── commit → send_task(queue=pulse) ; outbox re-send stale `pending` ;
                           reaper (stale heartbeat → interrupted) ; hourly retention
      ▼
pulse_worker ×N (Celery, threads, prefetch 1, autoscale)
   CAS pending→running · staleness/access/rate-limit checks · create chat session FIRST · heartbeat+deadline
   → stream_chat_message(wrapper agent, chat_session_id) ⇒ ChatSession + ChatMessages + WorkflowExecution
   → map workflow_execution.status → run status · counters · notifications · retention
```

## Data model
Migration `backend/alembic/versions/0009_pulse_schedules.py`, `down_revision = "0008_ombot_flow_rename"`.
Hand-written, applied by api_server on start. Re-point it at merge time if main adds a 0009.

**`pulse_schedule`**
- Identity and ownership: `id`, `workflow_id` (FK, cascade), `user_id` (owner; the run executes as this
  user), `name`, `enabled`.
- When it runs: `schedule_type` (cron | interval | once), `cron_expression`, `interval_seconds`, `run_at`,
  `timezone` (IANA).
- What it sends: `input_message`.
- Run tracking: `next_run_at` (partial index WHERE enabled), `last_run_at`, `last_run_status`,
  `last_success_scheduled_for`, `consecutive_failures`.
- `disabled_reason`, `retention_count`, `created_at`, `updated_at`.

**`pulse_run`**
- `id`, `schedule_id` (FK, cascade), `scheduled_for`, `trigger` (scheduled | manual).
- `status`: pending → running → succeeded | needs_input | failed | timed_out | cancelled | interrupted;
  or skipped | missed.
- Links: `chat_session_id` (FK set null, indexed), `workflow_execution_id`.
- Timing: `started_at`, `heartbeat_at`, `finished_at`, `duration_ms`.
- Output: `output_preview`, `error`, `skip_reason`.
- Indexes: partial UNIQUE(schedule_id, scheduled_for) WHERE trigger='scheduled'; (status, heartbeat_at).

**`chat_session.pulse_schedule_id`**: nullable FK (set null), indexed.

**Cut from v1:** `queued` status, retries, `start_at`/`end_at`, configurable overlap/misfire policies,
file attachments on schedules, and the multi-tenant cloud due-index (v1.1, design documented).

## Semantics (reviewer fixes folded in)
- **Overlap:** always skip; record a `skipped` run. `needs_input` counts as finished.
- **Misfire:**
  - Late by at most the grace: run once.
  - Later than that: record one `missed` row.
  - Either way, then set `next_run_at = next_after(db_now())`. Never loop through the backlog.
- **Next-run computation:**
  - Advance from `scheduled_for` (no drift).
  - Cron runs in the schedule's timezone. DST: a nonexistent time moves to the first valid instant; an
    ambiguous time fires once (`fold=0`). Intervals are pure UTC seconds.
  - `once` disables itself after firing.
  - Deterministic jitter: `hash(id) % min(60s, period/10)`.
  - Always use DB `now()`.
- **Concurrency guards:**
  - Ticker: `pg_try_advisory_xact_lock` per tenant tick, so duplicate replicas are harmless and the
    per-tenant concurrency cap is race-free.
  - Worker: `UPDATE … SET status='running' WHERE status='pending' RETURNING`. Duplicate deliveries become
    no-ops.
  - Outbox: re-send `pending` runs older than 60s.
- **Worker steps:**
  1. Staleness: if `now - scheduled_for > max(grace, period/2)`, mark the run `missed`. This covers Redis
     redelivering a message an hour late.
  2. Access re-check: owner active, workflow not deleted, `get_agent_by_id`. On failure: disable with
     `access_revoked`.
  3. `build_rate_limit_service(db).check(owner)`. If over the limit: record `skipped`.
  4. Create the chat session first (`pulse_schedule_id` set, `ombot_flow=False`). Store its id on the run.
  5. Start a heartbeat + deadline thread. It uses its own tenant session and runs every 30s. The deadline
     calls `set_fence(chat_session_id, True)` (`om/chat/stop_signal_checker.py`), which is a real timeout;
     Celery soft limits are a no-op on thread pools.
  6. Run `stream_chat_message(SendMessageRequest(chat_session_id=…, message=rendered))` +
     `collect_stream_response`, inside try/except.
  7. Map `workflow_execution.status` to the run status.
  8. Save `output_preview`. Update counters; auto-pause at 5 consecutive failures.
  9. Join the agent thread before closing the session.
- **Template variables:** `{{date}}`, `{{now}}`, `{{window_start}}` (the last success's `scheduled_for`),
  `{{window_end}}`.
- **Reaper:** for `running` runs whose heartbeat is older than 90s: mark `interrupted`, set
  `workflow_execution` failed, and write "Run interrupted" into the empty assistant message. Never
  auto-replay. A `worker_shutting_down` handler marks the host's runs `interrupted` immediately.
- **Notifications:** `PULSE_RUN_FAILED`, `PULSE_NEEDS_INPUT`, `PULSE_AUTO_PAUSED` in `NotificationType`, via
  `om/db/notification.py:create_notification`. At most one open notification per schedule per type; none on
  success.
- **Retention:** hourly. Keep the last N run sessions per schedule and soft-delete older ones, except
  sessions the user replied to or shared. Prune run rows after 90 days.

## API — `/pulse` (any user with access to the workflow; admins see all)
- CRUD: `GET`, `POST`, `PATCH /{id}`, `DELETE /{id}`.
- `POST /{id}/run-now`, `POST /{id}/duplicate`.
- `GET /{id}/runs?limit&cursor`.
- `POST /preview`: returns a validation error or a human-readable description + the next 5 DST-correct times.
- Admin: `GET /admin/pulse/health` returns scheduler lag, live scheduler replicas (from heartbeat rows in
  Redis) and counts by status.
- Chat:
  - `GET /converse/get-user-chat-sessions` gets `include_scheduled=false` by default, following the
    `only_non_workspace_chats` pattern.
  - `ChatSessionDetails` gains `pulse_schedule_id`.

## UI (user side; the UI says "Schedules", powered by Pulse)
- **Mockup first, in parallel:**
  - Right after approval, a separate agent builds `docs/scheduled-workflows/mockups/schedules.html` and
    hands it to the user. It is a static, theme-aware file with light/dark and an Ocean/Emerald/Violet
    switcher.
  - Screens: schedule modal with presets and live preview; Schedules table; detail page with run history;
    sidebar "Scheduled" section + badge; empty state; auto-paused banner.
  - Meanwhile the main thread builds the backend. The real UI follows the mockup and is adjusted after user
    feedback.
- **Routes:** `web/src/app/app/schedules/page.tsx`, `[id]/page.tsx` → `refresh-pages/SchedulesPage.tsx`,
  `ScheduleDetailPage.tsx`.
- **Sidebar** (`sections/sidebar/AppSidebar.tsx`, `hooks/useAppFocus.ts`):
  - A "Schedules" tab (`SvgClock`) below Workflows.
  - A collapsible **"Scheduled"** section above "Your chats": one row per schedule, opening the latest run.
  - `ChatButton.tsx` shows a clock badge when `pulse_schedule_id` is set.
- **ScheduleModal** (`sections/schedules/ScheduleModal.tsx` + `FrequencyPicker.tsx`):
  - Fields: workflow, name, input message (pre-filled from the workflow's starter message) + variable chips.
  - Presets:

    | Preset | Stored as |
    |---|---|
    | Every N min/hours | interval |
    | Daily / Weekdays / Weekly / Monthly | cron |
    | Once | `run_at` |
    | Custom | cron |

    `lib/schedules/cron.ts:cronToPreset()` maps a stored schedule back to a preset for editing.
  - Timezone defaults to the browser's.
  - Live preview: a debounced call to `/pulse/preview`.
  - Advanced section.
  - Footer: Cancel · Save & run now · Save.
- **Schedules page:**
  - Table columns: name/workflow · frequency · next run · last run (links to its chat) · enabled Switch ·
    ⋯ menu (Run now / Edit / Duplicate / View runs / Delete).
  - Tabs: All / Active / Paused / Needs attention. Search box. Empty-state templates.
- **Detail page:** run history table with an "Open chat" link per run; auto-pause banner with "Resume".
- **Entry points:** gallery `WorkflowCard.tsx` clock action; admin `WorkflowListPage.tsx` "Schedule" button.
  No workflow fields change, so the dual-editor rule is not triggered.
- **Shared code:** `lib/schedules/{api,interfaces,cron}.ts`, `hooks/useSchedules.ts`.
- **Theme:** components are refresh-components / `@opal`. Accent only via
  `var(--virtualai-accent, var(--theme-primary-05))`.

## Demo workflow — "Scheduled Intelligence Brief"
File: `workflow_creator/workflows/43_scheduled_intel_brief.json`. Sequential, public, timeout 900s.
1. **Knowledge Scout** (SearchTool): reads files through a LocalFolderConnector-watched folder
   (`om/connectors/folder/connector.py:151`).
2. **Web Scout** (WebSearchTool + OpenURLTool): looks for news since `{{window_start}}`; degrades gracefully
   if web search isn't available.
3. **Analyst:** merges and ranks the findings.
4. **Brief Writer:** fixed markdown sections, ends with `STATUS: COMPLETE`.

Default schedule: weekdays at 09:00.

## Phases (each: implement → test → update PROGRESS.md → local commit on the feature branch)
| # | Phase |
|---|---|
| 1 | DESIGN.md + PROGRESS.md; **launch the mockup agent in parallel** |
| 2 | `pulse.txt`, models, migration 0009, `om/db/pulse.py`, `om/pulse/timing.py` + unit tests |
| 3 | `om/pulse/scheduler.py` (ticker/outbox/reaper/retention), constants, Celery `pulse_worker` app/config/shim, `Dockerfile.pulse`, `scripts/pulse_entrypoint.sh`, compose services (all variants), Helm templates, env.template |
| 4 | `om/pulse/runner.py` + `tasks/pulse/tasks.py`, notifications |
| 5 | `/pulse` API + chat-list filter / `pulse_schedule_id` |
| 6 | Frontend per the mockup |
| 7 | Demo workflow + E2E on the test stack |
| 8 | Multi-agent review (concurrency/correctness · security/authz/multi-tenant · frontend/UX/theme) → fix → re-test |
| 9 | USER_GUIDE.md, OPERATIONS.md (env, scaling, metrics, runbook), final PROGRESS.md, `graphify update .` |

## Verification
- **Isolated test stack** (`deployment/docker_compose/docker-compose.pulse-dev.yml`, project `pulsedev`). The
  main `virtualai-*` stack is never touched.
  - `sched_dev` DB is a `pg_dump` clone of `postgres` inside `virtualai-relational_db-1`.
  - Services: `pulse-api` (:8090, same backend image, worktree mounts, runs `alembic upgrade head` itself on
    start), `pulse_scheduler` ×2, `pulse_worker` ×2, and a background beat/light worker (needed for the
    chat/indexing tasks), all on network `virtualai_default`.
  - Env: `POSTGRES_DB=sched_dev`, `REDIS_DB_NUMBER=3`, `REDIS_DB_NUMBER_CELERY=11`,
    `REDIS_DB_NUMBER_CELERY_RESULT_BACKEND=10`, `PULSE_MIN_INTERVAL_SECONDS=60`.
- **Unit tests** (`backend/tests/unit/om/pulse/`):
  - next-fire calculation for cron, interval and once;
  - both 2026 DST transitions (New_York, London) plus Kolkata;
  - misfire within and beyond the grace, with no backlog loop after a week of downtime;
  - jitter bounds, templating, preview validation.
- **DB / concurrency tests** (`backend/tests/external_dependency_unit/pulse/`, against `sched_dev`):
  - 2 scheduler replicas plus 5 concurrent ticks produce exactly 1 run per slot;
  - a CAS double delivery produces 1 execution;
  - outbox re-send;
  - reaper → `interrupted`;
  - overlap skip; `needs_input` does not block;
  - retention exemptions.
- **Integration tests** (`backend/tests/integration/tests/pulse/`, against :8090):
  - CRUD, preview, authz;
  - run-now → `succeeded` + chat session;
  - the chat list hides the session by default and shows it with `include_scheduled`;
  - a 60s interval fires at least twice by itself;
  - a paused schedule doesn't fire;
  - `docker kill` of a `pulse_worker` mid-run → `interrupted` within 90s;
  - deadline → `timed_out`;
  - killing one `pulse_scheduler` replica → schedules still fire (HA).
- **Demo E2E:** deploy `43_*.json` against :8090; drop a file in the watched folder; run-now → the brief
  cites the file.
- **Frontend:**
  - `npm ci` in the worktree's `web/`; `tsgo --noEmit -p tsconfig.types.json`; lint;
  - jest tests for `cronToPreset` and `FrequencyPicker`;
  - a dev server pointed at :8090 for a create → run-now → open chat → sidebar section/badge smoke test.

## Ground rules / user decisions
- Commit LOCALLY at the end of each phase on `feature/scheduled-workflows` only. `git add` explicit paths
  only; **never push** (the repo is public). Record this exception in the scheduled-workflows memory.
- Never run the alembic CLI. Never edit the main checkout or restart `virtualai-*`.
- Chat history: a "Scheduled" sidebar section; runs are excluded from "Your chats" by default.
- Ticker: its own `pulse_scheduler` service, HA with 2 replicas. Runs: the separate `pulse_worker` service.
  Both are built from `Dockerfile.pulse`.
- Multi-tenant cloud due-index: v1.1, documented only.

## Appendix A — Research citations (SOTA survey, 2026-10-24)
- n8n durable scheduler (DB-claimed schedules, leases, misfire grace + policies, default since 2.45):
  https://docs.n8n.io/deploy/host-n8n/configure-n8n/durable-scheduler
- n8n multi-instance double-fire / silent-stop reports (why in-memory timers + leader election was abandoned):
  https://community.n8n.io/t/schedule-trigger-node-triggering-multiple-instances-at-the-same-time/287442 ,
  https://community.n8n.io/t/schedule-trigger-silently-stops-firing-after-several-days-kubernetes-queue-mode/303072
- OpenClaw cron jobs (per-run isolated session, interrupted-not-replayed, auto-disable):
  https://docs.openclaw.ai/automation/cron-jobs/how-it-works , https://docs.openclaw.ai/automation/cron-jobs
- Celery beat single-instance warning: https://docs.celeryq.dev/en/stable/userguide/periodic-tasks.html
- Celery Redis visibility timeout / redelivery: https://docs.celeryq.dev/en/stable/getting-started/backends-and-brokers/redis.html
- RedBeat lock timeout (25 min default failover): https://redbeat.readthedocs.io/en/latest/config.html
- APScheduler 4 still alpha: https://pypi.org/project/APScheduler/#history
- Procrastinate periodic tasks (Postgres uniqueness): https://procrastinate.readthedocs.io/en/stable/howto/advanced/cron.html
- Temporal schedules (overlap policies, catch-up window, jitter): https://docs.temporal.io/evaluate/features/schedules
- Airflow HA scheduler (FOR UPDATE SKIP LOCKED): https://airflow.apache.org/docs/apache-airflow/2.2.3/concepts/scheduler.html ,
  AIP-15 https://cwiki.apache.org/confluence/spaces/AIRFLOW/pages/103092651
- Prefect scheduler service: https://docs.prefect.io/v3/api-ref/python/prefect-server-services-scheduler
- Dagster run_key: https://docs.dagster.io/api/dagster/schedules-sensors
- Kestra recoverMissedSchedules: https://kestra.io/docs/workflow-components/triggers/schedule-trigger
- Trigger.dev dedup key + IANA tz: https://trigger.dev/docs/tasks/scheduled
- Inngest jitter + DST 0/1/2 runs: https://www.inngest.com/docs/guides/scheduled-functions
- croniter 6.2.4 (pallets-eco): https://pypi.org/pypi/croniter/json ; cronsim alternative: https://pypi.org/pypi/cronsim/json

## Appendix B — Reviewer findings folded into the design
Reliability reviewer (20 findings; 5 critical): queued-state race → removed `queued`, CAS pending→running;
Celery soft_time_limit no-op on thread pools → deadline via chat stop fence; cloud beat 8× multiplier → own
`pulse_scheduler` loop; supervisord 10s SIGKILL → own service with 1900s stop grace; crash orphans → session-first +
reaper fixes execution/assistant message; dedicated worker (never share indexing worker); stale redelivery →
staleness check; heartbeat thread tenant/session; result mapping from workflow_execution; paused ≠ active for
overlap; rate-limit + access re-check headless; misfire backlog loop; manual-run unique collision → partial index;
racy tenant cap → advisory lock; jitter; DST rules; sidebar flooding; window_start/window_end variables.
UX reviewer: user-side schedules (non-admins can run workflows); sidebar flooding (50-session cap) → Scheduled
section; presets→single source per type; Save & run now; notifications via existing NotificationType;
retention required in v1; cut overlap/misfire variants, start/end, file attachments.

## Triggers: schedules and webhooks (added 2026-10-31)
This section supersedes the data model above where they differ. A schedule and a webhook are two ways to start a workflow, so what they share moved to a parent table. Migration: `0004_pulse_triggers`.

| Table | Holds |
|---|---|
| `pulse_trigger` | What every kind shares: `kind`, workflow, owner, name, enabled, timezone, `input_message`, retention, last-run fields, failure streak |
| `pulse_schedule` | Timing and input modes (same id as its trigger) |
| `pulse_webhook` | Token hash, signing secret, auth mode, dedup settings, revoke and rotate state, last rejection (same id as its trigger) |
| `pulse_run` | `trigger_id`, `fired_by` (scheduled, manual, webhook), `dedup_key`, `trigger_payload` |

`chat_session.pulse_schedule_id` became `pulse_trigger_id`.

**In code:** joined-table inheritance. `PulseSchedule` and `PulseWebhook` extend `PulseTrigger`, so `select(PulseSchedule)` only returns schedules. Count with `select(func.count()).select_from(PulseSchedule)`; a bare `func.count(PulseSchedule.id)` reads only the parent table and counts every kind.

**Adding a kind:** a table and model, a module in `om/pulse/triggers/` with an input step, and a line in `INPUT_STEPS`. The runner, history, retention and notifications don't change.

**Why webhooks have their own queue and worker:** events arrive in bursts and every event matters, while a schedule only cares about its next slot. On a shared worker a burst would delay schedules until they were recorded as missed. Webhook runs also don't count toward the capacity schedules and Run now are limited by.

**Request order on `POST /hooks/{token}`, cheapest first:** token shape, `Content-Length`, tenant, rate limits, hashed lookup, then read the body with a hard cap, verify the signature over the raw bytes, parse the JSON, and only then store one run. Everything that can't find an open webhook returns the same 404. See `om/pulse/webhooks/intake.py`.

**Payload safety:** values go into the prompt in tags with a random id made at render time, and templates are scanned once, so a payload can't fake the closing tag or expand a placeholder. `apply_input_mapping` is single-pass for the same reason. This reduces prompt injection but can't eliminate it, because the model still reads the text and runs with the owner's tools.

**Not in v1:** sending the result back to the caller (needs SSRF protection), running as a service identity rather than the owner, filters, debounce, and ready-made integrations.
