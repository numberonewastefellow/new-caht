"""Contract 3 — the single tenant-context surface every workstream imports.

This module is the *facade* for multi-tenant safety. It exposes:

* the current-tenant contextvar + accessor,
* tenant-scoped DB session helpers (each binds the tenant's Postgres schema),
* the set of tables that are global (``public`` schema) rather than per-tenant.

The underlying primitives (the contextvar, the schema-translated ``Session`` factory)
already exist and are used across the codebase; this facade re-exports them under stable
names and adds ergonomic helpers so that NEW code has one import path and never reaches
into engine internals. Do not hardcode a schema anywhere — always go through here.
"""

from __future__ import annotations

from collections.abc import Generator
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy.orm import Session

from om.db.engine.sql_engine import get_session_with_current_tenant
from om.db.engine.sql_engine import get_session_with_shared_schema
from om.db.engine.sql_engine import get_session_with_tenant
from om.db.engine.sql_engine import get_session as _get_session_dependency
from om.db.engine.sql_engine import is_valid_schema_name
from om.tenancy.config import MULTI_TENANT
from om.tenancy.config import POSTGRES_DEFAULT_SCHEMA
from shared_configs.contextvars import CURRENT_TENANT_ID_CONTEXTVAR
from shared_configs.contextvars import get_current_tenant_id

__all__ = [
    # current-tenant identity
    "CURRENT_TENANT_ID_CONTEXTVAR",
    "get_current_tenant_id",
    "tenant_context",
    "is_valid_schema_name",
    # tenant-scoped sessions
    "get_current_tenant_session",
    "get_tenant_session",
    "get_shared_schema_session",
    "get_tenant_session_dependency",
    # constants
    "DEFAULT_SCHEMA",
    "MULTI_TENANT",
    "PUBLIC_SCHEMA_TABLES",
]

# The schema used for the single global tenant (self-hosted) and for the small set of
# genuinely global tables in multi-tenant mode.
DEFAULT_SCHEMA: str = POSTGRES_DEFAULT_SCHEMA

# The ONLY tables that live in the ``public`` (global) schema. Everything else is
# per-tenant. New feature tables MUST NOT be added here (Contract 3 / Contract 4).
PUBLIC_SCHEMA_TABLES: frozenset[str] = frozenset(
    {
        "user_tenant_mapping",  # email -> tenant login routing (WS-M owns)
        "alembic_version",  # migration bookkeeping for the public baseline
    }
)


# --------------------------------------------------------------------------------------
# Current-tenant identity
# --------------------------------------------------------------------------------------
@contextmanager
def tenant_context(tenant_id: str) -> Iterator[str]:
    """Temporarily bind the current tenant for a block of work (background jobs, tests).

    Restores the previous value on exit even if the body raises.
    """
    token = CURRENT_TENANT_ID_CONTEXTVAR.set(tenant_id)
    try:
        yield tenant_id
    finally:
        CURRENT_TENANT_ID_CONTEXTVAR.reset(token)


# --------------------------------------------------------------------------------------
# Tenant-scoped DB sessions (all bind the tenant's schema via schema_translate_map)
# --------------------------------------------------------------------------------------
@contextmanager
def get_current_tenant_session() -> Generator[Session, None, None]:
    """Session for the tenant currently bound in the contextvar (request-scoped default)."""
    with get_session_with_current_tenant() as session:
        yield session


@contextmanager
def get_tenant_session(*, tenant_id: str) -> Generator[Session, None, None]:
    """Session for an explicit tenant (background jobs / cross-tenant iteration)."""
    with get_session_with_tenant(tenant_id=tenant_id) as session:
        yield session


@contextmanager
def get_shared_schema_session() -> Generator[Session, None, None]:
    """Session pinned to the global ``public`` schema. Use ONLY for PUBLIC_SCHEMA_TABLES."""
    with get_session_with_shared_schema() as session:
        yield session


def get_tenant_session_dependency() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a tenant-scoped session.

    Rejects unauthenticated requests in multi-tenant mode (they resolve to the default
    schema, which holds no tenant data).
    """
    yield from _get_session_dependency()
