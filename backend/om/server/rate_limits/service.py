"""Rate-limit orchestration service.

Framework-agnostic (no FastAPI here — the dependency maps the domain exception to HTTP 429). Ties
the sliding-window engine, the durable roll-up repository, team resolution, metrics, and structured
logs together, and implements the fail-open policy on engine errors.
"""

from dataclasses import dataclass
from uuid import UUID

from redis import RedisError
from sqlalchemy.orm import Session

from om.db.api_key import is_api_key_email_address
from om.db.models import ChatSession
from om.db.models import RateLimitPolicy
from om.db.models import User
from om.redis.redis_pool import get_redis_client
from om.server.rate_limits._teams import team_ids_for_user
from om.server.rate_limits._tenancy import get_current_tenant_id
from om.server.rate_limits._tenancy import get_current_tenant_session
from om.server.rate_limits.cache import policy_exists
from om.server.rate_limits.api_models import RemainingBudgetItem
from om.server.rate_limits.constants import RateLimitDecision
from om.server.rate_limits.constants import RateLimitScope
from om.server.rate_limits.constants import subject_key
from om.server.rate_limits.constants import TENANT_WIDE_SCOPES
from om.server.rate_limits.engine import RateLimiterEngine
from om.server.rate_limits.engine import WindowMath
from om.server.rate_limits.metrics import log_ratelimit_event
from om.server.rate_limits.metrics import observe_check
from om.server.rate_limits.metrics import observe_engine_error
from om.server.rate_limits.metrics import observe_recorded_tokens
from om.server.rate_limits.metrics import observe_remaining_budget
from om.server.rate_limits.metrics import Stopwatch
from om.server.rate_limits.repository import RateLimitRepository


class RateLimitExceededError(Exception):
    """Raised by ``check`` when an applicable policy is over budget. Mapped to HTTP 429."""

    def __init__(
        self,
        *,
        scope: RateLimitScope,
        subject: str,
        budget: int,
        used: int,
        reset_seconds: int,
        period_hours: int,
    ) -> None:
        self.scope = scope
        self.subject = subject
        self.budget = budget
        self.used = used
        self.remaining = 0
        self.reset_seconds = reset_seconds
        self.period_hours = period_hours
        super().__init__(
            f"Token budget exceeded for {scope.value} scope "
            f"({used}/{budget} tokens over {period_hours}h). "
            f"Try again in ~{reset_seconds}s."
        )


@dataclass
class _Evaluation:
    policy: RateLimitPolicy
    subject: str
    used: int
    remaining: int
    reset_seconds: int


class RateLimitService:
    def __init__(
        self,
        db_session: Session,
        tenant_id: str,
        engine: RateLimiterEngine,
    ) -> None:
        self._db = db_session
        self._tenant_id = tenant_id
        self._engine = engine
        self._repo = RateLimitRepository(db_session)

    # ---- enforcement -------------------------------------------------------------------

    def _applicable_policies(self, user: User | None) -> list[RateLimitPolicy]:
        """Enabled policies that govern a request by ``user`` (``None`` = anonymous/system).

        Anonymous users and API keys are only subject to tenant-wide policies (they have no team
        membership and no meaningful per-user identity for budgeting) — mirrors the prior behaviour.
        """
        if user is None or user.is_anonymous or is_api_key_email_address(user.email):
            return [
                p
                for p in self._repo.list_policies(enabled_only=True)
                if p.scope in TENANT_WIDE_SCOPES
            ]
        team_ids = team_ids_for_user(self._db, user.id)
        return list(self._repo.list_enabled_for_subjects(user.id, team_ids))

    def _subject_for(
        self, policy: RateLimitPolicy, requesting_user_id: UUID | None
    ) -> str:
        """Effective counter subject for a policy given who is making the request.

        A per-user *default* policy (``scope == USER``, ``user_id is None``) is enforced against each
        requesting user, so its subject is the requesting user — not the policy. Every other policy
        addresses a fixed subject.
        """
        if policy.scope == RateLimitScope.USER and policy.user_id is None:
            return f"user:{requesting_user_id}"
        return subject_key(policy.scope, policy.user_id, policy.team_id)

    def _evaluate(
        self, policy: RateLimitPolicy, requesting_user_id: UUID | None
    ) -> _Evaluation | None:
        """Read the live estimate for one policy. Returns None on engine failure (fail-open)."""
        subject = self._subject_for(policy, requesting_user_id)
        try:
            used = self._engine.estimate_used(subject, policy.period_hours)
        except RedisError:
            observe_engine_error("estimate")
            log_ratelimit_event(
                event="ratelimit.allowed",
                action="check",
                status="engine_error_fail_open",
                tenant_id=self._tenant_id,
                entity_id=policy.id,
                error="redis_unavailable",
            )
            return None
        remaining = max(0, policy.token_budget - used)
        reset_seconds = WindowMath.compute(
            policy.period_hours, RateLimiterEngine._now_ms()
        ).reset_seconds
        return _Evaluation(
            policy=policy,
            subject=subject,
            used=used,
            remaining=remaining,
            reset_seconds=reset_seconds,
        )

    @staticmethod
    def _publish_scope_gauges(evaluations: "list[_Evaluation]") -> None:
        """Set the per-scope remaining-budget gauge to the tightest value seen for each scope."""
        min_by_scope: dict[str, int] = {}
        for e in evaluations:
            scope = e.policy.scope.value
            min_by_scope[scope] = min(
                min_by_scope.get(scope, e.remaining), e.remaining
            )
        for scope, remaining in min_by_scope.items():
            observe_remaining_budget(scope, remaining)

    def check(self, user: User) -> None:
        """Enforce every applicable policy. Raises ``RateLimitExceededError`` if any is over budget."""
        watch = Stopwatch()
        policies = self._applicable_policies(user)
        if not policies:
            return

        requesting_user_id = None if user.is_anonymous else user.id
        evaluations = [
            e
            for e in (self._evaluate(p, requesting_user_id) for p in policies)
            if e is not None
        ]
        self._publish_scope_gauges(evaluations)
        tripped = [e for e in evaluations if e.used >= e.policy.token_budget]

        if tripped:
            # Reject on the most restrictive breached policy (least remaining, longest reset).
            worst = min(tripped, key=lambda e: (e.remaining, -e.reset_seconds))
            observe_check(worst.policy.scope.value, RateLimitDecision.THROTTLED)
            self._safe_increment_throttle(worst.policy.scope, worst.subject)
            log_ratelimit_event(
                event="ratelimit.throttled",
                entity="request",
                action="check",
                status="throttled",
                tenant_id=self._tenant_id,
                actor_user_id=str(user.id) if not user.is_anonymous else None,
                entity_id=worst.policy.id,
                duration_ms=watch.elapsed_ms(),
                remaining_budget=0,
                scope=worst.policy.scope.value,
            )
            raise RateLimitExceededError(
                scope=worst.policy.scope,
                subject=worst.subject,
                budget=worst.policy.token_budget,
                used=worst.used,
                reset_seconds=worst.reset_seconds,
                period_hours=worst.policy.period_hours,
            )

        # Allowed. Log one line with the tightest remaining budget across policies.
        min_remaining = min((e.remaining for e in evaluations), default=None)
        for e in evaluations:
            observe_check(e.policy.scope.value, RateLimitDecision.ALLOWED)
        log_ratelimit_event(
            event="ratelimit.allowed",
            entity="request",
            action="check",
            status="allowed",
            tenant_id=self._tenant_id,
            actor_user_id=str(user.id) if not user.is_anonymous else None,
            duration_ms=watch.elapsed_ms(),
            remaining_budget=min_remaining,
        )

    def _safe_increment_throttle(
        self, scope: RateLimitScope, subject: str
    ) -> None:
        try:
            self._repo.increment_usage(
                scope=scope, subject_key=subject, tokens=0, throttled=1
            )
        except Exception:
            log_ratelimit_event(
                event="ratelimit.throttled",
                action="rollup",
                status="rollup_error",
                tenant_id=self._tenant_id,
                error="rollup_increment_failed",
            )

    # ---- recording ---------------------------------------------------------------------

    def record(self, user: User | None, tokens: int) -> None:
        """Record ``tokens`` consumed against every applicable policy's counters + the roll-up.

        Best-effort: recording failures never propagate to the caller (the request already
        succeeded). Increments each policy's live Redis counter (per subject+period) and the durable
        per-subject hourly roll-up once per distinct subject.
        """
        if tokens <= 0:
            return
        try:
            policies = self._applicable_policies(user)
        except Exception:
            observe_engine_error("record_resolve")
            return
        if not policies:
            return

        requesting_user_id = None if (user is None or user.is_anonymous) else user.id
        recorded_subjects: set[tuple[str, str]] = set()
        for policy in policies:
            subject = self._subject_for(policy, requesting_user_id)
            try:
                self._engine.record_usage(subject, policy.period_hours, tokens)
            except RedisError:
                observe_engine_error("record")

            # Roll-up + tokens-recorded metric are per (scope, subject) — count once even if
            # several policies (different windows) share the same subject, so we don't multiply the
            # recorded-token total by the number of windows.
            key = (policy.scope.value, subject)
            if key not in recorded_subjects:
                recorded_subjects.add(key)
                observe_recorded_tokens(policy.scope.value, tokens)
                try:
                    self._repo.increment_usage(
                        scope=policy.scope,
                        subject_key=subject,
                        tokens=tokens,
                        allowed=1,
                    )
                except Exception:
                    observe_engine_error("rollup")

    # ---- observability views -----------------------------------------------------------

    def remaining_budget(self) -> list[RemainingBudgetItem]:
        """Live remaining-budget for every enabled policy (admin observability API + gauge)."""
        items: list[RemainingBudgetItem] = []
        min_by_scope: dict[str, int] = {}
        for policy in self._repo.list_policies(enabled_only=True):
            is_per_user_default = (
                policy.scope == RateLimitScope.USER and policy.user_id is None
            )
            if is_per_user_default:
                # A per-user default has one live counter *per user*, so there is no single
                # org-wide "used" value to read — show it as a template (budget only).
                subject = "user:(per-user default)"
                used = 0
            else:
                subject = subject_key(policy.scope, policy.user_id, policy.team_id)
                try:
                    used = self._engine.estimate_used(subject, policy.period_hours)
                except RedisError:
                    observe_engine_error("estimate")
                    used = 0
            remaining = max(0, policy.token_budget - used)
            reset_seconds = WindowMath.compute(
                policy.period_hours, RateLimiterEngine._now_ms()
            ).reset_seconds
            scope = policy.scope.value
            min_by_scope[scope] = min(min_by_scope.get(scope, remaining), remaining)
            items.append(
                RemainingBudgetItem(
                    policy_id=policy.id,
                    scope=policy.scope,
                    subject=subject,
                    period_hours=policy.period_hours,
                    budget=policy.token_budget,
                    used=used,
                    remaining=remaining,
                    reset_seconds=reset_seconds,
                )
            )
        for scope, remaining in min_by_scope.items():
            observe_remaining_budget(scope, remaining)
        return items


def build_rate_limit_service(db_session: Session) -> RateLimitService:
    """Construct a service bound to the current tenant (Contract 3) + tenant Redis client."""
    tenant_id = get_current_tenant_id()
    redis_client = get_redis_client(tenant_id=tenant_id)
    engine = RateLimiterEngine(redis_client, tenant_id)
    return RateLimitService(db_session, tenant_id, engine)


def record_chat_message_tokens(
    db_session: Session,
    chat_session_id: UUID,
    token_count: int | None,
) -> None:
    """Best-effort recording hook, called from ``create_new_chat_message``.

    Contains ALL the coupling in one place so the DB helper only imports this single function. Gated
    by the per-tenant existence cache so it is a near-no-op when no policy is configured (preserving
    the "no latency when unconfigured" property). Never raises — a recording failure must not break
    message persistence.
    """
    if not token_count or token_count <= 0:
        return
    try:
        tenant_id = get_current_tenant_id()
        # Read-only, TTL-cached — cheap and non-mutating on the caller's in-flight transaction.
        if not policy_exists(tenant_id, db_session):
            return
        # Resolve identity on the caller's session so a not-yet-committed session/user is visible.
        chat_session = db_session.get(ChatSession, chat_session_id)
        if chat_session is None:
            return
        user = (
            db_session.get(User, chat_session.user_id)
            if chat_session.user_id is not None
            else None
        )
        # Do the roll-up WRITES on an independent tenant session so we never commit the caller's
        # in-flight chat transaction (create_new_chat_message may be called with commit=False).
        redis_client = get_redis_client(tenant_id=tenant_id)
        engine = RateLimiterEngine(redis_client, tenant_id)
        with get_current_tenant_session() as rec_session:
            RateLimitService(rec_session, tenant_id, engine).record(user, token_count)
    except Exception:
        observe_engine_error("record_hook")
