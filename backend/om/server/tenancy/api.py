"""Self-hosted tenant-admin API (superuser-gated, no billing).

CRUD over tenants for a platform operator: list tenants + user counts, provision a tenant
on demand, assign/move a user, deactivate a tenant, and delete a tenant. Every mutating
route requires an instance ADMIN (via ``current_admin_user``) plus the optional
``TENANT_ADMIN_EMAILS`` allow-list (:func:`_enforce_platform_admin`), and every operation
emits a structured event (Standard 9) from the service/provisioning layer it calls.

There is deliberately **no** billing, seat-limit, or control-plane logic here — tenants are
a pure data-isolation construct in this deployment.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status

from om.auth.users import current_admin_user
from om.db.models import User
from om.tenancy.config import MULTI_TENANT
from om.tenancy.config import TENANT_ADMIN_EMAILS
from om.tenancy.models import AssignUserRequest
from om.tenancy.models import CreateTenantRequest
from om.tenancy.models import TenantActionResponse
from om.tenancy.models import TenantListResponse
from om.tenancy.schema import is_tenant_id
from om.tenancy.service import TenantService
from om.utils.logger import setup_logger

logger = setup_logger()

router = APIRouter(prefix="/admin/tenants", tags=["tenant-admin"])


def _enforce_platform_admin(user: User) -> None:
    """Second-stage gate on top of instance-ADMIN (``current_admin_user``).

    If the operator has configured the ``TENANT_ADMIN_EMAILS`` allow-list, membership in it
    is additionally required; when the list is empty (self-hosted default) any admin
    qualifies.

    NOTE: this is deliberately a plain helper, not a FastAPI dependency. ``check_router_auth``
    only recognises a fixed set of auth dependencies at the route's *top level* and does not
    recurse into sub-dependencies, so the routes depend directly on the recognised
    ``current_admin_user`` and call this helper for the extra allow-list check.
    """
    if TENANT_ADMIN_EMAILS and (user.email or "").lower() not in TENANT_ADMIN_EMAILS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. User is not a tenant administrator.",
        )


def _require_multi_tenant() -> None:
    if not MULTI_TENANT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant administration requires multi-tenant mode.",
        )


def _validate_tenant_id(tenant_id: str) -> None:
    if not is_tenant_id(tenant_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malformed tenant id.",
        )


@router.get("", response_model=TenantListResponse)
async def list_tenants(
    admin: User = Depends(current_admin_user),
) -> TenantListResponse:
    """List every tenant that has at least one user mapping, with seat counts."""
    _enforce_platform_admin(admin)
    try:
        return TenantService.list_tenants()
    except Exception:
        logger.exception("Failed to list tenants")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list tenants.",
        )


@router.post("", response_model=TenantActionResponse)
async def create_tenant(
    payload: CreateTenantRequest,
    admin: User = Depends(current_admin_user),
) -> TenantActionResponse:
    """Provision a new tenant on demand and route ``admin_email`` to it."""
    _enforce_platform_admin(admin)
    _require_multi_tenant()
    try:
        # Blocking (schema DDL + Alembic migration); keep the event loop responsive.
        tenant_id = await asyncio.to_thread(
            TenantService.create_tenant,
            admin_email=payload.admin_email,
            actor_user_id=str(admin.id),
        )
    except Exception:
        logger.exception("Failed to create tenant")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create tenant.",
        )
    return TenantActionResponse(
        tenant_id=tenant_id, success=True, detail="Tenant created"
    )


@router.post("/{tenant_id}/users", response_model=TenantActionResponse)
async def assign_user(
    tenant_id: str,
    payload: AssignUserRequest,
    admin: User = Depends(current_admin_user),
) -> TenantActionResponse:
    """Assign (or, with ``move_if_assigned``, move) a user to ``tenant_id``."""
    _enforce_platform_admin(admin)
    _require_multi_tenant()
    _validate_tenant_id(tenant_id)
    try:
        return TenantService.assign_user(
            tenant_id=tenant_id,
            email=payload.email,
            move_if_assigned=payload.move_if_assigned,
            actor_user_id=str(admin.id),
        )
    except Exception:
        logger.exception(f"Failed to assign user to tenant {tenant_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to assign user.",
        )


@router.post("/{tenant_id}/deactivate", response_model=TenantActionResponse)
async def deactivate_tenant(
    tenant_id: str,
    admin: User = Depends(current_admin_user),
) -> TenantActionResponse:
    """Deactivate all mappings for a tenant (retains its data for later reactivation)."""
    _enforce_platform_admin(admin)
    _require_multi_tenant()
    _validate_tenant_id(tenant_id)
    try:
        return TenantService.deactivate_tenant(
            tenant_id=tenant_id, actor_user_id=str(admin.id)
        )
    except Exception:
        logger.exception(f"Failed to deactivate tenant {tenant_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate tenant.",
        )


@router.delete("/{tenant_id}", response_model=TenantActionResponse)
async def delete_tenant(
    tenant_id: str,
    admin: User = Depends(current_admin_user),
) -> TenantActionResponse:
    """Permanently delete a tenant: drop its schema and every mapping row."""
    _enforce_platform_admin(admin)
    _require_multi_tenant()
    _validate_tenant_id(tenant_id)
    try:
        # Blocking (DROP SCHEMA CASCADE); offload so the loop stays responsive.
        return await asyncio.to_thread(
            TenantService.delete_tenant,
            tenant_id=tenant_id,
            actor_user_id=str(admin.id),
        )
    except Exception:
        logger.exception(f"Failed to delete tenant {tenant_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete tenant.",
        )
