"""Tenant identifier / Postgres schema-name rules.

A tenant id doubles as its Postgres schema name, so it can never be parameterized in
SQL and MUST be validated with a strict allow-list before being interpolated. Two
levels of checking are provided:

* :func:`is_safe_schema_name` — loose, injection-safe character allow-list. Used for any
  value that will reach a ``search_path`` / ``schema_translate_map`` (covers ``public``
  and operator-chosen default schemas too).
* :func:`is_tenant_id` — strict shape check for *provisioned* tenant ids (prefix + UUID or
  cloud instance id). Used before ``CREATE``/``DROP SCHEMA`` so we never touch ``public``.
"""

from __future__ import annotations

import re
import uuid

from om.tenancy.config import TENANT_ID_PREFIX

__all__ = [
    "TENANT_ID_PREFIX",
    "is_safe_schema_name",
    "is_tenant_id",
    "assert_tenant_id",
    "new_tenant_id",
]

# Injection-safe character allow-list for any schema name (broad).
_SAFE_SCHEMA_RE = re.compile(r"^[A-Za-z0-9_-]+$")

# Strict shape for a provisioned tenant id: "<prefix>" + UUID4 or "<prefix>i-<hex>"
# (cloud instance ids). Prevents CREATE/DROP from ever resolving to `public`.
_TENANT_ID_RE = re.compile(
    r"^"
    + re.escape(TENANT_ID_PREFIX)
    + r"(?:"
    + r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
    + r"|i-[0-9a-fA-F]+"
    + r")$"
)


def is_safe_schema_name(name: str) -> bool:
    """True if ``name`` is safe to interpolate as a Postgres schema identifier."""
    return bool(name) and _SAFE_SCHEMA_RE.match(name) is not None


def is_tenant_id(tenant_id: str) -> bool:
    """True if ``tenant_id`` has the strict provisioned-tenant shape."""
    return _TENANT_ID_RE.match(tenant_id) is not None


def assert_tenant_id(tenant_id: str) -> None:
    """Raise ``ValueError`` unless ``tenant_id`` is a valid provisioned tenant id."""
    if not is_tenant_id(tenant_id):
        raise ValueError(f"Invalid tenant id format: {tenant_id!r}")


def new_tenant_id() -> str:
    """Mint a fresh, well-formed tenant id."""
    return f"{TENANT_ID_PREFIX}{uuid.uuid4()}"
