"""FastAPI enforcement dependency for the rate-limits subsystem.

``enforce_rate_limits`` replaces the old ``check_token_rate_limits`` dependency on the chat/search
send endpoints. It short-circuits (near-zero cost) when the tenant has no enabled policy, using the
per-tenant existence cache in ``cache.py`` (the old ``@lru_cache`` check was process-global and would
have leaked one tenant's "no limits" answer to every other tenant).
"""

from fastapi import Depends
from fastapi import HTTPException
from sqlalchemy.orm import Session

from om.auth.users import current_chat_accessible_user
from om.db.engine.sql_engine import get_session
from om.db.models import User
from om.server.rate_limits._tenancy import get_current_tenant_id
from om.server.rate_limits.cache import policy_exists
from om.server.rate_limits.service import build_rate_limit_service
from om.server.rate_limits.service import RateLimitExceededError


def enforce_rate_limits(
    user: User = Depends(current_chat_accessible_user),
    db_session: Session = Depends(get_session),
) -> None:
    """Reject the request with 429 if any applicable rate-limit policy is over budget."""
    tenant_id = get_current_tenant_id()
    # Fast path: nothing configured for this tenant.
    if not policy_exists(tenant_id, db_session):
        return

    service = build_rate_limit_service(db_session)
    try:
        service.check(user)
    except RateLimitExceededError as exc:
        raise HTTPException(
            status_code=429,
            detail={
                "message": str(exc),
                "scope": exc.scope.value,
                "budget": exc.budget,
                "used": exc.used,
                "remaining": exc.remaining,
                "reset_seconds": exc.reset_seconds,
                "period_hours": exc.period_hours,
            },
            headers={
                "Retry-After": str(exc.reset_seconds),
                "RateLimit-Remaining": str(exc.remaining),
                "RateLimit-Reset": str(exc.reset_seconds),
            },
        )
