"""Structured, OpenSearch-friendly audit logging for SAML SSO (Standard 9).

No JSON/structured logging helper exists in the backend yet, so this is a small
greenfield emitter scoped to the SSO feature. Every significant SSO event
(login, logout, JIT provisioning, assertion rejection, config change) is written
as a single JSON object on the standard logger with the mandated fields:

    event, entity, entity_id, tenant_id, actor_user_id, action, status,
    duration_ms, error

Emission is always wrapped in try/except so a logging failure can never break
the auth flow.
"""

from __future__ import annotations

import json
from enum import Enum
from typing import Any

from om.utils.logger import setup_logger

logger = setup_logger()


class SsoEvent(str, Enum):
    """Canonical SSO audit event names (Standard 9 vocabulary)."""

    LOGIN = "sso.login"
    LOGOUT = "sso.logout"
    JIT_PROVISIONED = "sso.jit_provisioned"
    ASSERTION_REJECTED = "sso.assertion_rejected"
    AUTHORIZE = "sso.authorize"
    CONFIG_UPDATED = "sso.config_updated"
    CONFIG_VERIFIED = "sso.config_verified"


class SsoEntity(str, Enum):
    SAML_SESSION = "saml_session"
    SAML_CONFIG = "saml_config"
    USER = "user"


def _safe_tenant_id() -> str | None:
    try:
        from om.tenancy.context import get_current_tenant_id

        return get_current_tenant_id()
    except Exception:
        return None


def _safe_actor_user_id() -> str | None:
    try:
        from shared_configs.contextvars import CURRENT_USER_ID_CONTEXTVAR

        value = CURRENT_USER_ID_CONTEXTVAR.get()
        return str(value) if value else None
    except Exception:
        return None


def sso_audit(
    event: SsoEvent | str,
    entity: SsoEntity | str,
    *,
    action: str,
    status: str,
    entity_id: Any | None = None,
    actor_user_id: Any | None = None,
    duration_ms: float | None = None,
    error: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """Emit one structured SSO audit record. Never raises."""
    try:
        record: dict[str, Any] = {
            "event": event.value if isinstance(event, SsoEvent) else str(event),
            "entity": entity.value if isinstance(entity, SsoEntity) else str(entity),
            "entity_id": str(entity_id) if entity_id is not None else None,
            "tenant_id": _safe_tenant_id(),
            "actor_user_id": (
                str(actor_user_id)
                if actor_user_id is not None
                else _safe_actor_user_id()
            ),
            "action": action,
            "status": status,
            "duration_ms": round(duration_ms, 2) if duration_ms is not None else None,
            "error": error,
        }
        if extra:
            record.update(extra)
        logger.info("sso_audit %s", json.dumps(record, default=str, sort_keys=True))
    except Exception:
        # Logging must never break the auth flow.
        logger.exception("Failed to emit SSO audit log (event=%s)", event)
