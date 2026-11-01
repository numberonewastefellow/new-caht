"""Webhooks: optionally tell the owner when a run succeeds

Revision ID: 0006_webhook_notify_on_success
Revises: 0005_webhook_allowed_tools
Create Date: 2026-11-01

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0006_webhook_notify_on_success"
down_revision = "0005_webhook_allowed_tools"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "pulse_webhook",
        sa.Column("notify_on_success", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("pulse_webhook", "notify_on_success")
