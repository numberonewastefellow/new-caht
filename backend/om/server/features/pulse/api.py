"""Pulse API — create and manage scheduled workflow runs.

Any user who can run a workflow can schedule it (same rule as POST /workflow/{id}/run:
the workflow is public or owned by the user). Users see and manage their own
schedules; admins can list/manage everyone's (`?all_users=true`).
"""

from datetime import datetime
from datetime import timedelta

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.orm import Session

from om.auth.schemas import UserRole
from om.auth.users import current_admin_user
from om.auth.users import current_user
from om.configs.pulse_configs import PULSE_DEFAULT_RETENTION
from om.configs.pulse_configs import PULSE_MAX_RETENTION
from om.configs.pulse_configs import PULSE_MAX_SCHEDULES_PER_USER
from om.configs.pulse_configs import PULSE_MIN_INTERVAL_SECONDS
from om.db.engine.sql_engine import get_session
from om.db.models import PulseSchedule
from om.db.models import User
from om.db.pulse import count_active_runs
from om.db.pulse import count_enabled_schedules_for_user
from om.db.pulse import count_runs_by_status_since
from om.db.pulse import create_manual_run
from om.db.pulse import create_pulse_schedule
from om.db.pulse import db_now
from om.db.pulse import delete_pulse_schedule
from om.db.pulse import get_latest_runs_by_schedule
from om.db.pulse import get_latest_session_run_by_schedule
from om.db.pulse import get_pulse_run
from om.db.pulse import get_pulse_schedule_for_user
from om.db.pulse import has_active_run
from om.db.pulse import list_pulse_schedules
from om.db.pulse import list_runs_for_schedule
from om.db.pulse import RUN_FAILED
from om.db.pulse import RUN_INTERRUPTED
from om.db.pulse import RUN_NEEDS_INPUT
from om.db.pulse import RUN_TIMED_OUT
from om.pulse.access import get_accessible_workflow
from om.pulse.access import PulseAccessError
from om.pulse.dispatch import enqueue_pulse_run
from om.pulse.scheduler import SCHEDULER_PRESENCE_KEY_PREFIX
from om.pulse.spec import spec_from_schedule
from om.pulse.timing import describe
from om.pulse.timing import next_fire_after
from om.pulse.timing import next_fires
from om.pulse.timing import ScheduleSpec
from om.pulse.timing import ScheduleValidationError
from om.pulse.timing import TEMPLATE_VARIABLES
from om.pulse.timing import validate_spec
from om.redis.redis_pool import get_redis_client
from om.server.features.pulse.models import PulseConfigResponse
from om.server.features.pulse.models import PulseHealthResponse
from om.server.features.pulse.models import PulsePreviewRequest
from om.server.features.pulse.models import PulsePreviewResponse
from om.server.features.pulse.models import PulseRunResponse
from om.server.features.pulse.models import PulseScheduleCreate
from om.server.features.pulse.models import PulseScheduleResponse
from om.server.features.pulse.models import PulseScheduleUpdate
from om.server.features.pulse.models import PulseSidebarItem
from om.server.features.pulse.models import PulseStatsResponse
from om.utils.logger import setup_logger
from shared_configs.contextvars import get_current_tenant_id

logger = setup_logger()

router = APIRouter(prefix="/pulse")
admin_router = APIRouter(prefix="/admin/pulse")

TIMING_FIELDS = (
    "schedule_type",
    "cron_expression",
    "interval_seconds",
    "run_at",
    "timezone",
)


# ========================
# Helpers
# ========================


def _is_admin(user: User) -> bool:
    return user.role == UserRole.ADMIN


def _get_schedule_or_404(
    db_session: Session, schedule_id: int, user: User
) -> PulseSchedule:
    schedule = get_pulse_schedule_for_user(
        db_session, schedule_id, user.id, is_admin=_is_admin(user)
    )
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return schedule


def _validated_spec(spec: ScheduleSpec, now: datetime) -> ScheduleSpec:
    try:
        return validate_spec(
            spec, min_interval_seconds=PULSE_MIN_INTERVAL_SECONDS, now=now
        )
    except ScheduleValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


def _check_retention(value: int | None) -> int:
    if value is None:
        return PULSE_DEFAULT_RETENTION
    if value < 1 or value > PULSE_MAX_RETENTION:
        raise HTTPException(
            status_code=400,
            detail=f"retention_count must be between 1 and {PULSE_MAX_RETENTION}",
        )
    return value


def _check_quota(db_session: Session, user: User) -> None:
    if count_enabled_schedules_for_user(db_session, user.id) >= PULSE_MAX_SCHEDULES_PER_USER:
        raise HTTPException(
            status_code=400,
            detail=(
                f"You can have at most {PULSE_MAX_SCHEDULES_PER_USER} active schedules. "
                "Pause or delete one first."
            ),
        )


def _check_workflow(db_session: Session, workflow_id: int, user: User) -> None:
    try:
        get_accessible_workflow(db_session, workflow_id, user.id)
    except PulseAccessError as e:
        raise HTTPException(
            status_code=404 if e.workflow_deleted else 403, detail=str(e)
        )


def _initial_next_run(spec: ScheduleSpec, now: datetime) -> datetime | None:
    if spec.schedule_type == "once":
        return spec.run_at
    return next_fire_after(spec, now)


def _to_responses(
    db_session: Session, schedules: list[PulseSchedule], include_owner: bool
) -> list[PulseScheduleResponse]:
    ids = [s.id for s in schedules]
    latest = get_latest_runs_by_schedule(db_session, ids)
    latest_sessions = get_latest_session_run_by_schedule(db_session, ids)
    out = []
    for s in schedules:
        try:
            description = describe(spec_from_schedule(s))
        except ScheduleValidationError:
            description = "Invalid schedule"
        session_run = latest_sessions.get(s.id)
        out.append(
            PulseScheduleResponse.from_model(
                s,
                description=description,
                last_run=latest.get(s.id),
                latest_chat_session_id=session_run.chat_session_id
                if session_run
                else None,
                include_owner=include_owner,
            )
        )
    return out


def _to_response(
    db_session: Session, schedule: PulseSchedule, user: User
) -> PulseScheduleResponse:
    return _to_responses(db_session, [schedule], include_owner=_is_admin(user))[0]


# ========================
# Schedules
# ========================


@router.get("/config")
def get_pulse_config(_: User = Depends(current_user)) -> PulseConfigResponse:
    return PulseConfigResponse(
        min_interval_seconds=PULSE_MIN_INTERVAL_SECONDS,
        max_schedules_per_user=PULSE_MAX_SCHEDULES_PER_USER,
        max_retention=PULSE_MAX_RETENTION,
        default_retention=PULSE_DEFAULT_RETENTION,
        template_variables=list(TEMPLATE_VARIABLES),
    )


@router.post("/preview")
def preview_schedule(
    request: PulsePreviewRequest,
    _: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> PulsePreviewResponse:
    """Validate a schedule definition and show the next 5 fire times (DST-correct)."""
    now = db_now(db_session)
    spec = ScheduleSpec(
        schedule_type=request.schedule_type,
        timezone=request.timezone,
        cron_expression=request.cron_expression,
        interval_seconds=request.interval_seconds,
        run_at=request.run_at,
    )
    try:
        spec = validate_spec(
            spec, min_interval_seconds=PULSE_MIN_INTERVAL_SECONDS, now=now
        )
    except ScheduleValidationError as e:
        return PulsePreviewResponse(valid=False, error=str(e))
    first = _initial_next_run(spec, now)
    runs: list = []
    if first is not None:
        runs = [first] + next_fires(spec, after=first, count=4, anchor=first)
    return PulsePreviewResponse(
        valid=True,
        description=describe(spec),
        next_runs=runs[:5],
        cron_expression=spec.cron_expression,
    )


@router.get("/schedules")
def list_schedules(
    all_users: bool = False,
    workflow_id: int | None = None,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> list[PulseScheduleResponse]:
    include_all = all_users and _is_admin(user)
    schedules = list_pulse_schedules(db_session, user.id, include_all_users=include_all)
    if workflow_id is not None:
        schedules = [s for s in schedules if s.workflow_id == workflow_id]
    return _to_responses(db_session, schedules, include_owner=include_all)


@router.post("/schedules")
def create_schedule(
    request: PulseScheduleCreate,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> PulseScheduleResponse:
    _check_workflow(db_session, request.workflow_id, user)
    now = db_now(db_session)
    spec = _validated_spec(
        ScheduleSpec(
            schedule_type=request.schedule_type,
            timezone=request.timezone,
            cron_expression=request.cron_expression,
            interval_seconds=request.interval_seconds,
            run_at=request.run_at,
        ),
        now,
    )
    if request.enabled:
        _check_quota(db_session, user)
    schedule = create_pulse_schedule(
        db_session,
        user_id=user.id,
        workflow_id=request.workflow_id,
        name=request.name.strip(),
        schedule_type=spec.schedule_type,
        cron_expression=spec.cron_expression,
        interval_seconds=spec.interval_seconds,
        run_at=spec.run_at,
        timezone=spec.timezone,
        input_message=request.input_message,
        enabled=request.enabled,
        retention_count=_check_retention(request.retention_count),
        next_run_at=_initial_next_run(spec, now),    )
    return _to_response(db_session, schedule, user)


@router.get("/schedules/{schedule_id}")
def get_schedule(
    schedule_id: int,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> PulseScheduleResponse:
    return _to_response(
        db_session, _get_schedule_or_404(db_session, schedule_id, user), user
    )


@router.patch("/schedules/{schedule_id}")
def update_schedule(
    schedule_id: int,
    request: PulseScheduleUpdate,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> PulseScheduleResponse:
    schedule = _get_schedule_or_404(db_session, schedule_id, user)
    # Lock the row so a concurrent scheduler tick cannot interleave with this edit
    db_session.execute(
        select(PulseSchedule.id)
        .where(PulseSchedule.id == schedule.id)
        .with_for_update()
    )
    db_session.refresh(schedule)
    changes = request.model_dump(exclude_unset=True)
    now = db_now(db_session)

    timing_changed = any(k in changes for k in TIMING_FIELDS)
    if timing_changed:
        merged = {f: getattr(schedule, f) for f in TIMING_FIELDS}
        merged.update({k: v for k, v in changes.items() if k in TIMING_FIELDS})
        # Switching type clears the fields that no longer apply
        if merged["schedule_type"] != "cron":
            merged["cron_expression"] = None
        if merged["schedule_type"] != "interval":
            merged["interval_seconds"] = None
        if merged["schedule_type"] != "once":
            merged["run_at"] = None
        spec = _validated_spec(
            ScheduleSpec(
                schedule_type=merged["schedule_type"],
                timezone=merged["timezone"] or "UTC",
                cron_expression=merged["cron_expression"],
                interval_seconds=merged["interval_seconds"],
                run_at=merged["run_at"],
            ),
            now,
        )
        schedule.schedule_type = spec.schedule_type
        schedule.cron_expression = spec.cron_expression
        schedule.interval_seconds = spec.interval_seconds
        schedule.run_at = spec.run_at
        schedule.timezone = spec.timezone

    if "name" in changes and changes["name"] is not None:
        schedule.name = changes["name"].strip()
    if "input_message" in changes and changes["input_message"] is not None:
        schedule.input_message = changes["input_message"]
    if "retention_count" in changes:
        schedule.retention_count = _check_retention(changes["retention_count"])

    resuming = changes.get("enabled") is True and not schedule.enabled
    if resuming:
        _check_workflow(db_session, schedule.workflow_id, user)
        _check_quota(db_session, user)
        schedule.enabled = True
        schedule.disabled_reason = None
        schedule.consecutive_failures = 0
    elif changes.get("enabled") is False:
        schedule.enabled = False
        schedule.disabled_reason = None  # paused by the user

    if timing_changed or resuming:
        spec = spec_from_schedule(schedule)
        schedule.next_run_at = _initial_next_run(spec, now)
        if schedule.next_run_at is None or (
            spec.schedule_type == "once" and schedule.next_run_at < now - timedelta(seconds=60)
        ):
            raise HTTPException(status_code=400, detail="This schedule has no future runs")

    db_session.commit()
    db_session.refresh(schedule)
    return _to_response(db_session, schedule, user)


@router.delete("/schedules/{schedule_id}")
def delete_schedule(
    schedule_id: int,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> None:
    """Deletes the schedule and its run history. Run chats stay in chat history."""
    schedule = _get_schedule_or_404(db_session, schedule_id, user)
    delete_pulse_schedule(db_session, schedule)


@router.post("/schedules/{schedule_id}/duplicate")
def duplicate_schedule(
    schedule_id: int,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> PulseScheduleResponse:
    source = _get_schedule_or_404(db_session, schedule_id, user)
    _check_workflow(db_session, source.workflow_id, user)
    now = db_now(db_session)
    spec = spec_from_schedule(source)
    next_run = _initial_next_run(spec, now)
    # The copy starts paused so it never fires unexpectedly; the user enables it.
    copy = create_pulse_schedule(
        db_session,
        user_id=user.id,
        workflow_id=source.workflow_id,
        name=f"{source.name} (copy)"[:200],
        schedule_type=source.schedule_type,
        cron_expression=source.cron_expression,
        interval_seconds=source.interval_seconds,
        run_at=source.run_at,
        timezone=source.timezone,
        input_message=source.input_message,
        enabled=False,
        retention_count=source.retention_count,
        next_run_at=next_run,    )
    return _to_response(db_session, copy, user)


@router.post("/schedules/{schedule_id}/run-now")
def run_schedule_now(
    schedule_id: int,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> PulseRunResponse:
    """Run the schedule's workflow immediately (works for paused schedules too)."""
    schedule = _get_schedule_or_404(db_session, schedule_id, user)
    # Runs execute as the schedule owner, so check the owner's access
    try:
        get_accessible_workflow(db_session, schedule.workflow_id, schedule.user_id)
    except PulseAccessError as e:
        raise HTTPException(
            status_code=404 if e.workflow_deleted else 403, detail=str(e)
        )
    if has_active_run(db_session, schedule.id):
        raise HTTPException(
            status_code=409, detail="A run of this schedule is already in progress"
        )
    run = create_manual_run(db_session, schedule.id)
    try:
        enqueue_pulse_run(run.id, get_current_tenant_id())
    except Exception:
        # The scheduler's outbox sweeper re-sends pending runs; not fatal.
        logger.exception(f"Pulse: enqueue failed for manual run {run.id}")
    return PulseRunResponse.from_model(run)


@router.get("/schedules/{schedule_id}/runs")
def list_schedule_runs(
    schedule_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    before_id: int | None = None,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> list[PulseRunResponse]:
    schedule = _get_schedule_or_404(db_session, schedule_id, user)
    runs = list_runs_for_schedule(db_session, schedule.id, limit=limit, before_id=before_id)
    return [PulseRunResponse.from_model(r) for r in runs]


@router.get("/runs/{run_id}")
def get_run(
    run_id: int,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> PulseRunResponse:
    run = get_pulse_run(db_session, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    _get_schedule_or_404(db_session, run.schedule_id, user)
    return PulseRunResponse.from_model(run)


# ========================
# Sidebar + KPIs
# ========================


@router.get("/sidebar")
def get_sidebar_items(
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> list[PulseSidebarItem]:
    """The chat sidebar's "Scheduled" section: one row per schedule (never per run)."""
    schedules = list_pulse_schedules(db_session, user.id)
    latest_sessions = get_latest_session_run_by_schedule(
        db_session, [s.id for s in schedules]
    )
    items = [
        PulseSidebarItem(
            schedule_id=s.id,
            name=s.name,
            enabled=s.enabled,
            disabled_reason=s.disabled_reason,
            last_run_status=s.last_run_status,
            last_run_at=s.last_run_at,
            latest_chat_session_id=(
                latest_sessions[s.id].chat_session_id
                if s.id in latest_sessions
                else None
            ),
        )
        for s in schedules
    ]
    # Most recently active first; never-run schedules last
    items.sort(key=lambda i: (i.last_run_at is None, -(i.last_run_at.timestamp() if i.last_run_at else 0)))
    return items


@router.get("/stats")
def get_stats(
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> PulseStatsResponse:
    schedules = list_pulse_schedules(db_session, user.id)
    since = db_now(db_session) - timedelta(hours=24)
    by_status = count_runs_by_status_since(db_session, since, user_id=user.id)
    attention_statuses = {RUN_FAILED, RUN_TIMED_OUT, RUN_INTERRUPTED, RUN_NEEDS_INPUT}
    return PulseStatsResponse(
        active_schedules=sum(1 for s in schedules if s.enabled),
        paused_schedules=sum(1 for s in schedules if not s.enabled),
        needs_attention=sum(
            1
            for s in schedules
            if s.disabled_reason
            in ("auto_paused_failures", "access_revoked", "workflow_deleted")
            or s.last_run_status in attention_statuses
        ),
        runs_last_24h=sum(by_status.values()),
        failed_last_24h=sum(
            by_status.get(s, 0) for s in (RUN_FAILED, RUN_TIMED_OUT, RUN_INTERRUPTED)
        ),
    )


# ========================
# Admin
# ========================


@admin_router.get("/health")
def get_pulse_health(
    _: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
) -> PulseHealthResponse:
    """Operational health: live scheduler replicas, scheduler lag, run counts."""
    now = db_now(db_session)
    lag = db_session.execute(
        select(func.max(func.extract("epoch", now - PulseSchedule.next_run_at)))
        .where(PulseSchedule.enabled.is_(True))
        .where(PulseSchedule.next_run_at <= now)
    ).scalar_one_or_none()
    enabled = db_session.execute(
        select(func.count(PulseSchedule.id)).where(PulseSchedule.enabled.is_(True))
    ).scalar_one()

    replicas = 0
    try:
        from shared_configs.configs import POSTGRES_DEFAULT_SCHEMA

        r = get_redis_client(tenant_id=POSTGRES_DEFAULT_SCHEMA)
        replicas = sum(
            1 for _ in r.scan_iter(match=f"{SCHEDULER_PRESENCE_KEY_PREFIX}*", count=100)
        )
    except Exception:
        logger.exception("Pulse: could not read scheduler presence keys")

    return PulseHealthResponse(
        scheduler_replicas_alive=replicas,
        scheduler_lag_seconds=float(lag) if lag is not None else 0.0,
        active_runs=count_active_runs(db_session),
        enabled_schedules=enabled,
        runs_last_24h_by_status=count_runs_by_status_since(
            db_session, now - timedelta(hours=24)
        ),
    )

