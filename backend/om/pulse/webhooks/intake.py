"""The public webhook request, cheapest checks first. No HTTP framework types here, so
every step can be tested directly.

locate()  shape, size header, tenant, rate limits, token lookup. Runs before the body
          is read, so an unknown caller can't make us buffer anything.
accept()  signature over the raw bytes, then JSON checks, then one run or one capture.

Unknown, revoked and paused webhooks, and missing tenants, all raise the same NotFound,
so a caller learns nothing about which tokens exist.
"""

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from om.configs.pulse_configs import PULSE_WEBHOOK_MAX_BODY_BYTES
from om.configs.pulse_configs import PULSE_WEBHOOK_MAX_PENDING_RUNS
from om.configs.pulse_configs import PULSE_WEBHOOK_TENANT_MAX_ACTIVE_RUNS
from om.db.engine.sql_engine import get_session_with_tenant
from om.db.engine.sql_engine import is_valid_schema_name
from om.db.models import PulseWebhook
from om.db.pulse import db_now
from om.db.pulse_webhook import accept_webhook_event
from om.db.pulse_webhook import find_webhook_by_token_hash
from om.db.pulse_webhook import get_pulse_webhook
from om.db.pulse_webhook import record_webhook_rejection
from om.db.pulse_webhook import WebhookClosed
from om.db.pulse_webhook import WebhookOverloaded
from om.pulse.dispatch import enqueue_pulse_run
from om.pulse.webhooks import limits
from om.pulse.webhooks import listen
from om.pulse.webhooks.limits import client_address
from om.pulse.webhooks.limits import LimiterUnavailable
from om.pulse.webhooks.limits import RateLimited
from om.pulse.webhooks.payload import as_text
from om.pulse.webhooks.payload import parse_body
from om.pulse.webhooks.payload import PayloadError
from om.pulse.webhooks.payload import stored_payload
from om.pulse.webhooks.payload import strip_credential_headers
from om.pulse.webhooks.payload import value_at_path
from om.pulse.webhooks.policy import webhooks_allowed
from om.pulse.webhooks.tokens import has_token_shape
from om.pulse.webhooks.tokens import hash_token
from om.pulse.webhooks.tokens import tenant_from_token
from om.pulse.webhooks.verify import SignedRequest
from om.pulse.webhooks.verify import verify_request
from om.pulse.webhooks.verify import VerificationError
from om.pulse.webhooks.verify import VerifierConfig
from om.utils.logger import setup_logger
from shared_configs.contextvars import CURRENT_TENANT_ID_CONTEXTVAR

logger = setup_logger()

# Above this a dedup value is hashed, so it fits the column whatever the sender uses.
_MAX_DEDUP_KEY_CHARS = 256
_OVERLOAD_RETRY_SECONDS = 30
_UNAVAILABLE_RETRY_SECONDS = 15

DEDUP_WEBHOOK_ID = "webhook_id"
DEDUP_HEADER = "header"
DEDUP_JSON_PATH = "json_path"
DEDUP_NONE = "none"
DEDUP_SOURCES = (DEDUP_WEBHOOK_ID, DEDUP_HEADER, DEDUP_JSON_PATH, DEDUP_NONE)


class IntakeError(Exception):
    """Ends the request with this status."""

    def __init__(self, status: int, detail: str, retry_after: int | None = None) -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail
        self.retry_after = retry_after


def _not_found() -> IntakeError:
    return IntakeError(404, "Not Found")


@dataclass(frozen=True)
class LocatedWebhook:
    tenant_id: str
    webhook_id: int


@dataclass(frozen=True)
class IntakeResult:
    run_id: int | None = None
    duplicate: bool = False
    captured: bool = False


def _lookup(tenant_id: str, token_hash: str) -> LocatedWebhook | None:
    try:
        with get_session_with_tenant(tenant_id=tenant_id) as db_session:
            webhook = find_webhook_by_token_hash(db_session, token_hash)
            if webhook is None:
                limits.remember_miss(token_hash)
                return None
            if not webhook.enabled:
                return None
            return LocatedWebhook(tenant_id=tenant_id, webhook_id=webhook.id)
    except ProgrammingError:
        # A well-formed tenant name with no schema behind it.
        limits.remember_miss(token_hash)
        return None


def locate(
    token: str,
    *,
    content_length: str | None,
    peer: str | None,
    forwarded_for: str | None,
) -> LocatedWebhook:
    """Everything that can be decided without the body. Raises IntakeError."""
    if not has_token_shape(token):
        raise _not_found()
    if content_length is not None:
        if not content_length.isascii() or not content_length.isdigit():
            raise IntakeError(400, "Invalid Content-Length")
        if int(content_length) > PULSE_WEBHOOK_MAX_BODY_BYTES:
            raise IntakeError(413, "Request body too large")
    tenant_id = tenant_from_token(token)
    if not is_valid_schema_name(tenant_id):
        raise _not_found()

    token_hash = hash_token(token)
    try:
        limits.check_rate_limits(client_address(peer, forwarded_for), token_hash)
        if limits.is_known_miss(token_hash):
            raise _not_found()
        located = _lookup(tenant_id, token_hash)
    except RateLimited as e:
        raise IntakeError(429, "Too many requests", retry_after=e.retry_after) from e
    except LimiterUnavailable as e:
        raise IntakeError(
            503, "Temporarily unavailable", retry_after=_UNAVAILABLE_RETRY_SECONDS
        ) from e
    if located is None:
        raise _not_found()

    token_var = CURRENT_TENANT_ID_CONTEXTVAR.set(tenant_id)
    try:
        allowed = webhooks_allowed()
    except Exception as e:
        logger.exception("Pulse webhooks: could not read the admin switch")
        raise IntakeError(
            503, "Temporarily unavailable", retry_after=_UNAVAILABLE_RETRY_SECONDS
        ) from e
    finally:
        CURRENT_TENANT_ID_CONTEXTVAR.reset(token_var)
    if not allowed:
        raise _not_found()
    return located


def _verifier_config(webhook: PulseWebhook, now: Any) -> VerifierConfig:
    secrets = [webhook.signing_secret.get_value(apply_mask=False)]
    if (
        webhook.previous_signing_secret is not None
        and webhook.previous_valid_until is not None
        and webhook.previous_valid_until > now
    ):
        secrets.append(webhook.previous_signing_secret.get_value(apply_mask=False))
    return VerifierConfig(secrets=tuple(secrets), header_name=webhook.header_name)


def dedup_key_for(webhook: PulseWebhook, headers: Mapping[str, str], body: Any) -> str | None:
    """What identifies this event, or None when it can't be told apart from others."""
    value: str | None = None
    if webhook.dedup_source == DEDUP_WEBHOOK_ID:
        value = headers.get("webhook-id")
    elif webhook.dedup_source == DEDUP_HEADER and webhook.dedup_path:
        value = headers.get(webhook.dedup_path.lower())
    elif webhook.dedup_source == DEDUP_JSON_PATH and webhook.dedup_path:
        found = value_at_path(body, webhook.dedup_path)
        value = as_text(found) if found is not None else None
    if not value:
        return None
    if len(value) > _MAX_DEDUP_KEY_CHARS:
        return "sha256:" + hashlib.sha256(value.encode()).hexdigest()
    return value


def _reject(db_session: Session, webhook_id: int, status: int, reason: str) -> IntakeError:
    record_webhook_rejection(db_session, webhook_id, reason)
    logger.info(f"Pulse webhook {webhook_id}: rejected ({status}): {reason}")
    return IntakeError(status, reason)


def accept(
    located: LocatedWebhook,
    *,
    headers: Mapping[str, str],
    body: bytes,
    test_mode: bool,
) -> IntakeResult:
    """Verify, parse, then store. Raises IntakeError."""
    tenant_id, webhook_id = located.tenant_id, located.webhook_id
    run_id: int | None = None
    with get_session_with_tenant(tenant_id=tenant_id) as db_session:
        webhook = get_pulse_webhook(db_session, webhook_id)
        if webhook is None or not webhook.enabled or webhook.revoked_at is not None:
            raise _not_found()
        now = db_now(db_session)
        try:
            verify_request(
                webhook.auth_mode,
                SignedRequest(headers=headers, body=body, now_epoch=int(now.timestamp())),
                _verifier_config(webhook, now),
            )
        except VerificationError as e:
            raise _reject(db_session, webhook_id, 401, str(e)) from e
        try:
            parsed = parse_body(body)
        except PayloadError as e:
            raise _reject(db_session, webhook_id, 400, str(e)) from e

        kept_headers = strip_credential_headers(headers, webhook.header_name)
        payload = stored_payload(parsed, kept_headers)

        if test_mode:
            try:
                captured = listen.capture(
                    tenant_id, webhook_id, {"received_at": now.isoformat(), "payload": payload}
                )
            except LimiterUnavailable as e:
                raise IntakeError(
                    503, "Temporarily unavailable", retry_after=_UNAVAILABLE_RETRY_SECONDS
                ) from e
            if not captured:
                raise IntakeError(409, "Listen isn't open for this webhook")
            return IntakeResult(captured=True)

        try:
            event = accept_webhook_event(
                db_session,
                webhook_id=webhook_id,
                dedup_key=dedup_key_for(webhook, headers, parsed),
                payload=payload,
                max_pending=PULSE_WEBHOOK_MAX_PENDING_RUNS,
                tenant_max_active=PULSE_WEBHOOK_TENANT_MAX_ACTIVE_RUNS,
            )
        except WebhookClosed as e:
            raise _not_found() from e
        except WebhookOverloaded as e:
            record_webhook_rejection(db_session, webhook_id, str(e))
            raise IntakeError(
                429, "Too many requests", retry_after=_OVERLOAD_RETRY_SECONDS
            ) from e
        run_id = event.run_id
        if event.duplicate:
            return IntakeResult(run_id=run_id, duplicate=True)

    # Outbox: enqueue only after the run is durably committed.
    try:
        enqueue_pulse_run(run_id, tenant_id, webhook=True)
    except Exception:
        # The scheduler's sweeper re-sends it; the run stays `pending`.
        logger.exception(f"Pulse: enqueue failed for webhook run {run_id}")
    return IntakeResult(run_id=run_id)
