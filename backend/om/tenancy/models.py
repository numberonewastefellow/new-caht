"""API/DTO models for the self-hosted tenant-admin surface (no billing fields)."""

from __future__ import annotations

from pydantic import BaseModel
from pydantic import EmailStr
from pydantic import Field


class TenantSummary(BaseModel):
    """A tenant as seen by the platform-admin screen."""

    tenant_id: str
    active_user_count: int
    total_user_count: int


class TenantListResponse(BaseModel):
    tenants: list[TenantSummary]


class CreateTenantRequest(BaseModel):
    """Provision a new tenant with an initial admin user."""

    admin_email: EmailStr


class AssignUserRequest(BaseModel):
    email: EmailStr
    # If the user already belongs to a tenant, move them instead of erroring.
    move_if_assigned: bool = Field(default=False)


class TenantActionResponse(BaseModel):
    tenant_id: str
    success: bool
    detail: str | None = None
