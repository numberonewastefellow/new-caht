"""Pulse (scheduled workflow engine) settings. All overridable via environment."""

import os


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name) or default)
    except ValueError:
        return default


# How often each pulse_scheduler replica ticks (seconds)
PULSE_TICK_SECONDS = max(1, _int_env("PULSE_TICK_SECONDS", 5))
# Max due schedules claimed per tick per tenant
PULSE_CLAIM_BATCH_SIZE = _int_env("PULSE_CLAIM_BATCH_SIZE", 100)

# Guard rails for users
PULSE_MIN_INTERVAL_SECONDS = _int_env("PULSE_MIN_INTERVAL_SECONDS", 300)
PULSE_MAX_SCHEDULES_PER_USER = _int_env("PULSE_MAX_SCHEDULES_PER_USER", 20)
# Paused schedules count here too, so "create many paused + Run now" can't bypass limits
PULSE_MAX_TOTAL_SCHEDULES_PER_USER = _int_env("PULSE_MAX_TOTAL_SCHEDULES_PER_USER", 50)
# Run now: per-schedule cooldown and per-user cap on simultaneously pending/running runs
PULSE_MANUAL_RUN_COOLDOWN_SECONDS = _int_env("PULSE_MANUAL_RUN_COOLDOWN_SECONDS", 30)
PULSE_USER_MAX_ACTIVE_RUNS = _int_env("PULSE_USER_MAX_ACTIVE_RUNS", 3)
# Hard ceiling on a single run, whatever the workflow's own timeout says
PULSE_MAX_RUN_SECONDS = _int_env("PULSE_MAX_RUN_SECONDS", 1800)
# Max concurrently pending/running scheduled runs per tenant (backpressure)
PULSE_TENANT_MAX_CONCURRENT_RUNS = _int_env("PULSE_TENANT_MAX_CONCURRENT_RUNS", 8)

# A run may start at most this late (or half its period, whichever is larger)
PULSE_MISFIRE_GRACE_SECONDS = _int_env("PULSE_MISFIRE_GRACE_SECONDS", 300)
# Auto-pause a schedule after this many failed runs in a row (0 disables)
PULSE_MAX_CONSECUTIVE_FAILURES = _int_env("PULSE_MAX_CONSECUTIVE_FAILURES", 5)
# Default number of run chat sessions kept per schedule
PULSE_DEFAULT_RETENTION = _int_env("PULSE_DEFAULT_RETENTION", 50)
PULSE_MAX_RETENTION = _int_env("PULSE_MAX_RETENTION", 500)
# Run history rows older than this are pruned
PULSE_RUN_HISTORY_DAYS = _int_env("PULSE_RUN_HISTORY_DAYS", 90)

# Worker heartbeat cadence and reaper threshold (seconds)
PULSE_HEARTBEAT_SECONDS = _int_env("PULSE_HEARTBEAT_SECONDS", 30)
PULSE_REAP_AFTER_SECONDS = _int_env("PULSE_REAP_AFTER_SECONDS", 90)
# Outbox: re-send runs stuck in `pending` longer than this (> max jitter of 60s)
PULSE_PENDING_RESEND_SECONDS = _int_env("PULSE_PENDING_RESEND_SECONDS", 120)
# Extra time beyond the workflow's own timeout before the run is force-stopped
PULSE_DEADLINE_MARGIN_SECONDS = _int_env("PULSE_DEADLINE_MARGIN_SECONDS", 60)
# Retention / pruning cadence
PULSE_RETENTION_EVERY_SECONDS = _int_env("PULSE_RETENTION_EVERY_SECONDS", 3600)

# Worker concurrency (threads) — also sizes the worker's DB pool
PULSE_WORKER_CONCURRENCY = _int_env("PULSE_WORKER_CONCURRENCY", 4)
# The queue this worker serves; pulse_entrypoint.sh passes the same value to Celery
PULSE_WORKER_QUEUE = os.environ.get("PULSE_WORKER_QUEUE") or "pulse"

# ---------------------------------------------------------------------------
# Webhooks
# ---------------------------------------------------------------------------
# Largest request body accepted. nginx enforces the same limit (app.conf.template).
PULSE_WEBHOOK_MAX_BODY_BYTES = _int_env("PULSE_WEBHOOK_MAX_BODY_BYTES", 1024 * 1024)
# Requests per minute, before any database work
PULSE_WEBHOOK_RATE_PER_IP = _int_env("PULSE_WEBHOOK_RATE_PER_IP", 300)
PULSE_WEBHOOK_RATE_PER_TOKEN = _int_env("PULSE_WEBHOOK_RATE_PER_TOKEN", 120)
# Proxies in front of the API that append to X-Forwarded-For (nginx = 1). 0 trusts only
# the socket peer. Too high lets a caller choose their own rate-limit bucket.
PULSE_WEBHOOK_PROXY_HOPS = _int_env("PULSE_WEBHOOK_PROXY_HOPS", 1)
# How far a signature's timestamp may be from now, either way
PULSE_WEBHOOK_TIMESTAMP_TOLERANCE_SECONDS = _int_env(
    "PULSE_WEBHOOK_TIMESTAMP_TOLERANCE_SECONDS", 300
)
# Runs waiting per webhook before callers get 429, and per tenant across all webhooks
PULSE_WEBHOOK_MAX_PENDING_RUNS = _int_env("PULSE_WEBHOOK_MAX_PENDING_RUNS", 20)
PULSE_WEBHOOK_TENANT_MAX_ACTIVE_RUNS = _int_env(
    "PULSE_WEBHOOK_TENANT_MAX_ACTIVE_RUNS", 100
)
PULSE_MAX_WEBHOOKS_PER_USER = _int_env("PULSE_MAX_WEBHOOKS_PER_USER", 20)
# JSON shape limits, checked after the signature
PULSE_WEBHOOK_MAX_JSON_DEPTH = _int_env("PULSE_WEBHOOK_MAX_JSON_DEPTH", 32)
PULSE_WEBHOOK_MAX_JSON_NODES = _int_env("PULSE_WEBHOOK_MAX_JSON_NODES", 20000)
# Characters of payload put in the prompt: per {{payload.x}} value, and for {{payload}}
PULSE_WEBHOOK_MAX_VALUE_CHARS = _int_env("PULSE_WEBHOOK_MAX_VALUE_CHARS", 4000)
PULSE_WEBHOOK_MAX_PAYLOAD_CHARS = _int_env("PULSE_WEBHOOK_MAX_PAYLOAD_CHARS", 32000)
# Stored payloads are cleared after this long (the run row itself stays for history)
PULSE_WEBHOOK_PAYLOAD_RETENTION_DAYS = _int_env("PULSE_WEBHOOK_PAYLOAD_RETENTION_DAYS", 7)
# Listen mode stays open this long, and old credentials keep working after a rotate
PULSE_WEBHOOK_LISTEN_TTL_SECONDS = _int_env("PULSE_WEBHOOK_LISTEN_TTL_SECONDS", 300)
PULSE_WEBHOOK_MAX_ROTATION_GRACE_HOURS = _int_env("PULSE_WEBHOOK_MAX_ROTATION_GRACE_HOURS", 168)

# Scheduler liveness file (docker/k8s healthcheck checks its mtime)
PULSE_SCHEDULER_HEARTBEAT_FILE = os.environ.get(
    "PULSE_SCHEDULER_HEARTBEAT_FILE", "/tmp/pulse_scheduler.heartbeat"
)
