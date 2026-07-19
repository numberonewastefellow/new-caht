"""Cluster I: drop EE-origin cloud-tenant tables

Revision ID: 0006_drop_ee_cloud_tenants
Revises: 0005_drop_ee_usage_reporting
Create Date: 2026-07-19

Drops the last EE cloud-tenant tables left behind after the WS-M multi-tenant
isolation core (``om.tenancy``) replaced the old Onyx-EE cloud tenants subsystem
(``om/server/tenants/``, now deleted):

- ``available_tenant`` — backed the removed ``AvailableTenant`` model, the cloud
  *pre-provision pool* consumed by the deleted ``check_available_tenants`` /
  ``pre_provision_tenant`` celery tasks. The self-hosted design provisions tenants
  on demand (``om.tenancy.provisioning``), so no pool table is needed.
- ``tenant_anonymous_user_path`` — backed the removed ``TenantAnonymousUserPath``
  model (cloud anonymous-user path routing). Anonymous access in the WS-M design is
  cookie-based (``ALLOW_ANONYMOUS_TENANT_ACCESS``) and needs no table.

Both drops use ``IF EXISTS`` so the migration is a no-op where the table was never
created (fresh DB / already-clean environments).
"""

from alembic import op

revision = "0006_drop_ee_cloud_tenants"
down_revision = "0005_drop_ee_usage_reporting"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS available_tenant CASCADE")
    op.execute("DROP TABLE IF EXISTS tenant_anonymous_user_path CASCADE")


def downgrade() -> None:
    # Fresh-DB cleanup of dropped EE tables; no recreation path.
    pass
