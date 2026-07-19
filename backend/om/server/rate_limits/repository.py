"""Persistence for rate-limit policies + the durable usage roll-up.

Kept as a thin repository over a tenant-scoped ``Session`` (Standard 10: repositories separate
from services). All queries run inside the caller's tenant schema, so no explicit tenant filter
is needed — isolation is enforced by the schema binding (Contract 3).
"""

from collections.abc import Sequence
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from uuid import UUID

from sqlalchemy import and_
from sqlalchemy import func
from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from om.db.models import RateLimitPolicy
from om.db.models import RateLimitUsage
from om.server.rate_limits.constants import RateLimitAlgorithm
from om.server.rate_limits.constants import RateLimitScope


def _hour_bucket(moment: datetime) -> datetime:
    """Truncate a timestamp to the start of its UTC hour (the roll-up granularity)."""
    moment = moment.astimezone(timezone.utc)
    return moment.replace(minute=0, second=0, microsecond=0)


class RateLimitRepository:
    def __init__(self, db_session: Session) -> None:
        self._db = db_session

    # ---- policy CRUD -------------------------------------------------------------------

    def create_policy(
        self,
        *,
        scope: RateLimitScope,
        token_budget: int,
        period_hours: int,
        algorithm: RateLimitAlgorithm = RateLimitAlgorithm.SLIDING_WINDOW,
        enabled: bool = True,
        user_id: UUID | None = None,
        team_id: int | None = None,
    ) -> RateLimitPolicy:
        policy = RateLimitPolicy(
            scope=scope,
            token_budget=token_budget,
            period_hours=period_hours,
            algorithm=algorithm,
            enabled=enabled,
            user_id=user_id,
            team_id=team_id,
        )
        self._db.add(policy)
        self._db.commit()
        self._db.refresh(policy)
        return policy

    def get_policy(self, policy_id: int) -> RateLimitPolicy | None:
        return self._db.get(RateLimitPolicy, policy_id)

    def list_policies(
        self, scope: RateLimitScope | None = None, enabled_only: bool = False
    ) -> Sequence[RateLimitPolicy]:
        stmt = select(RateLimitPolicy)
        if scope is not None:
            stmt = stmt.where(RateLimitPolicy.scope == scope)
        if enabled_only:
            stmt = stmt.where(RateLimitPolicy.enabled.is_(True))
        stmt = stmt.order_by(RateLimitPolicy.created_at.desc())
        return self._db.scalars(stmt).all()

    def list_enabled_for_subjects(
        self, user_id: UUID, team_ids: Sequence[int]
    ) -> Sequence[RateLimitPolicy]:
        """Every enabled policy that applies to a request by ``user_id`` in ``team_ids``.

        That is: the two tenant-wide scopes; any USER policy that is either this user's specific
        override (``user_id == user_id``) or the per-user **default** (``scope == USER`` with
        ``user_id IS NULL``, enforced against each requesting user); and any TEAM policy for a team
        the user belongs to. The enforcement layer checks all of them.
        """
        conditions = [
            RateLimitPolicy.scope.in_(
                [RateLimitScope.GLOBAL, RateLimitScope.TENANT]
            ),
            RateLimitPolicy.user_id == user_id,
            and_(
                RateLimitPolicy.scope == RateLimitScope.USER,
                RateLimitPolicy.user_id.is_(None),
            ),
        ]
        if team_ids:
            conditions.append(RateLimitPolicy.team_id.in_(list(team_ids)))

        stmt = (
            select(RateLimitPolicy)
            .where(RateLimitPolicy.enabled.is_(True))
            .where(or_(*conditions))
        )
        return self._db.scalars(stmt).all()

    def update_policy(
        self,
        policy_id: int,
        *,
        token_budget: int,
        period_hours: int,
        enabled: bool,
        algorithm: RateLimitAlgorithm | None = None,
    ) -> RateLimitPolicy:
        policy = self._db.get(RateLimitPolicy, policy_id)
        if policy is None:
            raise ValueError(f"RateLimitPolicy {policy_id} not found")
        policy.token_budget = token_budget
        policy.period_hours = period_hours
        policy.enabled = enabled
        if algorithm is not None:
            policy.algorithm = algorithm
        self._db.commit()
        self._db.refresh(policy)
        return policy

    def delete_policy(self, policy_id: int) -> None:
        policy = self._db.get(RateLimitPolicy, policy_id)
        if policy is None:
            raise ValueError(f"RateLimitPolicy {policy_id} not found")
        self._db.delete(policy)
        self._db.commit()

    def any_enabled_policy_exists(self) -> bool:
        return (
            self._db.scalar(
                select(RateLimitPolicy.id).where(RateLimitPolicy.enabled.is_(True))
            )
            is not None
        )

    # ---- usage roll-up -----------------------------------------------------------------

    def increment_usage(
        self,
        *,
        scope: RateLimitScope,
        subject_key: str,
        tokens: int,
        allowed: int = 0,
        throttled: int = 0,
        moment: datetime | None = None,
    ) -> None:
        """Atomically add to the current hour's roll-up row (UPSERT; no read-modify-write race)."""
        bucket = _hour_bucket(moment or datetime.now(timezone.utc))
        stmt = (
            pg_insert(RateLimitUsage)
            .values(
                scope=scope,
                subject_key=subject_key,
                bucket_start=bucket,
                tokens_used=tokens,
                allowed_count=allowed,
                throttled_count=throttled,
            )
            .on_conflict_do_update(
                constraint="uq_rate_limit_usage_scope_subject_bucket",
                set_={
                    "tokens_used": RateLimitUsage.tokens_used + tokens,
                    "allowed_count": RateLimitUsage.allowed_count + allowed,
                    "throttled_count": RateLimitUsage.throttled_count + throttled,
                },
            )
        )
        self._db.execute(stmt)
        self._db.commit()

    def sum_recent_tokens(
        self, *, scope: RateLimitScope, subject_key: str, period_hours: int
    ) -> int:
        """Total tokens recorded for a subject over the last ``period_hours`` (roll-up).

        Used only for cold-start reconciliation of the Redis counters — a conservative figure.
        """
        since = datetime.now(timezone.utc) - timedelta(hours=period_hours)
        total = self._db.scalar(
            select(func.coalesce(func.sum(RateLimitUsage.tokens_used), 0)).where(
                RateLimitUsage.scope == scope,
                RateLimitUsage.subject_key == subject_key,
                RateLimitUsage.bucket_start >= _hour_bucket(since),
            )
        )
        return int(total or 0)

    def fetch_history(
        self, *, scope: RateLimitScope, subject_key: str, hours: int
    ) -> Sequence[RateLimitUsage]:
        """Hourly roll-up rows for the last ``hours`` — backs the admin history chart."""
        since = _hour_bucket(datetime.now(timezone.utc) - timedelta(hours=hours))
        stmt = (
            select(RateLimitUsage)
            .where(
                RateLimitUsage.scope == scope,
                RateLimitUsage.subject_key == subject_key,
                RateLimitUsage.bucket_start >= since,
            )
            .order_by(RateLimitUsage.bucket_start.asc())
        )
        return self._db.scalars(stmt).all()
