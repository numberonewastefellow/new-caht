"""Workflows: sticky notes on the canvas

Revision ID: 0009_workflow_notes
Revises: 0008_workflow_step_disabled
Create Date: 2026-11-02

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0009_workflow_notes"
down_revision = "0008_workflow_step_disabled"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_workflow_note",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "workflow_id",
            sa.Integer(),
            sa.ForeignKey("agent_workflow.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("text", sa.Text(), nullable=False, server_default=""),
        sa.Column("color", sa.String(16), nullable=False, server_default="yellow"),
        sa.Column("step_node_key", sa.String(64), nullable=True),
        sa.Column("x", sa.Integer(), nullable=False),
        sa.Column("y", sa.Integer(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_by_id",
            sa.Uuid(),
            sa.ForeignKey("user.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "updated_by_id",
            sa.Uuid(),
            sa.ForeignKey("user.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_agent_workflow_note_workflow_id", "agent_workflow_note", ["workflow_id"])


def downgrade() -> None:
    op.drop_index("ix_agent_workflow_note_workflow_id", table_name="agent_workflow_note")
    op.drop_table("agent_workflow_note")
