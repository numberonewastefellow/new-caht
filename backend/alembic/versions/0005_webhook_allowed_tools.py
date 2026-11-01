"""Webhooks: the tools a webhook's runs may use, kept on each run's chat as well

Revision ID: 0005_webhook_allowed_tools
Revises: 0004_pulse_triggers
Create Date: 2026-11-01

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0005_webhook_allowed_tools"
down_revision = "0004_pulse_triggers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "chat_session",
        sa.Column("tool_allowlist", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "pulse_webhook",
        sa.Column(
            "allowed_tool_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
    )


def downgrade() -> None:
    op.drop_column("pulse_webhook", "allowed_tool_ids")
    op.drop_column("chat_session", "tool_allowlist")
