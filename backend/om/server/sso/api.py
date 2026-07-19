"""FastAPI routers for SAML SSO.

- ``sso_router``       — PUBLIC SP endpoints under ``/sso/saml/*`` (must be listed
  in ``auth_check.PUBLIC_ENDPOINT_SPECS``; they run before a user session exists).
- ``admin_sso_router`` — admin config CRUD under ``/admin/sso/saml/*``, gated by
  ``current_admin_user`` so ``check_router_auth`` treats them as protected.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import Request
from fastapi import Response
from fastapi import status
from sqlalchemy.orm import Session

from om.auth.users import auth_backend
from om.auth.users import current_admin_user
from om.auth.users import get_user_manager
from om.auth.users import optional_user
from om.auth.users import UserManager
from om.db.models import User
from om.server.sso.audit import SsoEntity
from om.server.sso.audit import SsoEvent
from om.server.sso.audit import sso_audit
from om.server.sso.config_store import default_sp_acs_url
from om.server.sso.config_store import default_sp_entity_id
from om.server.sso.config_store import get_saml_config_row
from om.server.sso.config_store import load_saml_config
from om.server.sso.config_store import to_view
from om.server.sso.config_store import upsert_saml_config
from om.server.sso.saml_settings import build_saml_settings
from om.server.sso.schemas import SamlAuthorizeResponse
from om.server.sso.schemas import SamlConfigUpsertRequest
from om.server.sso.schemas import SamlConfigView
from om.server.sso.schemas import SamlLastLogin
from om.server.sso.schemas import SamlVerifyCheck
from om.server.sso.schemas import SamlVerifyResult
from om.server.sso.service import build_authorize_url
from om.server.sso.service import process_acs
from om.server.sso.service import process_logout
from om.server.sso.session_store import get_last_saml_session
from om.server.sso.verify import verify_saml_config
from om.tenancy.context import get_current_tenant_session
from om.tenancy.context import get_tenant_session_dependency
from om.utils.logger import setup_logger

logger = setup_logger()

sso_router = APIRouter(prefix="/sso/saml")
admin_sso_router = APIRouter(prefix="/admin/sso/saml")


# --------------------------------------------------------------------------- #
# Public SP endpoints
# --------------------------------------------------------------------------- #
@sso_router.get("/authorize")
async def saml_authorize(
    request: Request,
    next_url: str | None = Query(default=None, alias="next"),
) -> SamlAuthorizeResponse:
    """SP-initiated login — return the IdP redirect URL."""
    authorization_url = await build_authorize_url(request, next_url)
    return SamlAuthorizeResponse(authorization_url=authorization_url)


@sso_router.get("/acs")
async def saml_acs_get(
    request: Request,
    strategy: Any = Depends(auth_backend.get_strategy),
    user_manager: UserManager = Depends(get_user_manager),
) -> Response:
    """ACS — HTTP-Redirect (GET) binding fallback."""
    return await process_acs(request, strategy, user_manager)


@sso_router.post("/acs")
async def saml_acs_post(
    request: Request,
    strategy: Any = Depends(auth_backend.get_strategy),
    user_manager: UserManager = Depends(get_user_manager),
) -> Response:
    """ACS — HTTP-POST binding (primary path)."""
    return await process_acs(request, strategy, user_manager)


@sso_router.post("/logout")
async def saml_logout(
    request: Request,
    user: User | None = Depends(optional_user),
    strategy: Any = Depends(auth_backend.get_strategy),
) -> Response:
    """SP logout — expire the SAML session ledger and clear the auth cookie."""
    return await process_logout(request, user, strategy)


@sso_router.get("/metadata")
def saml_metadata() -> Response:
    """Publish this SP's SAML metadata XML (useful when registering the IdP)."""
    from onelogin.saml2.settings import (  # type: ignore[import-untyped]
        OneLogin_Saml2_Settings,
    )

    with get_current_tenant_session() as db_session:
        config = load_saml_config(db_session)
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SAML SSO is not configured.",
        )

    try:
        saml_settings = OneLogin_Saml2_Settings(
            build_saml_settings(config), sp_validation_only=True
        )
        metadata = saml_settings.get_sp_metadata()
        errors = saml_settings.validate_metadata(metadata)
    except Exception as exc:
        # Incomplete/invalid SP settings (e.g. missing entityId) raise here.
        logger.warning("Failed to build SP metadata: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SAML SP is not fully configured.",
        ) from exc

    if errors:
        logger.error("Invalid SP metadata: %s", errors)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Generated SP metadata is invalid.",
        )
    return Response(content=metadata, media_type="application/xml")


# --------------------------------------------------------------------------- #
# Admin config CRUD (admin-gated)
# --------------------------------------------------------------------------- #
@admin_sso_router.get("/config")
def get_saml_config(
    _: User = Depends(current_admin_user),
    db_session: Session = Depends(get_tenant_session_dependency),
) -> SamlConfigView:
    """Return the current (secret-masked) SAML configuration."""
    return to_view(get_saml_config_row(db_session))


@admin_sso_router.put("/config")
def put_saml_config(
    request: SamlConfigUpsertRequest,
    user: User = Depends(current_admin_user),
    db_session: Session = Depends(get_tenant_session_dependency),
) -> SamlConfigView:
    """Create or update the SAML configuration (singleton per tenant)."""
    row = upsert_saml_config(db_session, request)
    sso_audit(
        SsoEvent.CONFIG_UPDATED,
        SsoEntity.SAML_CONFIG,
        entity_id=row.id,
        actor_user_id=user.id,
        action="update",
        status="success",
        extra={"enabled": row.enabled},
    )
    return to_view(row)


@admin_sso_router.get("/verify")
def verify_saml(
    user: User = Depends(current_admin_user),
    db_session: Session = Depends(get_tenant_session_dependency),
) -> SamlVerifyResult:
    """Structurally validate the *saved* SAML config (no live IdP round-trip).

    Returns per-check pass/fail plus the SP details to register at the IdP and
    the most recent SAML session as an "it's working" signal.
    """
    # Public, IdP-facing metadata URL (served through the /api web proxy).
    metadata_url = "/api/sso/saml/metadata"

    config = load_saml_config(db_session)
    if config is None:
        result = SamlVerifyResult(
            valid=False,
            checks=[
                SamlVerifyCheck(
                    key="config",
                    label="Configuration",
                    status="error",
                    detail="No SAML configuration saved yet. Fill in the form and Save first.",
                )
            ],
            sp_entity_id=default_sp_entity_id(),
            sp_acs_url=default_sp_acs_url(),
            sp_metadata_url=metadata_url,
            last_successful_login=None,
        )
    else:
        valid, checks = verify_saml_config(config)
        last = get_last_saml_session(db_session)
        result = SamlVerifyResult(
            valid=valid,
            checks=checks,
            sp_entity_id=config.sp_entity_id,
            sp_acs_url=config.sp_acs_url,
            sp_metadata_url=metadata_url,
            last_successful_login=(
                SamlLastLogin(email=last[0], at=last[1].isoformat())
                if last is not None
                else None
            ),
        )

    sso_audit(
        SsoEvent.CONFIG_VERIFIED,
        SsoEntity.SAML_CONFIG,
        actor_user_id=user.id,
        action="verify",
        status="valid" if result.valid else "invalid",
        extra={"errors": [c.key for c in result.checks if c.status == "error"]},
    )
    return result
