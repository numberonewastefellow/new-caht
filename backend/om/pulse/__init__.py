"""Pulse — scheduled workflow engine.

Triggers start workflows automatically, and a schedule is one kind (see
om/pulse/triggers). Schedules (cron / interval / once) live in Postgres
(`pulse_schedule`, joined to `pulse_trigger`). One or more
`pulse_scheduler` replicas claim due rows and enqueue runs on the `pulse` Celery queue,
which `pulse_worker` processes headlessly. Each run becomes its own chat session.

Modules:
    timing     — pure scheduling math (cron/interval/once, timezones/DST, misfire, jitter, templating)
    scheduler  — the HA ticker loop (claim → outbox → reaper → retention)
    runner     — headless executor for a single run
"""
