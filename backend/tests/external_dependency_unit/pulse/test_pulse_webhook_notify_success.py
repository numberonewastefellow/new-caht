"""Telling a webhook's owner about a run that worked, and where the notification leads.

A webhook usually has nobody watching it, so a good result is easy to miss unless the owner
asked to hear about it.

Requires Postgres + Redis (see tests/external_dependency_unit). No LLM calls.
"""

from collections.abc import Generator
from uuid import UUID

import pytest
from sqlalchemy import delete
from sqlalchemy import select
from sqlalchemy.orm import Session

from om.configs.constants import NotificationType
from om.db.models import AgentWorkflow
from om.db.models import ChatSession
from om.db.models import Notification
from om.db.models import PulseRun
from om.db.models import PulseTrigger
from om.db.models import PulseWebhook
from om.db.pulse import create_manual_run
from om.db.pulse import create_pulse_schedule
from om.db.pulse import RUN_FAILED
from om.db.pulse import RUN_SUCCEEDED
from om.db.pulse_webhook import accept_webhook_event
from om.db.pulse_webhook import create_pulse_webhook
from om.pulse.notifications import MAX_DESCRIPTION_CHARS
from om.pulse.notifications import notify_needs_input
from om.pulse.outcome import finalize_run
from om.pulse.webhooks.tokens import generate_signing_secret
from om.pulse.webhooks.tokens import generate_token
from om.pulse.webhooks.tokens import hash_token
from tests.external_dependency_unit.conftest import create_test_user


@pytest.fixture
def owner_id(db_session: Session) -> UUID:
    return create_test_user(db_session, "pulse_notify_success_test").id


def _make_webhook(db_session: Session, owner_id: UUID, *, notify_on_success: bool) -> PulseWebhook:
    workflow = db_session.execute(select(AgentWorkflow).limit(1)).scalars().first()
    assert workflow is not None
    return create_pulse_webhook(
        db_session,
        user_id=owner_id,
        workflow_id=workflow.id,
        name="notify-success",
        timezone="UTC",
        input_message="{{payload}}",
        retention_count=50,
        enabled=True,
        token_hash=hash_token(generate_token(None)),
        token_last4="abcd",
        auth_mode="header_token",
        signing_secret=generate_signing_secret(),
        header_name="x-webhook-secret",
        dedup_source="none",
        dedup_path=None,
        notify_on_success=notify_on_success,
    )


@pytest.fixture
def make_webhook(db_session: Session, owner_id: UUID) -> Generator:
    made: list[PulseWebhook] = []

    def make(*, notify_on_success: bool) -> PulseWebhook:
        webhook = _make_webhook(db_session, owner_id, notify_on_success=notify_on_success)
        db_session.commit()
        made.append(webhook)
        return webhook

    yield make
    db_session.rollback()
    for webhook in made:
        db_session.execute(delete(ChatSession).where(ChatSession.pulse_trigger_id == webhook.id))
        db_session.execute(delete(PulseTrigger).where(PulseTrigger.id == webhook.id))
    db_session.execute(delete(Notification).where(Notification.user_id == owner_id))
    db_session.commit()


def _running_run(db_session: Session, webhook: PulseWebhook) -> int:
    run_id = accept_webhook_event(
        db_session,
        webhook_id=webhook.id,
        dedup_key=None,
        payload={"body": {}},
        max_pending=100,
        tenant_max_active=1000,
    ).run_id
    run = db_session.get(PulseRun, run_id)
    assert run is not None
    run.status = "running"
    db_session.commit()
    return run_id


def _notifications(db_session: Session, owner_id: UUID, kind: NotificationType) -> list[Notification]:
    db_session.commit()
    return list(
        db_session.execute(
            select(Notification)
            .where(Notification.user_id == owner_id)
            .where(Notification.notif_type == kind)
        ).scalars()
    )


def test_off_by_default_and_a_good_run_says_nothing(
    db_session: Session, owner_id: UUID, make_webhook
) -> None:
    webhook = make_webhook(notify_on_success=False)
    finalize_run(db_session, webhook, _running_run(db_session, webhook), status=RUN_SUCCEEDED)
    assert _notifications(db_session, owner_id, NotificationType.PULSE_RUN_SUCCEEDED) == []


def test_when_asked_a_good_run_notifies_with_its_result(
    db_session: Session, owner_id: UUID, make_webhook
) -> None:
    webhook = make_webhook(notify_on_success=True)
    run_id = _running_run(db_session, webhook)
    finalize_run(db_session, webhook, run_id, status=RUN_SUCCEEDED, output_preview="API is back")

    found = _notifications(db_session, owner_id, NotificationType.PULSE_RUN_SUCCEEDED)
    assert len(found) == 1
    assert webhook.name in found[0].title
    assert found[0].description == "API is back"
    assert found[0].additional_data["pulse_run_id"] == run_id


def test_every_good_run_gets_its_own_notification(
    db_session: Session, owner_id: UUID, make_webhook
) -> None:
    webhook = make_webhook(notify_on_success=True)
    for _ in range(2):
        finalize_run(db_session, webhook, _running_run(db_session, webhook), status=RUN_SUCCEEDED)
    assert len(_notifications(db_session, owner_id, NotificationType.PULSE_RUN_SUCCEEDED)) == 2


def test_a_long_result_is_shortened(db_session: Session, owner_id: UUID, make_webhook) -> None:
    webhook = make_webhook(notify_on_success=True)
    finalize_run(
        db_session,
        webhook,
        _running_run(db_session, webhook),
        status=RUN_SUCCEEDED,
        output_preview="x" * (MAX_DESCRIPTION_CHARS + 50),
    )
    found = _notifications(db_session, owner_id, NotificationType.PULSE_RUN_SUCCEEDED)
    assert len(found[0].description) == MAX_DESCRIPTION_CHARS


def test_a_failed_run_is_not_reported_as_a_success(
    db_session: Session, owner_id: UUID, make_webhook
) -> None:
    webhook = make_webhook(notify_on_success=True)
    finalize_run(db_session, webhook, _running_run(db_session, webhook), status=RUN_FAILED, error="no")
    assert _notifications(db_session, owner_id, NotificationType.PULSE_RUN_SUCCEEDED) == []
    assert len(_notifications(db_session, owner_id, NotificationType.PULSE_RUN_FAILED)) == 1


def test_notification_opens_the_webhook_page_when_the_run_has_no_chat(
    db_session: Session, owner_id: UUID, make_webhook
) -> None:
    webhook = make_webhook(notify_on_success=True)
    finalize_run(db_session, webhook, _running_run(db_session, webhook), status=RUN_SUCCEEDED)
    found = _notifications(db_session, owner_id, NotificationType.PULSE_RUN_SUCCEEDED)
    assert found[0].additional_data["link"] == f"/app/schedules/webhooks/{webhook.id}"


def test_notification_opens_the_run_chat_when_there_is_one(
    db_session: Session, owner_id: UUID, make_webhook
) -> None:
    webhook = make_webhook(notify_on_success=False)
    run_id = _running_run(db_session, webhook)
    chat = ChatSession(user_id=owner_id, agent_id=None, description="run", pulse_trigger_id=webhook.id)
    db_session.add(chat)
    db_session.flush()
    run = db_session.get(PulseRun, run_id)
    assert run is not None
    run.chat_session_id = chat.id
    db_session.commit()

    notify_needs_input(db_session, webhook, run)
    found = _notifications(db_session, owner_id, NotificationType.PULSE_NEEDS_INPUT)
    assert found[0].additional_data["link"] == f"/app?chatId={chat.id}"


def test_a_schedule_stays_silent_on_success(db_session: Session, owner_id: UUID) -> None:
    """The setting is only on webhooks, and a schedule must not trip over its absence."""
    workflow = db_session.execute(select(AgentWorkflow).limit(1)).scalars().first()
    assert workflow is not None
    schedule = create_pulse_schedule(
        db_session,
        user_id=owner_id,
        workflow_id=workflow.id,
        name="notify-success-schedule",
        schedule_type="interval",
        cron_expression=None,
        interval_seconds=3600,
        run_at=None,
        timezone="UTC",
        input_message="test",
        enabled=False,
        retention_count=50,
        next_run_at=None,
    )
    db_session.commit()
    try:
        run = create_manual_run(db_session, schedule.id)
        run.status = "running"
        db_session.commit()
        finalize_run(db_session, schedule, run.id, status=RUN_SUCCEEDED)
        assert _notifications(db_session, owner_id, NotificationType.PULSE_RUN_SUCCEEDED) == []
    finally:
        db_session.rollback()
        db_session.execute(delete(PulseTrigger).where(PulseTrigger.id == schedule.id))
        db_session.commit()
