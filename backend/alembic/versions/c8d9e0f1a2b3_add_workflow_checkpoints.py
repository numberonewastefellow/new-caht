"""add workflow checkpoints and can_request_input

Revision ID: c8d9e0f1a2b3
Revises: b7c3d4e5f6a1
Create Date: 2026-02-28 17:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "c8d9e0f1a2b3"
down_revision = "b7c3d4e5f6a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Phase 1: Human-in-the-loop — allow steps to request user input
    op.add_column(
        "agent_workflow_step",
        sa.Column(
            "can_request_input",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )

    # Phase 1+2: Checkpoint state on WorkflowExecution
    op.add_column(
        "workflow_execution",
        sa.Column(
            "paused_at_step_id",
            sa.Integer(),
            sa.ForeignKey("agent_workflow_step.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "workflow_execution",
        sa.Column(
            "checkpoint_data",
            postgresql.JSONB(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("workflow_execution", "checkpoint_data")
    op.drop_column("workflow_execution", "paused_at_step_id")
    op.drop_column("agent_workflow_step", "can_request_input")
