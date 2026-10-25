# Pulse — Operations Guide

Pulse is VirtualAI's scheduled-workflow engine (as Cortex is for inference/embeddings).

## Components
| Component | What it does | Scale |
|---|---|---|
| **Postgres** `pulse_schedule`, `pulse_run`, `chat_session.pulse_schedule_id` | Source of truth (migration `0009_pulse_schedules`) | — |
| **`pulse_scheduler`** (`python -m om.pulse.scheduler`) | Every `PULSE_TICK_SECONDS`, per tenant: claims due schedules, creates runs, enqueues them; re-sends lost enqueues; reaps dead runs; hourly retention | **2+ replicas** (HA, safe by design) |
| **`pulse_worker`** (Celery, queue `pulse`) | Executes runs headlessly through the normal chat pipeline → a chat session per run | Horizontal (`--scale`, HPA/KEDA) |
| **api_server** `/pulse/*`, `/admin/pulse/health` | CRUD, preview, run-now, history, sidebar, stats | existing |

Both Pulse services use one image: `om/pulse` (`backend/Dockerfile.pulse`, a thin layer `FROM`
the backend image + `requirements/pulse.txt`), entrypoint `scripts/pulse_entrypoint.sh
scheduler|worker|healthcheck`.

## Why it is safe to run several schedulers (no double-fire, no SPOF)
1. Each tick runs in one transaction that first takes `pg_try_advisory_xact_lock` per tenant —
   replicas that lose the race skip that tick.
2. Due rows are claimed with `SELECT … FOR UPDATE SKIP LOCKED`.
3. Scheduled runs are inserted with `ON CONFLICT DO NOTHING` against the partial unique index
   `(schedule_id, scheduled_for) WHERE trigger='scheduled'` — a slot can never produce two runs.
4. Runs are enqueued only after commit (transactional outbox); runs stuck in `pending` for
   `PULSE_PENDING_RESEND_SECONDS` are re-enqueued.
5. A worker starts a run with a compare-and-swap `pending → running`; duplicate Celery deliveries
   are no-ops. Tasks are acked on receipt and never auto-retried — a half-finished LLM run is
   never replayed.
6. All times come from the database clock (`now()`), not worker clocks.

Verified live: 2 replicas, 60-second schedule → consecutive slots fired once each, 0 duplicate
slots; killing one replica → the other fired the next slots on time.

## Failure handling
| Situation | Behaviour |
|---|---|
| Scheduler down < grace (300s) | Missed slot runs late, once |
| Scheduler down > grace | One `missed` row, then resumes at the next slot (never a backlog) |
| Worker killed mid-run | Heartbeat stops → after `PULSE_REAP_AFTER_SECONDS` (90s) the run is `interrupted`, its workflow execution failed, its chat gets an explanation, the chat "processing" flag is cleared. Not retried. |
| Worker shut down gracefully | Celery's thread pool waits for running runs (`stop_grace_period: 1900s`); a run cut off by SIGKILL is reaped like a crash |
| Run exceeds `min(timeout_seconds, PULSE_MAX_RUN_SECONDS)` + margin | Watchdog sets the chat stop fence → run `timed_out` (Celery soft limits don't work on thread pools). If the engine is stuck where it never checks the fence, the watchdog finalises the run itself at deadline + 2 × margin so the schedule is never blocked |
| Run reaped while still alive (e.g. heartbeats stalled) | The next heartbeat sees the run is no longer `running` and stops the workflow |
| Unexpected error inside the worker | Run `failed` with a reference id (details in the worker log), never left `running` |
| Late redelivery (e.g. Redis visibility timeout) | Worker sees the run is stale → `missed` |
| Previous run still active | New slot recorded as `skipped` |
| Tenant at `PULSE_TENANT_MAX_CONCURRENT_RUNS` | Slot stays due and retries next tick (becomes `missed` after the grace) |
| Owner deactivated / workflow deleted / access revoked | Run `skipped`, schedule disabled (`access_revoked` / `workflow_deleted`) |
| Rate-limit policy exceeded | Run `skipped` (same policy engine as chat) |
| 5 failures in a row (`PULSE_MAX_CONSECUTIVE_FAILURES`) | Schedule auto-paused (`auto_paused_failures`) + notification |

## Security model
- Runs execute **as the schedule owner** (their document access, files and connected
  accounts). Therefore only the owner can edit what runs, resume, duplicate or Run now.
  Admins can list everyone's schedules (prompts and outputs hidden), pause and delete.
- Every run re-checks the owner like an API request: active, not LIMITED, verified (when
  required), unexpired OIDC session, access to the workflow and its wrapper agent.
- Abuse limits: total + active schedule caps (serialised per user), min interval,
  Run-now cooldown, per-user and per-tenant active-run caps (429), the tenant rate-limit
  policies (chat token budgets) for both Run now and scheduled runs.
- Helm: Pulse pods are non-privileged (`allowPrivilegeEscalation: false`, all
  capabilities dropped) and don't mount a service-account token. Known follow-ups: the
  image still runs as root like the backend image; step agents are not re-checked
  individually (same as interactive workflow runs).

## Configuration (env)
| Variable | Default | Used by |
|---|---|---|
| `PULSE_TICK_SECONDS` | 5 | scheduler |
| `PULSE_CLAIM_BATCH_SIZE` | 100 | scheduler |
| `PULSE_MIN_INTERVAL_SECONDS` | 300 | api |
| `PULSE_MAX_SCHEDULES_PER_USER` | 20 (active) | api |
| `PULSE_MAX_TOTAL_SCHEDULES_PER_USER` | 50 (incl. paused) | api |
| `PULSE_MANUAL_RUN_COOLDOWN_SECONDS` | 30 (Run now, per schedule) | api |
| `PULSE_USER_MAX_ACTIVE_RUNS` | 3 (Run now, per user) | api |
| `PULSE_MAX_RUN_SECONDS` | 1800 (hard cap per run) | worker |
| `PULSE_TENANT_MAX_CONCURRENT_RUNS` | 8 | scheduler |
| `PULSE_MISFIRE_GRACE_SECONDS` | 300 | scheduler, worker |
| `PULSE_MAX_CONSECUTIVE_FAILURES` | 5 (0 = never) | worker, scheduler |
| `PULSE_DEFAULT_RETENTION` / `PULSE_MAX_RETENTION` | 50 / 500 | api, scheduler |
| `PULSE_RUN_HISTORY_DAYS` | 90 | scheduler |
| `PULSE_HEARTBEAT_SECONDS` / `PULSE_REAP_AFTER_SECONDS` | 30 / 90 | worker / scheduler |
| `PULSE_PENDING_RESEND_SECONDS` | 120 | scheduler |
| `PULSE_DEADLINE_MARGIN_SECONDS` | 60 | worker |
| `PULSE_WORKER_CONCURRENCY` | 4 (threads; also DB pool size) | worker |
| `PULSE_SCHEDULER_REPLICAS` | 2 | compose |

## Deploy
**Docker Compose** (`docker-compose.yml`, `docker-compose.dev-windows.yml`, `docker-compose.prod*.yml`):
```bash
docker compose build api_server            # backend image (installs requirements/pulse.txt)
docker compose build pulse_scheduler       # om/pulse image FROM the backend image
docker compose up -d                       # api_server applies migration 0009 on start
docker compose up -d --scale pulse_worker=3   # more run capacity
```
**Helm**: `pulse.enabled` (default true) renders `pulse-scheduler` (replicas 2) and
`pulse-worker` (+ HPA, or a KEDA ScaledObject when KEDA is the autoscaling engine). For KEDA
queue-depth scaling, note Celery's Redis priority lists: Pulse tasks go to the list `pulse:2`
(see the commented trigger in `values.yaml`).

## Observe
- `GET /api/admin/pulse/health` → `scheduler_replicas_alive`, `scheduler_lag_seconds`
  (oldest overdue enabled schedule), `active_runs`, `enabled_schedules`, 24h runs by status.
  Alert if replicas = 0 or lag > 60s.
- Logs: scheduler prints a line per tick that did something
  (`Pulse tick public: claimed=… fired=… skipped=… missed=… resent=… reaped=…`).
- Healthchecks: scheduler = heartbeat file touched every tick; worker = Celery readiness file.
- SQL: `select status, count(*) from pulse_run where created_at > now() - interval '1 day' group by 1;`

## Runbook
- **Schedules not firing**: check `/admin/pulse/health` (replicas, lag); `docker logs pulse_scheduler`;
  confirm migration 0009 applied (`select version_num from alembic_version`).
- **Runs stuck in pending**: no worker consuming `pulse` → `docker compose ps pulse_worker`; the
  sweeper re-sends every 120s, so they start as soon as a worker is up (stale ones become `missed`).
- **Many `interrupted`**: workers are being killed (OOM? deploys without grace period?).
- **A schedule paused itself**: open it, read the last run's error, fix, click Resume.

## Multi-tenant (cloud) note — v1.1
The scheduler loops over all tenant schemas each tick (fine for self-hosted / a few tenants). For
thousands of tenants, add a `public.pulse_schedule_due(tenant_id, schedule_id, next_run_at)` index
written in the same transaction as the tenant row, and have the scheduler fan out only to tenants
with due work.
