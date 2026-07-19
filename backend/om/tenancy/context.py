"""Tenant-context facade (Contract 3).

=============================================================================
INTEGRATOR NOTE — WS-M OWNS THIS MODULE.
This file is a THIN re-export shim added by WS-B so the WS-B worktree is
self-consistent and importable/testable in isolation. WS-M builds the canonical
``backend/om/tenancy/`` package (context facade + middleware + migrations). At
integration, DISCARD this shim and keep WS-M's version — the public surface is
identical (it re-exports the very same legacy primitives), so nothing downstream
changes.
=============================================================================

Per CONTRACTS.md Contract 3, all NEW code imports tenant primitives from ONE
place (``om.tenancy.context``) instead of the legacy locations directly. This
shim maps the contract names onto the legacy implementations that "still work".
"""

from shared_configs.contextvars import CURRENT_TENANT_ID_CONTEXTVAR
from shared_configs.contextvars import get_current_tenant_id

# Session helpers all bind the tenant's Postgres schema via schema_translate_map.
from om.db.engine.sql_engine import get_session as get_tenant_session_dependency
from om.db.engine.sql_engine import (
    get_session_with_current_tenant as get_current_tenant_session,
)
from om.db.engine.sql_engine import get_session_with_shared_schema as get_shared_schema_session
from om.db.engine.sql_engine import get_session_with_tenant as get_tenant_session

__all__ = [
    "CURRENT_TENANT_ID_CONTEXTVAR",
    "get_current_tenant_id",
    "get_current_tenant_session",
    "get_tenant_session",
    "get_shared_schema_session",
    "get_tenant_session_dependency",
]
