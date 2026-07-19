"""Shared index-filter construction (Contract 2 access filters + user filters).

Both the streaming orchestrator and admin search build their ``IndexFilters`` the
same way: start from the Contract-2 ACL filters (fail-closed) and layer the
user-selected dimensions on top. ACL is never reimplemented here.
"""

from sqlalchemy.orm import Session

from om.context.search.models import BaseFilters
from om.context.search.models import IndexFilters
from om.context.search.preprocessing.access_filters import build_user_only_filters
from om.db.models import User
from om.tenancy.context import get_current_tenant_id


def build_index_filters(
    user: User, session: Session, user_filters: BaseFilters | None
) -> IndexFilters:
    # Contract-2 primitive: IndexFilters with access_control_list populated.
    filters = build_user_only_filters(user, session)
    base = user_filters or BaseFilters()
    filters.source_type = base.source_type
    filters.document_set = base.document_set
    filters.time_cutoff = base.time_cutoff
    filters.tags = base.tags
    filters.workspace_id_filter = base.workspace_id_filter
    filters.agent_id_filter = base.agent_id_filter
    # Fail-closed: get_current_tenant_id() returns the default schema in
    # single-tenant mode and raises in multi-tenant mode if the tenant is unset.
    # We deliberately do NOT swallow that — a silent None here would drop the
    # tenant filter from the index query (cross-tenant risk).
    filters.tenant_id = get_current_tenant_id()
    return filters
