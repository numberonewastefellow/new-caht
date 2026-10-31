"""DB operations for Pulse webhooks. What all triggers share is in om/db/pulse.py."""

import datetime
from dataclasses import dataclass
from typing import Any
from typing import cast
from uuid import UUID

from sqlalchemy import func
from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy import Table
from sqlalchemy import text
from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from om.db.models import PulseRun
from om.db.models import PulseTrigger
from om.db.models import PulseWebhook
from om.db.pulse import ACTIVE_RUN_STATUSES
from om.db.pulse import db_now
from om.db.pulse import FIRED_WEBHOOK
from om.db.pulse import lock_trigger_row
from om.db.pulse import RUN_PENDING
from om.db.pulse import RUN_RUNNING
from om.db.pulse import TERMINAL_RUN_STATUSES

_MAX_REASON_CHARS = 200


def _webhook_table() -> Table:
    """Direct updates: see _write_credentials and record_webhook_rejection."""
    return cast(Table, PulseWebhook.__table__)


def create_pulse_webhook(
    db_session: Session,
    *,
    user_id: UUID,
    workflow_id: int,
    name: str,
    timezone: str,
    input_message: str,
    retention_count: int,
    enabled: bool,
    token_hash: str,
    token_last4: str,
    auth_mode: str,
    signing_secret: str,
    header_name: str | None,
    dedup_source: str,
    dedup_path: str | None,
) -> PulseWebhook:
    webhook = PulseWebhook(
        user_id=user_id,
        updated_by_id=user_id,
        workflow_id=workflow_id,
        name=name,
        timezone=timezone,
        input_message=input_message,
        retention_count=retention_count,
        enabled=enabled,
        consecutive_failures=0,
        token_hash=token_hash,
        token_last4=token_last4,
        auth_mode=auth_mode,
        signing_secret=signing_secret,
        header_name=header_name,
        dedup_source=dedup_source,
        dedup_path=dedup_path,
    )
    db_session.add(webhook)
    db_session.commit()
    db_session.refresh(webhook)
    return webhook


def get_pulse_webhook(db_session: Session, webhook_id: int) -> PulseWebhook | None:
    return db_session.get(PulseWebhook, webhook_id)


def list_pulse_webhooks(
    db_session: Session, user_id: UUID | None, include_all_users: bool = False
) -> list[PulseWebhook]:
    stmt = select(PulseWebhook).order_by(PulseWebhook.created_at.desc())
    if not include_all_users:
        stmt = stmt.where(PulseWebhook.user_id == user_id)
    return list(db_session.execute(stmt).scalars().all())


def count_webhooks_for_user(db_session: Session, user_id: UUID) -> int:
    return db_session.execute(
        select(func.count())
        .select_from(PulseWebhook)
        .where(PulseWebhook.user_id == user_id)
    ).scalar_one()


def find_webhook_by_token_hash(db_session: Session, token_hash: str) -> PulseWebhook | None:
    """The webhook a token opens: not revoked, and either the current token or the
    previous one while its rotation grace lasts. `enabled` is the caller's to check."""
    return db_session.execute(
        select(PulseWebhook)
        .where(PulseWebhook.revoked_at.is_(None))
        .where(
            or_(
                PulseWebhook.token_hash == token_hash,
                (PulseWebhook.previous_token_hash == token_hash)
                & (PulseWebhook.previous_valid_until > func.now()),
            )
        )
    ).scalar_one_or_none()


def rotate_webhook_credentials(
    db_session: Session,
    webhook: PulseWebhook,
    *,
    token_hash: str,
    token_last4: str,
    signing_secret: str,
    grace_hours: int,
) -> None:
    """New token and secret. The old ones keep working for `grace_hours`, unless they
    were revoked: a revoke means they may be compromised, so they never come back."""
    now = db_now(db_session)
    keep_old = grace_hours > 0 and webhook.revoked_at is None
    _write_credentials(
        db_session,
        webhook,
        token_hash=token_hash,
        token_last4=token_last4,
        signing_secret=signing_secret,
        previous_token_hash=webhook.token_hash if keep_old else None,
        previous_signing_secret=webhook.signing_secret if keep_old else None,
        previous_valid_until=(
            now + datetime.timedelta(hours=grace_hours) if keep_old else None
        ),
        rotated_at=now,
        revoked_at=None,
    )


def revoke_webhook_credentials(db_session: Session, webhook: PulseWebhook) -> None:
    """Kill the current and previous credentials at once. Run history stays."""
    _write_credentials(
        db_session,
        webhook,
        revoked_at=db_now(db_session),
        previous_token_hash=None,
        previous_signing_secret=None,
        previous_valid_until=None,
    )


def _write_credentials(db_session: Session, webhook: PulseWebhook, **values: Any) -> None:
    # Directly on the table: assigning to an encrypted attribute makes the ORM compare it
    # with the old value, and SensitiveValue refuses comparisons.
    table = _webhook_table()
    db_session.execute(update(table).where(table.c.id == webhook.id).values(**values))
    db_session.execute(
        update(PulseTrigger).where(PulseTrigger.id == webhook.id).values(updated_at=func.now())
    )
    db_session.commit()
    db_session.refresh(webhook)


def record_webhook_rejection(db_session: Session, webhook_id: int, reason: str) -> None:
    """Why the latest call was refused. One value per webhook, not a row per call, so
    someone holding the URL can't grow the database by sending bad requests."""
    table = _webhook_table()
    db_session.execute(
        update(table)
        .where(table.c.id == webhook_id)
        .values(last_rejected_at=func.now(), last_rejected_reason=reason[:_MAX_REASON_CHARS])
    )
    db_session.commit()


@dataclass(frozen=True)
class AcceptedEvent:
    run_id: int
    duplicate: bool


class WebhookOverloaded(Exception):
    """Too many runs are waiting. The message is shown to the owner."""


class WebhookClosed(Exception):
    """Paused, revoked or deleted after the call was located."""


def _run_for_dedup_key(db_session: Session, webhook_id: int, dedup_key: str) -> int | None:
    return db_session.execute(
        select(PulseRun.id)
        .where(PulseRun.trigger_id == webhook_id)
        .where(PulseRun.fired_by == FIRED_WEBHOOK)
        .where(PulseRun.dedup_key == dedup_key)
    ).scalar_one_or_none()


def _count_pending(db_session: Session, webhook_id: int) -> int:
    return db_session.execute(
        select(func.count(PulseRun.id))
        .where(PulseRun.trigger_id == webhook_id)
        .where(PulseRun.status == RUN_PENDING)
    ).scalar_one()


def count_active_webhook_runs(db_session: Session) -> int:
    return db_session.execute(
        select(func.count(PulseRun.id))
        .where(PulseRun.fired_by == FIRED_WEBHOOK)
        .where(PulseRun.status.in_(ACTIVE_RUN_STATUSES))
    ).scalar_one()


@dataclass(frozen=True)
class WebhookRunHealth:
    active_webhooks: int
    pending_runs: int
    running_runs: int
    oldest_pending_seconds: float | None


def get_webhook_run_health(db_session: Session) -> WebhookRunHealth:
    active_webhooks = db_session.execute(
        select(func.count())
        .select_from(PulseWebhook)
        .where(PulseWebhook.enabled.is_(True))
        .where(PulseWebhook.revoked_at.is_(None))
    ).scalar_one()
    rows = db_session.execute(
        select(PulseRun.status, func.count(), func.min(PulseRun.created_at))
        .where(PulseRun.fired_by == FIRED_WEBHOOK)
        .where(PulseRun.status.in_(ACTIVE_RUN_STATUSES))
        .group_by(PulseRun.status)
    ).all()
    counts = {status: count for status, count, _ in rows}
    oldest = next((first for status, _, first in rows if status == RUN_PENDING), None)
    return WebhookRunHealth(
        active_webhooks=active_webhooks,
        pending_runs=counts.get(RUN_PENDING, 0),
        running_runs=counts.get(RUN_RUNNING, 0),
        oldest_pending_seconds=(
            (db_now(db_session) - oldest).total_seconds() if oldest else None
        ),
    )


def accept_webhook_event(
    db_session: Session,
    *,
    webhook_id: int,
    dedup_key: str | None,
    payload: dict[str, Any],
    max_pending: int,
    tenant_max_active: int,
) -> AcceptedEvent:
    """Store one event as a pending run, or return the run an earlier copy created.

    Commits, so the caller can enqueue safely afterwards. The row lock serialises calls
    to one webhook, which makes the pending count exact. A duplicate is answered before
    the caps: the event is already accepted, so a full queue doesn't change that.

    Raises:
        WebhookOverloaded: Too many runs are already waiting.
        WebhookClosed: It was paused, revoked or deleted after the call was located.
    """
    lock_trigger_row(db_session, webhook_id)
    state = db_session.execute(
        select(PulseWebhook.enabled, PulseWebhook.revoked_at)
        .select_from(PulseWebhook)
        .where(PulseWebhook.id == webhook_id)
    ).first()
    if state is None or not state.enabled or state.revoked_at is not None:
        db_session.rollback()
        raise WebhookClosed()

    if dedup_key is not None:
        existing = _run_for_dedup_key(db_session, webhook_id, dedup_key)
        if existing is not None:
            db_session.commit()
            return AcceptedEvent(run_id=existing, duplicate=True)

    if _count_pending(db_session, webhook_id) >= max_pending:
        db_session.rollback()
        raise WebhookOverloaded(f"{max_pending} runs of this webhook are already waiting")
    if count_active_webhook_runs(db_session) >= tenant_max_active:
        db_session.rollback()
        raise WebhookOverloaded("Too many webhook runs are in progress in this workspace")

    now = db_now(db_session)
    run_id = db_session.execute(
        insert(PulseRun)
        .values(
            trigger_id=webhook_id,
            scheduled_for=now,
            fired_by=FIRED_WEBHOOK,
            status=RUN_PENDING,
            dedup_key=dedup_key,
            trigger_payload=payload,
        )
        .on_conflict_do_nothing(
            index_elements=["trigger_id", "dedup_key"],
            index_where=text("fired_by = 'webhook' AND dedup_key IS NOT NULL"),
        )
        .returning(PulseRun.id)
    ).scalar_one_or_none()
    table = _webhook_table()
    db_session.execute(
        update(table).where(table.c.id == webhook_id).values(last_received_at=now)
    )
    if run_id is None:  # the lock makes this unreachable; the index is the guarantee
        assert dedup_key is not None
        existing = _run_for_dedup_key(db_session, webhook_id, dedup_key)
        db_session.commit()
        assert existing is not None
        return AcceptedEvent(run_id=existing, duplicate=True)
    db_session.commit()
    return AcceptedEvent(run_id=run_id, duplicate=False)


def clear_old_payloads(db_session: Session, older_than: datetime.datetime) -> int:
    """Payloads can hold personal data, so they're kept for less time than the run row."""
    result = db_session.execute(
        update(PulseRun)
        .where(PulseRun.trigger_payload.is_not(None))
        .where(PulseRun.created_at < older_than)
        .where(PulseRun.status.in_(TERMINAL_RUN_STATUSES))
        .values(trigger_payload=None)
    )
    db_session.commit()
    return result.rowcount or 0  # type: ignore[attr-defined]
