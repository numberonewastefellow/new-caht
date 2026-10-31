"""A webhook token only opens a webhook in the tenant it belongs to.

Tenants are Postgres schemas. This makes a real second schema holding the webhook tables,
then calls `locate`, the same function the public endpoint uses, with tokens claiming each
tenant. Requires Postgres + Redis. No LLM calls.
"""

from collections.abc import Generator
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy import text
from sqlalchemy.orm import Session

from om.db.engine.sql_engine import get_session_with_current_tenant
from om.db.models import AgentWorkflow
from om.db.pulse_webhook import create_pulse_webhook
from om.pulse.webhooks import intake
from om.pulse.webhooks import limits
from om.pulse.webhooks import listen
from om.pulse.webhooks import tokens
from om.pulse.webhooks.intake import IntakeError
from om.pulse.webhooks.intake import locate
from om.pulse.webhooks.tokens import generate_token
from om.pulse.webhooks.tokens import hash_token
from tests.external_dependency_unit.conftest import create_test_user

OTHER_TENANT = "tenant_webhook_it"


def _create_other_tenant(db_session: Session) -> None:
    db_session.execute(text(f'DROP SCHEMA IF EXISTS "{OTHER_TENANT}" CASCADE'))
    db_session.execute(text(f'CREATE SCHEMA "{OTHER_TENANT}"'))
    for table in ("pulse_trigger", "pulse_webhook", "key_value_store"):
        db_session.execute(
            text(f'CREATE TABLE "{OTHER_TENANT}".{table} (LIKE public.{table} INCLUDING ALL)')
        )
    db_session.commit()


@pytest.fixture
def other_tenant(db_session: Session) -> Generator[str, None, None]:
    _create_other_tenant(db_session)
    yield OTHER_TENANT
    db_session.rollback()
    db_session.execute(text(f'DROP SCHEMA IF EXISTS "{OTHER_TENANT}" CASCADE'))
    db_session.commit()


@pytest.fixture
def multi_tenant_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tokens, "MULTI_TENANT", True)
    # This test isn't about rate limits, and one address would run out.
    monkeypatch.setattr(limits, "check_rate_limits", lambda address, token_hash: None)  # noqa: ARG005


def _call(token: str) -> int:
    return locate(token, content_length="2", peer="1.1.1.1", forwarded_for=None).webhook_id


def test_token_opens_only_its_own_tenant(
    db_session: Session, other_tenant: str, multi_tenant_tokens: None  # noqa: ARG001
) -> None:
    owner = create_test_user(db_session, "webhook_tenant_test")
    workflow = db_session.execute(select(AgentWorkflow).limit(1)).scalars().first()
    assert workflow is not None
    public_secret_part = generate_token(None)[len("whk_") :]
    public_token = f"whk_{public_secret_part}"
    webhook = create_pulse_webhook(
        db_session,
        user_id=owner.id,
        workflow_id=workflow.id,
        name="tenant-a",
        timezone="UTC",
        input_message="x",
        retention_count=5,
        enabled=True,
        token_hash=hash_token(public_token),
        token_last4="abcd",
        auth_mode="standard_webhooks",
        signing_secret="whsec_AAAA",
        header_name=None,
        dedup_source="none",
        dedup_path=None,
    )
    try:
        # The real owner of the token finds it.
        assert _call(public_token) == webhook.id

        # The same secret part, claiming the other tenant: looked up there, and absent.
        crossing = f"whk_{other_tenant}.{public_secret_part}"
        with pytest.raises(IntakeError) as caught:
            _call(crossing)
        assert caught.value.status == 404

        # A tenant name with no schema behind it answers the same, rather than a 500.
        missing = f"whk_tenant_nope_{uuid4().hex}.{public_secret_part}"
        with pytest.raises(IntakeError) as caught:
            _call(missing)
        assert caught.value.status == 404

        # A name that can't be a schema never reaches the database.
        unsafe = f"whk_bad%20name.{public_secret_part}"
        with pytest.raises(IntakeError) as caught:
            _call(unsafe)
        assert caught.value.status == 404
    finally:
        with get_session_with_current_tenant() as session:
            session.execute(text("DELETE FROM pulse_trigger WHERE id = :id"), {"id": webhook.id})
            session.commit()


def test_listen_state_is_per_tenant() -> None:
    """Webhook ids repeat between tenants, so the Redis keys must not collide."""
    webhook_id = 987654
    listen.stop_listening("tenant_a_listen", webhook_id)
    listen.stop_listening("tenant_b_listen", webhook_id)
    try:
        listen.start_listening("tenant_a_listen", webhook_id)
        assert listen.seconds_left("tenant_a_listen", webhook_id) > 0
        assert listen.seconds_left("tenant_b_listen", webhook_id) == 0
        assert listen.capture("tenant_b_listen", webhook_id, {"x": 1}) is False
        assert listen.capture("tenant_a_listen", webhook_id, {"x": 2}) is True
        assert listen.captures("tenant_a_listen", webhook_id) == [{"x": 2}]
        assert listen.captures("tenant_b_listen", webhook_id) == []
    finally:
        listen.stop_listening("tenant_a_listen", webhook_id)
        listen.stop_listening("tenant_b_listen", webhook_id)


def _unavailable(*_: object, **__: object) -> None:
    raise limits.LimiterUnavailable()


def test_redis_down_refuses_instead_of_dropping_the_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(limits, "check_rate_limits", _unavailable)
    with pytest.raises(IntakeError) as caught:
        _call(generate_token(None))
    assert caught.value.status == 503
    assert caught.value.retry_after


def test_unreadable_admin_switch_refuses_instead_of_reopening(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An admin may have turned webhooks off, so not knowing must not mean allowed."""
    monkeypatch.setattr(limits, "check_rate_limits", lambda address, token_hash: None)  # noqa: ARG005
    owner = create_test_user(db_session, "webhook_switch_test")
    workflow = db_session.execute(select(AgentWorkflow).limit(1)).scalars().first()
    assert workflow is not None
    token = generate_token(None)
    webhook = create_pulse_webhook(
        db_session,
        user_id=owner.id,
        workflow_id=workflow.id,
        name="switch",
        timezone="UTC",
        input_message="x",
        retention_count=5,
        enabled=True,
        token_hash=hash_token(token),
        token_last4="abcd",
        auth_mode="standard_webhooks",
        signing_secret="whsec_AAAA",
        header_name=None,
        dedup_source="none",
        dedup_path=None,
    )

    def broken() -> bool:
        raise RuntimeError("store unavailable")

    monkeypatch.setattr(intake, "webhooks_allowed", broken)
    try:
        with pytest.raises(IntakeError) as caught:
            _call(token)
        assert caught.value.status == 503
    finally:
        db_session.execute(text("DELETE FROM pulse_trigger WHERE id = :id"), {"id": webhook.id})
        db_session.commit()

