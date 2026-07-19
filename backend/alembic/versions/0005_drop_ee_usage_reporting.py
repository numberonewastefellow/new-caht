"""Cluster I: drop EE-origin usage-reporting / metering tables

Revision ID: 0005_drop_ee_usage_reporting
Revises: 0004_ws_h_analytics
Create Date: 2026-07-19

Drops the now-orphaned EE-origin tables left behind after the WS-H analytics /
query-history / reporting / app-settings rewrite replaced the old Onyx-EE
surface:

- ``usage_reports`` — backed the old ``UsageReport`` model (async usage-export
  pipeline). Replaced by the WS-H ``usage_report`` table (``UsageReportRecord``),
  which is created by 0004_ws_h_analytics and is intentionally NOT touched here.
- ``tenant_usage`` — backed the removed usage-metering feature (``TenantUsage``),
  already deleted from ``om.db.models`` in a prior step; dropped here defensively
  so the physical schema matches the ORM.

Both drops use ``IF EXISTS`` so the migration is a no-op where the table was
never created (fresh DB / already-clean environments).
"""

from alembic import op

revision = "0005_drop_ee_usage_reporting"
down_revision = "0004_ws_h_analytics"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS tenant_usage CASCADE")
    op.execute("DROP TABLE IF EXISTS usage_reports CASCADE")


def downgrade() -> None:
    # Fresh-DB cleanup of dropped EE tables; no recreation path.
    pass
