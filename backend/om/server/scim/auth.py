"""SCIM bearer-token generation, hashing and request authentication.

Tokens are opaque, high-entropy secrets. Only their SHA-256 hash is stored; the
raw token is shown to the admin exactly once. To make the SCIM API self-routing
in multi-tenant mode (IdP requests carry no session/cookie), the tenant id is
embedded in the token itself — the same technique the API-key subsystem uses —
so :func:`verify_scim_token` can resolve the tenant, bind the request to that
tenant's Postgres schema, and verify the token against the per-tenant
``scim_token`` table (Contract 3).

Token format::

    single-tenant:  scim_<random>
    multi-tenant:   scim_<url-encoded-tenant>.<random>

``verify_scim_token`` is the auth dependency guarding every provisioning route;
``auth_check.check_router_auth`` recognises it as a valid auth dependency.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from collections.abc import Generator
from dataclasses import dataclass
from urllib.parse import quote
from urllib.parse import unquote

from fastapi import Request
from sqlalchemy.orm import Session

from om.db.engine.sql_engine import is_valid_schema_name
from om.server.scim.constants import SCIM_TOKEN_ENTROPY_BYTES
from om.server.scim.constants import SCIM_TOKEN_PREFIX
from om.server.scim.errors import ScimError
from om.tenancy.context import CURRENT_TENANT_ID_CONTEXTVAR
from om.tenancy.context import get_tenant_session
from shared_configs.configs import MULTI_TENANT
from shared_configs.configs import POSTGRES_DEFAULT_SCHEMA


@dataclass
class ScimContext:
    """Authenticated SCIM request context handed to every provisioning route."""

    db: Session
    tenant_id: str
    token_id: int
    # The admin user that created the token — used as the actor in audit logs.
    actor_user_id: str


# --------------------------------------------------------------------------
# Token generation / hashing / display
# --------------------------------------------------------------------------
def generate_scim_token(tenant_id: str | None = None) -> str:
    """Mint a new raw SCIM token (CSPRNG). Tenant is embedded in MT mode."""
    random_part = secrets.token_urlsafe(SCIM_TOKEN_ENTROPY_BYTES)
    if not MULTI_TENANT or not tenant_id:
        return f"{SCIM_TOKEN_PREFIX}{random_part}"
    return f"{SCIM_TOKEN_PREFIX}{quote(tenant_id, safe='')}.{random_part}"


def hash_scim_token(raw_token: str) -> str:
    """SHA-256 hex digest of a raw token (the DB lookup key).

    No salt is needed: tokens are randomly generated with high entropy, so
    collisions are infeasible (same rationale as the API-key subsystem).
    """
    if not raw_token.startswith(SCIM_TOKEN_PREFIX):
        raise ScimError.unauthorized()
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def build_scim_token_display(raw_token: str) -> str:
    """Masked, last-4 form for the admin UI, e.g. ``scim_****ab12``."""
    return f"{SCIM_TOKEN_PREFIX}****{raw_token[-4:]}"


def parse_tenant_from_token(raw_token: str) -> str:
    """Recover the tenant schema embedded in a token (or the default schema)."""
    if not MULTI_TENANT:
        return POSTGRES_DEFAULT_SCHEMA
    body = raw_token[len(SCIM_TOKEN_PREFIX) :]
    if "." not in body:
        # No tenant segment — only valid against the default schema.
        return POSTGRES_DEFAULT_SCHEMA
    encoded_tenant, _, _ = body.partition(".")
    return unquote(encoded_tenant)


def tokens_match(presented_hash: str, stored_hash: str) -> bool:
    """Constant-time hash comparison (defence in depth over the DB lookup)."""
    return hmac.compare_digest(presented_hash, stored_hash)


# --------------------------------------------------------------------------
# Request authentication
# --------------------------------------------------------------------------
def _extract_bearer_token(request: Request) -> str:
    header = request.headers.get("Authorization") or request.headers.get(
        "authorization"
    )
    if not header:
        raise ScimError.unauthorized("Missing Authorization header.")
    scheme, _, credential = header.partition(" ")
    if scheme.lower() != "bearer" or not credential.strip():
        raise ScimError.unauthorized("Authorization header must be a Bearer token.")
    return credential.strip()


def verify_scim_token(request: Request) -> Generator[ScimContext, None, None]:
    """FastAPI dependency: authenticate a SCIM request and bind its tenant.

    Yields a :class:`ScimContext` carrying a tenant-scoped DB session. On any
    failure a :class:`ScimError` (401) is raised, which :class:`ScimRoute`
    renders as a SCIM error body.
    """
    raw_token = _extract_bearer_token(request)
    if not raw_token.startswith(SCIM_TOKEN_PREFIX):
        raise ScimError.unauthorized()

    tenant_id = parse_tenant_from_token(raw_token)
    if not is_valid_schema_name(tenant_id):
        raise ScimError.unauthorized()

    presented_hash = hash_scim_token(raw_token)

    # Bind the request to the token's tenant schema for its whole lifetime.
    contextvar_token = CURRENT_TENANT_ID_CONTEXTVAR.set(tenant_id)
    try:
        with get_tenant_session(tenant_id=tenant_id) as db:
            # Local import: repository imports pull in the ORM models.
            from om.db.scim import ScimRepository

            repo = ScimRepository(db)
            # The tenant schema is already validated (is_valid_schema_name above),
            # so the lookup cannot raise the session layer's schema HTTPException.
            token_row = repo.get_active_token_by_hash(presented_hash)
            if token_row is None or not tokens_match(
                presented_hash, token_row.hashed_token
            ):
                raise ScimError.unauthorized()

            repo.touch_token_last_used(token_row.id)
            db.commit()

            # NOTE: the broad try only guards pre-yield auth work; exceptions
            # thrown back in during teardown propagate untouched.
            yield ScimContext(
                db=db,
                tenant_id=tenant_id,
                token_id=token_row.id,
                actor_user_id=str(token_row.created_by),
            )
    finally:
        CURRENT_TENANT_ID_CONTEXTVAR.reset(contextvar_token)
