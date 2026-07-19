"""Pydantic request/response models for the Rate Limits admin API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from pydantic import Field
from pydantic import model_validator

from om.db.models import RateLimitPolicy
from om.db.models import RateLimitUsage
from om.server.rate_limits.constants import RateLimitAlgorithm
from om.server.rate_limits.constants import RateLimitScope
from om.server.rate_limits.constants import SUBJECT_SCOPES
from om.server.rate_limits.constants import TENANT_WIDE_SCOPES


class RateLimitPolicyArgs(BaseModel):
    """Create/update payload for a policy. Validated so the scope and its subject agree."""

    scope: RateLimitScope
    token_budget: int = Field(ge=0, description="Budget in raw tokens.")
    period_hours: int = Field(gt=0, le=24 * 365, description="Rolling window length in hours.")
    enabled: bool = True
    algorithm: RateLimitAlgorithm = RateLimitAlgorithm.SLIDING_WINDOW
    user_id: UUID | None = None
    team_id: int | None = None

    @model_validator(mode="after")
    def _check_subject(self) -> "RateLimitPolicyArgs":
        if self.scope == RateLimitScope.USER:
            # user_id is OPTIONAL: None = per-user default (applies to every user against their own
            # usage); set = a specific-user override.
            if self.team_id is not None:
                raise ValueError("USER-scoped policy must not set team_id")
        elif self.scope == RateLimitScope.TEAM:
            if self.team_id is None:
                raise ValueError("TEAM-scoped policy requires team_id")
            if self.user_id is not None:
                raise ValueError("TEAM-scoped policy must not set user_id")
        elif self.scope in TENANT_WIDE_SCOPES:
            if self.user_id is not None or self.team_id is not None:
                raise ValueError(f"{self.scope.value}-scoped policy must not set a subject")
        return self


class RateLimitPolicyUpdateArgs(BaseModel):
    """Update payload — only the mutable fields. Scope and subject are immutable, so they are not
    accepted here (this also avoids re-running the create-time scope↔subject validation, which would
    otherwise reject a simple enable/disable toggle that doesn't resend the subject)."""

    token_budget: int = Field(ge=0)
    period_hours: int = Field(gt=0, le=24 * 365)
    enabled: bool
    algorithm: RateLimitAlgorithm = RateLimitAlgorithm.SLIDING_WINDOW


class RateLimitPolicyResponse(BaseModel):
    id: int
    scope: RateLimitScope
    token_budget: int
    period_hours: int
    enabled: bool
    algorithm: RateLimitAlgorithm
    user_id: UUID | None
    team_id: int | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_db(cls, policy: RateLimitPolicy) -> "RateLimitPolicyResponse":
        return cls(
            id=policy.id,
            scope=policy.scope,
            token_budget=policy.token_budget,
            period_hours=policy.period_hours,
            enabled=policy.enabled,
            algorithm=policy.algorithm,
            user_id=policy.user_id,
            team_id=policy.team_id,
            created_at=policy.created_at,
            updated_at=policy.updated_at,
        )


class RemainingBudgetItem(BaseModel):
    """Live budget view for a single active policy (remaining-budget API + admin gauge)."""

    policy_id: int
    scope: RateLimitScope
    subject: str
    period_hours: int
    budget: int
    used: int
    remaining: int
    reset_seconds: int


class RemainingBudgetResponse(BaseModel):
    items: list[RemainingBudgetItem]


class UsageHistoryPoint(BaseModel):
    bucket_start: datetime
    tokens_used: int
    allowed_count: int
    throttled_count: int

    @classmethod
    def from_db(cls, row: RateLimitUsage) -> "UsageHistoryPoint":
        return cls(
            bucket_start=row.bucket_start,
            tokens_used=row.tokens_used,
            allowed_count=row.allowed_count,
            throttled_count=row.throttled_count,
        )


class UsageHistoryResponse(BaseModel):
    scope: RateLimitScope
    subject: str
    points: list[UsageHistoryPoint]


# Re-exported so callers can build a subject-scope check without importing constants directly.
__all__ = [
    "RateLimitPolicyArgs",
    "RateLimitPolicyResponse",
    "RemainingBudgetItem",
    "RemainingBudgetResponse",
    "UsageHistoryPoint",
    "UsageHistoryResponse",
    "SUBJECT_SCOPES",
]
