"""Input for a schedule's run, following its input mode (see om/pulse/inputs.py)."""

import datetime

from sqlalchemy.orm import Session

from om.db.models import PulseRun
from om.db.models import PulseSchedule
from om.db.pulse import claim_next_item_index
from om.db.pulse import RUN_FAILED
from om.db.pulse import RUN_NEEDS_INPUT
from om.pulse.inputs import default_ask_prompt
from om.pulse.inputs import item_for_index
from om.pulse.spec import spec_from_schedule
from om.pulse.timing import nominal_period_seconds
from om.pulse.timing import render_input_message
from om.pulse.triggers.base import FinishRun
from om.pulse.triggers.base import RunInput
from om.pulse.triggers.base import SendMessage


def prepare_schedule_input(
    db_session: Session,
    schedule: PulseSchedule,
    run: PulseRun,
    workflow_name: str,
    now: datetime.datetime,
) -> RunInput:
    # "ask" mode: the input changes every run and only the user has it. Open the
    # workflow chat and wait — no LLM call. When the user replies in that chat,
    # the normal chat pipeline runs the workflow with their reply.
    if schedule.input_mode == "ask":
        return FinishRun(
            status=RUN_NEEDS_INPUT,
            output_preview=schedule.input_prompt or default_ask_prompt(workflow_name),
        )

    # "list" mode: take the next item (atomically, so concurrent runs never
    # reuse or skip an item) and insert it via {{item}}.
    item: str | None = None
    if schedule.input_mode == "list":
        index = claim_next_item_index(db_session, schedule.id)
        item = item_for_index(schedule.input_items, index)
        if item is None:
            return FinishRun(status=RUN_FAILED, error="The schedule's item list is empty")

    return SendMessage(
        render_input_message(
            schedule.input_message,
            timezone=schedule.timezone,
            scheduled_for=run.scheduled_for,
            now=now,
            last_success_scheduled_for=schedule.last_success_scheduled_for,
            period_seconds=nominal_period_seconds(spec_from_schedule(schedule), now=now),
            item=item,
        )
    )
