"""The Pulse health endpoint reports what's really happening with webhook runs and workers.

Requires Postgres + Redis (see tests/external_dependency_unit). No LLM calls. Queue names in
the presence tests are unique, so real workers sharing this Redis can't change the counts.
"""

import datetime as dt
import fnmatch
import re
import threading
import time
from collections.abc import Generator
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy import text
from sqlalchemy import update
from sqlalchemy.orm import Session

from om.background.celery.apps import app_base
from om.background.celery.apps import pulse_worker
from om.db.models import AgentWorkflow
from om.db.models import PulseRun
from om.db.models import PulseWebhook
from om.db.pulse import RUN_RUNNING
from om.db.pulse_webhook import accept_webhook_event
from om.db.pulse_webhook import create_pulse_webhook
from om.db.pulse_webhook import get_webhook_run_health
from om.db.pulse_webhook import revoke_webhook_credentials
from om.pulse import worker_presence
from om.pulse.webhooks.tokens import generate_token
from om.pulse.webhooks.tokens import hash_token
from om.pulse.worker_presence import count_alive_workers
from om.pulse.worker_presence import WorkerPresence
from om.redis.redis_pool import get_redis_client
from om.server.features.pulse import api
from shared_configs.configs import POSTGRES_DEFAULT_SCHEMA
from tests.external_dependency_unit.conftest import create_test_user


def _queue() -> str:
    return f"test_{uuid4().hex}"


def _wait_for(queue: str, count: int) -> None:
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if count_alive_workers(queue) == count:
            return
        time.sleep(0.05)
    assert count_alive_workers(queue) == count


def test_a_worker_counts_only_for_its_own_queue() -> None:
    queue = _queue()
    # One queue's name starting with another's must not mix them up: pulse / pulse_webhook.
    longer = f"{queue}_webhook"
    presence = WorkerPresence(longer, "host-a")
    presence.start()
    try:
        _wait_for(longer, 1)
        assert count_alive_workers(queue) == 0
    finally:
        presence.stop()


def test_stopping_withdraws_at_once_and_replicas_add_up() -> None:
    queue = _queue()
    first = WorkerPresence(queue, "host-a")
    second = WorkerPresence(queue, "host-b")
    first.start()
    second.start()
    try:
        _wait_for(queue, 2)
    finally:
        first.stop()
    assert count_alive_workers(queue) == 1
    second.stop()
    assert count_alive_workers(queue) == 0


def test_withdrawing_stops_counting_without_waiting_for_shutdown() -> None:
    queue = _queue()
    presence = WorkerPresence(queue, "host-a")
    presence.start()
    _wait_for(queue, 1)
    presence.withdraw()
    _wait_for(queue, 0)
    presence.stop()


class _FakePresence:
    def __init__(self, queue: str, hostname: str) -> None:
        self.calls: list[tuple[str, ...]] = [("created", queue, hostname)]

    def start(self) -> None:
        self.calls.append(("start",))

    def withdraw(self) -> None:
        self.calls.append(("withdraw",))

    def stop(self) -> None:
        self.calls.append(("stop",))


def test_worker_signals_start_and_withdraw_presence(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pulse_worker, "WorkerPresence", _FakePresence)
    monkeypatch.setattr(pulse_worker, "PULSE_WORKER_QUEUE", "pulse_webhook")
    monkeypatch.setattr(pulse_worker, "_presence", None)
    monkeypatch.setattr(app_base, "on_worker_ready", lambda *_, **__: None)
    monkeypatch.setattr(app_base, "on_worker_shutdown", lambda *_, **__: None)
    sender: Any = type("Sender", (), {"hostname": "pulse_webhook@abc"})()

    pulse_worker.on_worker_ready(sender)
    presence = pulse_worker._presence
    assert isinstance(presence, _FakePresence)
    assert presence.calls == [("created", "pulse_webhook", "pulse_webhook@abc"), ("start",)]

    pulse_worker.on_worker_shutting_down()
    assert presence.calls[-1] == ("withdraw",)

    pulse_worker.on_worker_shutdown(sender)
    assert presence.calls[-1] == ("stop",)


@pytest.mark.parametrize("hostname", ["pulse@abc", "pulse_webhook@abc"])
def test_container_healthcheck_finds_each_workers_readiness_file(hostname: str) -> None:
    script = Path(__file__).parents[3] / "scripts" / "pulse_entrypoint.sh"
    pattern = re.search(r"for f in (/tmp/\S+readiness\.txt)", script.read_text())
    assert pattern is not None
    probe = app_base.make_probe_path("readiness", hostname)
    assert fnmatch.fnmatch(str(probe), pattern.group(1))


def test_presence_expires_so_a_worker_that_dies_disappears() -> None:
    queue = _queue()
    presence = WorkerPresence(queue, "host-a")
    presence.start()
    _wait_for(queue, 1)
    r = get_redis_client(tenant_id=POSTGRES_DEFAULT_SCHEMA)
    key = f"{worker_presence.WORKER_PRESENCE_KEY_PREFIX}{queue}:host-a"
    try:
        ttl = r.ttl(key)
        assert 0 < ttl <= worker_presence.PRESENCE_EXPIRY_SECONDS
        # Refreshed well before it expires, so one missed refresh doesn't look like a death
        assert worker_presence.PRESENCE_REFRESH_SECONDS * 2 < worker_presence.PRESENCE_EXPIRY_SECONDS
    finally:
        presence.stop()


def test_a_redis_failure_while_publishing_does_not_end_the_thread(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queue = _queue()
    real = worker_presence.get_redis_client
    failed = threading.Event()

    def flaky(*args: Any, **kwargs: Any) -> Any:
        # Only the publishing thread: the test's own reads have to work
        if threading.current_thread().name == "pulse-worker-presence" and not failed.is_set():
            failed.set()
            raise ConnectionError("redis down")
        return real(*args, **kwargs)

    monkeypatch.setattr(worker_presence, "get_redis_client", flaky)
    monkeypatch.setattr(worker_presence, "PRESENCE_REFRESH_SECONDS", 0.05)
    presence = WorkerPresence(queue, "host-a")
    presence.start()
    try:
        _wait_for(queue, 1)
        assert failed.is_set()
    finally:
        presence.stop()


@pytest.fixture
def webhook(db_session: Session) -> Generator[PulseWebhook, None, None]:
    workflow = db_session.execute(select(AgentWorkflow).limit(1)).scalars().first()
    assert workflow is not None
    created = create_pulse_webhook(
        db_session,
        user_id=create_test_user(db_session, "webhook_health_test").id,
        workflow_id=workflow.id,
        name="health",
        timezone="UTC",
        input_message="x",
        retention_count=5,
        enabled=True,
        token_hash=hash_token(generate_token(None)),
        token_last4="abcd",
        auth_mode="standard_webhooks",
        signing_secret="whsec_AAAA",
        header_name=None,
        dedup_source="none",
        dedup_path=None,
    )
    db_session.commit()
    yield created
    db_session.rollback()
    db_session.execute(text("DELETE FROM pulse_trigger WHERE id = :id"), {"id": created.id})
    db_session.commit()


def _accept(db_session: Session, webhook_id: int) -> int:
    return accept_webhook_event(
        db_session,
        webhook_id=webhook_id,
        dedup_key=None,
        payload={"body": {}},
        max_pending=20,
        tenant_max_active=100,
    ).run_id


def test_waiting_runs_show_how_long_the_oldest_has_waited(
    db_session: Session, webhook: PulseWebhook
) -> None:
    before = get_webhook_run_health(db_session)
    first = _accept(db_session, webhook.id)
    second = _accept(db_session, webhook.id)
    db_session.execute(
        update(PulseRun)
        .where(PulseRun.id == first)
        .values(created_at=PulseRun.created_at - dt.timedelta(minutes=10))
    )
    db_session.commit()

    health = get_webhook_run_health(db_session)
    assert health.pending_runs == before.pending_runs + 2
    assert health.oldest_pending_seconds is not None
    assert health.oldest_pending_seconds >= 600

    # A run that started no longer counts as waiting
    db_session.execute(
        update(PulseRun).where(PulseRun.id.in_([first, second])).values(status=RUN_RUNNING)
    )
    db_session.commit()
    after = get_webhook_run_health(db_session)
    assert after.pending_runs == before.pending_runs
    assert after.running_runs == before.running_runs + 2
    if before.pending_runs == 0:
        assert after.oldest_pending_seconds is None


def test_a_revoked_or_paused_webhook_is_not_active(
    db_session: Session, webhook: PulseWebhook
) -> None:
    active = get_webhook_run_health(db_session).active_webhooks

    webhook.enabled = False
    db_session.commit()
    assert get_webhook_run_health(db_session).active_webhooks == active - 1

    webhook.enabled = True
    db_session.commit()
    assert get_webhook_run_health(db_session).active_webhooks == active

    revoke_webhook_credentials(db_session, webhook)
    db_session.commit()
    assert get_webhook_run_health(db_session).active_webhooks == active - 1


def _call(db_session: Session) -> api.PulseHealthResponse:
    return api.get_pulse_health(None, db_session)  # type: ignore[arg-type]


def test_endpoint_reports_the_webhook_section(
    db_session: Session, webhook: PulseWebhook, monkeypatch: pytest.MonkeyPatch
) -> None:
    alive = {"pulse": 3, "pulse_webhook": 2}
    monkeypatch.setattr(api, "count_alive_workers", lambda queue: alive[queue])
    monkeypatch.setattr(api, "webhooks_allowed", lambda: True)
    pending = get_webhook_run_health(db_session).pending_runs
    _accept(db_session, webhook.id)

    health = _call(db_session)

    assert health.pulse_workers_alive == 3
    assert health.webhooks.workers_alive == 2
    assert health.webhooks.enabled is True
    assert health.webhooks.pending_runs == pending + 1
    assert health.webhooks.oldest_pending_seconds is not None


def test_unreadable_is_reported_as_unknown_not_as_zero_or_off(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken(*_: object) -> None:
        raise ConnectionError("store unavailable")

    monkeypatch.setattr(api, "count_alive_workers", broken)
    monkeypatch.setattr(api, "webhooks_allowed", broken)

    health = _call(db_session)

    assert health.pulse_workers_alive is None
    assert health.webhooks.workers_alive is None
    assert health.webhooks.enabled is None
