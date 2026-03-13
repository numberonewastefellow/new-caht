"""add_conditional_router_step_type

Revision ID: g3h4i5j6k7l8
Revises: f2a3b4c5d6e7
Create Date: 2026-03-13 02:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "g3h4i5j6k7l8"
down_revision = "f2a3b4c5d6e7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add step_type column — defaults to "agent" so all existing rows are valid
    op.add_column(
        "agent_workflow_step",
        sa.Column(
            "step_type",
            sa.String(),
            server_default="agent",
            nullable=False,
        ),
    )

    # Make persona_id nullable — conditional_router steps have no persona
    op.alter_column(
        "agent_workflow_step",
        "persona_id",
        existing_type=sa.Integer(),
        nullable=True,
    )


def downgrade() -> None:
    # Revert persona_id to non-nullable (delete any conditional_router rows first)
    op.execute(
        "DELETE FROM agent_workflow_step WHERE step_type = 'conditional_router'"
    )
    op.alter_column(
        "agent_workflow_step",
        "persona_id",
        existing_type=sa.Integer(),
        nullable=False,
    )

    op.drop_column("agent_workflow_step", "step_type")
