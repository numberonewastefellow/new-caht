"""Admin API for SCIM provisioning (session/admin-authenticated).

Distinct from the SCIM protocol router (`api.py`, bearer-token auth): this router
is mounted under the global API prefix and gated by ``current_admin_user``. It
lets admins mint/revoke SCIM bearer tokens and view provisioning status. The raw
token is returned exactly once, at creation; only its hash is stored.
"""

from __future__ import annotations

import datetime

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from om.auth.users import current_admin_user
from om.db.engine.sql_engine import get_session
from om.db.models import ScimToken
from om.db.models import User
from om.db.scim import ScimRepository
from om.server.scim import constants
from om.server.scim import scim_logging
from om.server.scim.auth import build_scim_token_display
from om.server.scim.auth import generate_scim_token
from om.server.scim.auth import hash_scim_token
from om.tenancy.context import get_current_tenant_id
from shared_configs.configs import MULTI_TENANT

scim_admin_router = APIRouter(prefix="/admin/scim")


# --------------------------------------------------------------------------
# Request / response models
# --------------------------------------------------------------------------
class ScimTokenCreateRequest(BaseModel):
    name: str


class ScimTokenInfo(BaseModel):
    id: int
    name: str
    token_display: str
    is_active: bool
    created_at: datetime.datetime
    last_used_at: datetime.datetime | None


class ScimTokenCreatedResponse(ScimTokenInfo):
    # The raw token, shown exactly once. Never retrievable again.
    raw_token: str


class ScimStatusResponse(BaseModel):
    base_url: str
    multi_tenant: bool
    active_token_count: int
    user_mapping_count: int
    team_mapping_count: int


def _base_url(request: Request) -> str:
    return str(request.base_url).rstrip("/") + constants.SCIM_ROOT_PATH


def _to_info(token: ScimToken) -> ScimTokenInfo:
    return ScimTokenInfo(
        id=token.id,
        name=token.name,
        token_display=token.token_display,
        is_active=token.is_active,
        created_at=token.created_at,
        last_used_at=token.last_used_at,
    )


# --------------------------------------------------------------------------
# Endpoints
# --------------------------------------------------------------------------
@scim_admin_router.get("/status")
def get_scim_status(
    request: Request,
    _: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
) -> ScimStatusResponse:
    repo = ScimRepository(db_session)
    return ScimStatusResponse(
        base_url=_base_url(request),
        multi_tenant=MULTI_TENANT,
        active_token_count=repo.count_active_tokens(),
        user_mapping_count=repo.count_user_mappings(),
        team_mapping_count=repo.count_team_mappings(),
    )


@scim_admin_router.get("/tokens")
def list_scim_tokens(
    _: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
) -> list[ScimTokenInfo]:
    repo = ScimRepository(db_session)
    return [_to_info(token) for token in repo.list_tokens()]


@scim_admin_router.post("/tokens", status_code=201)
def create_scim_token(
    body: ScimTokenCreateRequest,
    user: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
) -> ScimTokenCreatedResponse:
    name = body.name.strip()
    tenant_id = get_current_tenant_id() if MULTI_TENANT else None
    raw_token = generate_scim_token(tenant_id)
    repo = ScimRepository(db_session)
    token = repo.create_token(
        name=name or "SCIM token",
        hashed_token=hash_scim_token(raw_token),
        token_display=build_scim_token_display(raw_token),
        created_by=user.id,
    )
    db_session.commit()
    scim_logging.log_scim_event(
        event=scim_logging.EVENT_TOKEN_CREATED,
        entity=scim_logging.ENTITY_TOKEN,
        action="create",
        status=scim_logging.STATUS_SUCCESS,
        entity_id=token.id,
        actor_user_id=str(user.id),
    )
    info = _to_info(token)
    return ScimTokenCreatedResponse(**info.model_dump(), raw_token=raw_token)


@scim_admin_router.delete("/tokens/{token_id}", status_code=204)
def revoke_scim_token(
    token_id: int,
    user: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
) -> None:
    repo = ScimRepository(db_session)
    revoked = repo.revoke_token(token_id)
    db_session.commit()
    scim_logging.log_scim_event(
        event=scim_logging.EVENT_TOKEN_REVOKED,
        entity=scim_logging.ENTITY_TOKEN,
        action="delete",
        status=scim_logging.STATUS_SUCCESS if revoked else scim_logging.STATUS_ERROR,
        entity_id=token_id,
        actor_user_id=str(user.id),
        error=None if revoked else "token not found",
    )
    if not revoked:
        raise HTTPException(status_code=404, detail="SCIM token not found")
