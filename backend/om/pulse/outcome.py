"""Finalising a run: terminal status + trigger failure streak + notifications.

Shared by the worker (normal completion) and the scheduler's reaper (crashed
workers). Deliberately light on imports so `pulse_scheduler` stays small.
"""

import datetime

from sqlalchemy.orm import Session

from om.configs.pulse_configs import PULSE_MAX_CONSECUTIVE_FAILURES
from om.configs.pulse_configs import PULSE_WEBHOOK_RUN_MAX_WAIT_SECONDS
from om.db.models import PulseRun
from om.db.models import PulseTrigger
from om.db.models import PulseWebhook
from om.db.pulse import finish_run
from om.db.pulse import get_pulse_run
from om.db.pulse import record_trigger_outcome
from om.db.pulse import RUN_FAILED
from om.db.pulse import RUN_INTERRUPTED
from om.db.pulse import RUN_MISSED
from om.db.pulse import RUN_NEEDS_INPUT
from om.db.pulse import RUN_RUNNING
from om.db.pulse import RUN_SKIPPED
from om.db.pulse import RUN_SUCCEEDED
from om.db.pulse import RUN_TIMED_OUT
from om.pulse.notifications import notify_auto_paused
from om.pulse.notifications import notify_needs_input
from om.pulse.notifications import notify_run_failed
from om.pulse.notifications import notify_run_not_started
from om.pulse.notifications import notify_run_succeeded
from om.utils.logger import setup_logger

logger = setup_logger()

WEBHOOK_RUN_EXPIRED = "No worker picked it up in time, so it wasn't run"


def webhook_run_expired(run: PulseRun, now: datetime.datetime) -> bool:
    """Too old to run: acting on a stale event could do more harm than not acting."""
    return (now - run.created_at).total_seconds() > PULSE_WEBHOOK_RUN_MAX_WAIT_SECONDS


def finalize_run(
    db_session: Session,
    trigger: PulseTrigger,
    run_id: int,
    *,
    status: str,
    error: str | None = None,
    skip_reason: str | None = None,
    output_preview: str | None = None,
    workflow_execution_id: int | None = None,
    from_statuses: tuple[str, ...] = (RUN_RUNNING,),
    never_started: bool = False,
) -> str:
    """Move the run to `status` (only from `from_statuses`) and update the trigger.

    If the run was already finalised elsewhere (e.g. the reaper beat a slow worker),
    nothing is overwritten.

    A run that never started says nothing about the workflow, so it doesn't count towards
    the failure streak. It also gives up its duplicate key, so a resend can run. A run that
    did start keeps its key: it may already have changed something.
    """
    never_started = never_started or status in (RUN_SKIPPED, RUN_MISSED)
    updated = finish_run(
        db_session,
        run_id,
        status=status,
        from_statuses=from_statuses,
        error=error,
        skip_reason=skip_reason,
        output_preview=output_preview,
        workflow_execution_id=workflow_execution_id,
        clear_dedup_key=never_started,
    )
    if not updated:
        logger.warning(f"Pulse run {run_id}: already finalised, not overwriting")
        return status

    run = get_pulse_run(db_session, run_id)
    if run is None:
        return status

    if status in (RUN_SKIPPED, RUN_MISSED):
        # Nobody is told about a missed webhook event otherwise: the sender already got 202
        if status == RUN_MISSED and trigger.kind == "webhook":
            notify_run_not_started(db_session, trigger, run)
        return status

    failures, auto_paused = record_trigger_outcome(
        db_session,
        trigger.id,
        run_status=status,
        scheduled_for=run.scheduled_for,
        max_consecutive_failures=PULSE_MAX_CONSECUTIVE_FAILURES,
        counts_as_failure=not never_started,
    )
    db_session.refresh(trigger)
    if never_started:
        notify_run_not_started(db_session, trigger, run)
    elif status == RUN_NEEDS_INPUT:
        notify_needs_input(db_session, trigger, run)
    elif status in (RUN_FAILED, RUN_TIMED_OUT, RUN_INTERRUPTED):
        notify_run_failed(db_session, trigger, run, failures)
    elif status == RUN_SUCCEEDED and isinstance(trigger, PulseWebhook) and trigger.notify_on_success:
        notify_run_succeeded(db_session, trigger, run)
    if auto_paused:
        notify_auto_paused(db_session, trigger, run, failures)
    return status
