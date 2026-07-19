"""Contract-3 tenant-context facade — WS-D standalone stand-in.

Per ``rewrite-plans/CONTRACTS.md`` (Contract 3, FINALIZED by WS-M), all new code
imports the tenant primitives from ``om.tenancy.context``. WS-M owns the *canonical*
facade at this path. This file is a thin re-export of the underlying legacy
primitives (which the canonical facade also re-exports) so the ``rewrite/ws-d``
worktree imports and unit-tests standalone before WS-M is merged.

INTEGRATOR: on merge, KEEP WS-M's canonical ``om/tenancy/context.py`` and DELETE
this stand-in — the exported names are identical.
"""

from __future__ import annotations

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
    "get_current_tenant_session",
    "get_tenant_session",
    "get_shared_schema_session",
    "get_tenant_session_dependency",
]
