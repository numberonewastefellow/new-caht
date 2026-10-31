"""Pulse scheduler concurrency/correctness tests against a real Postgres.

Proves the HA claims of the design:
  * N concurrent ticks (= N scheduler replicas) fire a due slot exactly once
  * a duplicate Celery delivery executes a run at most once (CAS)
  * overlap is skipped, downtime produces one `missed` row (no backlog)
  * the outbox sweeper re-sends lost enqueues, the reaper interrupts dead runs
  * auto-pause after N failures, retention keeps N sessions and exempts engaged ones

Requires Postgres + Redis (see tests/external_dependency_unit). No LLM calls.
Stop any live `pulse_scheduler` pointed at the same database while running these.
"""

import datetime as dt
import threading
from collections.abc import Generator
from uuid import UUID

import pytest
from sqlalchemy import delete
from sqlalchemy import select
from sqlalchemy.orm import Session

from om.configs.constants import MessageType
from om.db.engine.sql_engine import get_session_with_current_tenant
from om.db.enums import ChatSessionSharedStatus
from om.db.models import AgentWorkflow
from om.db.models import ChatMessage
from om.db.models import ChatSession
from om.db.models import PulseRun
from om.db.models import PulseSchedule
from om.db.models import PulseTrigger
from om.db.pulse import create_manual_run
from om.db.pulse import create_pulse_schedule
from om.db.pulse import db_now
from om.db.pulse import get_sessions_to_expire
from om.db.pulse import record_trigger_outcome
from om.db.pulse import RUN_FAILED
from om.db.pulse import RUN_INTERRUPTED
from om.db.pulse import RUN_MISSED
from om.db.pulse import RUN_PENDING
from om.db.pulse import RUN_RUNNING
from om.db.pulse import RUN_SKIPPED
from om.db.pulse import start_run
from om.pulse import scheduler as scheduler_mod
from shared_configs.contextvars import get_current_tenant_id
from tests.external_dependency_unit.conftest import create_test_user

UTC = dt.timezone.utc


@pytest.fixture
def enqueued(monkeypatch: pytest.MonkeyPatch) -> list[tuple[int, int]]:
    """Capture enqueues instead of talking to Celery."""
    calls: list[tuple[int, int]] = []
    lock = threading.Lock()

    def fake_enqueue(
        run_id: int, tenant_id: str, countdown: int = 0, webhook: bool = False  # noqa: ARG001
    ) -> None:
        with lock:
            calls.append((run_id, countdown))

    monkeypatch.setattr(scheduler_mod, "enqueue_pulse_run", fake_enqueue)
    return calls


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
    return create_test_user(db_session, "pulse_test").id


@pytest.fixture
def make_schedule(
    db_session: Session, workflow_id: int, owner_id: UUID
) -> Generator:
    created: list[int] = []

    def _make(**overrides: object) -> PulseSchedule:
        now = db_now(db_session)
        params: dict = dict(
            user_id=owner_id,
            workflow_id=workflow_id,
            name="pulse-test",
            schedule_type="interval",
            cron_expression=None,
            interval_seconds=3600,
            run_at=None,
            timezone="UTC",
            input_message="test {{date}}",
            enabled=True,
            retention_count=50,
            next_run_at=now - dt.timedelta(seconds=1),
        )
        params.update(overrides)
        schedule = create_pulse_schedule(db_session, **params)
        created.append(schedule.id)
        return schedule

    yield _make

    db_session.rollback()
    if created:
        db_session.execute(
            delete(ChatSession).where(ChatSession.pulse_trigger_id.in_(created))
        )
        db_session.execute(delete(PulseTrigger).where(PulseTrigger.id.in_(created)))
        db_session.commit()


def _runs(db_session: Session, schedule_id: int) -> list[PulseRun]:
    db_session.expire_all()
    return list(
        db_session.execute(
            select(PulseRun).where(PulseRun.trigger_id == schedule_id).order_by(PulseRun.id)
        ).scalars()
    )


# ---------------------------------------------------------------- HA / exactly-once


def test_concurrent_ticks_fire_slot_exactly_once(
    db_session: Session, make_schedule, enqueued, tenant_context  # noqa: ANN001
) -> None:
    schedule = make_schedule()
    tenant_id = get_current_tenant_id()
    barrier = threading.Barrier(6)
    errors: list[BaseException] = []

    def replica() -> None:
        try:
            barrier.wait()
            scheduler_mod.tick_tenant(tenant_id)
        except BaseException as e:  # pragma: no cover - surfaced below
            errors.append(e)

    threads = [threading.Thread(target=replica) for _ in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)

    assert not errors, errors
    runs = _runs(db_session, schedule.id)
    fired = [r for r in runs if r.status == RUN_PENDING]
    assert len(fired) == 1, [(r.status, r.scheduled_for) for r in runs]
    assert [rid for rid, _ in enqueued].count(fired[0].id) == 1

    db_session.refresh(schedule)
    assert schedule.next_run_at is not None
    assert schedule.next_run_at > db_now(db_session)


def test_duplicate_delivery_cas_single_winner(
    db_session: Session, make_schedule, tenant_context  # noqa: ANN001
) -> None:
    schedule = make_schedule(enabled=False)
    run = create_manual_run(db_session, schedule.id)
    winners: list[int] = []
    barrier = threading.Barrier(5)

    def deliver(i: int) -> None:
        with get_session_with_current_tenant() as s:
            barrier.wait()
            if start_run(s, run.id, f"worker-{i}") is not None:
                winners.append(i)

    threads = [threading.Thread(target=deliver, args=(i,)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    assert len(winners) == 1
    assert _runs(db_session, schedule.id)[0].status == RUN_RUNNING


# ---------------------------------------------------------------- semantics


def test_overlap_is_skipped(
    db_session: Session, make_schedule, enqueued, tenant_context  # noqa: ANN001
) -> None:
    schedule = make_schedule(enabled=True)
    create_manual_run(db_session, schedule.id)  # an active (pending) run
    scheduler_mod.tick_tenant(get_current_tenant_id())
    statuses = [r.status for r in _runs(db_session, schedule.id)]
    assert RUN_SKIPPED in statuses
    assert enqueued == [] or all(
        rid != r.id for rid, _ in enqueued for r in _runs(db_session, schedule.id) if r.status == RUN_SKIPPED
    )


def test_downtime_records_one_missed_and_fires_latest(
    db_session: Session, make_schedule, enqueued, tenant_context  # noqa: ANN001
) -> None:
    now = db_now(db_session)
    # every 5 minutes, scheduler "down" for 3 hours
    schedule = make_schedule(
        interval_seconds=300, next_run_at=now - dt.timedelta(hours=3)
    )
    scheduler_mod.tick_tenant(get_current_tenant_id())
    runs = _runs(db_session, schedule.id)
    assert sum(r.status == RUN_MISSED for r in runs) == 1
    assert sum(r.status == RUN_PENDING for r in runs) == 1
    assert len(runs) == 2  # never a backlog of 36 runs


def test_beyond_grace_cron_only_missed(
    db_session: Session, make_schedule, enqueued, tenant_context  # noqa: ANN001
) -> None:
    now = db_now(db_session)
    schedule = make_schedule(
        schedule_type="cron",
        interval_seconds=None,
        cron_expression="0 3 * * *",
        next_run_at=now - dt.timedelta(hours=2),
    )
    scheduler_mod.tick_tenant(get_current_tenant_id())
    runs = _runs(db_session, schedule.id)
    assert [r.status for r in runs] == [RUN_MISSED]
    assert enqueued == []


def test_once_schedule_disables_after_firing(
    db_session: Session, make_schedule, enqueued, tenant_context  # noqa: ANN001
) -> None:
    now = db_now(db_session)
    schedule = make_schedule(
        schedule_type="once",
        interval_seconds=None,
        run_at=now - dt.timedelta(seconds=2),
        next_run_at=now - dt.timedelta(seconds=2),
    )
    scheduler_mod.tick_tenant(get_current_tenant_id())
    db_session.refresh(schedule)
    assert schedule.enabled is False
    assert schedule.disabled_reason == "completed_once"
    assert schedule.next_run_at is None
    assert len(enqueued) == 1


def test_tenant_capacity_defers_without_losing_slot(
    db_session: Session, make_schedule, enqueued, tenant_context, monkeypatch  # noqa: ANN001
) -> None:
    monkeypatch.setattr(scheduler_mod, "PULSE_TENANT_MAX_CONCURRENT_RUNS", 0)
    schedule = make_schedule()
    due_before = schedule.next_run_at
    scheduler_mod.tick_tenant(get_current_tenant_id())
    db_session.refresh(schedule)
    assert _runs(db_session, schedule.id) == []
    assert schedule.next_run_at == due_before  # stays due, retried next tick


# ---------------------------------------------------------------- outbox / reaper


def test_outbox_resends_stale_pending(
    db_session: Session, make_schedule, enqueued, tenant_context  # noqa: ANN001
) -> None:
    schedule = make_schedule(enabled=False)
    run = create_manual_run(db_session, schedule.id)
    run.created_at = db_now(db_session) - dt.timedelta(minutes=10)
    db_session.commit()
    resent = scheduler_mod._resend_stale_pending(get_current_tenant_id())
    assert resent >= 1
    assert run.id in [rid for rid, _ in enqueued]


def test_outbox_resend_is_throttled_per_run(
    db_session: Session, make_schedule, enqueued, tenant_context  # noqa: ANN001
) -> None:
    schedule = make_schedule(enabled=False)
    run = create_manual_run(db_session, schedule.id)
    run.created_at = db_now(db_session) - dt.timedelta(minutes=10)
    db_session.commit()
    tenant = get_current_tenant_id()
    scheduler_mod._resend_stale_pending(tenant)
    scheduler_mod._resend_stale_pending(tenant)  # immediately again (another replica)
    assert [rid for rid, _ in enqueued].count(run.id) == 1


def test_outbox_marks_too_late_scheduled_run_missed(
    db_session: Session, make_schedule, enqueued, tenant_context  # noqa: ANN001
) -> None:
    schedule = make_schedule(enabled=False, interval_seconds=600)
    old = db_now(db_session) - dt.timedelta(hours=2)
    db_session.add(
        PulseRun(
            trigger_id=schedule.id,
            scheduled_for=old,
            fired_by="scheduled",
            status=RUN_PENDING,
            created_at=old,
        )
    )
    db_session.commit()
    scheduler_mod._resend_stale_pending(get_current_tenant_id())
    runs = _runs(db_session, schedule.id)
    assert [r.status for r in runs] == [RUN_MISSED]
    assert enqueued == []


def test_once_schedule_waits_for_active_run_instead_of_skipping(
    db_session: Session, make_schedule, enqueued, tenant_context  # noqa: ANN001
) -> None:
    now = db_now(db_session)
    schedule = make_schedule(
        schedule_type="once",
        interval_seconds=None,
        run_at=now - dt.timedelta(seconds=2),
        next_run_at=now - dt.timedelta(seconds=2),
    )
    create_manual_run(db_session, schedule.id)  # active
    scheduler_mod.tick_tenant(get_current_tenant_id())
    db_session.refresh(schedule)
    assert schedule.enabled is True and schedule.next_run_at is not None
    assert all(r.status != RUN_SKIPPED for r in _runs(db_session, schedule.id))


def test_reaper_interrupts_dead_run_and_counts_failure(
    db_session: Session, make_schedule, tenant_context  # noqa: ANN001
) -> None:
    schedule = make_schedule(enabled=False)
    run = create_manual_run(db_session, schedule.id)
    assert start_run(db_session, run.id, "dead-worker") is not None
    db_session.refresh(run)
    run.heartbeat_at = db_now(db_session) - dt.timedelta(minutes=10)
    db_session.commit()

    reaped = scheduler_mod._reap_stale_running(get_current_tenant_id())
    assert reaped >= 1
    db_session.expire_all()
    assert db_session.get(PulseRun, run.id).status == RUN_INTERRUPTED  # type: ignore[union-attr]
    db_session.refresh(schedule)
    assert schedule.consecutive_failures == 1
    assert schedule.last_run_status == RUN_INTERRUPTED


def test_auto_pause_after_consecutive_failures(
    db_session: Session, make_schedule, tenant_context  # noqa: ANN001
) -> None:
    schedule = make_schedule()
    slot = db_now(db_session)
    paused_flags = [
        record_trigger_outcome(
            db_session,
            schedule.id,
            run_status=RUN_FAILED,
            scheduled_for=slot,
            max_consecutive_failures=3,
        )[1]
        for _ in range(3)
    ]
    assert paused_flags == [False, False, True]
    db_session.refresh(schedule)
    assert schedule.enabled is False
    assert schedule.disabled_reason == "auto_paused_failures"


# ---------------------------------------------------------------- retention


def test_retention_keeps_newest_and_exempts_engaged_sessions(
    db_session: Session, make_schedule, owner_id: UUID, tenant_context  # noqa: ANN001
) -> None:
    schedule = make_schedule(enabled=False, retention_count=1)
    base = db_now(db_session)
    sessions: list[ChatSession] = []
    for i in range(4):
        cs = ChatSession(
            user_id=owner_id,
            description=f"run {i}",
            pulse_trigger_id=schedule.id,
            time_created=base - dt.timedelta(hours=4 - i),
        )
        db_session.add(cs)
        sessions.append(cs)
    db_session.commit()
    oldest, replied, shared, newest = sessions

    # `replied`: the user answered in the run chat (2 USER messages)
    for _ in range(2):
        db_session.add(
            ChatMessage(
                chat_session_id=replied.id,
                message="hi",
                message_type=MessageType.USER,
                token_count=1,
            )
        )
    shared.shared_status = ChatSessionSharedStatus.PUBLIC
    db_session.commit()

    to_expire = set(get_sessions_to_expire(db_session, schedule))
    assert newest.id not in to_expire  # within retention_count
    assert replied.id not in to_expire  # engaged
    assert shared.id not in to_expire  # shared
    assert oldest.id in to_expire

    # An unanswered "needs input" run chat is still actionable -> kept
    db_session.add(
        PulseRun(
            trigger_id=schedule.id,
            scheduled_for=base,
            fired_by="manual",
            status="needs_input",
            chat_session_id=oldest.id,
        )
    )
    db_session.commit()
    assert oldest.id not in set(get_sessions_to_expire(db_session, schedule))


# ---------------------------------------------------------------- input modes


def test_list_mode_item_cursor_is_atomic(
    db_session: Session, make_schedule, tenant_context  # noqa: ANN001
) -> None:
    """Concurrent runs of a list-mode schedule each take a different item."""
    from om.db.pulse import claim_next_item_index
    from om.pulse.inputs import item_for_index

    items = ["asthma", "diabetes", "hypertension"]
    schedule = make_schedule(
        enabled=False, input_mode="list", input_message="{{item}}", input_items=items
    )
    taken: list[int] = []
    lock = threading.Lock()
    barrier = threading.Barrier(5)

    def take() -> None:
        with get_session_with_current_tenant() as s:
            barrier.wait()
            idx = claim_next_item_index(s, schedule.id)
            with lock:
                taken.append(idx)

    threads = [threading.Thread(target=take) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    assert sorted(taken) == [0, 1, 2, 3, 4]
    assert [item_for_index(items, i) for i in sorted(taken)] == [
        "asthma",
        "diabetes",
        "hypertension",
        "asthma",
        "diabetes",
    ]
    db_session.refresh(schedule)
    assert schedule.input_item_index == 5
