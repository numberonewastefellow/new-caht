"""Admin API for the Rate Limits subsystem.

Base path ``/admin/rate-limits`` (admin-gated). Provides policy CRUD, the live remaining-budget
view (observability), and hourly usage history for the admin charts. Every config change emits a
structured log (Standard 9) and invalidates the per-tenant policy-existence cache so enforcement
picks it up immediately.
"""

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from om.auth.users import current_admin_user
from om.configs.constants import PUBLIC_API_TAGS
from om.db.engine.sql_engine import get_session
from om.db.models import User
from om.server.rate_limits._tenancy import get_current_tenant_id
from om.server.rate_limits.api_models import RateLimitPolicyArgs
from om.server.rate_limits.api_models import RateLimitPolicyResponse
from om.server.rate_limits.api_models import RateLimitPolicyUpdateArgs
from om.server.rate_limits.api_models import RemainingBudgetResponse
from om.server.rate_limits.api_models import UsageHistoryPoint
from om.server.rate_limits.api_models import UsageHistoryResponse
from om.server.rate_limits.constants import RateLimitScope
from om.server.rate_limits.constants import subject_key
from om.server.rate_limits.constants import TENANT_WIDE_SCOPES
from om.server.rate_limits.cache import invalidate_policy_existence
from om.server.rate_limits.metrics import log_ratelimit_event
from om.server.rate_limits.metrics import Stopwatch
from om.server.rate_limits.repository import RateLimitRepository
from om.server.rate_limits.service import build_rate_limit_service

router = APIRouter(prefix="/admin/rate-limits", tags=PUBLIC_API_TAGS)


def _log_create_conflict(
    tenant_id: str,
    admin: User,
    args: RateLimitPolicyArgs,
    watch: Stopwatch,
) -> None:
    log_ratelimit_event(
        event="ratelimit.policy_created",
        action="create",
        status="conflict",
        tenant_id=tenant_id,
        actor_user_id=str(admin.id),
        duration_ms=watch.elapsed_ms(),
        error="duplicate_policy",
        scope=args.scope.value,
    )


@router.get("/policies")
def list_policies(
    scope: RateLimitScope | None = None,
    _: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
) -> list[RateLimitPolicyResponse]:
    repo = RateLimitRepository(db_session)
    return [
        RateLimitPolicyResponse.from_db(p) for p in repo.list_policies(scope=scope)
    ]


@router.post("/policies")
def create_policy(
    args: RateLimitPolicyArgs,
    admin: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
) -> RateLimitPolicyResponse:
    watch = Stopwatch()
    tenant_id = get_current_tenant_id()
    repo = RateLimitRepository(db_session)

    # Policies with a NULL subject (tenant-wide, or the per-user DEFAULT with user_id=None) are not
    # constrained by the unique index (Postgres treats NULLs as distinct), so guard duplicates here.
    is_null_subject = args.scope in TENANT_WIDE_SCOPES or (
        args.scope == RateLimitScope.USER and args.user_id is None
    )
    if is_null_subject:
        duplicate = any(
            p.period_hours == args.period_hours and p.user_id is None and p.team_id is None
            for p in repo.list_policies(scope=args.scope)
        )
        if duplicate:
            _log_create_conflict(tenant_id, admin, args, watch)
            raise HTTPException(
                status_code=409,
                detail=f"A {args.scope.value} policy for a {args.period_hours}h window already exists.",
            )

    try:
        policy = repo.create_policy(
            scope=args.scope,
            token_budget=args.token_budget,
            period_hours=args.period_hours,
            algorithm=args.algorithm,
            enabled=args.enabled,
            user_id=args.user_id,
            team_id=args.team_id,
        )
    except IntegrityError:
        db_session.rollback()
        _log_create_conflict(tenant_id, admin, args, watch)
        raise HTTPException(
            status_code=409,
            detail="A policy for this scope, subject, and window already exists.",
        )

    invalidate_policy_existence(tenant_id)
    log_ratelimit_event(
        event="ratelimit.policy_created",
        action="create",
        status="ok",
        tenant_id=tenant_id,
        actor_user_id=str(admin.id),
        entity_id=policy.id,
        duration_ms=watch.elapsed_ms(),
        scope=policy.scope.value,
    )
    return RateLimitPolicyResponse.from_db(policy)


@router.put("/policies/{policy_id}")
def update_policy(
    policy_id: int,
    args: RateLimitPolicyUpdateArgs,
    admin: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
) -> RateLimitPolicyResponse:
    watch = Stopwatch()
    tenant_id = get_current_tenant_id()
    repo = RateLimitRepository(db_session)
    try:
        policy = repo.update_policy(
            policy_id,
            token_budget=args.token_budget,
            period_hours=args.period_hours,
            enabled=args.enabled,
            algorithm=args.algorithm,
        )
    except ValueError:
        log_ratelimit_event(
            event="ratelimit.policy_updated",
            action="update",
            status="not_found",
            tenant_id=tenant_id,
            actor_user_id=str(admin.id),
            entity_id=policy_id,
            duration_ms=watch.elapsed_ms(),
            error="policy_not_found",
        )
        raise HTTPException(status_code=404, detail="Rate limit policy not found.")

    invalidate_policy_existence(tenant_id)
    log_ratelimit_event(
        event="ratelimit.policy_updated",
        action="update",
        status="ok",
        tenant_id=tenant_id,
        actor_user_id=str(admin.id),
        entity_id=policy.id,
        duration_ms=watch.elapsed_ms(),
        scope=policy.scope.value,
    )
    return RateLimitPolicyResponse.from_db(policy)


@router.delete("/policies/{policy_id}")
def delete_policy(
    policy_id: int,
    admin: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
) -> None:
    watch = Stopwatch()
    tenant_id = get_current_tenant_id()
    repo = RateLimitRepository(db_session)
    try:
        repo.delete_policy(policy_id)
    except ValueError:
        log_ratelimit_event(
            event="ratelimit.policy_deleted",
            action="delete",
            status="not_found",
            tenant_id=tenant_id,
            actor_user_id=str(admin.id),
            entity_id=policy_id,
            duration_ms=watch.elapsed_ms(),
            error="policy_not_found",
        )
        raise HTTPException(status_code=404, detail="Rate limit policy not found.")

    invalidate_policy_existence(tenant_id)
    log_ratelimit_event(
        event="ratelimit.policy_deleted",
        action="delete",
        status="ok",
        tenant_id=tenant_id,
        actor_user_id=str(admin.id),
        entity_id=policy_id,
        duration_ms=watch.elapsed_ms(),
    )


@router.get("/budget")
def get_remaining_budget(
    _: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
) -> RemainingBudgetResponse:
    """Live remaining-budget across every enabled policy (drives the admin gauge)."""
    service = build_rate_limit_service(db_session)
    return RemainingBudgetResponse(items=service.remaining_budget())


@router.get("/history")
def get_usage_history(
    scope: RateLimitScope,
    hours: int = Query(default=24, ge=1, le=24 * 30),
    user_id: str | None = None,
    team_id: int | None = None,
    _: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
) -> UsageHistoryResponse:
    """Hourly usage roll-up for a scope/subject over the last ``hours`` (drives the history chart)."""
    from uuid import UUID

    try:
        parsed_user_id = UUID(user_id) if user_id else None
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id (must be a UUID).")

    try:
        # subject_key enforces scope↔subject agreement (USER needs user_id, TEAM needs team_id).
        subject = subject_key(scope, parsed_user_id, team_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    repo = RateLimitRepository(db_session)
    rows = repo.fetch_history(scope=scope, subject_key=subject, hours=hours)
    return UsageHistoryResponse(
        scope=scope,
        subject=subject,
        points=[UsageHistoryPoint.from_db(r) for r in rows],
    )
