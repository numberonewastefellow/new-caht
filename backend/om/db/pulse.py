"""DB operations for Pulse (scheduled workflow runs).

Concurrency model (see docs/scheduled-workflows/DESIGN.md):
  * `pulse_scheduler` replicas serialise per tenant with `pg_try_advisory_xact_lock`
    and claim due schedules with `FOR UPDATE SKIP LOCKED`.
  * Scheduled runs are inserted with ON CONFLICT DO NOTHING against the partial unique
    index (schedule_id, scheduled_for) — a slot can never produce two runs.
  * A worker starts a run with a compare-and-swap (pending -> running); duplicate
    Celery deliveries become no-ops.
All timestamps written here come from the database clock (`now()`).
"""

import datetime
from uuid import UUID

from sqlalchemy import and_
from sqlalchemy import cast
from sqlalchemy import func
from sqlalchemy import Integer
from sqlalchemy import select
from sqlalchemy import text
from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from om.configs.constants import MessageType
from om.db.enums import ChatSessionSharedStatus
from om.db.models import ChatMessage
from om.db.models import ChatSession
from om.db.models import PulseRun
from om.db.models import PulseSchedule
from om.utils.logger import setup_logger

logger = setup_logger()

# Run statuses
RUN_PENDING = "pending"
RUN_RUNNING = "running"
RUN_SUCCEEDED = "succeeded"
RUN_NEEDS_INPUT = "needs_input"
RUN_FAILED = "failed"
RUN_TIMED_OUT = "timed_out"
RUN_CANCELLED = "cancelled"
RUN_INTERRUPTED = "interrupted"
RUN_SKIPPED = "skipped"
RUN_MISSED = "missed"

ACTIVE_RUN_STATUSES = (RUN_PENDING, RUN_RUNNING)
# Statuses that count toward consecutive_failures / auto-pause
FAILURE_RUN_STATUSES = (RUN_FAILED, RUN_TIMED_OUT, RUN_INTERRUPTED)
TERMINAL_RUN_STATUSES = (
    RUN_SUCCEEDED,
    RUN_NEEDS_INPUT,
    RUN_FAILED,
    RUN_TIMED_OUT,
    RUN_CANCELLED,
    RUN_INTERRUPTED,
    RUN_SKIPPED,
    RUN_MISSED,
)

TRIGGER_SCHEDULED = "scheduled"
TRIGGER_MANUAL = "manual"

# disabled_reason values set by the system
DISABLED_AUTO_PAUSED = "auto_paused_failures"
DISABLED_ACCESS_REVOKED = "access_revoked"
DISABLED_COMPLETED_ONCE = "completed_once"
DISABLED_WORKFLOW_DELETED = "workflow_deleted"

# Advisory lock key namespace for the per-tenant scheduler tick
_TICK_LOCK_SQL = text("SELECT pg_try_advisory_xact_lock(hashtext(:key))")
TICK_LOCK_KEY = "om:pulse:scheduler_tick"


def db_now(db_session: Session) -> datetime.datetime:
    """The database clock (single source of time for all replicas)."""
    return db_session.execute(select(func.now())).scalar_one()


# ========================
# Schedule CRUD
# ========================


def create_pulse_schedule(
    db_session: Session,
    *,
    user_id: UUID,
    workflow_id: int,
    name: str,
    schedule_type: str,
    cron_expression: str | None,
    interval_seconds: int | None,
    run_at: datetime.datetime | None,
    timezone: str,
    input_message: str,
    enabled: bool,
    retention_count: int,
    next_run_at: datetime.datetime | None,
) -> PulseSchedule:
    schedule = PulseSchedule(
        user_id=user_id,
        workflow_id=workflow_id,
        name=name,
        schedule_type=schedule_type,
        cron_expression=cron_expression,
        interval_seconds=interval_seconds,
        run_at=run_at,
        timezone=timezone,
        input_message=input_message,
        enabled=enabled,
        retention_count=retention_count,
        next_run_at=next_run_at,
        consecutive_failures=0,
    )
    db_session.add(schedule)
    db_session.commit()
    db_session.refresh(schedule)
    return schedule


def get_pulse_schedule(db_session: Session, schedule_id: int) -> PulseSchedule | None:
    return db_session.get(PulseSchedule, schedule_id)


def get_pulse_schedule_for_user(
    db_session: Session,
    schedule_id: int,
    user_id: UUID | None,
    is_admin: bool,
) -> PulseSchedule | None:
    schedule = db_session.get(PulseSchedule, schedule_id)
    if schedule is None:
        return None
    if not is_admin and schedule.user_id != user_id:
        return None
    return schedule


def list_pulse_schedules(
    db_session: Session,
    user_id: UUID | None,
    include_all_users: bool = False,
) -> list[PulseSchedule]:
    stmt = select(PulseSchedule).order_by(PulseSchedule.created_at.desc())
    if not include_all_users:
        stmt = stmt.where(PulseSchedule.user_id == user_id)
    return list(db_session.execute(stmt).scalars().all())


def count_enabled_schedules_for_user(db_session: Session, user_id: UUID) -> int:
    return db_session.execute(
        select(func.count(PulseSchedule.id))
        .where(PulseSchedule.user_id == user_id)
        .where(PulseSchedule.enabled.is_(True))
    ).scalar_one()


def delete_pulse_schedule(db_session: Session, schedule: PulseSchedule) -> None:
    db_session.delete(schedule)
    db_session.commit()


def disable_schedule(
    db_session: Session,
    schedule_id: int,
    reason: str | None,
    autocommit: bool = True,
) -> None:
    db_session.execute(
        update(PulseSchedule)
        .where(PulseSchedule.id == schedule_id)
        .values(enabled=False, disabled_reason=reason)
    )
    if autocommit:
        db_session.commit()


# ========================
# Run queries
# ========================


def get_pulse_run(db_session: Session, run_id: int) -> PulseRun | None:
    return db_session.get(PulseRun, run_id)


def list_runs_for_schedule(
    db_session: Session,
    schedule_id: int,
    limit: int = 50,
    before_id: int | None = None,
) -> list[PulseRun]:
    stmt = (
        select(PulseRun)
        .where(PulseRun.schedule_id == schedule_id)
        .order_by(PulseRun.id.desc())
        .limit(limit)
    )
    if before_id is not None:
        stmt = stmt.where(PulseRun.id < before_id)
    return list(db_session.execute(stmt).scalars().all())


def get_latest_runs_by_schedule(
    db_session: Session, schedule_ids: list[int]
) -> dict[int, PulseRun]:
    """Most recent run (by id) for each schedule."""
    if not schedule_ids:
        return {}
    latest_ids = (
        select(func.max(PulseRun.id).label("id"))
        .where(PulseRun.schedule_id.in_(schedule_ids))
        .where(PulseRun.status.notin_((RUN_SKIPPED, RUN_MISSED)))
        .group_by(PulseRun.schedule_id)
        .subquery()
    )
    runs = db_session.execute(
        select(PulseRun).where(PulseRun.id.in_(select(latest_ids.c.id)))
    ).scalars()
    return {run.schedule_id: run for run in runs}


def get_latest_session_run_by_schedule(
    db_session: Session, schedule_ids: list[int]
) -> dict[int, PulseRun]:
    """Most recent run that has a chat session, per schedule (sidebar 'Scheduled')."""
    if not schedule_ids:
        return {}
    latest_ids = (
        select(func.max(PulseRun.id).label("id"))
        .where(PulseRun.schedule_id.in_(schedule_ids))
        .where(PulseRun.chat_session_id.is_not(None))
        .group_by(PulseRun.schedule_id)
        .subquery()
    )
    runs = db_session.execute(
        select(PulseRun).where(PulseRun.id.in_(select(latest_ids.c.id)))
    ).scalars()
    return {run.schedule_id: run for run in runs}


def count_runs_by_status_since(
    db_session: Session,
    since: datetime.datetime,
    user_id: UUID | None = None,
) -> dict[str, int]:
    stmt = (
        select(PulseRun.status, func.count(PulseRun.id))
        .where(PulseRun.created_at >= since)
        .group_by(PulseRun.status)
    )
    if user_id is not None:
        stmt = stmt.join(PulseSchedule, PulseSchedule.id == PulseRun.schedule_id).where(
            PulseSchedule.user_id == user_id
        )
    return {status: count for status, count in db_session.execute(stmt).all()}


def has_active_run(db_session: Session, schedule_id: int) -> bool:
    return (
        db_session.execute(
            select(PulseRun.id)
            .where(PulseRun.schedule_id == schedule_id)
            .where(PulseRun.status.in_(ACTIVE_RUN_STATUSES))
            .limit(1)
        ).first()
        is not None
    )


def count_active_runs(db_session: Session) -> int:
    return db_session.execute(
        select(func.count(PulseRun.id)).where(
            PulseRun.status.in_(ACTIVE_RUN_STATUSES)
        )
    ).scalar_one()


def create_manual_run(db_session: Session, schedule_id: int) -> PulseRun:
    run = PulseRun(
        schedule_id=schedule_id,
        scheduled_for=db_now(db_session),
        trigger=TRIGGER_MANUAL,
        status=RUN_PENDING,
    )
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)
    return run


# ========================
# Scheduler primitives (used inside one transaction per tick)
# ========================


def try_acquire_tick_lock(db_session: Session) -> bool:
    """Per-tenant, transaction-scoped advisory lock. Released on commit/rollback."""
    return bool(
        db_session.execute(_TICK_LOCK_SQL, {"key": TICK_LOCK_KEY}).scalar_one()
    )


def claim_due_schedules(
    db_session: Session, now: datetime.datetime, limit: int
) -> list[PulseSchedule]:
    """Due + enabled schedules, row-locked. SKIP LOCKED lets an API edit (which
    holds the row lock) proceed without blocking the tick and vice versa."""
    stmt = (
        select(PulseSchedule)
        .where(PulseSchedule.enabled.is_(True))
        .where(PulseSchedule.next_run_at.is_not(None))
        .where(PulseSchedule.next_run_at <= now)
        .order_by(PulseSchedule.next_run_at)
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    return list(db_session.execute(stmt).scalars().all())


def insert_scheduled_run(
    db_session: Session,
    *,
    schedule_id: int,
    scheduled_for: datetime.datetime,
    status: str,
    skip_reason: str | None = None,
) -> int | None:
    """Idempotent insert of a scheduled slot. Returns the new run id, or None if
    the slot already exists (another replica / previous tick won)."""
    values: dict = {
        "schedule_id": schedule_id,
        "scheduled_for": scheduled_for,
        "trigger": TRIGGER_SCHEDULED,
        "status": status,
        "skip_reason": skip_reason,
    }
    if status in TERMINAL_RUN_STATUSES:
        values["finished_at"] = func.now()
    stmt = (
        insert(PulseRun)
        .values(**values)
        .on_conflict_do_nothing(
            index_elements=["schedule_id", "scheduled_for"],
            index_where=text("trigger = 'scheduled'"),
        )
        .returning(PulseRun.id)
    )
    return db_session.execute(stmt).scalar_one_or_none()


def get_stale_pending_runs(
    db_session: Session, older_than: datetime.datetime, limit: int = 200
) -> list[PulseRun]:
    return list(
        db_session.execute(
            select(PulseRun)
            .where(PulseRun.status == RUN_PENDING)
            .where(PulseRun.created_at < older_than)
            .order_by(PulseRun.id)
            .limit(limit)
        )
        .scalars()
        .all()
    )


def get_stale_running_runs(
    db_session: Session, heartbeat_before: datetime.datetime, limit: int = 200
) -> list[PulseRun]:
    """Running runs whose worker stopped heart-beating (crash / kill)."""
    return list(
        db_session.execute(
            select(PulseRun)
            .where(PulseRun.status == RUN_RUNNING)
            .where(
                func.coalesce(PulseRun.heartbeat_at, PulseRun.started_at)
                < heartbeat_before
            )
            .order_by(PulseRun.id)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        .scalars()
        .all()
    )


# ========================
# Worker primitives
# ========================


def start_run(db_session: Session, run_id: int, hostname: str) -> PulseRun | None:
    """CAS pending -> running. Returns the run if this caller won, else None."""
    result = db_session.execute(
        update(PulseRun)
        .where(PulseRun.id == run_id)
        .where(PulseRun.status == RUN_PENDING)
        .values(
            status=RUN_RUNNING,
            started_at=func.now(),
            heartbeat_at=func.now(),
            worker_hostname=hostname,
        )
        .returning(PulseRun.id)
    )
    won = result.scalar_one_or_none()
    db_session.commit()
    if won is None:
        return None
    run = db_session.get(PulseRun, run_id)
    if run is not None:
        db_session.refresh(run)
    return run


def heartbeat_run(db_session: Session, run_id: int) -> None:
    db_session.execute(
        update(PulseRun)
        .where(PulseRun.id == run_id)
        .where(PulseRun.status == RUN_RUNNING)
        .values(heartbeat_at=func.now())
    )
    db_session.commit()


def finish_run(
    db_session: Session,
    run_id: int,
    *,
    status: str,
    from_statuses: tuple[str, ...] = (RUN_PENDING, RUN_RUNNING),
    error: str | None = None,
    skip_reason: str | None = None,
    output_preview: str | None = None,
    workflow_execution_id: int | None = None,
) -> bool:
    """Move a run to a terminal status (only from `from_statuses`, so a reaped run
    is never overwritten by a late worker and vice versa). Returns True if updated."""
    values: dict = {
        "status": status,
        "finished_at": func.now(),
        "duration_ms": cast(
            func.extract(
                "epoch", func.now() - func.coalesce(PulseRun.started_at, func.now())
            )
            * 1000,
            Integer,
        ),
    }
    if error is not None:
        values["error"] = error[:4000]
    if skip_reason is not None:
        values["skip_reason"] = skip_reason
    if output_preview is not None:
        values["output_preview"] = output_preview
    if workflow_execution_id is not None:
        values["workflow_execution_id"] = workflow_execution_id
    result = db_session.execute(
        update(PulseRun)
        .where(PulseRun.id == run_id)
        .where(PulseRun.status.in_(from_statuses))
        .values(**values)
        .returning(PulseRun.id)
    )
    updated = result.scalar_one_or_none() is not None
    db_session.commit()
    return updated


def set_run_chat_session(
    db_session: Session, run_id: int, chat_session_id: UUID
) -> None:
    db_session.execute(
        update(PulseRun)
        .where(PulseRun.id == run_id)
        .values(chat_session_id=chat_session_id)
    )
    db_session.commit()


def record_schedule_outcome(
    db_session: Session,
    schedule_id: int,
    *,
    run_status: str,
    scheduled_for: datetime.datetime,
    max_consecutive_failures: int,
) -> tuple[int, bool]:
    """Update the schedule's last-run fields + failure streak.

    Returns (consecutive_failures, auto_paused_now). Row-locked so concurrent
    finishes for the same schedule (manual + scheduled) do not lose updates.
    """
    schedule = db_session.execute(
        select(PulseSchedule)
        .where(PulseSchedule.id == schedule_id)
        .with_for_update()
    ).scalar_one_or_none()
    if schedule is None:
        db_session.commit()
        return 0, False

    schedule.last_run_at = db_now(db_session)
    schedule.last_run_status = run_status
    auto_paused = False
    if run_status == RUN_SUCCEEDED:
        schedule.consecutive_failures = 0
        if (
            schedule.last_success_scheduled_for is None
            or scheduled_for > schedule.last_success_scheduled_for
        ):
            schedule.last_success_scheduled_for = scheduled_for
    elif run_status in FAILURE_RUN_STATUSES:
        schedule.consecutive_failures = (schedule.consecutive_failures or 0) + 1
        if (
            max_consecutive_failures > 0
            and schedule.consecutive_failures >= max_consecutive_failures
            and schedule.enabled
        ):
            schedule.enabled = False
            schedule.disabled_reason = DISABLED_AUTO_PAUSED
            auto_paused = True
    failures = schedule.consecutive_failures
    db_session.commit()
    return failures, auto_paused


def interrupt_runs_for_host(db_session: Session, hostname: str) -> list[int]:
    """Mark this host's running runs interrupted (graceful worker shutdown)."""
    result = db_session.execute(
        update(PulseRun)
        .where(PulseRun.status == RUN_RUNNING)
        .where(PulseRun.worker_hostname == hostname)
        .values(
            status=RUN_INTERRUPTED,
            finished_at=func.now(),
            error="Worker shut down while the run was in progress",
        )
        .returning(PulseRun.id)
    )
    ids = [row[0] for row in result.all()]
    db_session.commit()
    return ids


def latest_assistant_message(
    db_session: Session, chat_session_id: UUID
) -> ChatMessage | None:
    return db_session.execute(
        select(ChatMessage)
        .where(ChatMessage.chat_session_id == chat_session_id)
        .where(ChatMessage.message_type == MessageType.ASSISTANT)
        .order_by(ChatMessage.id.desc())
        .limit(1)
    ).scalar_one_or_none()


def fill_empty_assistant_message(
    db_session: Session, chat_session_id: UUID, text: str
) -> None:
    """Give a run that died mid-flight a visible explanation in its chat."""
    message = latest_assistant_message(db_session, chat_session_id)
    if message is not None and not (message.message or "").strip():
        message.message = text
        db_session.commit()


# ========================
# Retention
# ========================


def get_sessions_to_expire(
    db_session: Session, schedule: PulseSchedule, limit: int = 500
) -> list[UUID]:
    """Run chat sessions beyond the schedule's retention_count (newest kept).

    Exempt: sessions the user replied in (more than one USER message) and shared
    sessions — the user has engaged with those, so they are never auto-deleted.
    """
    keep = max(1, schedule.retention_count or 1)
    user_msg_count = (
        select(func.count(ChatMessage.id))
        .where(ChatMessage.chat_session_id == ChatSession.id)
        .where(ChatMessage.message_type == MessageType.USER)
        .correlate(ChatSession)
        .scalar_subquery()
    )
    ranked = (
        select(
            ChatSession.id.label("id"),
            func.row_number()
            .over(order_by=ChatSession.time_created.desc())
            .label("rn"),
        )
        .where(ChatSession.pulse_schedule_id == schedule.id)
        .where(ChatSession.deleted.is_(False))
        .subquery()
    )
    stmt = (
        select(ChatSession.id)
        .join(ranked, ranked.c.id == ChatSession.id)
        .where(ranked.c.rn > keep)
        .where(ChatSession.shared_status != ChatSessionSharedStatus.PUBLIC)
        .where(user_msg_count <= 1)
        .limit(limit)
    )
    return [row[0] for row in db_session.execute(stmt).all()]


def soft_delete_sessions(db_session: Session, session_ids: list[UUID]) -> int:
    if not session_ids:
        return 0
    result = db_session.execute(
        update(ChatSession)
        .where(ChatSession.id.in_(session_ids))
        .values(deleted=True)
    )
    db_session.commit()
    return result.rowcount or 0  # type: ignore[attr-defined]


def prune_old_runs(db_session: Session, older_than: datetime.datetime) -> int:
    result = db_session.execute(
        PulseRun.__table__.delete().where(
            and_(
                PulseRun.created_at < older_than,
                PulseRun.status.in_(TERMINAL_RUN_STATUSES),
            )
        )
    )
    db_session.commit()
    return result.rowcount or 0  # type: ignore[attr-defined]
