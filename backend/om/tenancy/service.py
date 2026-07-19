"""Tenant-administration service (clean-room, no billing).

Thin orchestration layer between the tenant-admin API routes and the lower-level pieces
(:mod:`om.tenancy.provisioning`, :mod:`om.tenancy.repository`, :mod:`om.tenancy.events`).
Keeping the business logic here — not in the route handlers — is what lets both the HTTP
layer and future callers (CLI, tests) drive tenant administration the same way.

Heavy, blocking operations (schema creation + Alembic migration) live in
:mod:`om.tenancy.provisioning`; the async API layer offloads them to a worker thread. The
light operations here are ordinary synchronous DB work, matching the rest of the app's
sync-SQLAlchemy style.
"""

from __future__ import annotations

from om.tenancy.events import EVENT_TENANT_DEACTIVATED
from om.tenancy.events import EVENT_USER_ASSIGNED
from om.tenancy.events import EVENT_USER_MOVED
from om.tenancy.events import STATUS_SUCCESS
from om.tenancy.events import emit_tenant_event
from om.tenancy.events import tenant_operation
from om.tenancy.models import TenantActionResponse
from om.tenancy.models import TenantListResponse
from om.tenancy.models import TenantSummary
from om.tenancy.provisioning import deprovision_tenant
from om.tenancy.provisioning import provision_tenant
from om.tenancy.repository import TenantMappingRepository
from om.tenancy.schema import assert_tenant_id
from om.utils.logger import setup_logger

__all__ = ["TenantService"]

logger = setup_logger()


class TenantService:
    """Superuser-facing tenant administration. All methods are side-effect logged."""

    # ------------------------------------------------------------------ reads
    @staticmethod
    def list_tenants() -> TenantListResponse:
        """Every tenant that appears in the mapping table, with user counts."""
        counts = TenantMappingRepository.user_counts_by_tenant()
        summaries = [
            TenantSummary(
                tenant_id=tenant_id,
                active_user_count=active,
                total_user_count=total,
            )
            for tenant_id, (active, total) in sorted(counts.items())
        ]
        return TenantListResponse(tenants=summaries)

    # --------------------------------------------------------------- lifecycle
    @staticmethod
    def create_tenant(*, admin_email: str, actor_user_id: str | None) -> str:
        """Provision a new tenant (blocking) and return its id.

        Delegates to :func:`provision_tenant`, which emits the ``tenant.created`` event and
        rolls back a half-built schema on failure.
        """
        return provision_tenant(admin_email=admin_email, actor_user_id=actor_user_id)

    @staticmethod
    def delete_tenant(
        *, tenant_id: str, actor_user_id: str | None
    ) -> TenantActionResponse:
        """Drop a tenant's schema and all its mappings (blocking)."""
        assert_tenant_id(tenant_id)
        deprovision_tenant(tenant_id=tenant_id, actor_user_id=actor_user_id)
        return TenantActionResponse(
            tenant_id=tenant_id, success=True, detail="Tenant deleted"
        )

    @staticmethod
    def deactivate_tenant(
        *, tenant_id: str, actor_user_id: str | None
    ) -> TenantActionResponse:
        """Deactivate every mapping for a tenant without destroying its data.

        Users can no longer route into the tenant, but the schema and rows are retained so
        it can be reactivated by re-assigning users.
        """
        assert_tenant_id(tenant_id)
        with tenant_operation(
            event=EVENT_TENANT_DEACTIVATED,
            entity_id=tenant_id,
            action="update",
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
        ):
            affected = TenantMappingRepository.set_tenant_active(tenant_id, False)
        return TenantActionResponse(
            tenant_id=tenant_id,
            success=True,
            detail=f"Deactivated {affected} mapping(s)",
        )

    # -------------------------------------------------------------- membership
    @staticmethod
    def assign_user(
        *,
        tenant_id: str,
        email: str,
        move_if_assigned: bool,
        actor_user_id: str | None,
    ) -> TenantActionResponse:
        """Route ``email`` to ``tenant_id``.

        If the user already has an active mapping to a *different* tenant, the behaviour
        depends on ``move_if_assigned``: move them (deactivate elsewhere, activate here) or
        reject with a clear error so the operator makes the call explicitly.
        """
        assert_tenant_id(tenant_id)
        current = TenantMappingRepository.get_active_tenant_for_email(email)

        if current == tenant_id:
            emit_tenant_event(
                event=EVENT_USER_ASSIGNED,
                entity_id=tenant_id,
                action="update",
                status=STATUS_SUCCESS,
                tenant_id=tenant_id,
                actor_user_id=actor_user_id,
                email=email,
                note="already_assigned",
            )
            return TenantActionResponse(
                tenant_id=tenant_id,
                success=True,
                detail="User already assigned to this tenant",
            )

        if current is not None and not move_if_assigned:
            return TenantActionResponse(
                tenant_id=tenant_id,
                success=False,
                detail=(
                    f"User is already active in tenant {current}; "
                    "pass move_if_assigned to move them"
                ),
            )

        if current is not None:
            with tenant_operation(
                event=EVENT_USER_MOVED,
                entity_id=tenant_id,
                action="update",
                tenant_id=tenant_id,
                actor_user_id=actor_user_id,
                email=email,
                from_tenant=current,
            ):
                TenantMappingRepository.move_user(email, current, tenant_id)
            return TenantActionResponse(
                tenant_id=tenant_id,
                success=True,
                detail=f"Moved user from {current}",
            )

        with tenant_operation(
            event=EVENT_USER_ASSIGNED,
            entity_id=tenant_id,
            action="create",
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            email=email,
        ):
            TenantMappingRepository.assign(email, tenant_id, active=True)
        return TenantActionResponse(
            tenant_id=tenant_id, success=True, detail="User assigned"
        )
