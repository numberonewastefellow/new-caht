"""Self-hosted, billing-free tenancy configuration.

Standard 5: a small, dedicated config surface for this feature. All tenancy configuration
is **deployment-level and read from the environment** (no external control plane, no
Stripe, no HubSpot) — the isolation model does not need runtime-editable toggles, so there
is intentionally no separate settings table/KV. If a runtime-editable toggle is ever
wanted, back it with the shared key-value store rather than adding cloud coupling here.
"""

from __future__ import annotations

import os

from shared_configs.configs import MULTI_TENANT
from shared_configs.configs import POSTGRES_DEFAULT_SCHEMA
from shared_configs.configs import TENANT_ID_PREFIX

__all__ = [
    "MULTI_TENANT",
    "POSTGRES_DEFAULT_SCHEMA",
    "TENANT_ID_PREFIX",
    "TENANT_ADMIN_EMAILS",
    "ALLOW_ANONYMOUS_TENANT_ACCESS",
]


def _csv_env(name: str) -> frozenset[str]:
    raw = os.environ.get(name, "") or ""
    return frozenset(
        part.strip().lower() for part in raw.split(",") if part.strip()
    )


# Optional allow-list of platform-operator emails permitted to manage tenants.
# Empty => any instance ADMIN may manage tenants (self-hosted default).
TENANT_ADMIN_EMAILS: frozenset[str] = _csv_env("TENANT_ADMIN_EMAILS")

# Whether anonymous (unauthenticated) access to a tenant is permitted. Off by default;
# the legacy `tenant_anonymous_user_path` mechanism is dropped unless this is enabled.
ALLOW_ANONYMOUS_TENANT_ACCESS: bool = (
    os.environ.get("ALLOW_ANONYMOUS_TENANT_ACCESS", "").lower() == "true"
)
