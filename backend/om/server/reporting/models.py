"""Pydantic schemas for the usage-reporting API (clean-room rewrite)."""

import datetime

from pydantic import BaseModel


class GenerateReportRequest(BaseModel):
    """Admin request to generate a usage report over an optional period."""

    period_from: datetime.datetime | None = None
    period_to: datetime.datetime | None = None


class UsageReportSchema(BaseModel):
    """Metadata for a generated usage report."""

    id: int
    report_name: str
    requestor_email: str | None
    period_from: datetime.datetime | None
    period_to: datetime.datetime | None
    created_at: datetime.datetime
