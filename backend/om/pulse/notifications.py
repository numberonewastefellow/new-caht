"""User notifications for Pulse runs (reuses the in-app notification system).

De-duplication relies on the notification table's unique (user, type, additional_data)
index: we key failures by the start of the failure streak, so a trigger produces at
most one open "failed" notification per streak, one "needs input" per run, and one
"auto-paused" per pause event. Successful runs never notify.
"""

from datetime import datetime
from datetime import timezone
from uuid import UUID

from sqlalchemy.orm import Session

from om.configs.constants import NotificationType
from om.db.models import PulseRun
from om.db.models import PulseTrigger
from om.db.notification import create_notification
from om.utils.logger import setup_logger

logger = setup_logger()


def _noun(trigger: PulseTrigger) -> str:
    return "Webhook" if trigger.kind == "webhook" else "Scheduled"


def _link(trigger: PulseTrigger, run: PulseRun | None) -> dict:
    data: dict = {"pulse_trigger_id": trigger.id}
    if run is not None:
        data["pulse_run_id"] = run.id
        if run.chat_session_id:
            data["chat_session_id"] = str(run.chat_session_id)
    return data


def notify_run_failed(
    db_session: Session, trigger: PulseTrigger, run: PulseRun, failures: int
) -> None:
    # Only the first failure of a streak notifies; further failures are visible on the
    # trigger's page and culminate in an auto-pause notification.
    if failures != 1:
        return
    try:
        create_notification(
            user_id=trigger.user_id,
            notif_type=NotificationType.PULSE_RUN_FAILED,
            db_session=db_session,
            title=f"{_noun(trigger)} run failed: {trigger.name}",
            description=(run.error or "The workflow run failed.")[:500],
            additional_data=_link(trigger, run),
        )
    except Exception:
        logger.exception("Pulse: failed to create run-failed notification")
        db_session.rollback()


def notify_needs_input(
    db_session: Session, trigger: PulseTrigger, run: PulseRun
) -> None:
    try:
        create_notification(
            user_id=trigger.user_id,
            notif_type=NotificationType.PULSE_NEEDS_INPUT,
            db_session=db_session,
            title=f"{_noun(trigger)} run needs your input: {trigger.name}",
            description="Open the run's chat and reply to continue the workflow.",
            additional_data=_link(trigger, run),
        )
    except Exception:
        logger.exception("Pulse: failed to create needs-input notification")
        db_session.rollback()


def notify_auto_paused(
    db_session: Session, trigger: PulseTrigger, run: PulseRun, failures: int
) -> None:
    try:
        create_notification(
            user_id=trigger.user_id,
            notif_type=NotificationType.PULSE_AUTO_PAUSED,
            db_session=db_session,
            title=f"{'Webhook' if trigger.kind == 'webhook' else 'Schedule'} paused: {trigger.name}",
            description=(
                f"Paused automatically after {failures} failed runs in a row. "
                f"Fix the problem and resume it from the "
                f"{'Webhooks' if trigger.kind == 'webhook' else 'Schedules'} page."
            ),
            additional_data=_link(trigger, run),
        )
    except Exception:
        logger.exception("Pulse: failed to create auto-paused notification")
        db_session.rollback()


def notify_owner_of_admin_change(
    db_session: Session,
    *,
    owner_id: UUID,
    trigger_id: int,
    trigger_name: str,
    admin_email: str,
    action: str,
    noun: str = "schedule",
) -> None:
    """An admin edited or deleted someone else's trigger: tell the owner (audit)."""
    try:
        create_notification(
            user_id=owner_id,
            notif_type=NotificationType.PULSE_SCHEDULE_CHANGED_BY_ADMIN,
            db_session=db_session,
            title=f"Your {noun} “{trigger_name}” was {action} by an admin",
            description=f"{admin_email} {action} it. It still runs as you.",
            # unique per change so repeated edits each notify
            additional_data={
                "pulse_trigger_id": trigger_id,
                "action": action,
                "admin": admin_email,
                "at": datetime.now(timezone.utc).isoformat(),
            },
        )
    except Exception:
        logger.exception("Pulse: failed to notify owner of admin change")
        db_session.rollback()
