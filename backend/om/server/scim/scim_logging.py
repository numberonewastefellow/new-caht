"""Structured, OpenSearch-friendly logging for SCIM provisioning events.

Every create/update/delete and other significant SCIM event emits a single
JSON object with the Standard-9 fields: ``event``, ``entity``, ``entity_id``,
``tenant_id``, ``actor_user_id``, ``action``, ``status``, ``duration_ms``,
``error``. All emission is wrapped in try/except so logging can never break a
provisioning request.
"""

from __future__ import annotations

import json
import time
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any
from typing import Final

from om.utils.logger import setup_logger

logger = setup_logger()

# --- event names (Standard 9) --------------------------------------------
EVENT_USER_PROVISIONED: Final = "scim.user_provisioned"
EVENT_USER_UPDATED: Final = "scim.user_updated"
EVENT_USER_DEPROVISIONED: Final = "scim.user_deprovisioned"
EVENT_GROUP_SYNCED: Final = "scim.group_synced"
EVENT_GROUP_DEPROVISIONED: Final = "scim.group_deprovisioned"
EVENT_TOKEN_CREATED: Final = "scim.token_created"
EVENT_TOKEN_REVOKED: Final = "scim.token_revoked"

# --- entity names ---------------------------------------------------------
ENTITY_USER: Final = "scim_user"
ENTITY_TEAM: Final = "scim_team"
ENTITY_TOKEN: Final = "scim_token"

# --- status ---------------------------------------------------------------
STATUS_SUCCESS: Final = "success"
STATUS_ERROR: Final = "error"


def _current_tenant_id() -> str | None:
    try:
        from om.tenancy.context import get_current_tenant_id

        return get_current_tenant_id()
    except Exception:
        return None


def log_scim_event(
    *,
    event: str,
    entity: str,
    action: str,
    status: str,
    entity_id: str | int | None = None,
    actor_user_id: str | None = None,
    tenant_id: str | None = None,
    duration_ms: float | None = None,
    error: str | None = None,
    as_error: bool | None = None,
    **extra: Any,
) -> None:
    """Emit one structured SCIM log line. Never raises.

    ``as_error`` overrides the log level: expected client rejections (SCIM 4xx)
    carry ``status=error`` for auditing but should log at INFO, not ERROR — pass
    ``as_error=False`` for those. When ``None``, the level follows ``status``.
    """
    try:
        payload: dict[str, Any] = {
            "event": event,
            "entity": entity,
            "entity_id": str(entity_id) if entity_id is not None else None,
            "tenant_id": tenant_id if tenant_id is not None else _current_tenant_id(),
            "actor_user_id": actor_user_id,
            "action": action,
            "status": status,
            "duration_ms": round(duration_ms, 2) if duration_ms is not None else None,
            "error": error,
        }
        if extra:
            payload.update(extra)
        line = json.dumps(payload, default=str)
        emit_error = (status == STATUS_ERROR) if as_error is None else as_error
        if emit_error:
            logger.error(line)
        else:
            logger.info(line)
    except Exception:
        # Logging must never break provisioning.
        logger.exception("Failed to emit SCIM structured log event")


@contextmanager
def scim_operation(
    *,
    event: str,
    entity: str,
    action: str,
    actor_user_id: str | None = None,
    tenant_id: str | None = None,
) -> Generator["_OperationHandle", None, None]:
    """Time a SCIM operation and emit a success/error event automatically.

    Usage::

        with scim_operation(event=..., entity=..., action="create") as op:
            ...
            op.entity_id = created.id
    """
    handle = _OperationHandle()
    started = time.monotonic()
    try:
        yield handle
    except Exception as exc:
        # Expected SCIM client rejections (4xx) are audited but logged at INFO;
        # only unexpected/server failures (>=500 or non-SCIM) log at ERROR.
        status_code = getattr(exc, "status_code", 500)
        log_scim_event(
            event=event,
            entity=entity,
            action=action,
            status=STATUS_ERROR,
            entity_id=handle.entity_id,
            actor_user_id=actor_user_id,
            tenant_id=tenant_id,
            duration_ms=(time.monotonic() - started) * 1000.0,
            error=f"{type(exc).__name__}: {exc}",
            as_error=status_code >= 500,
        )
        raise
    else:
        log_scim_event(
            event=event,
            entity=entity,
            action=action,
            status=STATUS_SUCCESS,
            entity_id=handle.entity_id,
            actor_user_id=actor_user_id,
            tenant_id=tenant_id,
            duration_ms=(time.monotonic() - started) * 1000.0,
        )


class _OperationHandle:
    """Mutable handle so a ``with scim_operation(...)`` block can set entity_id."""

    def __init__(self) -> None:
        self.entity_id: str | int | None = None
