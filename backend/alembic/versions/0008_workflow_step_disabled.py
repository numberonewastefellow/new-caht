"""Workflows: a step can be kept but not run

Revision ID: 0008_workflow_step_disabled
Revises: 0007_datasource_rename
Create Date: 2026-11-02

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0008_workflow_step_disabled"
down_revision = "0007_datasource_rename"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agent_workflow_step",
        sa.Column("disabled", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("agent_workflow_step", "disabled")
