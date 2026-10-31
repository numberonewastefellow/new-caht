"""Input for a webhook's run: the owner's template with the event's data inserted as
untrusted text."""

import datetime

from sqlalchemy.orm import Session

from om.db.models import PulseRun
from om.db.models import PulseWebhook
from om.pulse.timing import render_input_message
from om.pulse.triggers.base import RunInput
from om.pulse.triggers.base import SendMessage
from om.pulse.webhooks.payload import UntrustedRenderer


def render_webhook_message(
    template: str,
    *,
    payload: dict | None,
    timezone: str,
    fired_at: datetime.datetime,
    now: datetime.datetime,
) -> str:
    """Also used by the preview, so the owner sees exactly what a run would send."""
    renderer = UntrustedRenderer(payload)
    message = render_input_message(
        template,
        timezone=timezone,
        scheduled_for=fired_at,
        now=now,
        last_success_scheduled_for=None,
        period_seconds=None,
        resolve_extra=renderer,
    )
    return renderer.with_notice(message)


def prepare_webhook_input(
    db_session: Session,  # noqa: ARG001
    webhook: PulseWebhook,
    run: PulseRun,
    workflow_name: str,  # noqa: ARG001
    now: datetime.datetime,
) -> RunInput:
    return SendMessage(
        render_webhook_message(
            webhook.input_message,
            payload=run.trigger_payload,
            timezone=webhook.timezone,
            fired_at=run.scheduled_for,
            now=now,
        )
    )
