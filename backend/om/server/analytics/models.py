"""Pydantic response schemas for the WS-H analytics API."""

import datetime

from pydantic import BaseModel


class DailyUsagePoint(BaseModel):
    """One day of aggregated usage metrics (a single point on the charts)."""

    date: datetime.date
    total_queries: int
    active_users: int
    likes: int
    dislikes: int
    # Average assistant response latency for the day; None when unmeasured.
    avg_latency_ms: float | None


class UsageSummary(BaseModel):
    """Totals across the whole selected window, for the dashboard KPI tiles."""

    total_queries: int
    total_active_users: int
    total_likes: int
    total_dislikes: int
    avg_latency_ms: float | None


class AgentUsagePoint(BaseModel):
    """Message volume for a single agent (bar-chart datum)."""

    agent_name: str
    total_messages: int


class RollupPoint(BaseModel):
    """A materialized ``analytics_rollup`` row."""

    window_start: datetime.date
    metric: str
    value: float


class AssistantDailyUsagePoint(BaseModel):
    """One day of usage for a single assistant/agent (chart datum)."""

    date: datetime.date
    total_messages: int
    total_unique_users: int


class AssistantStatsResponse(BaseModel):
    """Per-assistant usage stats over a window: daily series + window totals."""

    daily_stats: list[AssistantDailyUsagePoint]
    total_messages: int
    total_unique_users: int
