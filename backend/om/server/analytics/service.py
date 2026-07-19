"""Tenant-scoped analytics aggregation service.

Clean-room reimplementation of the usage-analytics queries. The service NEVER
opens its own DB session — it operates on the tenant-bound session handed in by
the FastAPI route (``Depends(get_session)``), so every query runs inside the
current tenant's Postgres schema and cannot leak across tenants.

Live aggregation over ``chat_message`` / ``chat_feedback`` / ``chat_session`` is
the source of truth. ``analytics_rollup`` is an optional per-day cache that can be
refreshed on demand for cheap large-range chart queries.
"""

import datetime

from sqlalchemy import case
from sqlalchemy import cast
from sqlalchemy import Date
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from om.configs.constants import MessageType
from om.db.models import Agent
from om.db.models import AnalyticsRollup
from om.db.models import ChatMessage
from om.db.models import ChatMessageFeedback
from om.db.models import ChatSession
from om.server.analytics.models import AgentUsagePoint
from om.server.analytics.models import DailyUsagePoint
from om.server.analytics.models import RollupPoint
from om.server.analytics.models import UsageSummary


class RollupMetric:
    """Metric keys stored in the ``analytics_rollup`` table."""

    QUERIES = "queries"
    ACTIVE_USERS = "active_users"
    LIKES = "likes"
    DISLIKES = "dislikes"
    AVG_LATENCY_MS = "avg_latency_ms"


class AnalyticsService:
    """Aggregates tenant-scoped usage metrics from live chat data."""

    def __init__(self, db_session: Session) -> None:
        self._db = db_session

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def get_daily_usage(
        self, start: datetime.datetime, end: datetime.datetime
    ) -> list[DailyUsagePoint]:
        """Per-day queries / active-users / feedback / latency over [start, end]."""
        volume = self._daily_volume(start, end)
        feedback = self._daily_feedback(start, end)

        points: list[DailyUsagePoint] = []
        for day in sorted(set(volume) | set(feedback)):
            queries, users, latency_s = volume.get(day, (0, 0, None))
            likes, dislikes = feedback.get(day, (0, 0))
            points.append(
                DailyUsagePoint(
                    date=day,
                    total_queries=queries,
                    active_users=users,
                    likes=likes,
                    dislikes=dislikes,
                    avg_latency_ms=(
                        round(latency_s * 1000.0, 2) if latency_s is not None else None
                    ),
                )
            )
        return points

    def get_summary(
        self, start: datetime.datetime, end: datetime.datetime
    ) -> UsageSummary:
        """Totals across the whole window (KPI tiles)."""
        vol_stmt = (
            select(
                func.count(func.distinct(ChatMessage.id)),
                func.count(func.distinct(ChatSession.user_id)),
                func.avg(ChatMessage.processing_duration_seconds),
            )
            .select_from(ChatMessage)
            .join(ChatSession, ChatSession.id == ChatMessage.chat_session_id)
            .where(ChatMessage.message_type == MessageType.ASSISTANT)
            .where(ChatMessage.time_sent >= start)
            .where(ChatMessage.time_sent <= end)
        )
        queries, users, latency_s = self._db.execute(vol_stmt).one()

        fb_stmt = (
            select(
                func.coalesce(
                    func.sum(case((ChatMessageFeedback.is_positive.is_(True), 1), else_=0)),
                    0,
                ),
                func.coalesce(
                    func.sum(case((ChatMessageFeedback.is_positive.is_(False), 1), else_=0)),
                    0,
                ),
            )
            .select_from(ChatMessageFeedback)
            .join(ChatMessage, ChatMessage.id == ChatMessageFeedback.chat_message_id)
            .where(ChatMessage.message_type == MessageType.ASSISTANT)
            .where(ChatMessage.time_sent >= start)
            .where(ChatMessage.time_sent <= end)
        )
        likes, dislikes = self._db.execute(fb_stmt).one()

        return UsageSummary(
            total_queries=int(queries or 0),
            total_active_users=int(users or 0),
            total_likes=int(likes or 0),
            total_dislikes=int(dislikes or 0),
            avg_latency_ms=(
                round(float(latency_s) * 1000.0, 2) if latency_s is not None else None
            ),
        )

    def get_top_agents(
        self,
        start: datetime.datetime,
        end: datetime.datetime,
        limit: int = 10,
    ) -> list[AgentUsagePoint]:
        """Top agents by assistant-message volume in the window (bar chart)."""
        stmt = (
            select(Agent.name, func.count(ChatMessage.id))
            .select_from(ChatMessage)
            .join(ChatSession, ChatSession.id == ChatMessage.chat_session_id)
            .join(Agent, Agent.id == ChatSession.agent_id)
            .where(ChatMessage.message_type == MessageType.ASSISTANT)
            .where(ChatMessage.time_sent >= start)
            .where(ChatMessage.time_sent <= end)
            .group_by(Agent.name)
            .order_by(func.count(ChatMessage.id).desc())
            .limit(limit)
        )
        return [
            AgentUsagePoint(agent_name=name, total_messages=int(count or 0))
            for name, count in self._db.execute(stmt).all()
        ]

    # ------------------------------------------------------------------ #
    # Rollup cache
    # ------------------------------------------------------------------ #
    def refresh_rollups(
        self, start: datetime.datetime, end: datetime.datetime
    ) -> int:
        """Recompute daily metrics for the window and upsert into analytics_rollup.

        Returns the number of ``(day, metric)`` rows written.
        """
        daily = self.get_daily_usage(start, end)
        rows: list[tuple[datetime.date, str, float]] = []
        for point in daily:
            rows.append((point.date, RollupMetric.QUERIES, float(point.total_queries)))
            rows.append(
                (point.date, RollupMetric.ACTIVE_USERS, float(point.active_users))
            )
            rows.append((point.date, RollupMetric.LIKES, float(point.likes)))
            rows.append((point.date, RollupMetric.DISLIKES, float(point.dislikes)))
            if point.avg_latency_ms is not None:
                rows.append(
                    (point.date, RollupMetric.AVG_LATENCY_MS, float(point.avg_latency_ms))
                )

        for window_start, metric, value in rows:
            stmt = pg_insert(AnalyticsRollup).values(
                window_start=window_start, metric=metric, value=value
            )
            stmt = stmt.on_conflict_do_update(
                constraint="uq_analytics_rollup_day_metric",
                set_={"value": value, "computed_at": func.now()},
            )
            self._db.execute(stmt)

        self._db.commit()
        return len(rows)

    def get_rollups(
        self, start: datetime.datetime, end: datetime.datetime
    ) -> list[RollupPoint]:
        """Read cached rollup rows for the window."""
        stmt = (
            select(AnalyticsRollup)
            .where(AnalyticsRollup.window_start >= start.date())
            .where(AnalyticsRollup.window_start <= end.date())
            .order_by(AnalyticsRollup.window_start, AnalyticsRollup.metric)
        )
        return [
            RollupPoint(
                window_start=row.window_start, metric=row.metric, value=row.value
            )
            for row in self._db.execute(stmt).scalars().all()
        ]

    # ------------------------------------------------------------------ #
    # Internal aggregation queries
    # ------------------------------------------------------------------ #
    def _daily_volume(
        self, start: datetime.datetime, end: datetime.datetime
    ) -> dict[datetime.date, tuple[int, int, float | None]]:
        """Per-day (queries, active_users, avg_latency_seconds).

        No feedback join here — joining the one-to-many ``chat_feedback`` table
        would inflate the message/user counts and skew the latency average.
        """
        day = cast(ChatMessage.time_sent, Date)
        stmt = (
            select(
                day.label("day"),
                func.count(func.distinct(ChatMessage.id)),
                func.count(func.distinct(ChatSession.user_id)),
                func.avg(ChatMessage.processing_duration_seconds),
            )
            .select_from(ChatMessage)
            .join(ChatSession, ChatSession.id == ChatMessage.chat_session_id)
            .where(ChatMessage.message_type == MessageType.ASSISTANT)
            .where(ChatMessage.time_sent >= start)
            .where(ChatMessage.time_sent <= end)
            .group_by(day)
        )
        out: dict[datetime.date, tuple[int, int, float | None]] = {}
        for d, queries, users, latency in self._db.execute(stmt).all():
            out[d] = (
                int(queries or 0),
                int(users or 0),
                float(latency) if latency is not None else None,
            )
        return out

    def _daily_feedback(
        self, start: datetime.datetime, end: datetime.datetime
    ) -> dict[datetime.date, tuple[int, int]]:
        """Per-day (likes, dislikes) counted as feedback events on assistant msgs."""
        day = cast(ChatMessage.time_sent, Date)
        stmt = (
            select(
                day.label("day"),
                func.sum(case((ChatMessageFeedback.is_positive.is_(True), 1), else_=0)),
                func.sum(
                    case((ChatMessageFeedback.is_positive.is_(False), 1), else_=0)
                ),
            )
            .select_from(ChatMessageFeedback)
            .join(ChatMessage, ChatMessage.id == ChatMessageFeedback.chat_message_id)
            .where(ChatMessage.message_type == MessageType.ASSISTANT)
            .where(ChatMessage.time_sent >= start)
            .where(ChatMessage.time_sent <= end)
            .group_by(day)
        )
        out: dict[datetime.date, tuple[int, int]] = {}
        for d, likes, dislikes in self._db.execute(stmt).all():
            out[d] = (int(likes or 0), int(dislikes or 0))
        return out
