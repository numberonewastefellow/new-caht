"""Workflow node registry + versioning columns

Revision ID: 0002_workflow_nodes
Revises: 0001_om_baseline
Create Date: 2026-10-30

Additive only; existing workflows keep their exact behaviour (see
docs/flow-nodes/DESIGN.md "Old workflows: migration plan").

- agent_workflow_step:
    node_key        stable step identity, backfilled as 's' || id, unique per workflow
    type_version    pinned node type version (existing rows = 1)
    config          JSON config for node types without legacy columns
    parent_step_id  container membership (parallel / loop), NULL = top level
    branch_index    branch inside a parallel container
- agent_workflow: version (bumped per save), schema_version (1 = legacy semantics)
- agent_workflow_version: immutable definition snapshot per save
- workflow_execution.workflow_version_id: the definition a run started on
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002_workflow_nodes"
down_revision = "0001_om_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── agent_workflow_step ──
    op.add_column(
        "agent_workflow_step", sa.Column("node_key", sa.String(), nullable=True)
    )
    op.execute("UPDATE agent_workflow_step SET node_key = 's' || id::text")
    op.alter_column("agent_workflow_step", "node_key", nullable=False)
    op.create_unique_constraint(
        "uq_workflow_step_node_key", "agent_workflow_step", ["workflow_id", "node_key"]
    )
    op.add_column(
        "agent_workflow_step",
        sa.Column("type_version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "agent_workflow_step",
        sa.Column("config", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "agent_workflow_step",
        sa.Column(
            "parent_step_id",
            sa.Integer(),
            sa.ForeignKey("agent_workflow_step.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.add_column(
        "agent_workflow_step", sa.Column("branch_index", sa.Integer(), nullable=True)
    )

    # ── agent_workflow ──
    op.add_column(
        "agent_workflow",
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "agent_workflow",
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
    )

    # ── agent_workflow_version ──
    op.create_table(
        "agent_workflow_version",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "workflow_id",
            sa.Integer(),
            sa.ForeignKey("agent_workflow.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("definition", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "workflow_id", "version", name="uq_workflow_version_number"
        ),
    )

    # ── workflow_execution ──
    op.add_column(
        "workflow_execution",
        sa.Column(
            "workflow_version_id",
            sa.Integer(),
            sa.ForeignKey("agent_workflow_version.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("workflow_execution", "workflow_version_id")
    op.drop_table("agent_workflow_version")
    op.drop_column("agent_workflow", "schema_version")
    op.drop_column("agent_workflow", "version")
    op.drop_column("agent_workflow_step", "branch_index")
    op.drop_column("agent_workflow_step", "parent_step_id")
    op.drop_column("agent_workflow_step", "config")
    op.drop_column("agent_workflow_step", "type_version")
    op.drop_constraint(
        "uq_workflow_step_node_key", "agent_workflow_step", type_="unique"
    )
    op.drop_column("agent_workflow_step", "node_key")
