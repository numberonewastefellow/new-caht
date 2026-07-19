"""Structured audit logging for team / RBAC mutations (Engineering Standard 9).

Emits one JSON-friendly line per significant event with the fixed field set the
OpenSearch pipeline expects: ``event``, ``entity``, ``entity_id``, ``tenant_id``,
``actor_user_id``, ``action``, ``status``, ``duration_ms``, ``error``.

Use :func:`audit_event` as a context manager around a mutation so timing and
failure are captured automatically and the emit itself can never raise into the
business path (Standard 9: always wrapped in try/except with a meaningful msg).
"""

from __future__ import annotations

import time
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from om.utils.logger import setup_logger

logger = setup_logger()


def _current_tenant_id() -> str | None:
    try:
        from om.tenancy.context import get_current_tenant_id

        return get_current_tenant_id()
    except Exception:
        return None


def emit_event(
    *,
    event: str,
    entity: str,
    action: str,
    status: str,
    entity_id: str | int | None = None,
    actor_user_id: str | None = None,
    duration_ms: float | None = None,
    error: str | None = None,
    **extra: Any,
) -> None:
    """Emit a single structured event line. Never raises."""
    try:
        payload: dict[str, Any] = {
            "event": event,
            "entity": entity,
            "entity_id": str(entity_id) if entity_id is not None else None,
            "tenant_id": _current_tenant_id(),
            "actor_user_id": actor_user_id,
            "action": action,
            "status": status,
            "duration_ms": round(duration_ms, 2) if duration_ms is not None else None,
            "error": error,
        }
        if extra:
            payload.update(extra)
        if status == "error":
            logger.error("rbac_audit %s", payload)
        else:
            logger.info("rbac_audit %s", payload)
    except Exception:
        # Auditing must never take down the request it is auditing.
        logger.exception("failed to emit rbac audit event")


@contextmanager
def audit_event(
    *,
    event: str,
    entity: str,
    action: str,
    entity_id: str | int | None = None,
    actor_user_id: str | None = None,
    **extra: Any,
) -> Generator[dict[str, Any], None, None]:
    """Context manager that times a mutation and logs success/error.

    Yields a mutable ``dict`` so the body can set ``entity_id`` once it is known
    (e.g. after an INSERT assigns the primary key)::

        with audit_event(event="team.created", entity="team", action="create",
                         actor_user_id=str(user.id)) as ev:
            team = ...
            ev["entity_id"] = team.id
    """
    start = time.monotonic()
    ctx: dict[str, Any] = {"entity_id": entity_id, "actor_user_id": actor_user_id}
    try:
        yield ctx
    except Exception as exc:
        emit_event(
            event=event,
            entity=entity,
            action=action,
            status="error",
            entity_id=ctx.get("entity_id"),
            actor_user_id=ctx.get("actor_user_id"),
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
            status="success",
            entity_id=ctx.get("entity_id"),
            actor_user_id=ctx.get("actor_user_id"),
            duration_ms=(time.monotonic() - start) * 1000.0,
            **extra,
        )
