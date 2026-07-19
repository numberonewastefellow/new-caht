"""Core SAML SSO orchestration: authorize, ACS (assertion consumer), logout.

This is the only module that drives the python3-saml toolkit. It ties together
config loading, assertion validation, email extraction, JIT provisioning, session
issuance, and the session-ledger write. Everything is tenant-scoped via the
Contract-3 facade and audited via structured logs.
"""

from __future__ import annotations

import time
from http.cookies import SimpleCookie
from typing import Any
from typing import NoReturn

from fastapi import HTTPException
from fastapi import Request
from fastapi import Response
from fastapi import status
from onelogin.saml2.auth import OneLogin_Saml2_Auth  # type: ignore[import-untyped]

from om.auth.users import auth_backend
from om.db.models import User
from om.server.sso.audit import SsoEntity
from om.server.sso.audit import SsoEvent
from om.server.sso.audit import sso_audit
from om.server.sso.config_store import load_saml_config
from om.server.sso.config_store import SamlConfigData
from om.server.sso.email import extract_email
from om.server.sso.provisioning import provision_sso_user
from om.server.sso.relay_state import sanitize_relay_state
from om.server.sso.saml_settings import build_request_dict
from om.server.sso.saml_settings import build_saml_settings
from om.server.sso.session_store import expire_saml_sessions_for_user
from om.server.sso.session_store import upsert_saml_session
from om.tenancy.context import get_current_tenant_session
from om.utils.logger import setup_logger

logger = setup_logger()


def _load_usable_config() -> SamlConfigData:
    """Load the tenant's SAML config or raise a 400 if it is not usable."""
    with get_current_tenant_session() as db_session:
        config = load_saml_config(db_session)
    if config is None or not config.is_usable():
        sso_audit(
            SsoEvent.ASSERTION_REJECTED,
            SsoEntity.SAML_CONFIG,
            action="validate",
            status="rejected",
            error="SAML SSO is not configured or disabled",
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SAML SSO is not configured.",
        )
    return config


async def build_authorize_url(request: Request, next_url: str | None) -> str:
    """SP-initiated login: return the IdP redirect URL (RelayState sanitized)."""
    config = _load_usable_config()
    settings = build_saml_settings(config)
    req = build_request_dict(
        config, get_data=dict(request.query_params), post_data={}
    )

    try:
        auth = OneLogin_Saml2_Auth(req, settings)
        return_to = sanitize_relay_state(next_url)
        authorization_url = auth.login(return_to=return_to)
    except Exception as exc:
        logger.exception("Failed to build SAML AuthnRequest")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to build SAML login request.",
        ) from exc

    sso_audit(
        SsoEvent.AUTHORIZE,
        SsoEntity.SAML_CONFIG,
        action="read",
        status="success",
    )
    return authorization_url


def _reject_assertion(reason: str) -> NoReturn:
    sso_audit(
        SsoEvent.ASSERTION_REJECTED,
        SsoEntity.SAML_SESSION,
        action="validate",
        status="rejected",
        error=reason,
    )
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="SAML assertion could not be validated.",
    )


def _extract_cookie_value(response: Response, cookie_name: str) -> str | None:
    """Pull the issued auth cookie value out of a login response's Set-Cookie."""
    for header_key, header_value in response.raw_headers:
        if header_key.decode("latin-1").lower() != "set-cookie":
            continue
        jar: SimpleCookie = SimpleCookie()
        try:
            jar.load(header_value.decode("latin-1"))
        except Exception:
            continue
        if cookie_name in jar:
            return jar[cookie_name].value
    return None


def _record_session(response: Response, user: User) -> None:
    """Best-effort write of the cookie↔user ledger row. Never breaks login."""
    try:
        cookie_name = auth_backend.transport.cookie_name  # type: ignore[attr-defined]
        cookie_value = _extract_cookie_value(response, cookie_name)
        if not cookie_value:
            logger.warning("No auth cookie found on SAML login response; skipping ledger")
            return
        with get_current_tenant_session() as db_session:
            upsert_saml_session(db_session, user.id, cookie_value)
    except Exception:
        logger.exception("Failed to persist SAML session ledger for user %s", user.id)


async def process_acs(
    request: Request,
    strategy: Any,
    user_manager: Any,
) -> Response:
    """Assertion Consumer Service: validate, provision, issue session cookie."""
    started = time.monotonic()
    config = _load_usable_config()

    # Gather bindings: POST form + any GET params (the web route normalizes GET→POST).
    post_data: dict[str, Any] = {}
    try:
        form = await request.form()
        for key in ("SAMLResponse", "RelayState"):
            if key in form and isinstance(form[key], str):
                post_data[key] = form[key]
    except Exception:
        logger.warning("Failed to read SAML ACS form body")
    get_data = dict(request.query_params)
    # GET (HTTP-Redirect) fallback: python3-saml only reads SAMLResponse/RelayState
    # from post_data, so promote them if they only arrived as query params.
    for key in ("SAMLResponse", "RelayState"):
        if key not in post_data and key in get_data:
            post_data[key] = get_data[key]
    relay_raw = post_data.get("RelayState")

    if "SAMLResponse" not in post_data:
        _reject_assertion("missing SAMLResponse")

    settings = build_saml_settings(config)
    req = build_request_dict(config, get_data=get_data, post_data=post_data)

    # Validate the assertion (strict mode: signature, conditions, destination,
    # audience, timestamps). request_id=None accepts IdP-initiated (unsolicited) SSO.
    try:
        auth = OneLogin_Saml2_Auth(req, settings)
        auth.process_response()
    except Exception as exc:
        logger.warning("SAML process_response raised: %s", exc)
        _reject_assertion(f"process_response error: {type(exc).__name__}")

    errors = auth.get_errors()
    if errors or not auth.is_authenticated():
        _reject_assertion(
            f"errors={errors} reason={auth.get_last_error_reason()}"
        )

    attributes = auth.get_attributes()
    name_id = auth.get_nameid()
    email = extract_email(attributes, name_id, config)
    if not email:
        _reject_assertion("no usable email in assertion")
    assert email is not None  # for type-checkers; _reject_assertion raises otherwise

    # Sanitized here (defense-in-depth + recorded in the audit log); the web ACS
    # route performs the actual redirect and re-validates independently.
    relay_state = sanitize_relay_state(relay_raw)

    user = await provision_sso_user(email, user_manager, request)

    response = await auth_backend.login(strategy, user)
    await user_manager.on_after_login(user, request, response)

    _record_session(response, user)

    sso_audit(
        SsoEvent.LOGIN,
        SsoEntity.USER,
        entity_id=user.id,
        actor_user_id=user.id,
        action="login",
        status="success",
        duration_ms=(time.monotonic() - started) * 1000.0,
        extra={"email": user.email, "relay_state": relay_state},
    )
    return response


async def process_logout(
    request: Request,
    user: User | None,
    strategy: Any,
) -> Response:
    """SP logout: expire the SAML session ledger + clear the auth cookie."""
    started = time.monotonic()
    cookie_name = auth_backend.transport.cookie_name  # type: ignore[attr-defined]
    token = request.cookies.get(cookie_name)

    if user is not None:
        try:
            with get_current_tenant_session() as db_session:
                expire_saml_sessions_for_user(db_session, user.id)
        except Exception:
            logger.exception("Failed to expire SAML session ledger for %s", user.id)

    if user is not None and token is not None:
        response = await auth_backend.logout(strategy, user, token)
    else:
        try:
            response = await auth_backend.transport.get_logout_response()
        except Exception:
            response = Response(status_code=status.HTTP_204_NO_CONTENT)

    sso_audit(
        SsoEvent.LOGOUT,
        SsoEntity.USER,
        entity_id=getattr(user, "id", None),
        actor_user_id=getattr(user, "id", None),
        action="logout",
        status="success",
        duration_ms=(time.monotonic() - started) * 1000.0,
    )
    return response
