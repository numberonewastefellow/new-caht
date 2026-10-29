"""Tenant-tracking ASGI middleware (clean-room).

Every inbound HTTP request is resolved to exactly one tenant and that tenant id is
bound into :data:`CURRENT_TENANT_ID_CONTEXTVAR` for the lifetime of the request. All
tenant-scoped DB sessions (Contract 3) read that contextvar, so binding it here is what
keeps one tenant's request from ever touching another tenant's Postgres schema.

Design choices (see ``README.md`` for the write-up + sources):

* **Pure ASGI middleware**, not ``BaseHTTPMiddleware``. A ``ContextVar`` set inside a
  ``BaseHTTPMiddleware.dispatch`` does not reliably propagate to the route handler
  (Starlette runs the downstream app in a child anyio task). A raw ASGI middleware sets
  the contextvar in the *same* task that runs the endpoint, so propagation is guaranteed,
  and the token is always reset in a ``finally`` block.
* **Resolution order** (first match wins): API-key / PAT header → session auth token
  (Redis) → anonymous-user cookie (only when anonymous access is enabled) → explicit
  tenant cookie → default schema. Unauthenticated requests fall through to the default
  schema, which holds no tenant data, so tenant-scoped endpoints reject them downstream.
* **Schema-name validation**. A tenant id doubles as a Postgres schema name and is
  interpolated (via ``schema_translate_map``) into SQL, so any externally supplied value
  is validated against a strict allow-list before it is trusted; a malformed value is
  rejected with ``400`` rather than silently routed anywhere.
"""

from __future__ import annotations

import logging

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp
from starlette.types import Receive
from starlette.types import Scope
from starlette.types import Send

from om.auth.users import decode_anonymous_user_jwt_token
from om.auth.utils import extract_tenant_from_auth_header
from om.configs.constants import ANONYMOUS_USER_COOKIE_NAME
from om.configs.constants import TENANT_ID_COOKIE_NAME
from om.db.engine.sql_engine import is_valid_schema_name
from om.redis.redis_pool import retrieve_auth_token_data_from_redis
from om.tenancy.config import ALLOW_ANONYMOUS_TENANT_ACCESS
from om.tenancy.config import POSTGRES_DEFAULT_SCHEMA
from om.utils.logger import setup_logger
from shared_configs.contextvars import CURRENT_TENANT_ID_CONTEXTVAR

__all__ = [
    "TenantTrackingMiddleware",
    "add_tenant_tracking_middleware",
    "resolve_tenant_id",
    "InvalidTenantError",
]

_module_logger = setup_logger()

# The key under which the session auth token (stored in Redis) carries the tenant id.
_AUTH_TOKEN_TENANT_KEY = "tenant_id"


class InvalidTenantError(Exception):
    """Raised when a request supplies a tenant id that is not a valid schema name."""

    def __init__(self, raw_value: str) -> None:
        super().__init__(f"Invalid tenant identifier: {raw_value!r}")
        self.raw_value = raw_value


def _validated(candidate: str) -> str:
    """Return ``candidate`` if it is a safe schema name, else raise ``InvalidTenantError``."""
    if not is_valid_schema_name(candidate):
        raise InvalidTenantError(candidate)
    return candidate


async def resolve_tenant_id(request: Request) -> str:
    """Resolve the tenant for ``request`` following the documented precedence.

    Raises :class:`InvalidTenantError` if a supplied identifier is not a valid schema
    name. Falls back to the default schema when nothing identifies a tenant.
    """
    # 1. API key / Personal Access Token (bearer header). Cheapest + most explicit.
    header_tenant = extract_tenant_from_auth_header(request)
    if header_tenant:
        return _validated(header_tenant)

    # 2. Logged-in session: the auth token in Redis carries the tenant it was minted for.
    try:
        token_data = await retrieve_auth_token_data_from_redis(request)
    except Exception:
        # Redis hiccups must not 500 the whole request; treat as "no session tenant".
        _module_logger.exception("Failed to read auth token data while resolving tenant")
        token_data = None
    if token_data:
        session_tenant = token_data.get(_AUTH_TOKEN_TENANT_KEY)
        if session_tenant:
            return _validated(str(session_tenant))

    # 3. Anonymous access — only honoured when the operator has explicitly enabled it.
    if ALLOW_ANONYMOUS_TENANT_ACCESS:
        anon_cookie = request.cookies.get(ANONYMOUS_USER_COOKIE_NAME)
        if anon_cookie:
            try:
                payload = decode_anonymous_user_jwt_token(anon_cookie)
            except Exception:
                _module_logger.debug("Ignoring undecodable anonymous-user cookie")
            else:
                anon_tenant = payload.get(_AUTH_TOKEN_TENANT_KEY)
                if anon_tenant:
                    return _validated(str(anon_tenant))

    # 4. Explicit tenant cookie (front-end workaround for flows without a session token).
    cookie_tenant = request.cookies.get(TENANT_ID_COOKIE_NAME)
    if cookie_tenant:
        return _validated(cookie_tenant)

    # 5. Nothing identified a tenant: the default schema (holds no per-tenant data).
    return POSTGRES_DEFAULT_SCHEMA


class TenantTrackingMiddleware:
    """Bind the resolved tenant id into the request-scoped contextvar."""

    def __init__(self, app: ASGIApp, logger: logging.Logger | None = None) -> None:
        self.app = app
        self.logger = logger or _module_logger

    async def __call__(
        self, scope: Scope, receive: Receive, send: Send
    ) -> None:
        # Only HTTP requests carry a tenant; pass websockets/lifespan straight through.
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        try:
            tenant_id = await resolve_tenant_id(request)
        except InvalidTenantError as exc:
            self.logger.warning(f"Rejecting request with {exc}")
            response = JSONResponse(
                status_code=400, content={"detail": "Invalid tenant identifier"}
            )
            await response(scope, receive, send)
            return

        token = CURRENT_TENANT_ID_CONTEXTVAR.set(tenant_id)
        try:
            await self.app(scope, receive, send)
        finally:
            # Always unwind so the contextvar never leaks into a pooled worker task.
            CURRENT_TENANT_ID_CONTEXTVAR.reset(token)


def add_tenant_tracking_middleware(
    app: ASGIApp, logger: logging.Logger | None = None
) -> None:
    """Register the tenant-tracking middleware on a FastAPI/Starlette application.

    Kept as a thin function so ``main.py`` wires tenancy the same way it wires its other
    middleware, and so WS-A's removal of the license-enforcement middleware touches an
    adjacent, clearly-owned block.
    """
    # ``add_middleware`` is only defined on Starlette/FastAPI apps; typed as ASGIApp for
    # the class above, so access it dynamically.
    app.add_middleware(TenantTrackingMiddleware, logger=logger)  # type: ignore[attr-defined]
    (logger or _module_logger).info("Registered tenant-tracking middleware")
