"""What happens to a webhook run that never gets to start.

The sender already got 202, so nothing else will tell it. The owner has to hear about it, a
resend has to work, and it mustn't look like the workflow is failing.

Requires Postgres + Redis (see tests/external_dependency_unit). No LLM calls.
"""

import datetime as dt
from collections.abc import Callable
from collections.abc import Generator
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock
from unittest.mock import patch
from uuid import UUID

import pytest
from sqlalchemy import delete
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.orm import Session

from om.configs.constants import NotificationType
from om.configs.constants import RateLimitScope
from om.configs.pulse_configs import PULSE_MAX_CONSECUTIVE_FAILURES
from om.configs.pulse_configs import PULSE_WEBHOOK_RUN_MAX_WAIT_SECONDS
from om.db.models import AgentWorkflow
from om.db.models import ChatSession
from om.db.models import Notification
from om.db.models import PulseRun
from om.db.models import PulseTrigger
from om.db.models import PulseWebhook
from om.db.models import User
from om.db.pulse import RUN_FAILED
from om.db.pulse import RUN_MISSED
from om.db.pulse import RUN_PENDING
from om.db.pulse import RUN_RUNNING
from om.db.pulse import RUN_SKIPPED
from om.db.pulse_webhook import accept_webhook_event
from om.db.pulse_webhook import AcceptedEvent
from om.db.pulse_webhook import create_pulse_webhook
from om.pulse import runner
from om.pulse import scheduler as scheduler_mod
from om.pulse.outcome import finalize_run
from om.pulse.webhooks.tokens import generate_signing_secret
from om.pulse.webhooks.tokens import generate_token
from om.pulse.webhooks.tokens import hash_token
from om.server.rate_limits.service import RateLimitExceededError
from om.tools.tool_constructor import construct_tools
from shared_configs.contextvars import get_current_tenant_id
from tests.external_dependency_unit.conftest import create_test_user

KEY = "event-1"
TOO_OLD = dt.timedelta(seconds=PULSE_WEBHOOK_RUN_MAX_WAIT_SECONDS + 60)


@pytest.fixture
def owner_id(db_session: Session) -> UUID:
    return create_test_user(db_session, "pulse_never_started_test").id


@pytest.fixture
def webhook(db_session: Session, owner_id: UUID) -> Generator[PulseWebhook, None, None]:
    workflow = db_session.execute(select(AgentWorkflow).limit(1)).scalars().first()
    assert workflow is not None
    created = create_pulse_webhook(
        db_session,
        user_id=owner_id,
        workflow_id=workflow.id,
        name="never-started",
        timezone="UTC",
        input_message="{{payload}}",
        retention_count=50,
        enabled=True,
        token_hash=hash_token(generate_token(None)),
        token_last4="abcd",
        auth_mode="standard_webhooks",
        signing_secret=generate_signing_secret(),
        header_name=None,
        dedup_source="webhook_id",
        dedup_path=None,
    )
    db_session.commit()
    yield created
    db_session.rollback()
    db_session.execute(delete(ChatSession).where(ChatSession.pulse_trigger_id == created.id))
    db_session.execute(delete(Notification).where(Notification.user_id == owner_id))
    db_session.execute(delete(PulseTrigger).where(PulseTrigger.id == created.id))
    db_session.commit()


def _accept(db_session: Session, webhook_id: int, key: str | None = KEY) -> AcceptedEvent:
    return accept_webhook_event(
        db_session,
        webhook_id=webhook_id,
        dedup_key=key,
        payload={"body": {}},
        max_pending=100,
        tenant_max_active=1000,
    )


def _run(db_session: Session, run_id: int) -> PulseRun:
    db_session.commit()
    return db_session.execute(
        select(PulseRun).where(PulseRun.id == run_id).execution_options(populate_existing=True)
    ).scalar_one()


def _execute(run_id: int) -> None:
    runner.execute_pulse_run(run_id, get_current_tenant_id(), "test-host")


def _execute_until_chat_exists(run_id: int) -> None:
    """Run it for real as far as the chat. The workflow itself isn't the point here."""

    def stop_here(*_: Any, **__: Any) -> Any:
        raise RuntimeError("stopped by the test")

    with patch.object(runner, "stream_chat_message", stop_here):
        _execute(run_id)


def _age(db_session: Session, run_id: int, by: dt.timedelta) -> None:
    db_session.execute(
        update(PulseRun)
        .where(PulseRun.id == run_id)
        .values(
            created_at=PulseRun.created_at - by,
            scheduled_for=PulseRun.scheduled_for - by,
        )
    )
    db_session.commit()


def _notifications(db_session: Session, owner_id: UUID, run_id: int) -> list[Notification]:
    db_session.commit()
    found = db_session.execute(
        select(Notification)
        .where(Notification.user_id == owner_id)
        .where(Notification.notif_type == NotificationType.PULSE_RUN_FAILED)
    ).scalars()
    return [n for n in found if (n.additional_data or {}).get("pulse_run_id") == run_id]


@pytest.fixture
def over_rate_limit(monkeypatch: pytest.MonkeyPatch, owner_id: UUID) -> None:
    def over_budget(_: Any) -> None:
        raise RateLimitExceededError(
            scope=RateLimitScope.USER,
            subject="owner",
            budget=1,
            used=1,
            reset_seconds=60,
            period_hours=1,
        )

    monkeypatch.setattr(
        runner,
        "resolve_run_context",
        lambda *_, **__: SimpleNamespace(user=SimpleNamespace(id=owner_id)),
    )
    monkeypatch.setattr(runner, "policy_exists", lambda *_: True)
    monkeypatch.setattr(
        runner,
        "build_rate_limit_service",
        lambda _: SimpleNamespace(check=over_budget),
    )


def test_resend_after_a_pause_runs_again(db_session: Session, webhook: PulseWebhook) -> None:
    first = _accept(db_session, webhook.id)
    webhook.enabled = False
    db_session.commit()
    _execute(first.run_id)
    assert _run(db_session, first.run_id).status == RUN_SKIPPED

    webhook.enabled = True
    db_session.commit()
    second = _accept(db_session, webhook.id)

    assert not second.duplicate
    assert second.run_id != first.run_id


def test_a_repeat_while_still_waiting_is_a_duplicate(
    db_session: Session, webhook: PulseWebhook
) -> None:
    first = _accept(db_session, webhook.id)
    second = _accept(db_session, webhook.id)
    assert second.duplicate
    assert second.run_id == first.run_id


def test_a_run_that_started_keeps_its_key(db_session: Session, webhook: PulseWebhook) -> None:
    """It may already have changed something, so a resend must not do that again."""
    first = _accept(db_session, webhook.id)
    db_session.execute(
        update(PulseRun).where(PulseRun.id == first.run_id).values(status=RUN_RUNNING)
    )
    db_session.commit()
    finalize_run(db_session, webhook, first.run_id, status=RUN_FAILED, error="boom")

    second = _accept(db_session, webhook.id)

    assert second.duplicate
    assert second.run_id == first.run_id


@pytest.mark.usefixtures("over_rate_limit")
def test_rate_limit_is_visible_and_resendable_but_not_a_failure_streak(
    db_session: Session, webhook: PulseWebhook, owner_id: UUID
) -> None:
    for attempt in range(PULSE_MAX_CONSECUTIVE_FAILURES + 1):
        event = _accept(db_session, webhook.id)
        assert not event.duplicate, f"attempt {attempt}"
        _execute(event.run_id)
        run = _run(db_session, event.run_id)
        assert run.status == RUN_FAILED
        assert "rate limit" in (run.error or "")
        assert _notifications(db_session, owner_id, event.run_id)

    db_session.refresh(webhook)
    assert webhook.enabled, "a rate limit must not auto-pause the webhook"
    assert webhook.consecutive_failures == 0


def test_a_real_failure_streak_still_auto_pauses(
    db_session: Session, webhook: PulseWebhook
) -> None:
    for _ in range(PULSE_MAX_CONSECUTIVE_FAILURES):
        event = _accept(db_session, webhook.id, key=None)
        db_session.execute(
            update(PulseRun).where(PulseRun.id == event.run_id).values(status=RUN_RUNNING)
        )
        db_session.commit()
        finalize_run(db_session, webhook, event.run_id, status=RUN_FAILED, error="boom")

    db_session.refresh(webhook)
    assert not webhook.enabled


def test_a_run_too_old_when_the_worker_returns_is_not_executed(
    db_session: Session, webhook: PulseWebhook, owner_id: UUID
) -> None:
    event = _accept(db_session, webhook.id)
    _age(db_session, event.run_id, TOO_OLD)

    _execute(event.run_id)

    run = _run(db_session, event.run_id)
    assert run.status == RUN_MISSED
    assert run.chat_session_id is None, "the workflow must not have started"
    assert _notifications(db_session, owner_id, event.run_id)
    assert not _accept(db_session, webhook.id).duplicate


def test_sweeper_expires_a_run_nobody_picked_up(
    db_session: Session,
    webhook: PulseWebhook,
    owner_id: UUID,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sent: list[int] = []
    enqueue: Callable[..., None] = lambda run_id, *_, **__: sent.append(run_id)
    monkeypatch.setattr(scheduler_mod, "enqueue_pulse_run", enqueue)
    event = _accept(db_session, webhook.id)
    _age(db_session, event.run_id, TOO_OLD)

    scheduler_mod._resend_stale_pending(get_current_tenant_id())

    assert event.run_id not in sent
    assert _run(db_session, event.run_id).status == RUN_MISSED
    assert _notifications(db_session, owner_id, event.run_id)


def test_sweeper_still_resends_a_run_within_the_limit(
    db_session: Session, webhook: PulseWebhook, monkeypatch: pytest.MonkeyPatch
) -> None:
    sent: list[int] = []
    enqueue: Callable[..., None] = lambda run_id, *_, **__: sent.append(run_id)
    monkeypatch.setattr(scheduler_mod, "enqueue_pulse_run", enqueue)
    event = _accept(db_session, webhook.id)
    _age(db_session, event.run_id, dt.timedelta(minutes=10))

    scheduler_mod._resend_stale_pending(get_current_tenant_id())

    assert event.run_id in sent
    assert _run(db_session, event.run_id).status == RUN_PENDING


def test_a_run_s_chat_keeps_its_limit_after_the_webhook_is_deleted(
    db_session: Session, webhook: PulseWebhook, owner_id: UUID
) -> None:
    webhook.allowed_tool_ids = [5]
    db_session.commit()
    event = _accept(db_session, webhook.id)
    _execute_until_chat_exists(event.run_id)
    run = _run(db_session, event.run_id)
    chat = db_session.get(ChatSession, run.chat_session_id)
    assert chat is not None
    assert chat.tool_allowlist == [5]

    db_session.execute(delete(PulseTrigger).where(PulseTrigger.id == webhook.id))
    db_session.commit()
    db_session.refresh(chat)
    assert chat.pulse_trigger_id is None
    assert chat.tool_allowlist == [5]
    db_session.delete(chat)
    db_session.commit()


def test_the_memory_tool_cannot_get_past_an_exact_list(db_session: Session, owner_id: UUID) -> None:
    """It's normally added whatever the list says, so a limit has to switch that off."""
    user = db_session.get(User, owner_id)
    assert user is not None
    user.enable_memory_tool = True
    db_session.commit()
    agent = SimpleNamespace(tools=[], id=1, name="a", llm_model_version_override=None)
    common: dict[str, Any] = {
        "agent": agent,
        "db_session": db_session,
        "emitter": MagicMock(),
        "user": user,
        "llm": MagicMock(),
    }
    assert construct_tools(**common, allowed_tool_ids=[]) != {}
    assert construct_tools(**common, allowed_tool_ids=[], strict_allowlist=True) == {}
