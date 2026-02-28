"""add workflow_id to persona

Revision ID: a3f8b2c71d04
Revises: 0251ef56926f
Create Date: 2026-02-27 10:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "a3f8b2c71d04"
down_revision = "0251ef56926f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "persona",
        sa.Column(
            "workflow_id",
            sa.Integer(),
            sa.ForeignKey("agent_workflow.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("persona", "workflow_id")
