"""Admin analytics API (clean-room reimplementation).

Serves the lightweight admin analytics dashboard: daily usage time-series, KPI
summary, top-agent volume, and the optional rollup cache. Every endpoint is
admin-gated and tenant-scoped (the ``get_session`` dependency binds the current
tenant's Postgres schema).
"""

import datetime

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from sqlalchemy.orm import Session

from om.auth.users import current_admin_user
from om.db.engine.sql_engine import get_session
from om.db.models import User
from om.server.analytics.models import AgentUsagePoint
from om.server.analytics.models import DailyUsagePoint
from om.server.analytics.models import RollupPoint
from om.server.analytics.models import UsageSummary
from om.server.analytics.service import AnalyticsService
from om.server.analytics.structured_logging import log_structured_event

router = APIRouter(prefix="/analytics")

_DEFAULT_LOOKBACK_DAYS = 30


def _resolve_range(
    start: datetime.datetime | None, end: datetime.datetime | None
) -> tuple[datetime.datetime, datetime.datetime]:
    """Apply the default 30-day lookback when the range is not fully specified."""
    end = end or datetime.datetime.now(tz=datetime.timezone.utc)
    start = start or (end - datetime.timedelta(days=_DEFAULT_LOOKBACK_DAYS))
    return start, end


@router.get("/admin/usage")
def get_usage(
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
    _: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
) -> list[DailyUsagePoint]:
    """Per-day queries / active-users / feedback / latency over the window."""
    start, end = _resolve_range(start, end)
    return AnalyticsService(db_session).get_daily_usage(start, end)


@router.get("/admin/summary")
def get_summary(
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
    _: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
) -> UsageSummary:
    """Totals across the window for the dashboard KPI tiles."""
    start, end = _resolve_range(start, end)
    return AnalyticsService(db_session).get_summary(start, end)


@router.get("/admin/top-agents")
def get_top_agents(
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
    limit: int = Query(10, ge=1, le=50),
    _: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
) -> list[AgentUsagePoint]:
    """Top agents by assistant-message volume (bar chart)."""
    start, end = _resolve_range(start, end)
    return AnalyticsService(db_session).get_top_agents(start, end, limit=limit)


@router.get("/admin/rollups")
def get_rollups(
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
    _: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
) -> list[RollupPoint]:
    """Read cached daily rollup rows for the window."""
    start, end = _resolve_range(start, end)
    return AnalyticsService(db_session).get_rollups(start, end)


@router.post("/admin/rollups/refresh")
def refresh_rollups(
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
    user: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
) -> dict[str, int]:
    """Recompute and upsert the daily rollup cache for the window."""
    start, end = _resolve_range(start, end)
    rows_written = AnalyticsService(db_session).refresh_rollups(start, end)
    log_structured_event(
        event="analytics.rollups_refreshed",
        entity="analytics_rollup",
        action="update",
        actor_user_id=str(user.id),
        rows_written=rows_written,
    )
    return {"rows_written": rows_written}
