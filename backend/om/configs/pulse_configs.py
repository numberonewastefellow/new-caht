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

# Scheduler liveness file (docker/k8s healthcheck checks its mtime)
PULSE_SCHEDULER_HEARTBEAT_FILE = os.environ.get(
    "PULSE_SCHEDULER_HEARTBEAT_FILE", "/tmp/pulse_scheduler.heartbeat"
)
