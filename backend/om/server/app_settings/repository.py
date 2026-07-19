"""Data access for the singleton ``app_settings`` row.

The row lives in the per-tenant Postgres schema (tenant isolation is enforced by
the tenant-bound session passed in), so a plain "first row / create if absent"
lookup is safe — there is exactly one settings row per tenant schema.
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from om.db.models import AppSettings


class AppSettingsRepository:
    def __init__(self, db_session: Session) -> None:
        self._db = db_session

    def get_or_create(self) -> AppSettings:
        """Return the tenant's settings row, creating a default one if missing."""
        row = (
            self._db.execute(select(AppSettings).order_by(AppSettings.id).limit(1))
            .scalars()
            .first()
        )
        if row is None:
            row = AppSettings()
            self._db.add(row)
            self._db.commit()
            self._db.refresh(row)
        return row

    def update(self, values: dict[str, Any]) -> AppSettings:
        """Patch the settings row with the given column values."""
        row = self.get_or_create()
        for key, value in values.items():
            setattr(row, key, value)
        self._db.commit()
        self._db.refresh(row)
        return row
