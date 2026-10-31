"""Pulse webhooks: the public endpoint outside systems call, and the API to manage them.

Management follows the schedule rules: anyone who can run a workflow can create one, and
admins can see, edit, pause, revoke and delete any. Two things stay with the owner:
rotating, because whoever holds the new secret can start runs as the owner, and Listen and
stored payloads, because event data is private to the owner.
"""

import json
import re
import time

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from prometheus_client import Counter
from sqlalchemy.orm import Session

from om.auth.schemas import UserRole
from om.auth.users import current_user
from om.configs.app_configs import ENCRYPTION_KEY_SECRET
from om.configs.app_configs import WEB_DOMAIN
from om.configs.pulse_configs import PULSE_DEFAULT_RETENTION
from om.configs.pulse_configs import PULSE_MAX_RETENTION
from om.configs.pulse_configs import PULSE_MAX_WEBHOOKS_PER_USER
from om.configs.pulse_configs import PULSE_WEBHOOK_LISTEN_TTL_SECONDS
from om.configs.pulse_configs import PULSE_WEBHOOK_MAX_BODY_BYTES
from om.configs.pulse_configs import PULSE_WEBHOOK_MAX_ROTATION_GRACE_HOURS
from om.db.engine.sql_engine import get_session
from om.db.models import PulseRun
from om.db.models import PulseWebhook
from om.db.models import User
from om.db.pulse import db_now
from om.db.pulse import delete_pulse_trigger
from om.db.pulse import get_latest_runs_by_trigger
from om.db.pulse import get_latest_session_run_by_trigger
from om.db.pulse import get_pulse_run
from om.db.pulse import list_runs_for_trigger
from om.db.pulse import lock_trigger_row
from om.db.pulse import lock_user_schedules
from om.db.pulse_webhook import count_webhooks_for_user
from om.db.pulse_webhook import create_pulse_webhook
from om.db.pulse_webhook import get_pulse_webhook
from om.db.pulse_webhook import list_pulse_webhooks
from om.db.pulse_webhook import revoke_webhook_credentials
from om.db.pulse_webhook import rotate_webhook_credentials
from om.pulse.access import get_accessible_workflow
from om.pulse.access import PulseAccessError
from om.pulse.notifications import notify_owner_of_admin_change
from om.pulse.timing import get_zone
from om.pulse.timing import ScheduleValidationError
from om.pulse.triggers.webhook import render_webhook_message
from om.pulse.webhooks import listen
from om.pulse.webhooks.intake import accept
from om.pulse.webhooks.intake import DEDUP_HEADER
from om.pulse.webhooks.intake import DEDUP_JSON_PATH
from om.pulse.webhooks.intake import DEDUP_NONE
from om.pulse.webhooks.intake import DEDUP_WEBHOOK_ID
from om.pulse.webhooks.intake import IntakeError
from om.pulse.webhooks.intake import locate
from om.pulse.webhooks.intake import LocatedWebhook
from om.pulse.webhooks.payload import DEFAULT_WEBHOOK_MESSAGE
from om.pulse.webhooks.payload import is_valid_json_path
from om.pulse.webhooks.payload import stored_payload
from om.pulse.webhooks.tokens import generate_signing_secret
from om.pulse.webhooks.tokens import generate_token
from om.pulse.webhooks.tokens import hash_token
from om.pulse.webhooks.tokens import token_last4
from om.pulse.webhooks.verify import AUTH_HEADER_TOKEN
from om.pulse.webhooks.verify import AUTH_STANDARD_WEBHOOKS
from om.pulse.webhooks.verify import DEFAULT_SECRET_HEADER
from om.pulse.webhooks.verify import sign_standard_webhook
from om.server.features.pulse.models import PulseRunResponse
from om.server.features.pulse.webhook_models import WebhookConfigResponse
from om.server.features.pulse.webhook_models import WebhookCreate
from om.server.features.pulse.webhook_models import WebhookCredentials
from om.server.features.pulse.webhook_models import WebhookListenStatus
from om.server.features.pulse.webhook_models import WebhookPreviewRequest
from om.server.features.pulse.webhook_models import WebhookPreviewResponse
from om.server.features.pulse.webhook_models import WebhookResponse
from om.server.features.pulse.webhook_models import WebhookRotateRequest
from om.server.features.pulse.webhook_models import WebhookRunPayload
from om.server.features.pulse.webhook_models import WebhookTestEventRequest
from om.server.features.pulse.webhook_models import WebhookUpdate
from om.server.settings.store import load_settings
from om.utils.logger import setup_logger
from shared_configs.contextvars import get_current_tenant_id

logger = setup_logger()

public_router = APIRouter(prefix="/hooks")
router = APIRouter(prefix="/pulse/webhooks")

_EVENTS = Counter(
    "pulse_webhook_events_total", "Calls to public webhook URLs, by result", ["result"]
)
_HEADER_NAME = re.compile(r"^[A-Za-z0-9\-]{1,64}$")
# Headers a secret must not travel in: the platform or a proxy gives these meaning.
_RESERVED_HEADERS = frozenset(
    {"authorization", "cookie", "host", "content-length", "content-type", "connection"}
)
_TEMPLATE_VARIABLES = ["payload", "payload.<path>", "date", "now"]


# ========================
# Public endpoint
# ========================


async def _read_capped_body(request: Request) -> bytes:
    """Read as it arrives, because Content-Length can be absent or wrong (chunked uploads)."""
    chunks: list[bytes] = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > PULSE_WEBHOOK_MAX_BODY_BYTES:
            raise IntakeError(413, "Request body too large")
        chunks.append(chunk)
    return b"".join(chunks)


async def _receive(token: str, request: Request, test_mode: bool) -> JSONResponse:
    # Async only to read the stream: all Redis and database work is in a thread.
    headers = dict(request.headers)
    try:
        located = await run_in_threadpool(
            locate,
            token,
            content_length=headers.get("content-length"),
            peer=request.client.host if request.client else None,
            forwarded_for=headers.get("x-forwarded-for"),
        )
        body = await _read_capped_body(request)
        result = await run_in_threadpool(
            accept, located, headers=headers, body=body, test_mode=test_mode
        )
    except IntakeError as e:
        _EVENTS.labels(result=str(e.status)).inc()
        response_headers = {"Retry-After": str(e.retry_after)} if e.retry_after else None
        return JSONResponse(
            status_code=e.status, content={"detail": e.detail}, headers=response_headers
        )
    if result.captured:
        _EVENTS.labels(result="captured").inc()
        return JSONResponse(status_code=202, content={"captured": True})
    _EVENTS.labels(result="duplicate" if result.duplicate else "accepted").inc()
    return JSONResponse(
        status_code=202, content={"run_id": result.run_id, "duplicate": result.duplicate}
    )


@public_router.post("/test/{token}")
async def receive_webhook_test_event(token: str, request: Request) -> JSONResponse:
    """Works only while the owner has Listen open. Captures the call and runs nothing."""
    return await _receive(token, request, test_mode=True)


@public_router.post("/{token}")
async def receive_webhook_event(token: str, request: Request) -> JSONResponse:
    """Start one run. Authenticated by the webhook's token and signature, not a session."""
    return await _receive(token, request, test_mode=False)


# ========================
# Helpers
# ========================


def _is_admin(user: User) -> bool:
    return user.role == UserRole.ADMIN


def _get_webhook_or_404(db_session: Session, webhook_id: int, user: User) -> PulseWebhook:
    webhook = get_pulse_webhook(db_session, webhook_id)
    if webhook is None or (webhook.user_id != user.id and not _is_admin(user)):
        raise HTTPException(status_code=404, detail="Webhook not found")
    return webhook


def _require_owner(webhook: PulseWebhook, user: User, action: str) -> None:
    if webhook.user_id != user.id:
        raise HTTPException(
            status_code=403, detail=f"Only the webhook's owner can {action}."
        )


def _check_enabled_setting() -> None:
    if not load_settings().webhooks_enabled:
        raise HTTPException(status_code=403, detail="An admin has turned webhooks off")


def _check_workflow(db_session: Session, workflow_id: int, owner: User) -> None:
    """The workflow must be usable by the OWNER, because runs execute as them."""
    try:
        get_accessible_workflow(db_session, workflow_id, owner.id)
    except PulseAccessError as e:
        raise HTTPException(status_code=404 if e.workflow_deleted else 403, detail=str(e))


def _check_retention(value: int | None) -> int:
    if value is None:
        return PULSE_DEFAULT_RETENTION
    if value < 1 or value > PULSE_MAX_RETENTION:
        raise HTTPException(
            status_code=400,
            detail=f"retention_count must be between 1 and {PULSE_MAX_RETENTION}",
        )
    return value


def _check_timezone(timezone: str) -> str:
    try:
        get_zone(timezone)
    except ScheduleValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return timezone


def _check_header_name(name: str | None) -> str:
    chosen = (name or DEFAULT_SECRET_HEADER).strip().lower()
    if not _HEADER_NAME.match(chosen) or chosen in _RESERVED_HEADERS:
        raise HTTPException(status_code=400, detail=f"{chosen!r} can't carry the secret")
    return chosen


def _check_dedup(
    auth_mode: str, source: str | None, path: str | None
) -> tuple[str, str | None]:
    chosen = source or (
        DEDUP_WEBHOOK_ID if auth_mode == AUTH_STANDARD_WEBHOOKS else DEDUP_NONE
    )
    if chosen == DEDUP_WEBHOOK_ID and auth_mode != AUTH_STANDARD_WEBHOOKS:
        raise HTTPException(
            status_code=400, detail="webhook-id needs Standard Webhooks signatures"
        )
    if chosen == DEDUP_HEADER:
        # The signature doesn't cover other headers, so anyone replaying a captured call
        # could change this one and run it again. The body and webhook-id are signed.
        if auth_mode == AUTH_STANDARD_WEBHOOKS:
            raise HTTPException(
                status_code=400,
                detail="A signed webhook can't use a header to find repeats, because the "
                "signature doesn't cover it. Use webhook-id or a field in the body.",
            )
        if not path or not _HEADER_NAME.match(path):
            raise HTTPException(status_code=400, detail="Enter the header that identifies an event")
        return chosen, path.lower()
    if chosen == DEDUP_JSON_PATH:
        if not path or not is_valid_json_path(path):
            raise HTTPException(
                status_code=400, detail="Enter a JSON path like event.id or items[0].id"
            )
        return chosen, path
    return chosen, None


def _urls(token: str) -> tuple[str, str]:
    base = WEB_DOMAIN.rstrip("/")
    return f"{base}/api/hooks/{token}", f"{base}/api/hooks/test/{token}"


def _to_responses(
    db_session: Session, webhooks: list[PulseWebhook], viewer: User, include_owner: bool
) -> list[WebhookResponse]:
    ids = [w.id for w in webhooks]
    latest = get_latest_runs_by_trigger(db_session, ids)
    sessions = get_latest_session_run_by_trigger(db_session, ids)
    responses = []
    for webhook in webhooks:
        session_run = sessions.get(webhook.id)
        response = WebhookResponse.from_model(
            webhook,
            last_run=latest.get(webhook.id),
            latest_chat_session_id=session_run.chat_session_id if session_run else None,
            include_owner=include_owner,
        )
        if webhook.user_id != viewer.id and response.last_run is not None:
            # Outputs of another user's runs are private to that user.
            response = response.model_copy(
                update={
                    "last_run": response.last_run.model_copy(
                        update={"output_preview": None, "error": None, "chat_session_id": None}
                    ),
                    "latest_chat_session_id": None,
                }
            )
        responses.append(response)
    return responses


def _to_response(db_session: Session, webhook: PulseWebhook, user: User) -> WebhookResponse:
    return _to_responses(db_session, [webhook], user, include_owner=_is_admin(user))[0]


def _run_response(run: PulseRun, webhook: PulseWebhook, viewer: User) -> PulseRunResponse:
    response = PulseRunResponse.from_model(run)
    if webhook.user_id != viewer.id:
        return response.model_copy(
            update={"output_preview": None, "error": None, "chat_session_id": None}
        )
    return response


def _notify_admin_change(
    db_session: Session, webhook: PulseWebhook, user: User, action: str
) -> None:
    if webhook.user_id != user.id:
        notify_owner_of_admin_change(
            db_session,
            owner_id=webhook.user_id,
            trigger_id=webhook.id,
            trigger_name=webhook.name,
            admin_email=user.email,
            action=action,
            noun="webhook",
        )


# ========================
# Management
# ========================


@router.get("/config")
def get_webhook_config(_: User = Depends(current_user)) -> WebhookConfigResponse:
    return WebhookConfigResponse(
        enabled=load_settings().webhooks_enabled,
        secret_encryption_configured=bool(ENCRYPTION_KEY_SECRET),
        default_input_message=DEFAULT_WEBHOOK_MESSAGE,
        max_body_bytes=PULSE_WEBHOOK_MAX_BODY_BYTES,
        listen_seconds=PULSE_WEBHOOK_LISTEN_TTL_SECONDS,
        max_grace_hours=PULSE_WEBHOOK_MAX_ROTATION_GRACE_HOURS,
        template_variables=_TEMPLATE_VARIABLES,
    )


@router.get("")
def list_webhooks(
    all_users: bool = False,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> list[WebhookResponse]:
    include_all = all_users and _is_admin(user)
    webhooks = list_pulse_webhooks(db_session, user.id, include_all_users=include_all)
    return _to_responses(db_session, webhooks, user, include_owner=include_all)


@router.post("")
def create_webhook(
    request: WebhookCreate,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> WebhookCredentials:
    _check_enabled_setting()
    _check_workflow(db_session, request.workflow_id, user)
    header_name = (
        _check_header_name(request.header_name)
        if request.auth_mode == AUTH_HEADER_TOKEN
        else None
    )
    dedup_source, dedup_path = _check_dedup(
        request.auth_mode, request.dedup_source, request.dedup_path
    )
    lock_user_schedules(db_session, user.id)
    if count_webhooks_for_user(db_session, user.id) >= PULSE_MAX_WEBHOOKS_PER_USER:
        raise HTTPException(
            status_code=400,
            detail=f"You can have at most {PULSE_MAX_WEBHOOKS_PER_USER} webhooks. Delete one first.",
        )
    token = generate_token(get_current_tenant_id())
    secret = generate_signing_secret()
    webhook = create_pulse_webhook(
        db_session,
        user_id=user.id,
        workflow_id=request.workflow_id,
        name=request.name.strip(),
        timezone=_check_timezone(request.timezone),
        input_message=request.input_message.strip() or DEFAULT_WEBHOOK_MESSAGE,
        retention_count=_check_retention(request.retention_count),
        enabled=request.enabled,
        token_hash=hash_token(token),
        token_last4=token_last4(token),
        auth_mode=request.auth_mode,
        signing_secret=secret,
        header_name=header_name,
        dedup_source=dedup_source,
        dedup_path=dedup_path,
    )
    url, test_url = _urls(token)
    return WebhookCredentials(
        webhook=_to_response(db_session, webhook, user),
        url=url,
        test_url=test_url,
        signing_secret=secret,
    )


@router.get("/{webhook_id}")
def get_webhook(
    webhook_id: int,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> WebhookResponse:
    return _to_response(db_session, _get_webhook_or_404(db_session, webhook_id, user), user)


@router.patch("/{webhook_id}")
def update_webhook(
    webhook_id: int,
    request: WebhookUpdate,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> WebhookResponse:
    webhook = _get_webhook_or_404(db_session, webhook_id, user)
    changes = request.model_dump(exclude_unset=True)
    lock_trigger_row(db_session, webhook.id)
    db_session.refresh(webhook)

    if changes.get("name") is not None:
        webhook.name = changes["name"].strip()
    if changes.get("input_message") is not None:
        webhook.input_message = changes["input_message"].strip() or DEFAULT_WEBHOOK_MESSAGE
    if changes.get("timezone") is not None:
        webhook.timezone = _check_timezone(changes["timezone"])
    if "retention_count" in changes:
        webhook.retention_count = _check_retention(changes["retention_count"])
    if "dedup_source" in changes or "dedup_path" in changes:
        webhook.dedup_source, webhook.dedup_path = _check_dedup(
            webhook.auth_mode,
            changes.get("dedup_source", webhook.dedup_source),
            changes.get("dedup_path", webhook.dedup_path),
        )

    if changes.get("enabled") is True and not webhook.enabled:
        if webhook.revoked_at is not None:
            raise HTTPException(
                status_code=400, detail="This webhook is revoked. Rotate it to get new credentials."
            )
        _check_enabled_setting()
        _check_workflow(db_session, webhook.workflow_id, webhook.user)
        webhook.enabled = True
        webhook.disabled_reason = None
        webhook.consecutive_failures = 0
    elif changes.get("enabled") is False:
        webhook.enabled = False
        webhook.disabled_reason = None  # paused by a person

    webhook.updated_by_id = user.id
    webhook.updated_at = db_now(db_session)
    db_session.commit()
    db_session.refresh(webhook)
    if changes:
        _notify_admin_change(
            db_session,
            webhook,
            user,
            "paused" if set(changes) == {"enabled"} and changes["enabled"] is False else "updated",
        )
    return _to_response(db_session, webhook, user)


@router.delete("/{webhook_id}")
def delete_webhook(
    webhook_id: int,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> None:
    """Deletes the webhook and its run history. Run chats stay in chat history."""
    webhook = _get_webhook_or_404(db_session, webhook_id, user)
    owner_id, name, wid = webhook.user_id, webhook.name, webhook.id
    delete_pulse_trigger(db_session, webhook)
    if owner_id != user.id:
        notify_owner_of_admin_change(
            db_session,
            owner_id=owner_id,
            trigger_id=wid,
            trigger_name=name,
            admin_email=user.email,
            action="deleted",
            noun="webhook",
        )


@router.post("/{webhook_id}/rotate")
def rotate_webhook(
    webhook_id: int,
    request: WebhookRotateRequest,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> WebhookCredentials:
    webhook = _get_webhook_or_404(db_session, webhook_id, user)
    _require_owner(webhook, user, "rotate its credentials")
    if request.grace_hours > PULSE_WEBHOOK_MAX_ROTATION_GRACE_HOURS:
        raise HTTPException(
            status_code=400,
            detail=f"The grace period can be at most {PULSE_WEBHOOK_MAX_ROTATION_GRACE_HOURS} hours",
        )
    lock_trigger_row(db_session, webhook.id)
    db_session.refresh(webhook)
    token = generate_token(get_current_tenant_id())
    secret = generate_signing_secret()
    rotate_webhook_credentials(
        db_session,
        webhook,
        token_hash=hash_token(token),
        token_last4=token_last4(token),
        signing_secret=secret,
        grace_hours=request.grace_hours,
    )
    url, test_url = _urls(token)
    return WebhookCredentials(
        webhook=_to_response(db_session, webhook, user),
        url=url,
        test_url=test_url,
        signing_secret=secret,
    )


@router.post("/{webhook_id}/revoke")
def revoke_webhook(
    webhook_id: int,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> WebhookResponse:
    """Emergency stop: the URL and secret, current and previous, stop working at once."""
    webhook = _get_webhook_or_404(db_session, webhook_id, user)
    lock_trigger_row(db_session, webhook.id)
    db_session.refresh(webhook)
    revoke_webhook_credentials(db_session, webhook)
    _notify_admin_change(db_session, webhook, user, "revoked")
    return _to_response(db_session, webhook, user)


# ========================
# Listen mode and preview
# ========================


def _listen_status(webhook: PulseWebhook) -> WebhookListenStatus:
    tenant_id = get_current_tenant_id()
    left = listen.seconds_left(tenant_id, webhook.id)
    return WebhookListenStatus(
        listening=left > 0,
        seconds_left=left,
        captures=listen.captures(tenant_id, webhook.id) if left > 0 else [],
    )


@router.post("/{webhook_id}/listen")
def start_listen(
    webhook_id: int,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> WebhookListenStatus:
    webhook = _get_webhook_or_404(db_session, webhook_id, user)
    _require_owner(webhook, user, "listen for its events")
    listen.start_listening(get_current_tenant_id(), webhook.id)
    return _listen_status(webhook)


@router.get("/{webhook_id}/listen")
def get_listen(
    webhook_id: int,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> WebhookListenStatus:
    webhook = _get_webhook_or_404(db_session, webhook_id, user)
    _require_owner(webhook, user, "listen for its events")
    return _listen_status(webhook)


@router.delete("/{webhook_id}/listen")
def stop_listen(
    webhook_id: int,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> None:
    webhook = _get_webhook_or_404(db_session, webhook_id, user)
    _require_owner(webhook, user, "listen for its events")
    listen.stop_listening(get_current_tenant_id(), webhook.id)


@router.post("/{webhook_id}/test-event")
def send_test_event(
    webhook_id: int,
    request: WebhookTestEventRequest,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> WebhookListenStatus:
    """Sign a sample with the webhook's own secret and put it through the same checks a
    real call gets, without needing an outside system. Runs nothing."""
    webhook = _get_webhook_or_404(db_session, webhook_id, user)
    _require_owner(webhook, user, "send it test events")
    if webhook.revoked_at is not None or not webhook.enabled:
        raise HTTPException(status_code=409, detail="This webhook isn't active")
    body = json.dumps(request.body).encode()
    if len(body) > PULSE_WEBHOOK_MAX_BODY_BYTES:
        raise HTTPException(status_code=413, detail="The sample is too large")
    secret = webhook.signing_secret.get_value(apply_mask=False)
    if webhook.auth_mode == AUTH_STANDARD_WEBHOOKS:
        now = int(time.time())
        message_id = f"test_{now}"
        headers = {
            "content-type": "application/json",
            "webhook-id": message_id,
            "webhook-timestamp": str(now),
            "webhook-signature": sign_standard_webhook(secret, message_id, now, body),
        }
    else:
        headers = {
            "content-type": "application/json",
            webhook.header_name or DEFAULT_SECRET_HEADER: secret,
        }
    located = LocatedWebhook(tenant_id=get_current_tenant_id(), webhook_id=webhook.id)
    try:
        accept(located, headers=headers, body=body, test_mode=True)
    except IntakeError as e:
        raise HTTPException(status_code=e.status, detail=e.detail)
    return _listen_status(webhook)


@router.post("/{webhook_id}/preview")
def preview_message(
    webhook_id: int,
    request: WebhookPreviewRequest,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> WebhookPreviewResponse:
    """The message a run would send the workflow for this sample."""
    webhook = _get_webhook_or_404(db_session, webhook_id, user)
    now = db_now(db_session)
    return WebhookPreviewResponse(
        message=render_webhook_message(
            request.input_message or webhook.input_message,
            payload=stored_payload(request.body, {}),
            timezone=webhook.timezone,
            fired_at=now,
            now=now,
        )
    )


# ========================
# Runs
# ========================


@router.get("/{webhook_id}/runs")
def list_webhook_runs(
    webhook_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    before_id: int | None = None,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> list[PulseRunResponse]:
    webhook = _get_webhook_or_404(db_session, webhook_id, user)
    runs = list_runs_for_trigger(db_session, webhook.id, limit=limit, before_id=before_id)
    return [_run_response(r, webhook, user) for r in runs]


@router.get("/{webhook_id}/runs/{run_id}/payload")
def get_run_payload(
    webhook_id: int,
    run_id: int,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> WebhookRunPayload:
    webhook = _get_webhook_or_404(db_session, webhook_id, user)
    _require_owner(webhook, user, "read its event data")
    run = get_pulse_run(db_session, run_id)
    if run is None or run.trigger_id != webhook.id:
        raise HTTPException(status_code=404, detail="Run not found")
    return WebhookRunPayload(payload=run.trigger_payload, cleared=run.trigger_payload is None)
