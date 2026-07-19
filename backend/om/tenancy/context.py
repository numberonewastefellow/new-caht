"""Contract-3 tenant-context facade.

.. warning::
    **INTEGRATION SHIM (WS-G worktree only).** WS-M owns the canonical
    ``om.tenancy.context`` module. This thin re-export exists so the WS-G
    worktree is coherent standalone (it branches off ``rename_onyx_to_om``,
    which predates WS-M's package). At integration time the integrator drops
    this file in favour of WS-M's authoritative implementation, which
    re-exports the same primitives — so importers need no changes.

All WS-G code imports the tenant primitives from here (never from the legacy
locations directly), per Contract 3.
"""

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy.orm import Session

from om.db.engine.sql_engine import get_session
from om.db.engine.sql_engine import get_session_with_current_tenant
from om.db.engine.sql_engine import get_session_with_shared_schema
from om.db.engine.sql_engine import get_session_with_tenant
from shared_configs.contextvars import CURRENT_TENANT_ID_CONTEXTVAR
from shared_configs.contextvars import get_current_tenant_id

__all__ = [
    "CURRENT_TENANT_ID_CONTEXTVAR",
    "get_current_tenant_id",
    "get_current_tenant_session",
    "get_tenant_session",
    "get_shared_schema_session",
    "get_tenant_session_dependency",
]


# (b) Get tenant-scoped DB session (request-scoped, tenant read from contextvar).
get_current_tenant_session = get_session_with_current_tenant


@contextmanager
def get_tenant_session(*, tenant_id: str) -> Generator[Session, None, None]:
    """Explicit-tenant session (background jobs / cross-tenant loops)."""
    with get_session_with_tenant(tenant_id=tenant_id) as session:
        yield session


# Pinned to the shared ``public`` schema (ONLY for genuinely global tables).
get_shared_schema_session = get_session_with_shared_schema

# FastAPI dependency yielding a session bound to the current-request tenant.
get_tenant_session_dependency = get_session
