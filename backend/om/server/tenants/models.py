from pydantic import BaseModel


class CreateTenantRequest(BaseModel):
    tenant_id: str
    initial_admin_email: str


class ImagentteRequest(BaseModel):
    email: str


class TenantCreationPayload(BaseModel):
    tenant_id: str
    email: str
    referral_source: str | None = None


class TenantDeletionPayload(BaseModel):
    tenant_id: str
    email: str


class AnonymousUserPath(BaseModel):
    anonymous_user_path: str | None


class TenantByDomainResponse(BaseModel):
    tenant_id: str
    number_of_users: int
    creator_email: str


class TenantByDomainRequest(BaseModel):
    email: str


class RequestInviteRequest(BaseModel):
    tenant_id: str


class RequestInviteResponse(BaseModel):
    success: bool
    message: str


class PendingUserSnapshot(BaseModel):
    email: str


class ApproveUserRequest(BaseModel):
    email: str
