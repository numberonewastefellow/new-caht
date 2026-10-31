"""Request/response models for Pulse webhooks. Secrets appear only in WebhookCredentials,
which is returned once: when a webhook is created or rotated."""

import datetime
from typing import Any
from typing import Literal
from uuid import UUID

from pydantic import BaseModel
from pydantic import Field

from om.db.models import PulseRun
from om.db.models import PulseWebhook
from om.server.features.pulse.models import PulseRunResponse

AuthModeLiteral = Literal["standard_webhooks", "header_token"]
DedupSourceLiteral = Literal["webhook_id", "header", "json_path", "none"]


class WebhookCreate(BaseModel):
    workflow_id: int
    name: str = Field(min_length=1, max_length=200)
    # Empty means DEFAULT_WEBHOOK_MESSAGE
    input_message: str = Field(default="", max_length=20000)
    timezone: str = "UTC"
    auth_mode: AuthModeLiteral = "standard_webhooks"
    header_name: str | None = Field(default=None, max_length=64)
    # Default depends on auth_mode: webhook_id when signed, otherwise none
    dedup_source: DedupSourceLiteral | None = None
    dedup_path: str | None = Field(default=None, max_length=200)
    enabled: bool = True
    retention_count: int | None = None


class WebhookUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    input_message: str | None = Field(default=None, max_length=20000)
    timezone: str | None = None
    dedup_source: DedupSourceLiteral | None = None
    dedup_path: str | None = Field(default=None, max_length=200)
    enabled: bool | None = None
    retention_count: int | None = None


class WebhookRotateRequest(BaseModel):
    # How long the old URL and secret keep working
    grace_hours: int = Field(default=24, ge=0)


class WebhookTestEventRequest(BaseModel):
    body: Any = Field(default_factory=lambda: {"message": "Hello from a test event"})


class WebhookPreviewRequest(BaseModel):
    input_message: str | None = Field(default=None, max_length=20000)
    body: Any = None


class WebhookPreviewResponse(BaseModel):
    message: str


class WebhookConfigResponse(BaseModel):
    enabled: bool
    # False means the signing secret is stored as plaintext on this server
    secret_encryption_configured: bool
    default_input_message: str
    max_body_bytes: int
    listen_seconds: int
    max_grace_hours: int
    default_grace_hours: int = 24
    template_variables: list[str]


class WebhookResponse(BaseModel):
    id: int
    kind: str = "webhook"
    name: str
    workflow_id: int
    workflow_name: str | None
    user_id: UUID
    owner_email: str | None = None
    updated_by_email: str | None = None
    enabled: bool
    disabled_reason: str | None
    revoked: bool
    auth_mode: str
    header_name: str | None
    dedup_source: str
    dedup_path: str | None
    input_message: str
    timezone: str
    retention_count: int
    # Only the end of the token is ever shown again
    token_last4: str
    rotated_at: datetime.datetime | None
    previous_valid_until: datetime.datetime | None
    last_received_at: datetime.datetime | None
    last_rejected_at: datetime.datetime | None
    last_rejected_reason: str | None
    last_run_at: datetime.datetime | None
    last_run_status: str | None
    consecutive_failures: int
    created_at: datetime.datetime
    updated_at: datetime.datetime
    last_run: PulseRunResponse | None = None
    latest_chat_session_id: UUID | None = None

    @classmethod
    def from_model(
        cls,
        webhook: PulseWebhook,
        *,
        last_run: PulseRun | None = None,
        latest_chat_session_id: UUID | None = None,
        include_owner: bool = False,
    ) -> "WebhookResponse":
        return cls(
            id=webhook.id,
            name=webhook.name,
            workflow_id=webhook.workflow_id,
            workflow_name=webhook.workflow.name if webhook.workflow else None,
            user_id=webhook.user_id,
            owner_email=webhook.user.email if include_owner and webhook.user else None,
            updated_by_email=webhook.updated_by.email if webhook.updated_by else None,
            enabled=webhook.enabled,
            disabled_reason=webhook.disabled_reason,
            revoked=webhook.revoked_at is not None,
            auth_mode=webhook.auth_mode,
            header_name=webhook.header_name,
            dedup_source=webhook.dedup_source,
            dedup_path=webhook.dedup_path,
            input_message=webhook.input_message,
            timezone=webhook.timezone,
            retention_count=webhook.retention_count,
            token_last4=webhook.token_last4,
            rotated_at=webhook.rotated_at,
            previous_valid_until=webhook.previous_valid_until,
            last_received_at=webhook.last_received_at,
            last_rejected_at=webhook.last_rejected_at,
            last_rejected_reason=webhook.last_rejected_reason,
            last_run_at=webhook.last_run_at,
            last_run_status=webhook.last_run_status,
            consecutive_failures=webhook.consecutive_failures,
            created_at=webhook.created_at,
            updated_at=webhook.updated_at,
            last_run=PulseRunResponse.from_model(last_run) if last_run else None,
            latest_chat_session_id=latest_chat_session_id,
        )


class WebhookCredentials(BaseModel):
    """Shown once. None of this can be read back later."""

    webhook: WebhookResponse
    url: str
    test_url: str
    signing_secret: str


class WebhookListenStatus(BaseModel):
    listening: bool
    seconds_left: int
    captures: list[dict[str, Any]]


class WebhookRunPayload(BaseModel):
    payload: dict[str, Any] | None
    # True when retention already cleared it
    cleared: bool


class PulseTriggerSummary(BaseModel):
    """What the chat banner needs for a run's trigger, whatever its kind."""

    id: int
    kind: str
    name: str
    workflow_name: str | None
    disabled_reason: str | None
    input_mode: str | None = None
    input_prompt: str | None = None
