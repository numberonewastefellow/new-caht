"""`pulse_scheduler` — the HA ticker. Run with: `python -m om.pulse.scheduler`.

Every PULSE_TICK_SECONDS, for each tenant, in ONE transaction:
  1. `pg_try_advisory_xact_lock` (per tenant) — if another replica holds it, skip.
     Two or more replicas are therefore safe: they never double-fire, and if one
     dies the other keeps ticking (no leader election, no single point of failure).
  2. claim due schedules `FOR UPDATE SKIP LOCKED`
  3. per schedule: misfire decision, overlap skip, per-tenant concurrency cap,
     idempotent run insert (UNIQUE schedule_id+scheduled_for), advance next_run_at
  4. commit, THEN enqueue the new runs (transactional outbox)
Housekeeping in the same loop:
  * outbox sweeper — re-enqueue runs stuck in `pending` (enqueue lost after commit)
  * reaper — runs whose worker stopped heart-beating become `interrupted`
  * retention (hourly, one replica via Redis SET NX) — soft-delete old run sessions
"""

import os
import signal
import socket
import threading
import time
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from om.chat.chat_processing_checker import set_processing_status
from om.configs.pulse_configs import PULSE_CLAIM_BATCH_SIZE
from om.configs.pulse_configs import PULSE_MISFIRE_GRACE_SECONDS
from om.configs.pulse_configs import PULSE_PENDING_RESEND_SECONDS
from om.configs.pulse_configs import PULSE_REAP_AFTER_SECONDS
from om.configs.pulse_configs import PULSE_RETENTION_EVERY_SECONDS
from om.configs.pulse_configs import PULSE_RUN_HISTORY_DAYS
from om.configs.pulse_configs import PULSE_SCHEDULER_HEARTBEAT_FILE
from om.configs.pulse_configs import PULSE_TENANT_MAX_CONCURRENT_RUNS
from om.configs.pulse_configs import PULSE_TICK_SECONDS
from om.configs.pulse_configs import PULSE_WEBHOOK_PAYLOAD_RETENTION_DAYS
from om.db.engine.sql_engine import get_session_with_tenant
from om.db.engine.sql_engine import SqlEngine
from om.db.engine.tenant_utils import get_all_tenant_ids
from om.db.models import PulseSchedule
from om.db.pulse import claim_due_schedules
from om.db.pulse import count_active_runs
from om.db.pulse import db_now
from om.db.pulse import DISABLED_COMPLETED_ONCE
from om.db.pulse import fill_empty_assistant_message
from om.db.pulse import get_pulse_trigger
from om.db.pulse import get_sessions_to_expire
from om.db.pulse import claim_stale_pending_runs
from om.db.pulse import get_stale_running_runs
from om.db.pulse import has_active_run
from om.db.pulse import insert_scheduled_run
from om.db.pulse import list_pulse_triggers
from om.db.pulse import prune_old_runs
from om.db.pulse import RUN_INTERRUPTED
from om.db.pulse import RUN_MISSED
from om.db.pulse import RUN_PENDING
from om.db.pulse import RUN_RUNNING
from om.db.pulse import RUN_SKIPPED
from om.db.pulse import soft_delete_sessions
from om.db.pulse import FIRED_SCHEDULED
from om.db.pulse import FIRED_WEBHOOK
from om.db.pulse import try_acquire_tick_lock
from om.db.pulse_webhook import clear_old_payloads
from om.db.workflow import get_latest_execution_by_chat_session
from om.pulse.dispatch import enqueue_pulse_run
from om.pulse.outcome import finalize_run
from om.pulse.spec import spec_from_schedule
from om.pulse.timing import decide_fire
from om.pulse.timing import jitter_seconds
from om.pulse.timing import max_start_delay_seconds
from om.pulse.timing import nominal_period_seconds
from om.redis.redis_pool import get_redis_client
from om.utils.logger import setup_logger
from shared_configs.configs import POSTGRES_DEFAULT_SCHEMA
from shared_configs.contextvars import CURRENT_TENANT_ID_CONTEXTVAR

logger = setup_logger()

POSTGRES_PULSE_SCHEDULER_APP_NAME = "pulse_scheduler"
SCHEDULER_PRESENCE_KEY_PREFIX = "pulse:scheduler:alive:"
RETENTION_LOCK_KEY = "pulse:retention:lock"
INTERRUPTED_MESSAGE = (
    "⚠️ This scheduled run was interrupted (the worker running it stopped). "
    "It was not retried automatically; use Run now on the schedule to run it again."
)


@dataclass
class TickStats:
    locked_out: bool = False
    claimed: int = 0
    fired: int = 0
    skipped_overlap: int = 0
    deferred_capacity: int = 0
    missed: int = 0
    resent: int = 0
    reaped: int = 0
    enqueue: list[tuple[int, int]] = field(default_factory=list)  # (run_id, countdown)


# ---------------------------------------------------------------------------
# one tick for one tenant
# ---------------------------------------------------------------------------


def _process_schedule(
    db_session: Session,
    schedule: PulseSchedule,
    now: datetime,  # from the DB clock
    stats: TickStats,
    capacity: int,
) -> int:
    """Apply the fire decision to one claimed schedule. Returns remaining capacity."""
    assert schedule.next_run_at is not None
    spec = spec_from_schedule(schedule)
    try:
        decision = decide_fire(
            spec,
            due=schedule.next_run_at,
            now=now,
            misfire_grace_seconds=PULSE_MISFIRE_GRACE_SECONDS,
        )
    except Exception:
        # A corrupt schedule must not wedge the tick for everyone else.
        logger.exception(f"Pulse: schedule {schedule.id} has an invalid spec; disabling")
        schedule.enabled = False
        schedule.disabled_reason = "invalid_schedule"
        return capacity

    fire_slot = decision.fire_slot
    if fire_slot is not None:
        if has_active_run(db_session, schedule.id) and spec.schedule_type == "once":
            # A one-time schedule has a single slot: keep it due (retried every tick)
            # rather than consuming it as `skipped`; it becomes `missed` after the grace.
            stats.deferred_capacity += 1
            return capacity
        if has_active_run(db_session, schedule.id):
            insert_scheduled_run(
                db_session,
                schedule_id=schedule.id,
                scheduled_for=fire_slot,
                status=RUN_SKIPPED,
                skip_reason="previous run still in progress",
            )
            stats.skipped_overlap += 1
            fire_slot = None
        elif capacity <= 0:
            # Leave it due; it retries next tick (and becomes `missed` after the grace).
            stats.deferred_capacity += 1
            return capacity

    if decision.missed_slot is not None:
        insert_scheduled_run(
            db_session,
            schedule_id=schedule.id,
            scheduled_for=decision.missed_slot,
            status=RUN_MISSED,
            skip_reason="scheduler was unavailable at this time",
        )
        stats.missed += 1

    if fire_slot is not None:
        run_id = insert_scheduled_run(
            db_session,
            schedule_id=schedule.id,
            scheduled_for=fire_slot,
            status=RUN_PENDING,
        )
        if run_id is not None:
            period = nominal_period_seconds(spec, now=now)
            stats.enqueue.append((run_id, jitter_seconds(schedule.id, period)))
            stats.fired += 1
            capacity -= 1

    schedule.next_run_at = decision.next_run_at
    if decision.next_run_at is None:
        schedule.enabled = False
        schedule.disabled_reason = DISABLED_COMPLETED_ONCE
    return capacity


def tick_tenant(tenant_id: str) -> TickStats:
    stats = TickStats()
    with get_session_with_tenant(tenant_id=tenant_id) as db_session:
        if not try_acquire_tick_lock(db_session, tenant_id):
            db_session.rollback()
            stats.locked_out = True
            # Sweeper + reaper are safe concurrently (SKIP LOCKED + status CAS), so a
            # replica that lost the tick lock still helps with them.
            stats.resent = _resend_stale_pending(tenant_id)
            stats.reaped = _reap_stale_running(tenant_id)
            return stats

        now = db_now(db_session)
        capacity = PULSE_TENANT_MAX_CONCURRENT_RUNS - count_active_runs(db_session)
        schedules = claim_due_schedules(db_session, now, PULSE_CLAIM_BATCH_SIZE)
        stats.claimed = len(schedules)
        for schedule in schedules:
            capacity = _process_schedule(db_session, schedule, now, stats, capacity)
        db_session.commit()  # releases the advisory lock + row locks

    # Outbox: enqueue only after the runs are durably committed.
    for run_id, countdown in stats.enqueue:
        try:
            enqueue_pulse_run(run_id, tenant_id, countdown=countdown)
        except Exception:
            # The sweeper re-sends it; the run stays `pending`.
            logger.exception(f"Pulse: enqueue failed for run {run_id}")

    stats.resent = _resend_stale_pending(tenant_id)
    stats.reaped = _reap_stale_running(tenant_id)
    return stats


def _resend_stale_pending(tenant_id: str) -> int:
    """Outbox sweeper: re-send runs whose enqueue was lost (or that still wait in the
    queue), at most once per PULSE_PENDING_RESEND_SECONDS per run. Scheduled runs
    that are already too late to start are recorded as `missed` instead."""
    ids: list[tuple[int, bool]] = []  # (run_id, is it a webhook run)
    expired: list[tuple[int, int]] = []
    with get_session_with_tenant(tenant_id=tenant_id) as db_session:
        now = db_now(db_session)
        cutoff = now - timedelta(seconds=PULSE_PENDING_RESEND_SECONDS)
        for run in claim_stale_pending_runs(db_session, cutoff):
            trigger = run.trigger
            if run.fired_by == FIRED_SCHEDULED and isinstance(trigger, PulseSchedule):
                limit = max_start_delay_seconds(
                    spec_from_schedule(trigger),
                    misfire_grace_seconds=PULSE_MISFIRE_GRACE_SECONDS,
                    now=now,
                )
                if (now - run.scheduled_for).total_seconds() > limit:
                    expired.append((run.id, trigger.id))
                    continue
            ids.append((run.id, run.fired_by == FIRED_WEBHOOK))
        db_session.commit()  # persists last_enqueued_at before sending (outbox)

        for run_id, trigger_id in expired:
            expired_trigger = get_pulse_trigger(db_session, trigger_id)
            if expired_trigger is not None:
                finalize_run(
                    db_session,
                    expired_trigger,
                    run_id,
                    status=RUN_MISSED,
                    skip_reason="no worker picked it up in time",
                    from_statuses=(RUN_PENDING,),
                )
    for run_id, is_webhook in ids:
        try:
            enqueue_pulse_run(run_id, tenant_id, webhook=is_webhook)
        except Exception:
            logger.exception(f"Pulse: re-enqueue failed for run {run_id}")
    if ids:
        logger.warning(f"Pulse: re-enqueued {len(ids)} stale pending run(s): {ids}")
    return len(ids)


def interrupt_run(
    db_session: Session,
    tenant_id: str,
    *,
    run_id: int,
    trigger_id: int,
    chat_session_id: UUID | None,
    error: str,
) -> bool:
    """Finalise a run whose worker died: `interrupted` (never replayed), failure
    streak + notifications, failed workflow_execution, an explanation in the chat,
    and the chat's stale "processing" flag cleared. Returns True if this call did it."""
    trigger = get_pulse_trigger(db_session, trigger_id)
    if trigger is None:
        return False
    status = finalize_run(
        db_session,
        trigger,
        run_id,
        status=RUN_INTERRUPTED,
        error=error,
        from_statuses=(RUN_RUNNING,),
    )
    if status != RUN_INTERRUPTED:
        return False
    if chat_session_id is not None:
        execution = get_latest_execution_by_chat_session(db_session, chat_session_id)
        if execution is not None and execution.status == "running":
            execution.status = "failed"
            execution.error_message = "Interrupted: worker stopped"
            db_session.commit()
        fill_empty_assistant_message(db_session, chat_session_id, INTERRUPTED_MESSAGE)
        # The dead worker never cleared the chat's "processing" flag (30 min TTL);
        # clear it so the chat page doesn't show "loading" forever.
        try:
            set_processing_status(
                chat_session_id, get_redis_client(tenant_id=tenant_id), False
            )
        except Exception:
            logger.exception("Pulse: failed to clear chat processing flag")
    return True


def _reap_stale_running(tenant_id: str) -> int:
    reaped = 0
    with get_session_with_tenant(tenant_id=tenant_id) as db_session:
        cutoff = db_now(db_session) - timedelta(seconds=PULSE_REAP_AFTER_SECONDS)
        stale = get_stale_running_runs(db_session, cutoff)
        stale_info = [(r.id, r.trigger_id, r.chat_session_id) for r in stale]
        db_session.commit()  # release row locks; finalize_run re-checks status

        for run_id, trigger_id, chat_session_id in stale_info:
            if interrupt_run(
                db_session,
                tenant_id,
                run_id=run_id,
                trigger_id=trigger_id,
                chat_session_id=chat_session_id,
                error="Worker stopped responding (no heartbeat); run was not retried",
            ):
                reaped += 1
    if reaped:
        logger.warning(f"Pulse: reaped {reaped} interrupted run(s) in {tenant_id}")
    return reaped


# ---------------------------------------------------------------------------
# retention (hourly, one replica)
# ---------------------------------------------------------------------------


def run_retention(tenant_id: str) -> tuple[int, int]:
    deleted_sessions = 0
    with get_session_with_tenant(tenant_id=tenant_id) as db_session:
        for trigger in list_pulse_triggers(db_session):
            ids = get_sessions_to_expire(db_session, trigger)
            deleted_sessions += soft_delete_sessions(db_session, ids)
        now = db_now(db_session)
        cutoff = now - timedelta(days=PULSE_RUN_HISTORY_DAYS)
        pruned_runs = prune_old_runs(db_session, cutoff)
        clear_old_payloads(
            db_session, now - timedelta(days=PULSE_WEBHOOK_PAYLOAD_RETENTION_DAYS)
        )
    if deleted_sessions or pruned_runs:
        logger.info(
            f"Pulse retention ({tenant_id}): soft-deleted {deleted_sessions} run "
            f"session(s), pruned {pruned_runs} old run row(s)"
        )
    return deleted_sessions, pruned_runs


def _retention_due() -> bool:
    try:
        r = get_redis_client(tenant_id=POSTGRES_DEFAULT_SCHEMA)
        return bool(
            r.set(RETENTION_LOCK_KEY, "1", nx=True, ex=PULSE_RETENTION_EVERY_SECONDS)
        )
    except Exception:
        logger.exception("Pulse: retention lock check failed")
        return False


# ---------------------------------------------------------------------------
# main loop
# ---------------------------------------------------------------------------


class PulseScheduler:
    def __init__(self) -> None:
        self.hostname = socket.gethostname()
        self._stop = threading.Event()

    def stop(self, *_: object) -> None:
        logger.info("Pulse scheduler: stop requested")
        self._stop.set()

    def _mark_alive(self) -> None:
        try:
            Path(PULSE_SCHEDULER_HEARTBEAT_FILE).touch()
        except OSError:
            pass
        try:
            r = get_redis_client(tenant_id=POSTGRES_DEFAULT_SCHEMA)
            r.set(
                f"{SCHEDULER_PRESENCE_KEY_PREFIX}{self.hostname}",
                str(int(time.time())),
                ex=max(30, PULSE_TICK_SECONDS * 6),
            )
        except Exception:
            logger.exception("Pulse: failed to publish scheduler presence")

    def tick_once(self) -> dict[str, TickStats]:
        results: dict[str, TickStats] = {}
        do_retention = _retention_due()
        for tenant_id in get_all_tenant_ids():
            token = CURRENT_TENANT_ID_CONTEXTVAR.set(tenant_id)
            try:
                stats = tick_tenant(tenant_id)
                results[tenant_id] = stats
                if stats.fired or stats.missed or stats.skipped_overlap or stats.reaped:
                    logger.info(
                        f"Pulse tick {tenant_id}: claimed={stats.claimed} fired={stats.fired} "
                        f"skipped={stats.skipped_overlap} deferred={stats.deferred_capacity} "
                        f"missed={stats.missed} resent={stats.resent} reaped={stats.reaped}"
                    )
                if do_retention:
                    run_retention(tenant_id)
            except Exception:
                logger.exception(f"Pulse: tick failed for tenant {tenant_id}")
            finally:
                CURRENT_TENANT_ID_CONTEXTVAR.reset(token)
        return results

    def run_forever(self) -> None:
        logger.info(
            f"Pulse scheduler starting on {self.hostname} "
            f"(tick={PULSE_TICK_SECONDS}s, pid={os.getpid()})"
        )
        while not self._stop.is_set():
            started = time.monotonic()
            self.tick_once()
            self._mark_alive()
            elapsed = time.monotonic() - started
            self._stop.wait(max(0.0, PULSE_TICK_SECONDS - elapsed))
        logger.info("Pulse scheduler stopped")


def _wait_for_db(max_wait_seconds: int = 300) -> None:
    deadline = time.monotonic() + max_wait_seconds
    while True:
        try:
            with get_session_with_tenant(tenant_id=POSTGRES_DEFAULT_SCHEMA) as db:
                db_now(db)
            return
        except Exception as e:
            if time.monotonic() > deadline:
                raise
            logger.info(f"Pulse scheduler: waiting for database ({e})")
            time.sleep(5)


def main() -> None:
    SqlEngine.set_app_name(POSTGRES_PULSE_SCHEDULER_APP_NAME)
    SqlEngine.init_engine(pool_size=4, max_overflow=4)
    _wait_for_db()

    scheduler = PulseScheduler()
    signal.signal(signal.SIGTERM, scheduler.stop)
    signal.signal(signal.SIGINT, scheduler.stop)
    scheduler.run_forever()


if __name__ == "__main__":
    main()
