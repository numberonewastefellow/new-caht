"""Headless executor for one Pulse run (called by the `pulse_worker` Celery task).

Order of operations (see DESIGN.md "Worker steps"):
  1. CAS pending -> running            (duplicate deliveries become no-ops)
  2. staleness check                   (a late redelivery is recorded as `missed`)
  3. access re-check                   (revoked access disables the schedule)
  4. rate-limit check                  (over budget => `skipped`, retried next slot)
  5. create the chat session FIRST and link it to the run (so a crash never orphans it)
  6. heartbeat + deadline watchdog thread (deadline uses the chat stop fence — Celery
     soft time limits do not work on thread pools)
  7. stream the workflow through the normal chat pipeline (same persistence as the UI)
  8. map workflow_execution.status -> run status, record outcome, notify
"""

import threading
import time
from uuid import UUID

from sqlalchemy.orm import Session

from om.chat.message_handler import stream_chat_message
from om.chat.models import StreamingError
from om.chat.stop_signal_checker import set_fence
from om.configs.pulse_configs import PULSE_DEADLINE_MARGIN_SECONDS
from om.configs.pulse_configs import PULSE_HEARTBEAT_SECONDS
from om.configs.pulse_configs import PULSE_MISFIRE_GRACE_SECONDS
from om.db.chat import create_chat_session
from om.db.engine.sql_engine import get_session_with_tenant
from om.db.models import PulseRun
from om.db.models import PulseSchedule
from om.db.pulse import db_now
from om.db.pulse import DISABLED_ACCESS_REVOKED
from om.db.pulse import DISABLED_WORKFLOW_DELETED
from om.db.pulse import disable_schedule
from om.db.pulse import fill_empty_assistant_message
from om.db.pulse import finish_run
from om.db.pulse import get_pulse_schedule
from om.db.pulse import heartbeat_run
from om.db.pulse import latest_assistant_message
from om.db.pulse import RUN_CANCELLED
from om.db.pulse import RUN_FAILED
from om.db.pulse import RUN_MISSED
from om.db.pulse import RUN_NEEDS_INPUT
from om.db.pulse import RUN_SKIPPED
from om.db.pulse import RUN_SUCCEEDED
from om.db.pulse import RUN_TIMED_OUT
from om.db.pulse import set_run_chat_session
from om.db.pulse import start_run
from om.db.pulse import TRIGGER_SCHEDULED
from om.db.workflow import get_latest_execution_by_chat_session
from om.pulse.access import PulseAccessError
from om.pulse.access import resolve_run_context
from om.pulse.outcome import finalize_run
from om.pulse.spec import spec_from_schedule
from om.pulse.timing import ensure_utc
from om.pulse.timing import get_zone
from om.pulse.timing import max_start_delay_seconds
from om.pulse.timing import nominal_period_seconds
from om.pulse.timing import render_input_message
from om.pulse.timing import ScheduleValidationError
from om.redis.redis_pool import get_redis_client
from om.server.query_and_chat.models import MessageOrigin
from om.server.query_and_chat.models import SendMessageRequest
from om.utils.logger import setup_logger

logger = setup_logger()

OUTPUT_PREVIEW_CHARS = 500
FAILED_RUN_MESSAGE = "⚠️ This scheduled run did not complete: {reason}"


class _Watchdog:
    """Heartbeat + deadline thread. Uses its own DB sessions (never the run's)."""

    def __init__(
        self,
        *,
        run_id: int,
        tenant_id: str,
        deadline_monotonic: float,
        chat_session_id: UUID,
    ) -> None:
        self.run_id = run_id
        self.tenant_id = tenant_id
        self.deadline_monotonic = deadline_monotonic
        self.chat_session_id = chat_session_id
        self.deadline_hit = False
        self._last_beat = 0.0
        self._stop = threading.Event()
        self._thread = threading.Thread(
            target=self._loop, name=f"pulse-watchdog-{run_id}", daemon=True
        )

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=5)

    def _loop(self) -> None:
        while not self._stop.wait(timeout=min(PULSE_HEARTBEAT_SECONDS, 5)):
            now = time.monotonic()
            if not self.deadline_hit and now >= self.deadline_monotonic:
                self.deadline_hit = True
                logger.warning(f"Pulse run {self.run_id}: deadline reached, stopping")
                try:
                    set_fence(
                        self.chat_session_id,
                        get_redis_client(tenant_id=self.tenant_id),
                        True,
                    )
                except Exception:
                    logger.exception("Pulse: failed to set stop fence")
            self._maybe_heartbeat(now)

    def _maybe_heartbeat(self, now: float) -> None:
        if now - self._last_beat < PULSE_HEARTBEAT_SECONDS:
            return
        self._last_beat = now
        try:
            with get_session_with_tenant(tenant_id=self.tenant_id) as db:
                heartbeat_run(db, self.run_id)
        except Exception:
            logger.exception(f"Pulse run {self.run_id}: heartbeat failed")


def _output_preview(db_session: Session, chat_session_id: UUID) -> str | None:
    message = latest_assistant_message(db_session, chat_session_id)
    if message is None or not message.message:
        return None
    text = " ".join(message.message.split())
    return text[:OUTPUT_PREVIEW_CHARS]


def _session_title(schedule: PulseSchedule, run: PulseRun) -> str:
    when = ensure_utc(run.scheduled_for)
    try:
        when = when.astimezone(get_zone(schedule.timezone))
    except ScheduleValidationError:
        pass
    return f"{schedule.name} · {when.strftime('%d %b %H:%M')}"


def execute_pulse_run(run_id: int, tenant_id: str, hostname: str) -> str | None:
    """Execute one run. Returns the final run status, or None if another worker owns it."""
    with get_session_with_tenant(tenant_id=tenant_id) as db_session:
        run = start_run(db_session, run_id, hostname)
        if run is None:
            logger.info(f"Pulse run {run_id}: not pending (duplicate delivery) — skip")
            return None

        schedule = get_pulse_schedule(db_session, run.schedule_id)
        if schedule is None:
            finish_run(db_session, run_id, status=RUN_FAILED, error="Schedule deleted")
            return RUN_FAILED

        spec = spec_from_schedule(schedule)
        now = db_now(db_session)

        # 2. staleness — only for scheduled slots (manual runs are always wanted)
        if run.trigger == TRIGGER_SCHEDULED:
            max_delay = max_start_delay_seconds(
                spec, misfire_grace_seconds=PULSE_MISFIRE_GRACE_SECONDS, now=now
            )
            lateness = (now - run.scheduled_for).total_seconds()
            if lateness > max_delay:
                return finalize_run(
                    db_session,
                    schedule,
                    run_id,
                    status=RUN_MISSED,
                    skip_reason=f"started {int(lateness)}s late (limit {max_delay}s)",
                )

        # 3. access re-check
        try:
            ctx = resolve_run_context(
                db_session, workflow_id=schedule.workflow_id, owner_id=schedule.user_id
            )
        except PulseAccessError as e:
            disable_schedule(
                db_session,
                schedule.id,
                DISABLED_WORKFLOW_DELETED if e.workflow_deleted else DISABLED_ACCESS_REVOKED,
            )
            return finalize_run(
                db_session, schedule, run_id, status=RUN_SKIPPED, skip_reason=str(e)
            )

        # 4. rate limits (same policy engine as the chat endpoint)
        try:
            from om.server.rate_limits.cache import policy_exists
            from om.server.rate_limits.service import build_rate_limit_service
            from om.server.rate_limits.service import RateLimitExceededError

            if policy_exists(tenant_id, db_session):
                try:
                    build_rate_limit_service(db_session).check(ctx.user)
                except RateLimitExceededError as e:
                    return finalize_run(
                        db_session,
                        schedule,
                        run_id,
                        status=RUN_SKIPPED,
                        skip_reason=f"rate limited: {e}"[:250],
                    )
        except ImportError:
            pass

        # 5. chat session first
        chat_session = create_chat_session(
            db_session=db_session,
            description=_session_title(schedule, run),
            user_id=ctx.user.id,
            agent_id=ctx.agent.id,
            ombot_flow=False,
        )
        chat_session.pulse_schedule_id = schedule.id
        db_session.commit()
        set_run_chat_session(db_session, run_id, chat_session.id)

        message = render_input_message(
            schedule.input_message,
            timezone=schedule.timezone,
            scheduled_for=run.scheduled_for,
            now=now,
            last_success_scheduled_for=schedule.last_success_scheduled_for,
            period_seconds=nominal_period_seconds(spec, now=now),
        )

        # 6. watchdog
        timeout = int(ctx.workflow.timeout_seconds or 1800) + PULSE_DEADLINE_MARGIN_SECONDS
        watchdog = _Watchdog(
            run_id=run_id,
            tenant_id=tenant_id,
            deadline_monotonic=time.monotonic() + timeout,
            chat_session_id=chat_session.id,
        )
        watchdog.start()

        # 7. run through the normal chat pipeline
        stream_error: str | None = None
        try:
            request = SendMessageRequest(
                message=message,
                chat_session_id=chat_session.id,
                origin=MessageOrigin.API,
                stream=False,
            )
            for item in stream_chat_message(
                new_msg_req=request, user=ctx.user, db_session=db_session
            ):
                if isinstance(item, StreamingError):
                    stream_error = item.error
        except Exception as e:  # never let a workflow crash the worker task
            logger.exception(f"Pulse run {run_id}: workflow raised")
            stream_error = f"{type(e).__name__}: {e}"
            db_session.rollback()
        finally:
            watchdog.stop()

        # 8. result mapping from the authoritative workflow_execution row
        db_session.expire_all()
        execution = get_latest_execution_by_chat_session(db_session, chat_session.id)
        exec_status = execution.status if execution else None
        execution_id = execution.id if execution else None

        if watchdog.deadline_hit:
            status = RUN_TIMED_OUT
            error = f"Stopped after exceeding the {timeout}s time limit"
        elif exec_status == "completed":
            status, error = RUN_SUCCEEDED, None
        elif exec_status == "paused":
            status, error = RUN_NEEDS_INPUT, None
        elif exec_status == "cancelled":
            status, error = RUN_CANCELLED, "Run was stopped"
        elif exec_status == "timeout":
            status, error = RUN_TIMED_OUT, execution.error_message if execution else None
        else:
            status = RUN_FAILED
            error = (
                stream_error
                or (execution.error_message if execution else None)
                or "Workflow did not complete"
            )

        if status in (RUN_FAILED, RUN_TIMED_OUT, RUN_CANCELLED):
            try:
                fill_empty_assistant_message(
                    db_session,
                    chat_session.id,
                    FAILED_RUN_MESSAGE.format(reason=error or status),
                )
            except Exception:
                db_session.rollback()

        # Mark the execution failed if the engine left it dangling
        if execution is not None and execution.status == "running":
            execution.status = "failed"
            execution.error_message = error
            db_session.commit()

        return finalize_run(
            db_session,
            schedule,
            run_id,
            status=status,
            error=error,
            output_preview=_output_preview(db_session, chat_session.id),
            workflow_execution_id=execution_id,
        )
