"""Structured, OpenSearch-friendly logging for the clean-room search stack.

Engineering Standard 9: on every significant search event we emit a single JSON
line carrying a fixed field set (``event``, ``entity``, ``entity_id``,
``tenant_id``, ``actor_user_id``, ``action``, ``status``, ``duration_ms``,
``error``) plus optional feature-specific fields. Every emit is wrapped in
try/except so logging can never break a request.

Canonical event names (Standard 9 for WS-E):
- ``search.executed``      - a full search flow ran (orchestration).
- ``search.expanded``      - query expansion produced variants.
- ``search.history_saved`` - a SearchQuery row persisted.
- ``search.admin``         - an admin (curator/admin) search ran.
"""

import json
import time
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any
from uuid import UUID

from om.tenancy.context import get_current_tenant_id
from om.utils.logger import setup_logger

logger = setup_logger()


# entity constant reused across the stack
SEARCH_QUERY_ENTITY = "search_query"

# action verbs (Standard 9)
ACTION_CREATE = "create"
ACTION_READ = "read"
ACTION_EXECUTE = "execute"
ACTION_UPDATE = "update"
ACTION_DELETE = "delete"

# status values
STATUS_SUCCESS = "success"
STATUS_ERROR = "error"
STATUS_STARTED = "started"


def _safe_tenant_id() -> str | None:
    """Read the current tenant id without ever raising into the caller."""
    try:
        return get_current_tenant_id()
    except Exception:
        return None


def emit_search_event(
    *,
    event: str,
    action: str,
    status: str,
    entity: str = SEARCH_QUERY_ENTITY,
    entity_id: str | UUID | int | None = None,
    actor_user_id: str | UUID | None = None,
    duration_ms: float | None = None,
    error: str | None = None,
    **extra: Any,
) -> None:
    """Emit one structured JSON log line. Never raises."""
    try:
        payload: dict[str, Any] = {
            "event": event,
            "entity": entity,
            "entity_id": str(entity_id) if entity_id is not None else None,
            "tenant_id": _safe_tenant_id(),
            "actor_user_id": str(actor_user_id) if actor_user_id is not None else None,
            "action": action,
            "status": status,
            "duration_ms": (round(duration_ms, 2) if duration_ms is not None else None),
            "error": error,
        }
        # feature-specific fields (e.g. num_variants, num_results, expansion_enabled)
        for key, value in extra.items():
            if value is not None:
                payload[key] = value
        logger.info(json.dumps(payload, default=str))
    except Exception:
        # logging must never break the request path
        logger.exception("failed to emit structured search log for event=%s", event)


@contextmanager
def timed_search_event(
    *,
    event: str,
    action: str,
    entity: str = SEARCH_QUERY_ENTITY,
    entity_id: str | UUID | int | None = None,
    actor_user_id: str | UUID | None = None,
    **extra: Any,
) -> Generator[dict[str, Any], None, None]:
    """Time a block and emit a success/error structured event on exit.

    Yields a mutable dict; fields added to it are merged into the final log line
    (e.g. set ``fields["num_results"] = len(results)`` inside the block).
    Re-raises the original exception after logging it as ``status=error``.
    """
    started = time.monotonic()
    fields: dict[str, Any] = {}
    try:
        yield fields
    except Exception as exc:
        emit_search_event(
            event=event,
            action=action,
            status=STATUS_ERROR,
            entity=entity,
            entity_id=entity_id,
            actor_user_id=actor_user_id,
            duration_ms=(time.monotonic() - started) * 1000.0,
            error=f"{type(exc).__name__}: {exc}",
            **{**extra, **fields},
        )
        raise
    else:
        emit_search_event(
            event=event,
            action=action,
            status=STATUS_SUCCESS,
            entity=entity,
            entity_id=entity_id,
            actor_user_id=actor_user_id,
            duration_ms=(time.monotonic() - started) * 1000.0,
            **{**extra, **fields},
        )
