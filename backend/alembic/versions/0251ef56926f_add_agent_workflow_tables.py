"""add agent workflow tables

Revision ID: 0251ef56926f
Revises: 631fd2504136, c7bf5721733e
Create Date: 2026-02-26 10:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0251ef56926f"
down_revision = ("631fd2504136", "c7bf5721733e")
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_workflow",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("user.id", ondelete="CASCADE"),
            nullable=True,
        ),
        # Orchestration config
        sa.Column(
            "orchestration_mode",
            sa.String(),
            nullable=False,
            server_default="llm_decision",
        ),
        sa.Column("orchestrator_prompt", sa.Text(), nullable=True),
        sa.Column("orchestrator_llm_provider", sa.String(), nullable=True),
        sa.Column("orchestrator_llm_model", sa.String(), nullable=True),
        sa.Column("max_steps", sa.Integer(), server_default="10"),
        sa.Column("timeout_seconds", sa.Integer(), server_default="1800"),
        # Metadata
        sa.Column("is_public", sa.Boolean(), server_default="true"),
        sa.Column("is_visible", sa.Boolean(), server_default="true"),
        sa.Column("deleted", sa.Boolean(), server_default="false"),
        sa.Column("icon_name", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "agent_workflow_step",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "workflow_id",
            sa.Integer(),
            sa.ForeignKey("agent_workflow.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "persona_id",
            sa.Integer(),
            sa.ForeignKey("persona.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("step_order", sa.Integer(), nullable=False),
        sa.Column("step_name", sa.String(), nullable=False),
        sa.Column("step_description", sa.Text(), nullable=True),
        sa.Column("input_mapping", postgresql.JSONB(), nullable=True),
        sa.Column("output_key", sa.String(), server_default="output"),
        sa.Column("condition", postgresql.JSONB(), nullable=True),
        sa.Column("is_terminal", sa.Boolean(), server_default="false"),
        sa.UniqueConstraint(
            "workflow_id", "step_order", name="uq_workflow_step_order"
        ),
    )

    op.create_table(
        "workflow_execution",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "workflow_id",
            sa.Integer(),
            sa.ForeignKey("agent_workflow.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "chat_session_id",
            sa.Uuid(),
            sa.ForeignKey("chat_session.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("user.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", sa.String(), server_default="running"),
        sa.Column("steps_executed", postgresql.JSONB(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), server_default="0"),
        sa.Column("total_duration_ms", sa.Integer(), server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("workflow_execution")
    op.drop_table("agent_workflow_step")
    op.drop_table("agent_workflow")
