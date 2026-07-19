"""Enums, namespaces, and key/subject helpers for the rate-limits subsystem.

Kept dependency-light so both the engine, the repository, and the API models can import it
without cycles.
"""

from enum import Enum
from uuid import UUID

# The DB-facing enums live in om.configs.constants (house pattern, mirrors
# TokenRateLimitScope) so om.db.models never imports from the server layer. They are
# re-exported here so the rest of this module has a single import site.
#
# RateLimitScope: in the multi-tenant, per-schema deployment every table already lives
# inside the tenant's Postgres schema, so GLOBAL and TENANT are both "the whole tenant"
# (TENANT is the recommended, explicitly tenant-aware label; GLOBAL is kept for parity and
# can be used as a second, independent org-wide policy).
#
# RateLimitAlgorithm: only SLIDING_WINDOW is implemented (see engine.py). The column is a
# forward-compatible config field (stored + surfaced in the API/UI) reserved so further strategies
# can be added without a schema migration; the engine implements SLIDING_WINDOW only today.
from om.configs.constants import RateLimitAlgorithm
from om.configs.constants import RateLimitScope

__all__ = [
    "RateLimitAlgorithm",
    "RateLimitScope",
    "RateLimitDecision",
    "SUBJECT_SCOPES",
    "TENANT_WIDE_SCOPES",
    "REDIS_RATELIMIT_NAMESPACE",
    "SECONDS_PER_HOUR",
    "subject_key",
]


class RateLimitDecision(str, Enum):
    """Outcome of an enforcement check — used for metrics/log labels."""

    ALLOWED = "allowed"
    THROTTLED = "throttled"


# Scopes that address a specific subject (need a non-null subject id).
SUBJECT_SCOPES: frozenset[RateLimitScope] = frozenset(
    {RateLimitScope.TEAM, RateLimitScope.USER}
)
# Scopes that cover the entire tenant schema (subject id is always null).
TENANT_WIDE_SCOPES: frozenset[RateLimitScope] = frozenset(
    {RateLimitScope.GLOBAL, RateLimitScope.TENANT}
)

# Redis key namespace for live sliding-window counters. The tenant id is prepended
# separately (see engine.py) so keys are isolated per tenant.
REDIS_RATELIMIT_NAMESPACE = "om:ratelimit:v1"

SECONDS_PER_HOUR = 3600


def subject_key(
    scope: RateLimitScope,
    user_id: UUID | None,
    team_id: int | None,
) -> str:
    """Stable string that identifies a policy's subject bucket.

    Tenant-wide scopes have no subject, so the scope name itself is the bucket. Subject scopes
    key on their id. This value is used both as the Redis key component and the persisted
    ``rate_limit_usage.subject_key``, so enforcement and history always agree.
    """
    if scope in TENANT_WIDE_SCOPES:
        return scope.value
    if scope == RateLimitScope.USER:
        if user_id is None:
            raise ValueError("USER-scoped policy requires a user_id")
        return f"user:{user_id}"
    if scope == RateLimitScope.TEAM:
        if team_id is None:
            raise ValueError("TEAM-scoped policy requires a team_id")
        return f"team:{team_id}"
    raise ValueError(f"Unhandled scope: {scope}")
