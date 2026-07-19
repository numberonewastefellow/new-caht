"""Usage-reporting service (clean-room rewrite).

Generates a usage report synchronously: aggregate daily usage metrics over the
period, write a CSV to the file store, and record a ``usage_report`` row. Reports
are tenant-scoped (the injected session binds the tenant schema; the file store
also writes into the tenant's file records). Emits ``report.generated`` /
``report_exported`` structured events (CONTRACTS Standard 9).
"""

import csv
import datetime
import tempfile
import uuid
from collections.abc import Generator
from typing import IO
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import joinedload
from sqlalchemy.orm import Session

from om.configs.constants import FileOrigin
from om.db.models import UsageReportRecord
from om.file_store.constants import MAX_IN_MEMORY_SIZE
from om.file_store.constants import STANDARD_CHUNK_SIZE
from om.file_store.file_store import get_default_file_store
from om.server.analytics.models import DailyUsagePoint
from om.server.analytics.service import AnalyticsService
from om.server.analytics.structured_logging import log_structured_event
from om.server.analytics.structured_logging import timed_event
from om.server.reporting.models import UsageReportSchema

_CSV_COLUMNS = [
    "date",
    "total_queries",
    "active_users",
    "likes",
    "dislikes",
    "avg_latency_ms",
]

# Epoch used as the aggregation floor when a report has no explicit start.
_EPOCH = datetime.datetime.fromtimestamp(0, tz=datetime.timezone.utc)


class UsageReportService:
    def __init__(self, db_session: Session) -> None:
        self._db = db_session

    # ------------------------------------------------------------------ #
    # Generation
    # ------------------------------------------------------------------ #
    def generate(
        self,
        requestor_user_id: UUID | None,
        period_from: datetime.datetime | None,
        period_to: datetime.datetime | None,
    ) -> UsageReportSchema:
        with timed_event(
            event="report.generated",
            entity="usage_report",
            action="create",
            actor_user_id=str(requestor_user_id) if requestor_user_id else None,
        ) as ctx:
            agg_start = period_from or _EPOCH
            agg_end = period_to or datetime.datetime.now(tz=datetime.timezone.utc)

            daily = AnalyticsService(self._db).get_daily_usage(agg_start, agg_end)

            report_name = (
                f"{datetime.datetime.now(tz=datetime.timezone.utc).strftime('%Y-%m-%d')}"
                f"_usage_report_{uuid.uuid4().hex}.csv"
            )
            file_id = self._write_csv(report_name, daily)

            record = UsageReportRecord(
                report_name=report_name,
                file_id=file_id,
                requestor_user_id=requestor_user_id,
                period_from=period_from,
                period_to=period_to,
            )
            self._db.add(record)
            self._db.commit()
            self._db.refresh(record)
            ctx["entity_id"] = record.id

            return self._to_schema(record)

    def _write_csv(self, file_id: str, daily: list[DailyUsagePoint]) -> str:
        file_store = get_default_file_store()
        with tempfile.SpooledTemporaryFile(
            max_size=MAX_IN_MEMORY_SIZE, mode="w+"
        ) as temp_file:
            writer = csv.writer(temp_file)
            writer.writerow(_CSV_COLUMNS)
            for point in daily:
                writer.writerow(
                    [
                        point.date.isoformat(),
                        point.total_queries,
                        point.active_users,
                        point.likes,
                        point.dislikes,
                        point.avg_latency_ms if point.avg_latency_ms is not None else "",
                    ]
                )
            temp_file.seek(0)
            # No explicit db_session: the file store resolves the current tenant
            # from the contextvar (set for the request), keeping the write
            # tenant-scoped without depending on the abstract base signature.
            stored_id = file_store.save_file(
                content=temp_file,
                display_name=file_id,
                file_origin=FileOrigin.GENERATED_REPORT,
                file_type="text/csv",
                file_id=file_id,
            )
        return stored_id

    # ------------------------------------------------------------------ #
    # Listing / download
    # ------------------------------------------------------------------ #
    def list_reports(self) -> list[UsageReportSchema]:
        stmt = (
            select(UsageReportRecord)
            .options(joinedload(UsageReportRecord.requestor))
            .order_by(UsageReportRecord.created_at.desc())
        )
        return [
            self._to_schema(record)
            for record in self._db.execute(stmt).unique().scalars().all()
        ]

    def get_report_file(self, report_id: int) -> tuple[str, IO[bytes]]:
        record = self._db.get(UsageReportRecord, report_id)
        if record is None:
            raise ValueError(f"Usage report '{report_id}' does not exist.")
        file_store = get_default_file_store()
        handle = file_store.read_file(
            record.file_id, mode="b", use_tempfile=True
        )
        return record.report_name, handle

    @staticmethod
    def iter_file(handle: IO[bytes]) -> Generator[bytes, None, None]:
        try:
            while True:
                chunk = handle.read(STANDARD_CHUNK_SIZE)
                if not chunk:
                    break
                yield chunk
        finally:
            handle.close()

    # ------------------------------------------------------------------ #
    # Mapping
    # ------------------------------------------------------------------ #
    @staticmethod
    def _to_schema(record: UsageReportRecord) -> UsageReportSchema:
        return UsageReportSchema(
            id=record.id,
            report_name=record.report_name,
            requestor_email=record.requestor.email if record.requestor else None,
            period_from=record.period_from,
            period_to=record.period_to,
            created_at=record.created_at,
        )


def log_report_downloaded(report_id: int, actor_user_id: str | None) -> None:
    """Emit a structured event when a stored report is downloaded."""
    log_structured_event(
        event="report_exported",
        entity="usage_report",
        entity_id=report_id,
        action="export",
        actor_user_id=actor_user_id,
    )
