"""What each kind of trigger sends the workflow.

The runner handles everything all kinds share (access, chat session, watchdog,
outcome). The one thing that differs is the input, so each kind has a step here.
A new kind adds a table, a module with its step, and a line in INPUT_STEPS.
"""

import datetime
from collections.abc import Callable
from typing import Any

from sqlalchemy.orm import Session

from om.db.models import PulseRun
from om.db.models import PulseTrigger
from om.pulse.triggers.base import FinishRun
from om.pulse.triggers.base import RunInput
from om.pulse.triggers.base import SendMessage
from om.pulse.triggers.schedule import prepare_schedule_input
from om.pulse.triggers.webhook import prepare_webhook_input

__all__ = ["FinishRun", "RunInput", "SendMessage", "prepare_run_input"]

# The first argument is the kind the step is registered for.
InputStep = Callable[[Session, Any, PulseRun, str, datetime.datetime], RunInput]

INPUT_STEPS: dict[str, InputStep] = {
    "schedule": prepare_schedule_input,
    "webhook": prepare_webhook_input,
}


def prepare_run_input(
    db_session: Session,
    trigger: PulseTrigger,
    run: PulseRun,
    workflow_name: str,
    now: datetime.datetime,
) -> RunInput:
    return INPUT_STEPS[trigger.kind](db_session, trigger, run, workflow_name, now)
