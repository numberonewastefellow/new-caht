"""User notifications for Pulse runs (reuses the in-app notification system).

De-duplication relies on the notification table's unique (user, type, additional_data)
index: we key failures by the start of the failure streak, so a schedule produces at
most one open "failed" notification per streak, one "needs input" per run, and one
"auto-paused" per pause event. Successful runs never notify.
"""

from datetime import datetime
from datetime import timezone
from uuid import UUID

from sqlalchemy.orm import Session

from om.configs.constants import NotificationType
from om.db.models import PulseRun
from om.db.models import PulseSchedule
from om.db.notification import create_notification
from om.utils.logger import setup_logger

logger = setup_logger()


def _link(schedule: PulseSchedule, run: PulseRun | None) -> dict:
    data: dict = {"pulse_schedule_id": schedule.id}
    if run is not None:
        data["pulse_run_id"] = run.id
        if run.chat_session_id:
            data["chat_session_id"] = str(run.chat_session_id)
    return data


def notify_run_failed(
    db_session: Session, schedule: PulseSchedule, run: PulseRun, failures: int
) -> None:
    # Only the first failure of a streak notifies; further failures are visible on the
    # schedule page and culminate in an auto-pause notification.
    if failures != 1:
        return
    try:
        create_notification(
            user_id=schedule.user_id,
            notif_type=NotificationType.PULSE_RUN_FAILED,
            db_session=db_session,
            title=f"Scheduled run failed: {schedule.name}",
            description=(run.error or "The workflow run failed.")[:500],
            additional_data=_link(schedule, run),
        )
    except Exception:
        logger.exception("Pulse: failed to create run-failed notification")
        db_session.rollback()


def notify_needs_input(
    db_session: Session, schedule: PulseSchedule, run: PulseRun
) -> None:
    try:
        create_notification(
            user_id=schedule.user_id,
            notif_type=NotificationType.PULSE_NEEDS_INPUT,
            db_session=db_session,
            title=f"Scheduled run needs your input: {schedule.name}",
            description="Open the run's chat and reply to continue the workflow.",
            additional_data=_link(schedule, run),
        )
    except Exception:
        logger.exception("Pulse: failed to create needs-input notification")
        db_session.rollback()


def notify_auto_paused(
    db_session: Session, schedule: PulseSchedule, run: PulseRun, failures: int
) -> None:
    try:
        create_notification(
            user_id=schedule.user_id,
            notif_type=NotificationType.PULSE_AUTO_PAUSED,
            db_session=db_session,
            title=f"Schedule paused: {schedule.name}",
            description=(
                f"Paused automatically after {failures} failed runs in a row. "
                "Fix the problem and resume it from the Schedules page."
            ),
            additional_data=_link(schedule, run),
        )
    except Exception:
        logger.exception("Pulse: failed to create auto-paused notification")
        db_session.rollback()


def notify_owner_of_admin_change(
    db_session: Session,
    *,
    owner_id: UUID,
    schedule_id: int,
    schedule_name: str,
    admin_email: str,
    action: str,
) -> None:
    """An admin edited or deleted someone else's schedule: tell the owner (audit)."""
    try:
        create_notification(
            user_id=owner_id,
            notif_type=NotificationType.PULSE_SCHEDULE_CHANGED_BY_ADMIN,
            db_session=db_session,
            title=f"Your schedule “{schedule_name}” was {action} by an admin",
            description=f"{admin_email} {action} it. It still runs as you.",
            # unique per change so repeated edits each notify
            additional_data={
                "pulse_schedule_id": schedule_id,
                "action": action,
                "admin": admin_email,
                "at": datetime.now(timezone.utc).isoformat(),
            },
        )
    except Exception:
        logger.exception("Pulse: failed to notify owner of admin change")
        db_session.rollback()
