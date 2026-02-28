"""add max_calls_per_agent to agent_workflow

Revision ID: b7c3d4e5f6a1
Revises: a3f8b2c71d04
Create Date: 2026-02-28 10:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "b7c3d4e5f6a1"
down_revision = "a3f8b2c71d04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agent_workflow",
        sa.Column(
            "max_calls_per_agent",
            sa.Integer(),
            nullable=False,
            server_default="2",
        ),
    )


def downgrade() -> None:
    op.drop_column("agent_workflow", "max_calls_per_agent")
