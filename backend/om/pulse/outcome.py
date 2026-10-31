"""Finalising a run: terminal status + trigger failure streak + notifications.

Shared by the worker (normal completion) and the scheduler's reaper (crashed
workers). Deliberately light on imports so `pulse_scheduler` stays small.
"""

from sqlalchemy.orm import Session

from om.configs.pulse_configs import PULSE_MAX_CONSECUTIVE_FAILURES
from om.db.models import PulseTrigger
from om.db.pulse import finish_run
from om.db.pulse import get_pulse_run
from om.db.pulse import record_trigger_outcome
from om.db.pulse import RUN_FAILED
from om.db.pulse import RUN_INTERRUPTED
from om.db.pulse import RUN_MISSED
from om.db.pulse import RUN_NEEDS_INPUT
from om.db.pulse import RUN_RUNNING
from om.db.pulse import RUN_SKIPPED
from om.db.pulse import RUN_TIMED_OUT
from om.pulse.notifications import notify_auto_paused
from om.pulse.notifications import notify_needs_input
from om.pulse.notifications import notify_run_failed
from om.utils.logger import setup_logger

logger = setup_logger()


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
) -> str:
    """Move the run to `status` (only from `from_statuses`) and update the trigger.

    If the run was already finalised elsewhere (e.g. the reaper beat a slow worker),
    nothing is overwritten.
    """
    updated = finish_run(
        db_session,
        run_id,
        status=status,
        from_statuses=from_statuses,
        error=error,
        skip_reason=skip_reason,
        output_preview=output_preview,
        workflow_execution_id=workflow_execution_id,
    )
    if not updated:
        logger.warning(f"Pulse run {run_id}: already finalised, not overwriting")
        return status

    if status in (RUN_SKIPPED, RUN_MISSED):
        return status

    run = get_pulse_run(db_session, run_id)
    if run is None:
        return status

    failures, auto_paused = record_trigger_outcome(
        db_session,
        trigger.id,
        run_status=status,
        scheduled_for=run.scheduled_for,
        max_consecutive_failures=PULSE_MAX_CONSECUTIVE_FAILURES,
    )
    db_session.refresh(trigger)
    if status == RUN_NEEDS_INPUT:
        notify_needs_input(db_session, trigger, run)
    elif status in (RUN_FAILED, RUN_TIMED_OUT, RUN_INTERRUPTED):
        notify_run_failed(db_session, trigger, run, failures)
    if auto_paused:
        notify_auto_paused(db_session, trigger, run, failures)
    return status
