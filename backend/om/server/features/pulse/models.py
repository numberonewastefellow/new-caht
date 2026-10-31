"""Request/response models for the Pulse (scheduled workflows) API."""

import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel
from pydantic import Field

from om.db.models import PulseRun
from om.db.models import PulseSchedule
from om.pulse.inputs import item_for_index

ScheduleTypeLiteral = Literal["cron", "interval", "once"]
InputModeLiteral = Literal["fixed", "window", "ask", "list"]
# 366 days; also keeps values inside the int4 column
MAX_INTERVAL_SECONDS = 366 * 24 * 3600


class ScheduleTiming(BaseModel):
    schedule_type: ScheduleTypeLiteral
    cron_expression: str | None = None
    interval_seconds: int | None = Field(default=None, ge=1, le=MAX_INTERVAL_SECONDS)
    run_at: datetime.datetime | None = None
    timezone: str = "UTC"


class PulseScheduleCreate(ScheduleTiming):
    workflow_id: int
    name: str = Field(min_length=1, max_length=200)
    # What each run receives (see om/pulse/inputs.py); message rules depend on the mode
    input_mode: InputModeLiteral = "fixed"
    input_message: str = Field(default="", max_length=20000)
    input_prompt: str | None = Field(default=None, max_length=2000)
    input_items: list[str] | None = None
    enabled: bool = True
    retention_count: int | None = None


class PulseScheduleUpdate(BaseModel):
    """Partial update. Timing fields are validated together when any is present."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    input_mode: InputModeLiteral | None = None
    input_message: str | None = Field(default=None, max_length=20000)
    input_prompt: str | None = Field(default=None, max_length=2000)
    input_items: list[str] | None = None
    enabled: bool | None = None
    retention_count: int | None = Field(default=None, ge=1, le=100000)
    schedule_type: ScheduleTypeLiteral | None = None
    cron_expression: str | None = None
    interval_seconds: int | None = Field(default=None, ge=1, le=MAX_INTERVAL_SECONDS)
    run_at: datetime.datetime | None = None
    timezone: str | None = None


class PulsePreviewRequest(ScheduleTiming):
    pass


class PulsePreviewResponse(BaseModel):
    valid: bool
    error: str | None = None
    description: str | None = None
    next_runs: list[datetime.datetime] = []
    # Normalised cron expression (whitespace collapsed) when valid
    cron_expression: str | None = None


class PulseRunResponse(BaseModel):
    id: int
    trigger_id: int
    scheduled_for: datetime.datetime
    fired_by: str
    status: str
    chat_session_id: UUID | None
    created_at: datetime.datetime
    started_at: datetime.datetime | None
    finished_at: datetime.datetime | None
    duration_ms: int | None
    output_preview: str | None
    error: str | None
    skip_reason: str | None

    @classmethod
    def from_model(cls, run: PulseRun) -> "PulseRunResponse":
        return cls(
            id=run.id,
            trigger_id=run.trigger_id,
            scheduled_for=run.scheduled_for,
            fired_by=run.fired_by,
            status=run.status,
            chat_session_id=run.chat_session_id,
            created_at=run.created_at,
            started_at=run.started_at,
            finished_at=run.finished_at,
            duration_ms=run.duration_ms,
            output_preview=run.output_preview,
            error=run.error,
            skip_reason=run.skip_reason,
        )


class PulseScheduleResponse(BaseModel):
    id: int
    name: str
    workflow_id: int
    workflow_name: str | None
    # Creator / owner — runs execute as this user; never changes on edits
    user_id: UUID
    owner_email: str | None = None
    # Who made the latest change (owner, or an admin)
    updated_by_id: UUID | None = None
    updated_by_email: str | None = None
    enabled: bool
    schedule_type: str
    cron_expression: str | None
    interval_seconds: int | None
    run_at: datetime.datetime | None
    timezone: str
    input_mode: str
    input_message: str
    input_prompt: str | None = None
    input_items: list[str] | None = None
    # list mode: the item the next run will use
    next_item: str | None = None
    description: str
    next_run_at: datetime.datetime | None
    last_run_at: datetime.datetime | None
    last_run_status: str | None
    consecutive_failures: int
    disabled_reason: str | None
    retention_count: int
    created_at: datetime.datetime
    updated_at: datetime.datetime
    last_run: PulseRunResponse | None = None
    # Most recent run that produced a chat (for "open latest")
    latest_chat_session_id: UUID | None = None

    @classmethod
    def from_model(
        cls,
        schedule: PulseSchedule,
        *,
        description: str,
        last_run: PulseRun | None = None,
        latest_chat_session_id: UUID | None = None,
        include_owner: bool = False,
    ) -> "PulseScheduleResponse":
        return cls(
            id=schedule.id,
            name=schedule.name,
            workflow_id=schedule.workflow_id,
            workflow_name=schedule.workflow.name if schedule.workflow else None,
            user_id=schedule.user_id,
            owner_email=(
                schedule.user.email if include_owner and schedule.user else None
            ),
            updated_by_id=schedule.updated_by_id,
            updated_by_email=(
                schedule.updated_by.email if schedule.updated_by else None
            ),
            enabled=schedule.enabled,
            schedule_type=schedule.schedule_type,
            cron_expression=schedule.cron_expression,
            interval_seconds=schedule.interval_seconds,
            run_at=schedule.run_at,
            timezone=schedule.timezone,
            input_mode=schedule.input_mode,
            input_message=schedule.input_message,
            input_prompt=schedule.input_prompt,
            input_items=schedule.input_items,
            next_item=item_for_index(schedule.input_items, schedule.input_item_index),
            description=description,
            next_run_at=schedule.next_run_at,
            last_run_at=schedule.last_run_at,
            last_run_status=schedule.last_run_status,
            consecutive_failures=schedule.consecutive_failures,
            disabled_reason=schedule.disabled_reason,
            retention_count=schedule.retention_count,
            created_at=schedule.created_at,
            updated_at=schedule.updated_at,
            last_run=PulseRunResponse.from_model(last_run) if last_run else None,
            latest_chat_session_id=latest_chat_session_id,
        )


class PulseSidebarItem(BaseModel):
    """One row in the chat sidebar's "Scheduled" section."""

    trigger_id: int
    kind: str
    name: str
    enabled: bool
    disabled_reason: str | None
    last_run_status: str | None
    last_run_at: datetime.datetime | None
    latest_chat_session_id: UUID | None


class PulseStatsResponse(BaseModel):
    active_schedules: int
    paused_schedules: int
    needs_attention: int
    runs_last_24h: int
    failed_last_24h: int


class PulseWebhookHealth(BaseModel):
    # None means it couldn't be read, which isn't the same as off or zero
    enabled: bool | None
    secret_encryption_configured: bool
    workers_alive: int | None
    active_webhooks: int
    pending_runs: int
    running_runs: int
    # If this keeps growing, runs are waiting and no worker is taking them
    oldest_pending_seconds: float | None


class PulseHealthResponse(BaseModel):
    scheduler_replicas_alive: int
    scheduler_lag_seconds: float | None
    active_runs: int
    enabled_schedules: int
    runs_last_24h_by_status: dict[str, int]
    pulse_workers_alive: int | None
    webhooks: PulseWebhookHealth


class PulseConfigResponse(BaseModel):
    """Limits the UI needs to validate input before calling the API."""

    min_interval_seconds: int
    max_schedules_per_user: int
    max_retention: int
    default_retention: int
    template_variables: list[str]
    # Input modes ("What should each run receive?") and their defaults
    input_modes: list[str]
    default_window_message: str
    default_list_message: str
