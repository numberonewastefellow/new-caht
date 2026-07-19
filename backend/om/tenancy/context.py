"""WS-C worktree shim for the Contract-3 tenancy facade.

Contract 3 (``rewrite-plans/CONTRACTS.md``) mandates that NEW code import the
tenant primitives from ``om.tenancy.context`` so every workstream depends on ONE
canonical location. WS-M owns and publishes that canonical module, but it is not
yet merged into this worktree. This thin re-export shim keeps the WS-C branch
coherent and importable in isolation.

Integrator note: DROP this file in favor of WS-M's canonical
``om/tenancy/context.py`` at merge time. Contains only re-exports — never add
logic here.
"""

from om.db.engine.async_sql_engine import get_async_session
from om.db.engine.async_sql_engine import get_async_session_context_manager
from om.db.engine.sql_engine import get_session as get_tenant_session_dependency
from om.db.engine.sql_engine import (
    get_session_with_current_tenant as get_current_tenant_session,
)
from om.db.engine.sql_engine import (
    get_session_with_shared_schema as get_shared_schema_session,
)
from om.db.engine.sql_engine import get_session_with_tenant as get_tenant_session
from shared_configs.contextvars import CURRENT_TENANT_ID_CONTEXTVAR
from shared_configs.contextvars import get_current_tenant_id

__all__ = [
    "CURRENT_TENANT_ID_CONTEXTVAR",
    "get_current_tenant_id",
    # sync sessions (context managers + FastAPI dependency)
    "get_current_tenant_session",
    "get_tenant_session",
    "get_shared_schema_session",
    "get_tenant_session_dependency",
    # async sessions
    "get_async_session",
    "get_async_session_context_manager",
]
