"""Structured (OpenSearch-friendly) event logging for the WS-H feature set.

CONTRACTS Standard 9 requires a JSON-friendly structured log on every significant
create/update/delete event, with a fixed field contract:

    event, entity, entity_id, tenant_id, actor_user_id, action, status,
    duration_ms, error

The existing ``om.utils.logger`` is plain-text only (no JSON formatter), so this
module serializes the field bag to a single JSON line and emits it through the
standard logger. Every helper here is wrapped in ``try/except`` — logging must
never break the request path it instruments.

Scoped to the analytics package (imported by analytics / query_history / reporting
/ app_settings) to avoid colliding with any other workstream's logging helper.
"""

import datetime
import json
import time
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from om.utils.logger import setup_logger
from shared_configs.contextvars import get_current_tenant_id

logger = setup_logger()


def _resolve_tenant_id() -> str | None:
    """Best-effort read of the current tenant id; never raises."""
    try:
        return get_current_tenant_id()
    except Exception:
        return None


def log_structured_event(
    *,
    event: str,
    entity: str,
    action: str,
    status: str = "success",
    entity_id: str | int | None = None,
    actor_user_id: str | None = None,
    duration_ms: float | None = None,
    error: str | None = None,
    **extra: Any,
) -> None:
    """Emit one JSON structured log line for OpenSearch ingestion.

    Never raises: any failure while building/emitting the log is swallowed so
    instrumentation can never break the caller.
    """
    try:
        payload: dict[str, Any] = {
            "event": event,
            "entity": entity,
            "entity_id": str(entity_id) if entity_id is not None else None,
            "tenant_id": _resolve_tenant_id(),
            "actor_user_id": actor_user_id,
            "action": action,
            "status": status,
            "duration_ms": (
                round(duration_ms, 2) if duration_ms is not None else None
            ),
            "error": error,
            "logged_at": datetime.datetime.now(tz=datetime.timezone.utc).isoformat(),
        }
        if extra:
            payload.update(extra)
        message = json.dumps(payload, default=str, sort_keys=True)
        if status == "error":
            logger.error(message)
        else:
            logger.info(message)
    except Exception:
        # Structured logging must never break the caller.
        try:
            logger.exception(f"Failed to emit structured event: {event}")
        except Exception:
            pass


@contextmanager
def timed_event(
    *,
    event: str,
    entity: str,
    action: str,
    entity_id: str | int | None = None,
    actor_user_id: str | None = None,
    **extra: Any,
) -> Generator[dict[str, Any], None, None]:
    """Time a block and emit a structured event on exit.

    Yields a mutable context dict; the caller may set ``ctx["entity_id"]`` (or
    add keys under ``ctx["extra"]``) once the id is known inside the block. On an
    exception the event is logged with ``status="error"`` and the message, then
    the exception is re-raised.
    """
    start = time.monotonic()
    ctx: dict[str, Any] = {"entity_id": entity_id, "extra": dict(extra)}
    try:
        yield ctx
    except Exception as exc:
        duration_ms = (time.monotonic() - start) * 1000.0
        log_structured_event(
            event=event,
            entity=entity,
            action=action,
            status="error",
            entity_id=ctx.get("entity_id"),
            actor_user_id=actor_user_id,
            duration_ms=duration_ms,
            error=str(exc),
            **ctx.get("extra", {}),
        )
        raise
    else:
        duration_ms = (time.monotonic() - start) * 1000.0
        log_structured_event(
            event=event,
            entity=entity,
            action=action,
            status="success",
            entity_id=ctx.get("entity_id"),
            actor_user_id=actor_user_id,
            duration_ms=duration_ms,
            **ctx.get("extra", {}),
        )
