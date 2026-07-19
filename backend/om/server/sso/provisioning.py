"""JIT provisioning for SSO logins.

We deliberately reuse ``UserManager.create`` rather than hand-rolling user
insertion: that path already implements the exact SSO rules WS-C requires —
invite-only is bypassed for ``AuthType.SAML`` (``verify_email_is_invited``), the
first user in a tenant becomes ADMIN and everyone else BASIC, the account is
created verified, and (in multi-tenant) the tenant is provisioned/resolved from
the email. This mirrors the existing JWT JIT path for consistency.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import HTTPException
from fastapi import Request
from fastapi import status
from fastapi_users import exceptions

from om.auth.schemas import UserCreate
from om.db.models import User
from om.server.sso.audit import SsoEntity
from om.server.sso.audit import SsoEvent
from om.server.sso.audit import sso_audit
from om.utils.logger import setup_logger

if TYPE_CHECKING:
    from om.auth.users import UserManager

logger = setup_logger()


def _reject_if_not_loginable(user: User) -> User:
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated.",
        )
    if not user.role.is_web_login():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is not permitted to sign in via SSO.",
        )
    return user


async def provision_sso_user(
    email: str,
    user_manager: "UserManager",
    request: Request | None = None,
) -> User:
    """Return the existing user for ``email`` or JIT-create one.

    Raises ``HTTPException(403)`` for deactivated / non-web-login accounts. The
    caller is expected to have already validated the assertion and extracted a
    trusted, normalized email.
    """
    from om.auth.users import generate_password

    normalized = email.strip().lower()

    # 1. Existing user — SSO is just a login.
    try:
        existing = await user_manager.get_by_email(normalized)
        return _reject_if_not_loginable(existing)
    except exceptions.UserNotExists:
        pass

    # 2. New user — JIT provision (verified; role decided by UserManager.create).
    logger.info("Provisioning user %s from SAML SSO login", normalized)
    try:
        user = await user_manager.create(
            UserCreate(
                email=normalized,
                password=generate_password(),
                is_verified=True,
            ),
            request=request,
        )
    except exceptions.UserAlreadyExists:
        # Race: another request created it between our check and insert.
        existing = await user_manager.get_by_email(normalized)
        return _reject_if_not_loginable(existing)

    sso_audit(
        SsoEvent.JIT_PROVISIONED,
        SsoEntity.USER,
        entity_id=user.id,
        actor_user_id=user.id,
        action="create",
        status="success",
        extra={"email": user.email, "role": user.role.value},
    )
    return _reject_if_not_loginable(user)
