"""Tenant-context bridge for the rate-limits module (Contract 3).

Per Contract 3, new code MUST import the tenant primitives from the ``om.tenancy.context``
facade published by WS-M. That facade is delivered in a sibling worktree and may not yet be
present when this module is imported in isolation, so this bridge prefers the facade and
falls back to the underlying primitives that the facade re-exports.

Integrator note: once WS-M is merged, this file can be reduced to a straight re-export of
``om.tenancy.context`` (the fallback branch becomes dead and should be dropped).
"""

from collections.abc import Callable
from contextlib import AbstractContextManager

from sqlalchemy.orm import Session

try:  # pragma: no cover - exercised only post-integration
    from om.tenancy.context import get_current_tenant_id as _get_current_tenant_id
    from om.tenancy.context import (
        get_current_tenant_session as _get_current_tenant_session,
    )
except ImportError:  # pre-integration fallback to the primitives WS-M re-exports
    from om.db.engine.sql_engine import (
        get_session_with_current_tenant as _get_current_tenant_session,
    )
    from shared_configs.contextvars import (
        get_current_tenant_id as _get_current_tenant_id,
    )


def get_current_tenant_id() -> str:
    """Return the current request's tenant id (Postgres schema)."""
    fn: Callable[[], str] = _get_current_tenant_id
    return fn()


def get_current_tenant_session() -> AbstractContextManager[Session]:
    """Return a context-managed, tenant-schema-bound SQLAlchemy session."""
    fn: Callable[[], AbstractContextManager[Session]] = _get_current_tenant_session
    return fn()
