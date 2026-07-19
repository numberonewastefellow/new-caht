"""Contract-3 tenant-context facade.

CONTRACTS.md (Contract 3, WS-M) declares ``om.tenancy.context`` as the single
canonical import location for the tenant primitives, re-exporting the stable
underlying functions so every workstream imports from ONE place.

WS-M owns the canonical module. It has not landed on this branch yet, so this
file is a **thin integrator-removable shim**: it re-exports the real primitives
from their current locations under the contract names. When WS-M's canonical
``om/tenancy/context.py`` is merged, the integrator should DELETE this shim (the
public surface is identical).

Contract name  ->  underlying implementation
-------------------------------------------------------------------
get_current_tenant_id          shared_configs.contextvars.get_current_tenant_id
CURRENT_TENANT_ID_CONTEXTVAR   shared_configs.contextvars.CURRENT_TENANT_ID_CONTEXTVAR
get_current_tenant_session     om.db.engine.sql_engine.get_session_with_current_tenant
get_tenant_session             om.db.engine.sql_engine.get_session_with_tenant
get_shared_schema_session      om.db.engine.sql_engine.get_session_with_shared_schema
get_tenant_session_dependency  om.db.engine.sql_engine.get_session
"""

from shared_configs.contextvars import CURRENT_TENANT_ID_CONTEXTVAR
from shared_configs.contextvars import get_current_tenant_id

from om.db.engine.sql_engine import get_session as get_tenant_session_dependency
from om.db.engine.sql_engine import (
    get_session_with_current_tenant as get_current_tenant_session,
)
from om.db.engine.sql_engine import (
    get_session_with_shared_schema as get_shared_schema_session,
)
from om.db.engine.sql_engine import get_session_with_tenant as get_tenant_session

__all__ = [
    "CURRENT_TENANT_ID_CONTEXTVAR",
    "get_current_tenant_id",
    "get_current_tenant_session",
    "get_tenant_session",
    "get_shared_schema_session",
    "get_tenant_session_dependency",
]
