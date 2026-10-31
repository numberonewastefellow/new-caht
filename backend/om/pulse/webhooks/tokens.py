"""The webhook URL token and signing secret.

Token format::

    single-tenant:  whk_<random>
    multi-tenant:   whk_<url-encoded-tenant>.<random>

The tenant travels in the token because a webhook call has no session or cookie to
identify it (same technique as SCIM tokens and API keys). Only the token's SHA-256 is
stored; no salt is needed because the token is high-entropy random.
"""

import base64
import hashlib
import re
import secrets
from urllib.parse import quote
from urllib.parse import unquote

from shared_configs.configs import MULTI_TENANT
from shared_configs.configs import POSTGRES_DEFAULT_SCHEMA

TOKEN_PREFIX = "whk_"
SECRET_PREFIX = "whsec_"

_TOKEN_ENTROPY_BYTES = 32
_SECRET_ENTROPY_BYTES = 32
# token_urlsafe(32) is always 43 characters
_TOKEN_SHAPE = re.compile(r"^whk_(?:[A-Za-z0-9_%\-]{1,128}\.)?[A-Za-z0-9_\-]{43}$")


def generate_token(tenant_id: str | None) -> str:
    random_part = secrets.token_urlsafe(_TOKEN_ENTROPY_BYTES)
    if not MULTI_TENANT or not tenant_id:
        return f"{TOKEN_PREFIX}{random_part}"
    return f"{TOKEN_PREFIX}{quote(tenant_id, safe='')}.{random_part}"


def has_token_shape(token: str) -> bool:
    return _TOKEN_SHAPE.match(token) is not None


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def token_last4(token: str) -> str:
    return token[-4:]


def tenant_from_token(token: str) -> str:
    """The tenant a token claims. Unverified: the lookup in that tenant's schema is
    what proves it, so another tenant's token simply isn't found."""
    if not MULTI_TENANT:
        return POSTGRES_DEFAULT_SCHEMA
    body = token[len(TOKEN_PREFIX) :]
    if "." not in body:
        return POSTGRES_DEFAULT_SCHEMA
    encoded_tenant, _, _ = body.partition(".")
    return unquote(encoded_tenant)


def generate_signing_secret() -> str:
    """A Standard Webhooks secret: whsec_ + base64 of the key bytes."""
    key = secrets.token_bytes(_SECRET_ENTROPY_BYTES)
    return f"{SECRET_PREFIX}{base64.b64encode(key).decode('ascii')}"
