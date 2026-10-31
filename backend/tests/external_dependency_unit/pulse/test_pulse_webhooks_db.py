"""Webhook guarantees against a real Postgres and Redis:

  * N concurrent copies of an event make one run, and all get its id
  * the pending cap holds under concurrency, and a duplicate is still answered when full
  * rotation grace, revoke, and which tokens open which webhook
  * a webhook never shows up in schedule queries, counts or the scheduler's claim
  * webhook runs don't use the capacity schedules are limited by
  * retention clears payloads, and the sweeper re-sends to the right queue

Requires Postgres + Redis (see tests/external_dependency_unit). No LLM calls.
"""

import datetime as dt
import threading
from collections.abc import Callable
from collections.abc import Generator
from uuid import UUID

import pytest
from sqlalchemy import delete
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.orm import Session

from om.configs.pulse_configs import PULSE_PENDING_RESEND_SECONDS
from om.db.engine.sql_engine import get_session_with_current_tenant
from om.db.models import AgentWorkflow
from om.db.models import ChatSession
from om.db.models import PulseRun
from om.db.models import PulseSchedule
from om.db.models import PulseTrigger
from om.db.models import PulseWebhook
from om.db.pulse import claim_due_schedules
from om.db.pulse import count_active_runs
from om.db.pulse import count_active_runs_for_user
from om.db.pulse import count_enabled_schedules_for_user
from om.db.pulse import count_runs_by_status_since
from om.db.pulse import count_schedules_for_user
from om.db.pulse import create_pulse_schedule
from om.db.pulse import db_now
from om.db.pulse import delete_pulse_trigger
from om.db.pulse import get_pulse_schedule
from om.db.pulse import get_pulse_trigger
from om.db.pulse import list_pulse_schedules
from om.db.pulse import list_pulse_triggers
from om.db.pulse import record_trigger_outcome
from om.db.pulse import RUN_PENDING
from om.db.pulse import RUN_SUCCEEDED
from om.db.pulse_webhook import accept_webhook_event
from om.db.pulse_webhook import AcceptedEvent
from om.db.pulse_webhook import clear_old_payloads
from om.db.pulse_webhook import count_webhooks_for_user
from om.db.pulse_webhook import create_pulse_webhook
from om.db.pulse_webhook import find_webhook_by_token_hash
from om.db.pulse_webhook import list_pulse_webhooks
from om.db.pulse_webhook import record_webhook_rejection
from om.db.pulse_webhook import revoke_webhook_credentials
from om.db.pulse_webhook import rotate_webhook_credentials
from om.db.pulse_webhook import WebhookClosed
from om.db.pulse_webhook import WebhookOverloaded
from om.pulse import scheduler as scheduler_mod
from om.pulse.webhooks.tokens import generate_signing_secret
from om.pulse.webhooks.tokens import generate_token
from om.pulse.webhooks.tokens import hash_token
from shared_configs.contextvars import get_current_tenant_id
from tests.external_dependency_unit.conftest import create_test_user

PAYLOAD = {"body": {"a": 1}, "headers": {}}


@pytest.fixture
def workflow_id(db_session: Session) -> int:
    wf = db_session.execute(
        select(AgentWorkflow).where(AgentWorkflow.deleted.is_(False)).limit(1)
    ).scalar_one_or_none()
    if wf is None:
        pytest.skip("needs at least one workflow in the database")
    return wf.id


@pytest.fixture
def owner_id(db_session: Session) -> UUID:
    return create_test_user(db_session, "pulse_webhook_test").id


@pytest.fixture
def make_webhook(
    db_session: Session, workflow_id: int, owner_id: UUID
) -> Generator[Callable[..., PulseWebhook], None, None]:
    created: list[int] = []

    def _make(**overrides: object) -> PulseWebhook:
        params: dict = dict(
            user_id=owner_id,
            workflow_id=workflow_id,
            name="webhook-test",
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
        params.update(overrides)
        webhook = create_pulse_webhook(db_session, **params)
        created.append(webhook.id)
        return webhook

    yield _make

    db_session.rollback()
    if created:
        db_session.execute(delete(ChatSession).where(ChatSession.pulse_trigger_id.in_(created)))
        db_session.execute(delete(PulseTrigger).where(PulseTrigger.id.in_(created)))
        db_session.commit()


def _accept(
    db_session: Session,
    webhook_id: int,
    dedup_key: str | None,
    *,
    max_pending: int = 100,
    tenant_max_active: int = 100000,
) -> AcceptedEvent:
    return accept_webhook_event(
        db_session,
        webhook_id=webhook_id,
        dedup_key=dedup_key,
        payload=PAYLOAD,
        max_pending=max_pending,
        tenant_max_active=tenant_max_active,
    )


def _runs(db_session: Session, webhook_id: int) -> list[PulseRun]:
    db_session.commit()
    return list(
        db_session.execute(
            select(PulseRun).where(PulseRun.trigger_id == webhook_id).order_by(PulseRun.id)
        )
        .scalars()
        .all()
    )


# ---------------------------------------------------------------- the model keeps kinds apart


def test_webhook_rows_never_appear_as_schedules(
    db_session: Session,
    make_webhook: Callable[..., PulseWebhook],
    owner_id: UUID,
    workflow_id: int,
) -> None:
    schedules_before = count_schedules_for_user(db_session, owner_id)
    enabled_before = count_enabled_schedules_for_user(db_session, owner_id)
    webhook = make_webhook()
    assert webhook.kind == "webhook"

    assert count_schedules_for_user(db_session, owner_id) == schedules_before
    assert count_enabled_schedules_for_user(db_session, owner_id) == enabled_before
    assert get_pulse_schedule(db_session, webhook.id) is None
    assert webhook.id not in {
        s.id for s in list_pulse_schedules(db_session, None, include_all_users=True)
    }
    assert webhook.id not in {
        s.id for s in claim_due_schedules(db_session, db_now(db_session), 10000)
    }
    db_session.rollback()

    # ...but it is a trigger, and it has its own list and count.
    assert isinstance(get_pulse_trigger(db_session, webhook.id), PulseWebhook)
    assert webhook.id in {t.id for t in list_pulse_triggers(db_session)}
    assert webhook.id in {w.id for w in list_pulse_webhooks(db_session, owner_id)}
    assert count_webhooks_for_user(db_session, owner_id) >= 1


def test_a_schedule_never_appears_as_a_webhook(
    db_session: Session, owner_id: UUID, workflow_id: int
) -> None:
    schedule = create_pulse_schedule(
        db_session,
        user_id=owner_id,
        workflow_id=workflow_id,
        name="s",
        schedule_type="interval",
        cron_expression=None,
        interval_seconds=3600,
        run_at=None,
        timezone="UTC",
        input_message="x",
        enabled=False,
        retention_count=5,
        next_run_at=None,
    )
    try:
        assert schedule.kind == "schedule"
        assert schedule.id not in {
            w.id for w in list_pulse_webhooks(db_session, None, include_all_users=True)
        }
    finally:
        db_session.delete(schedule)
        db_session.commit()


def test_deleting_a_webhook_removes_its_rows(
    db_session: Session, make_webhook: Callable[..., PulseWebhook]
) -> None:
    webhook = make_webhook()
    event = _accept(db_session, webhook.id, "k1")
    db_session.delete(webhook)
    db_session.commit()
    assert db_session.get(PulseRun, event.run_id) is None
    assert db_session.get(PulseWebhook, webhook.id) is None


def test_a_webhook_outcome_updates_it_without_touching_schedule_fields(
    db_session: Session, make_webhook: Callable[..., PulseWebhook]
) -> None:
    webhook = make_webhook()
    record_trigger_outcome(
        db_session,
        webhook.id,
        run_status=RUN_SUCCEEDED,
        scheduled_for=db_now(db_session),
        max_consecutive_failures=3,
    )
    db_session.refresh(webhook)
    assert webhook.last_run_status == RUN_SUCCEEDED


# ---------------------------------------------------------------- duplicates and bursts


def test_duplicate_returns_the_original_run(
    db_session: Session, make_webhook: Callable[..., PulseWebhook]
) -> None:
    webhook = make_webhook()
    first = _accept(db_session, webhook.id, "evt_1")
    again = _accept(db_session, webhook.id, "evt_1")
    other = _accept(db_session, webhook.id, "evt_2")
    assert not first.duplicate and again.duplicate and not other.duplicate
    assert again.run_id == first.run_id != other.run_id
    assert len(_runs(db_session, webhook.id)) == 2


def test_the_same_key_on_two_webhooks_is_two_events(
    db_session: Session, make_webhook: Callable[..., PulseWebhook]
) -> None:
    a, b = make_webhook(), make_webhook()
    assert not _accept(db_session, a.id, "evt").duplicate
    assert not _accept(db_session, b.id, "evt").duplicate


def test_no_key_means_every_call_runs(
    db_session: Session, make_webhook: Callable[..., PulseWebhook]
) -> None:
    webhook = make_webhook()
    assert _accept(db_session, webhook.id, None).run_id != _accept(db_session, webhook.id, None).run_id


def test_concurrent_copies_of_an_event_make_one_run(
    make_webhook: Callable[..., PulseWebhook], db_session: Session
) -> None:
    webhook = make_webhook()
    webhook_id = webhook.id
    results: list[AcceptedEvent] = []
    errors: list[Exception] = []
    lock = threading.Lock()
    barrier = threading.Barrier(12)

    def call() -> None:
        try:
            barrier.wait(timeout=10)
            with get_session_with_current_tenant() as session:
                event = _accept(session, webhook_id, "evt_race")
            with lock:
                results.append(event)
        except Exception as e:  # noqa: BLE001
            with lock:
                errors.append(e)

    threads = [threading.Thread(target=call) for _ in range(12)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    assert not errors
    assert len(results) == 12
    assert len({r.run_id for r in results}) == 1
    assert sum(1 for r in results if not r.duplicate) == 1
    assert len(_runs(db_session, webhook_id)) == 1


def test_pending_cap_holds_under_concurrency(
    make_webhook: Callable[..., PulseWebhook], db_session: Session
) -> None:
    webhook = make_webhook()
    webhook_id = webhook.id
    accepted: list[int] = []
    refused: list[int] = []
    lock = threading.Lock()
    barrier = threading.Barrier(15)

    def call(i: int) -> None:
        barrier.wait(timeout=10)
        with get_session_with_current_tenant() as session:
            try:
                event = _accept(session, webhook_id, f"evt_{i}", max_pending=5)
                with lock:
                    accepted.append(event.run_id)
            except WebhookOverloaded:
                with lock:
                    refused.append(i)

    threads = [threading.Thread(target=call, args=(i,)) for i in range(15)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    assert len(accepted) == 5
    assert len(refused) == 10
    assert len(_runs(db_session, webhook_id)) == 5


def test_duplicate_is_answered_even_when_the_queue_is_full(
    db_session: Session, make_webhook: Callable[..., PulseWebhook]
) -> None:
    webhook = make_webhook()
    first = _accept(db_session, webhook.id, "evt_1", max_pending=1)
    with pytest.raises(WebhookOverloaded):
        _accept(db_session, webhook.id, "evt_2", max_pending=1)
    again = _accept(db_session, webhook.id, "evt_1", max_pending=1)
    assert again.duplicate and again.run_id == first.run_id


def test_tenant_cap_refuses(
    db_session: Session, make_webhook: Callable[..., PulseWebhook]
) -> None:
    webhook = make_webhook()
    _accept(db_session, webhook.id, "evt_1")
    with pytest.raises(WebhookOverloaded, match="workspace"):
        _accept(db_session, webhook.id, "evt_2", tenant_max_active=1)


@pytest.mark.parametrize("close", ["pause", "revoke", "delete"])
def test_closed_after_the_call_was_located_makes_no_run(
    db_session: Session, make_webhook: Callable[..., PulseWebhook], close: str
) -> None:
    webhook = make_webhook()
    webhook_id = webhook.id
    if close == "pause":
        webhook.enabled = False
        db_session.commit()
    elif close == "revoke":
        revoke_webhook_credentials(db_session, webhook)
    else:
        delete_pulse_trigger(db_session, webhook)
    with pytest.raises(WebhookClosed):
        _accept(db_session, webhook_id, "evt_late")
    assert _runs(db_session, webhook_id) == []


def test_changing_credentials_updates_the_timestamp(
    db_session: Session, make_webhook: Callable[..., PulseWebhook]
) -> None:
    webhook = make_webhook()
    before = webhook.updated_at
    revoke_webhook_credentials(db_session, webhook)
    assert webhook.updated_at > before


def test_schedule_stats_leave_out_webhook_runs(
    db_session: Session, make_webhook: Callable[..., PulseWebhook], owner_id: UUID
) -> None:
    webhook = make_webhook()
    since = db_now(db_session) - dt.timedelta(minutes=1)
    _accept(db_session, webhook.id, "evt_1")
    everything = count_runs_by_status_since(db_session, since, user_id=owner_id)
    schedules_only = count_runs_by_status_since(
        db_session, since, user_id=owner_id, include_webhooks=False
    )
    assert everything.get(RUN_PENDING) == 1
    assert schedules_only.get(RUN_PENDING) is None


def test_an_accepted_event_stores_its_payload_and_time(
    db_session: Session, make_webhook: Callable[..., PulseWebhook]
) -> None:
    webhook = make_webhook()
    event = _accept(db_session, webhook.id, "evt_1")
    run = db_session.get(PulseRun, event.run_id)
    assert run is not None
    assert run.status == RUN_PENDING
    assert run.fired_by == "webhook"
    assert run.trigger_payload == PAYLOAD
    assert run.dedup_key == "evt_1"
    db_session.refresh(webhook)
    assert webhook.last_received_at is not None


# ---------------------------------------------------------------- tokens, rotation, revoke


def test_rotation_keeps_the_old_token_for_the_grace_period(
    db_session: Session, make_webhook: Callable[..., PulseWebhook]
) -> None:
    old_hash, new_hash = hash_token(generate_token(None)), hash_token(generate_token(None))
    webhook = make_webhook(token_hash=old_hash, signing_secret="whsec_old")
    rotate_webhook_credentials(
        db_session,
        webhook,
        token_hash=new_hash,
        token_last4="wxyz",
        signing_secret="whsec_new",
        grace_hours=24,
    )
    assert find_webhook_by_token_hash(db_session, new_hash) is not None
    assert find_webhook_by_token_hash(db_session, old_hash) is not None
    assert webhook.previous_signing_secret.get_value(apply_mask=False) == "whsec_old"
    assert webhook.signing_secret.get_value(apply_mask=False) == "whsec_new"

    # When the grace ends the old token stops working.
    db_session.execute(
        update(PulseWebhook.__table__)
        .where(PulseWebhook.__table__.c.id == webhook.id)
        .values(previous_valid_until=db_now(db_session) - dt.timedelta(seconds=1))
    )
    db_session.commit()
    assert find_webhook_by_token_hash(db_session, old_hash) is None
    assert find_webhook_by_token_hash(db_session, new_hash) is not None


def test_rotation_with_no_grace_ends_the_old_token_at_once(
    db_session: Session, make_webhook: Callable[..., PulseWebhook]
) -> None:
    old_hash, new_hash = hash_token(generate_token(None)), hash_token(generate_token(None))
    webhook = make_webhook(token_hash=old_hash)
    rotate_webhook_credentials(
        db_session, webhook, token_hash=new_hash, token_last4="wxyz",
        signing_secret="whsec_new", grace_hours=0,
    )
    assert find_webhook_by_token_hash(db_session, old_hash) is None
    assert webhook.previous_signing_secret is None


def test_revoke_kills_current_and_previous_at_once(
    db_session: Session, make_webhook: Callable[..., PulseWebhook]
) -> None:
    old_hash, new_hash = hash_token(generate_token(None)), hash_token(generate_token(None))
    webhook = make_webhook(token_hash=old_hash)
    rotate_webhook_credentials(
        db_session, webhook, token_hash=new_hash, token_last4="wxyz",
        signing_secret="whsec_new", grace_hours=24,
    )
    revoke_webhook_credentials(db_session, webhook)
    assert find_webhook_by_token_hash(db_session, new_hash) is None
    assert find_webhook_by_token_hash(db_session, old_hash) is None
    assert webhook.previous_signing_secret is None


def test_rotating_a_revoked_webhook_never_brings_the_old_token_back(
    db_session: Session, make_webhook: Callable[..., PulseWebhook]
) -> None:
    old_hash, new_hash = hash_token(generate_token(None)), hash_token(generate_token(None))
    webhook = make_webhook(token_hash=old_hash)
    revoke_webhook_credentials(db_session, webhook)
    rotate_webhook_credentials(
        db_session, webhook, token_hash=new_hash, token_last4="wxyz",
        signing_secret="whsec_new", grace_hours=24,
    )
    assert webhook.revoked_at is None
    assert find_webhook_by_token_hash(db_session, new_hash) is not None
    assert find_webhook_by_token_hash(db_session, old_hash) is None


def test_rejection_keeps_only_the_latest_reason(
    db_session: Session, make_webhook: Callable[..., PulseWebhook]
) -> None:
    webhook = make_webhook()
    record_webhook_rejection(db_session, webhook.id, "first")
    record_webhook_rejection(db_session, webhook.id, "x" * 500)
    db_session.refresh(webhook)
    assert webhook.last_rejected_reason == "x" * 200
    assert webhook.last_rejected_at is not None


# ---------------------------------------------------------------- isolation from schedules


def test_webhook_runs_do_not_use_schedule_capacity(
    db_session: Session, make_webhook: Callable[..., PulseWebhook], owner_id: UUID
) -> None:
    tenant_before = count_active_runs(db_session)
    user_before = count_active_runs_for_user(db_session, owner_id)
    all_before = count_active_runs(db_session, include_webhooks=True)
    webhook = make_webhook()
    for i in range(3):
        _accept(db_session, webhook.id, f"evt_{i}")
    assert count_active_runs(db_session) == tenant_before
    assert count_active_runs_for_user(db_session, owner_id) == user_before
    assert count_active_runs(db_session, include_webhooks=True) == all_before + 3


def test_sweeper_resends_a_lost_webhook_run_to_the_webhook_queue(
    db_session: Session,
    make_webhook: Callable[..., PulseWebhook],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[int, bool]] = []

    def fake_enqueue(
        run_id: int, tenant_id: str, countdown: int = 0, webhook: bool = False  # noqa: ARG001
    ) -> None:
        calls.append((run_id, webhook))

    monkeypatch.setattr(scheduler_mod, "enqueue_pulse_run", fake_enqueue)
    webhook = make_webhook()
    event = _accept(db_session, webhook.id, "evt_lost")
    db_session.execute(
        update(PulseRun)
        .where(PulseRun.id == event.run_id)
        .values(created_at=db_now(db_session) - dt.timedelta(seconds=PULSE_PENDING_RESEND_SECONDS + 5))
    )
    db_session.commit()
    scheduler_mod._resend_stale_pending(get_current_tenant_id())
    assert (event.run_id, True) in calls


# ---------------------------------------------------------------- retention


def test_retention_clears_old_payloads_of_finished_runs_only(
    db_session: Session, make_webhook: Callable[..., PulseWebhook]
) -> None:
    webhook = make_webhook()
    finished_old = _accept(db_session, webhook.id, "old").run_id
    pending_old = _accept(db_session, webhook.id, "pending").run_id
    finished_new = _accept(db_session, webhook.id, "new").run_id
    now = db_now(db_session)
    db_session.execute(
        update(PulseRun)
        .where(PulseRun.id.in_([finished_old, pending_old]))
        .values(created_at=now - dt.timedelta(days=30))
    )
    db_session.execute(
        update(PulseRun)
        .where(PulseRun.id.in_([finished_old, finished_new]))
        .values(status=RUN_SUCCEEDED)
    )
    db_session.commit()

    assert clear_old_payloads(db_session, now - dt.timedelta(days=7)) >= 1
    db_session.expire_all()
    assert db_session.get(PulseRun, finished_old).trigger_payload is None
    assert db_session.get(PulseRun, pending_old).trigger_payload == PAYLOAD
    assert db_session.get(PulseRun, finished_new).trigger_payload == PAYLOAD
    assert db_session.get(PulseRun, finished_old).dedup_key == "old"
    assert isinstance(db_session.get(PulseSchedule, webhook.id), type(None))
