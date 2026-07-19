"""Structured, OpenSearch-friendly event logging for standard answers (Standard 9).

The repo's ``OmLoggingAdapter`` only emits text lines, so this module adds a thin
structured layer: every create/update/delete and every match emits a single
JSON object carrying the mandated fields — ``event``, ``entity``, ``entity_id``,
``tenant_id``, ``actor_user_id``, ``action``, ``status``, ``duration_ms``,
``error`` — which OpenSearch can index directly off the log stream.

Emission is *always* wrapped in try/except so instrumentation can never break the
operation it observes. ``tenant_id`` is resolved from the request contextvar
(Contract 3) automatically.
"""

from __future__ import annotations

import json
import time
from contextlib import contextmanager
from enum import Enum
from typing import Any
from typing import Iterator

from om.tenancy.context import get_current_tenant_id
from om.utils.logger import setup_logger

logger = setup_logger()

# Marker prefix so OpenSearch/Filebeat pipelines can select these lines and parse
# the trailing JSON without ambiguity against ordinary text logs.
EVENT_LOG_PREFIX = "standard_answer_event "


class SAEvent(str, Enum):
    """The ``event`` field values emitted by this feature."""

    CREATED = "standard_answer.created"
    UPDATED = "standard_answer.updated"
    DELETED = "standard_answer.deleted"
    MATCHED = "standard_answer.matched"
    CATEGORY_CREATED = "standard_answer.category.created"
    CATEGORY_UPDATED = "standard_answer.category.updated"
    CATEGORY_DELETED = "standard_answer.category.deleted"
    CONFIG_UPDATED = "standard_answer.config.updated"


class SAEntity(str, Enum):
    """The ``entity`` field values."""

    STANDARD_ANSWER = "standard_answer"
    CATEGORY = "category"
    CONFIG = "config"


class SAAction(str, Enum):
    """The ``action`` field values."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    MATCH = "match"


class SAStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"


def _resolve_tenant_id() -> str | None:
    try:
        return get_current_tenant_id()
    except Exception:  # noqa: BLE001 - tenant may be unset in some contexts
        return None


def emit_event(
    *,
    event: SAEvent,
    entity: SAEntity,
    action: SAAction,
    status: SAStatus,
    entity_id: int | str | None = None,
    actor_user_id: str | None = None,
    duration_ms: float | None = None,
    error: str | None = None,
    **extra: Any,
) -> None:
    """Emit one structured event line. Never raises."""

    try:
        payload: dict[str, Any] = {
            "event": event.value,
            "entity": entity.value,
            "entity_id": entity_id,
            "tenant_id": _resolve_tenant_id(),
            "actor_user_id": actor_user_id,
            "action": action.value,
            "status": status.value,
            "duration_ms": round(duration_ms, 2) if duration_ms is not None else None,
            "error": error,
        }
        if extra:
            payload.update(extra)
        line = EVENT_LOG_PREFIX + json.dumps(payload, default=str, sort_keys=True)
        if status is SAStatus.ERROR:
            logger.error(line)
        else:
            logger.info(line)
    except Exception:  # noqa: BLE001 - logging must never break the caller
        # Last-ditch: a plain, best-effort line so the failure is not fully silent.
        try:
            logger.error(
                f"Failed to emit standard_answer event={getattr(event, 'value', event)} "
                f"entity_id={entity_id}"
            )
        except Exception:  # noqa: BLE001
            pass


@contextmanager
def logged_operation(
    *,
    event: SAEvent,
    entity: SAEntity,
    action: SAAction,
    entity_id: int | str | None = None,
    actor_user_id: str | None = None,
    **extra: Any,
) -> Iterator[dict[str, Any]]:
    """Time a mutating operation, emit a success/error event, and re-raise on error.

    Yields a mutable context dict; set ``ctx["entity_id"]`` inside the block once the
    id is known (e.g. after INSERT flush) so the emitted event carries it.
    """

    start = time.monotonic()
    ctx: dict[str, Any] = {"entity_id": entity_id}
    try:
        yield ctx
    except Exception as exc:
        emit_event(
            event=event,
            entity=entity,
            action=action,
            status=SAStatus.ERROR,
            entity_id=ctx.get("entity_id"),
            actor_user_id=actor_user_id,
            duration_ms=(time.monotonic() - start) * 1000.0,
            error=f"{type(exc).__name__}: {exc}",
            **extra,
        )
        raise
    else:
        emit_event(
            event=event,
            entity=entity,
            action=action,
            status=SAStatus.SUCCESS,
            entity_id=ctx.get("entity_id"),
            actor_user_id=actor_user_id,
            duration_ms=(time.monotonic() - start) * 1000.0,
            **extra,
        )
