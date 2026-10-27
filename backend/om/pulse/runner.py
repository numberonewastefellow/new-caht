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
from om.configs.pulse_configs import PULSE_MAX_RUN_SECONDS
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
from om.db.pulse import get_pulse_run
from om.db.pulse import get_pulse_schedule
from om.db.pulse import heartbeat_run
from om.db.pulse import claim_next_item_index
from om.db.pulse import latest_assistant_message
from om.db.pulse import RUN_CANCELLED
from om.db.pulse import RUN_FAILED
from om.db.pulse import RUN_INTERRUPTED
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
from om.pulse.inputs import default_ask_prompt
from om.pulse.inputs import item_for_index
from om.pulse.outcome import finalize_run
from om.pulse.spec import spec_from_schedule
from om.pulse.timing import ensure_utc
from om.pulse.timing import get_zone
from om.pulse.timing import max_start_delay_seconds
from om.pulse.timing import nominal_period_seconds
from om.pulse.timing import render_input_message
from om.pulse.timing import ScheduleValidationError
from om.redis.redis_pool import get_redis_client
from om.server.rate_limits.cache import policy_exists
from om.server.rate_limits.service import build_rate_limit_service
from om.server.rate_limits.service import RateLimitExceededError
from om.server.query_and_chat.models import MessageOrigin
from om.server.query_and_chat.models import SendMessageRequest
from om.utils.logger import setup_logger

logger = setup_logger()

OUTPUT_PREVIEW_CHARS = 500
FAILED_RUN_MESSAGE = "⚠️ This scheduled run did not complete: {reason}"


class _Watchdog:
    """Heartbeat + deadline thread. Uses its own DB sessions (never the run's).

    * deadline      -> set the chat stop fence (the engine stops at its next check)
    * hard deadline -> deadline + 2 x margin: if the engine is stuck somewhere that
                       never checks the fence, finalise the run as `timed_out` from here
                       so the schedule is not blocked forever (the stuck thread's own
                       finalisation later becomes a no-op via the status CAS)
    * lost          -> the run row is no longer `running` (reaped / schedule deleted):
                       stop the workflow and stop heart-beating
    """

    def __init__(
        self,
        *,
        run_id: int,
        schedule_id: int,
        tenant_id: str,
        deadline_monotonic: float,
        chat_session_id: UUID,
    ) -> None:
        self.run_id = run_id
        self.schedule_id = schedule_id
        self.tenant_id = tenant_id
        self.deadline_monotonic = deadline_monotonic
        self.hard_deadline_monotonic = (
            deadline_monotonic + 2 * PULSE_DEADLINE_MARGIN_SECONDS
        )
        self.chat_session_id = chat_session_id
        self.deadline_hit = False
        self.hard_stopped = False
        self.lost = False
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

    def _set_fence(self) -> None:
        try:
            set_fence(
                self.chat_session_id, get_redis_client(tenant_id=self.tenant_id), True
            )
        except Exception:
            logger.exception("Pulse: failed to set stop fence")

    def _loop(self) -> None:
        while not self._stop.wait(timeout=min(PULSE_HEARTBEAT_SECONDS, 5)):
            now = time.monotonic()
            if not self.deadline_hit and now >= self.deadline_monotonic:
                self.deadline_hit = True
                logger.warning(f"Pulse run {self.run_id}: deadline reached, stopping")
                self._set_fence()
            if self.deadline_hit and now >= self.hard_deadline_monotonic:
                self._hard_stop()
                return
            if not self._maybe_heartbeat(now):
                return

    def _hard_stop(self) -> None:
        logger.error(
            f"Pulse run {self.run_id}: still running after the hard deadline; "
            "finalising it as timed out"
        )
        self.hard_stopped = True
        try:
            with get_session_with_tenant(tenant_id=self.tenant_id) as db:
                schedule = get_pulse_schedule(db, self.schedule_id)
                if schedule is not None:
                    finalize_run(
                        db,
                        schedule,
                        self.run_id,
                        status=RUN_TIMED_OUT,
                        error="The workflow did not stop after its time limit",
                    )
                fill_empty_assistant_message(
                    db,
                    self.chat_session_id,
                    FAILED_RUN_MESSAGE.format(reason="it exceeded its time limit"),
                )
        except Exception:
            logger.exception(f"Pulse run {self.run_id}: hard stop failed")

    def _maybe_heartbeat(self, now: float) -> bool:
        """Returns False when the run is no longer ours (stop watching)."""
        if now - self._last_beat < PULSE_HEARTBEAT_SECONDS:
            return True
        self._last_beat = now
        try:
            with get_session_with_tenant(tenant_id=self.tenant_id) as db:
                still_running = heartbeat_run(db, self.run_id)
        except Exception:
            logger.exception(f"Pulse run {self.run_id}: heartbeat failed")
            return True
        if not still_running:
            logger.warning(
                f"Pulse run {self.run_id}: run is no longer `running` "
                "(reaped or schedule deleted); stopping the workflow"
            )
            self.lost = True
            self._set_fence()
            return False
        return True


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
    """Execute one run. Returns the final run status, or None if another worker owns it.

    Any unexpected exception finalises the run as `failed` (instead of leaving it
    `running` for the reaper to mislabel as `interrupted`)."""
    try:
        return _execute_pulse_run(run_id, tenant_id, hostname)
    except Exception:
        logger.exception(f"Pulse run {run_id}: unexpected error")
        try:
            with get_session_with_tenant(tenant_id=tenant_id) as db_session:
                run = get_pulse_run(db_session, run_id)
                schedule = get_pulse_schedule(db_session, run.schedule_id) if run else None
                if run is not None and schedule is not None:
                    finalize_run(
                        db_session,
                        schedule,
                        run_id,
                        status=RUN_FAILED,
                        error=f"Internal error while running the workflow (Pulse run {run_id})",
                    )
        except Exception:
            logger.exception(f"Pulse run {run_id}: could not record the failure")
        return RUN_FAILED


def _execute_pulse_run(run_id: int, tenant_id: str, hostname: str) -> str | None:
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
        chat_session_id = chat_session.id
        schedule_id = schedule.id
        set_run_chat_session(db_session, run_id, chat_session_id)

        # "ask" mode: the input changes every run and only the user has it. Open the
        # workflow chat and wait — no LLM call. When the user replies in that chat,
        # the normal chat pipeline runs the workflow with their reply.
        if schedule.input_mode == "ask":
            prompt = schedule.input_prompt or default_ask_prompt(ctx.workflow.name)
            return finalize_run(
                db_session,
                schedule,
                run_id,
                status=RUN_NEEDS_INPUT,
                output_preview=prompt,
            )

        # "list" mode: take the next item (atomically, so concurrent runs never
        # reuse or skip an item) and insert it via {{item}}.
        item: str | None = None
        if schedule.input_mode == "list":
            index = claim_next_item_index(db_session, schedule.id)
            item = item_for_index(schedule.input_items, index)
            if item is None:
                return finalize_run(
                    db_session,
                    schedule,
                    run_id,
                    status=RUN_FAILED,
                    error="The schedule's item list is empty",
                )

        message = render_input_message(
            schedule.input_message,
            timezone=schedule.timezone,
            scheduled_for=run.scheduled_for,
            now=now,
            last_success_scheduled_for=schedule.last_success_scheduled_for,
            period_seconds=nominal_period_seconds(spec, now=now),
            item=item,
        )

        # 6. watchdog
        timeout = (
            min(
                int(ctx.workflow.timeout_seconds or PULSE_MAX_RUN_SECONDS),
                PULSE_MAX_RUN_SECONDS,
            )
            + PULSE_DEADLINE_MARGIN_SECONDS
        )
        watchdog = _Watchdog(
            run_id=run_id,
            schedule_id=schedule_id,
            tenant_id=tenant_id,
            deadline_monotonic=time.monotonic() + timeout,
            chat_session_id=chat_session_id,
        )
        watchdog.start()

        # 7. run through the normal chat pipeline
        stream_error: str | None = None
        try:
            request = SendMessageRequest(
                message=message,
                chat_session_id=chat_session_id,
                origin=MessageOrigin.API,
                stream=False,
            )
            for item in stream_chat_message(
                new_msg_req=request, user=ctx.user, db_session=db_session
            ):
                if isinstance(item, StreamingError):
                    stream_error = item.error
        except Exception:  # never let a workflow crash the worker task
            # Details stay in the server log; users get a reference, not internals
            # (exception text can contain SQL, hostnames or provider responses).
            logger.exception(f"Pulse run {run_id}: workflow raised")
            stream_error = f"Internal error while running the workflow (Pulse run {run_id})"
            db_session.rollback()
        finally:
            watchdog.stop()

    # 8. Result mapping in a FRESH session: when a run is stopped (deadline / Stop /
    # lost), the engine abandons the agent thread without joining it and that thread
    # may still use the run's session — never touch it again.
    with get_session_with_tenant(tenant_id=tenant_id) as result_session:
        return _finish_from_execution(
            result_session,
            run_id=run_id,
            schedule_id=schedule_id,
            chat_session_id=chat_session_id,
            watchdog=watchdog,
            timeout=timeout,
            stream_error=stream_error,
        )


def _finish_from_execution(
    db_session: Session,
    *,
    run_id: int,
    schedule_id: int,
    chat_session_id: UUID,
    watchdog: _Watchdog,
    timeout: int,
    stream_error: str | None,
) -> str:
    schedule = get_pulse_schedule(db_session, schedule_id)
    if schedule is None:  # deleted mid-run (the run row went with it)
        return RUN_CANCELLED
    if watchdog.hard_stopped or watchdog.lost:
        # Already finalised elsewhere (hard stop / reaper); nothing to overwrite.
        return RUN_TIMED_OUT if watchdog.hard_stopped else RUN_INTERRUPTED

    execution = get_latest_execution_by_chat_session(db_session, chat_session_id)
    exec_status = execution.status if execution else None
    execution_id = execution.id if execution else None

    # A finished result wins over a deadline that fired just as it completed.
    if exec_status == "completed":
        status, error = RUN_SUCCEEDED, None
    elif exec_status == "paused":
        status, error = RUN_NEEDS_INPUT, None
    elif watchdog.deadline_hit:
        status = RUN_TIMED_OUT
        error = f"Stopped after exceeding the {timeout}s time limit"
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
        fill_empty_assistant_message(
            db_session,
            chat_session_id,
            FAILED_RUN_MESSAGE.format(reason=error or status),
        )

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
        output_preview=_output_preview(db_session, chat_session_id),
        workflow_execution_id=execution_id,
    )
