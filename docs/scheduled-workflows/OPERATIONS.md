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

## Webhooks
Webhook runs need their own service, `pulse_webhook_worker`: the same image as `pulse_worker`, with `PULSE_WORKER_QUEUE=pulse_webhook`. **Without it, accepted events wait in the queue and never run.** Scale it separately with `docker compose up -d --scale pulse_webhook_worker=N`.

**Helm:** the chart doesn't include this worker or the nginx limits below yet. Add both before using webhooks on Kubernetes.

**Upgrading to `0004_pulse_triggers`:** stop `pulse_scheduler` and `pulse_worker` first, because the old code can't read the renamed tables. Back up the database. Recreate nginx too, or the limits below won't apply.

**Turn them off:** Admin > Workspace > General > "Allow webhooks". Every webhook URL then returns 404 and no new ones can be created. Existing webhooks are kept.

**If a URL or secret leaks:** open the webhook and press Revoke. It stops working at once and runs still waiting are skipped. A run already in progress finishes. The owner can then rotate to get new credentials.

### Signing secrets and the encryption key
Secrets are stored in an `EncryptedString` column, which is only encrypted when `ENCRYPTION_KEY_SECRET` is set. Without it they are plaintext, like every other stored credential, and the create dialog says so. Setting a key on a running system makes existing values unreadable, so it needs a migration of those values first.

### What nginx does
The `/api/hooks/` location in `app.conf.template`, `.prod` and `.no-letsencrypt`:
- Rejects bodies over 1 MB before buffering them. Keep this in step with `PULSE_WEBHOOK_MAX_BODY_BYTES`.
- Logs `/api/hooks/[redacted]` instead of the URL, because the URL contains the token.
- Sets this path's error log to `crit`, because nginx prints the full URL on warnings and errors. Upstream failures on this path therefore show only as status codes in the access log.

### Settings
| Variable | Default | Meaning |
|---|---|---|
| `PULSE_WEBHOOK_WORKER_CONCURRENCY` | 2 | Runs at once per webhook worker |
| `PULSE_WEBHOOK_RATE_PER_IP` | 300 | Requests per minute per address |
| `PULSE_WEBHOOK_RATE_PER_TOKEN` | 120 | Requests per minute per token |
| `PULSE_WEBHOOK_PROXY_HOPS` | 1 | Proxies appending to `X-Forwarded-For`. Too high lets callers choose their own rate-limit bucket; too low puts all callers in one |
| `PULSE_WEBHOOK_MAX_PENDING_RUNS` | 20 | Runs waiting per webhook before callers get 429 |
| `PULSE_WEBHOOK_TENANT_MAX_ACTIVE_RUNS` | 100 | Active webhook runs per tenant. Approximate: calls to different webhooks aren't serialised, so it can overshoot slightly |
| `PULSE_MAX_WEBHOOKS_PER_USER` | 20 | Webhooks per owner |
| `PULSE_WEBHOOK_MAX_BODY_BYTES` | 1048576 | Largest body accepted |
| `PULSE_WEBHOOK_TIMESTAMP_TOLERANCE_SECONDS` | 300 | Allowed clock difference on signatures |
| `PULSE_WEBHOOK_PAYLOAD_RETENTION_DAYS` | 7 | `trigger_payload` is cleared after this; the run row stays. Rendered values also sit in the run's chat, which follows chat retention, not this setting |
| `PULSE_WEBHOOK_LISTEN_TTL_SECONDS` | 300 | How long Listen stays open |

### Observe
`GET /api/admin/pulse/health` (admin only) has a `webhooks` section, and `pulse_workers_alive` for the schedule queue:

| Field | Meaning |
|---|---|
| `workers_alive` | Workers taking new runs. 0 means none, so runs wait. A stopping worker stops counting at once; a crashed one takes up to 90 s. `null` means Redis couldn't be read |
| `pending_runs`, `oldest_pending_seconds` | Runs waiting, and how long the oldest has waited. A growing age means runs are stuck |
| `running_runs`, `active_webhooks` | Runs in progress; webhooks switched on and not revoked |
| `enabled` | The "Allow webhooks" switch. `null` means it couldn't be read, and calls get 503 |
| `secret_encryption_configured` | `false` means `ENCRYPTION_KEY_SECRET` isn't set |

Workers publish a Redis key, `pulse:worker:alive:<queue>:<host>`, every 30 s with a 90 s expiry.

`pulse_webhook_events_total{result}` counts calls by result: `accepted`, `duplicate`, `captured`, or a status code. It's at `/api/metrics`, which needs no login. Each API process keeps its own count and a scrape reaches only one, so use it for trends rather than exact totals. Each webhook also shows its latest refused call and why on its page.

The container healthcheck (`pulse_entrypoint.sh healthcheck`) covers both workers, so `docker compose ps` shows whether each is ready.

### Responses
| Status | Meaning | Should the caller retry? |
|---|---|---|
| 202 | Accepted. Body has `run_id`, and `duplicate: true` for a repeat | No |
| 400 | Body isn't acceptable JSON | No |
| 401 | Signature or secret is wrong, or the timestamp is too old | No |
| 404 | Unknown, paused, revoked, or webhooks are off | No |
| 409 | Test URL used while Listen is closed | No |
| 413 | Body over 1 MB | No |
| 429 | Rate limit or queue full; see `Retry-After` | Yes |
| 503 | Redis is down; see `Retry-After` | Yes |
