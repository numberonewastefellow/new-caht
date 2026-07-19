"""Structured, OpenSearch-friendly event logging for tenancy operations (Standard 9).

Every create / update / delete / assignment emits a single JSON-serializable log line with
a stable field set so dashboards can filter on ``event`` / ``tenant_id`` / ``status``. The
emit call itself is defensive: logging must never break the operation it describes.
"""

from __future__ import annotations

import json
import time
from contextlib import contextmanager
from collections.abc import Iterator
from typing import Any

from om.utils.logger import setup_logger

logger = setup_logger()

# Canonical event names for the tenancy domain.
EVENT_TENANT_CREATED = "tenant.created"
EVENT_TENANT_UPDATED = "tenant.updated"
EVENT_TENANT_DELETED = "tenant.deleted"
EVENT_TENANT_DEACTIVATED = "tenant.deactivated"
EVENT_USER_ASSIGNED = "tenant.user_assigned"
EVENT_USER_REMOVED = "tenant.user_removed"
EVENT_USER_MOVED = "tenant.user_moved"

STATUS_SUCCESS = "success"
STATUS_FAILURE = "failure"


def emit_tenant_event(
    *,
    event: str,
    entity_id: str,
    action: str,
    status: str,
    tenant_id: str | None,
    actor_user_id: str | None,
    duration_ms: float | None = None,
    error: str | None = None,
    **extra: Any,
) -> None:
    """Emit one structured tenancy log line. Never raises."""
    try:
        payload: dict[str, Any] = {
            "event": event,
            "entity": "tenant",
            "entity_id": entity_id,
            "tenant_id": tenant_id,
            "actor_user_id": actor_user_id,
            "action": action,
            "status": status,
            "duration_ms": round(duration_ms, 2) if duration_ms is not None else None,
            "error": error,
        }
        if extra:
            payload.update(extra)
        line = json.dumps(payload, default=str, sort_keys=True)
        if status == STATUS_FAILURE:
            logger.error(f"tenancy_event {line}")
        else:
            logger.info(f"tenancy_event {line}")
    except Exception:
        # Structured logging must never mask the underlying operation.
        logger.exception("Failed to emit tenancy event")


@contextmanager
def tenant_operation(
    *,
    event: str,
    entity_id: str,
    action: str,
    tenant_id: str | None,
    actor_user_id: str | None,
    **extra: Any,
) -> Iterator[None]:
    """Time an operation and emit a success/failure event automatically.

    Usage::

        with tenant_operation(event=EVENT_TENANT_CREATED, entity_id=tid,
                              action="create", tenant_id=tid, actor_user_id=uid):
            ...  # do the work; exceptions are logged as failure then re-raised
    """
    started = time.monotonic()
    try:
        yield
    except Exception as exc:
        emit_tenant_event(
            event=event,
            entity_id=entity_id,
            action=action,
            status=STATUS_FAILURE,
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            duration_ms=(time.monotonic() - started) * 1000.0,
            error=str(exc),
            **extra,
        )
        raise
    else:
        emit_tenant_event(
            event=event,
            entity_id=entity_id,
            action=action,
            status=STATUS_SUCCESS,
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            duration_ms=(time.monotonic() - started) * 1000.0,
            error=None,
            **extra,
        )
