"""Add step-level overrides to agent_workflow_step

Supports workflow-level overrides for persona settings (LLM, prompts, tools,
document sets, max_output_tokens, replace_base_system_prompt). When set,
these override the persona's defaults at runtime without mutating the
shared persona.

Revision ID: e1f2a3b4c5d6
Revises: f1a2b3c4d5e6
Create Date: 2026-03-07
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = "e1f2a3b4c5d6"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agent_workflow_step",
        sa.Column("llm_provider_override", sa.String(), nullable=True),
    )
    op.add_column(
        "agent_workflow_step",
        sa.Column("llm_model_override", sa.String(), nullable=True),
    )
    op.add_column(
        "agent_workflow_step",
        sa.Column("max_output_tokens_override", sa.Integer(), nullable=True),
    )
    op.add_column(
        "agent_workflow_step",
        sa.Column("system_prompt_override", sa.Text(), nullable=True),
    )
    op.add_column(
        "agent_workflow_step",
        sa.Column("task_prompt_override", sa.Text(), nullable=True),
    )
    op.add_column(
        "agent_workflow_step",
        sa.Column("tool_ids_override", JSONB(), nullable=True),
    )
    op.add_column(
        "agent_workflow_step",
        sa.Column("document_set_ids_override", JSONB(), nullable=True),
    )
    op.add_column(
        "agent_workflow_step",
        sa.Column("replace_base_system_prompt_override", sa.Boolean(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("agent_workflow_step", "replace_base_system_prompt_override")
    op.drop_column("agent_workflow_step", "document_set_ids_override")
    op.drop_column("agent_workflow_step", "tool_ids_override")
    op.drop_column("agent_workflow_step", "task_prompt_override")
    op.drop_column("agent_workflow_step", "system_prompt_override")
    op.drop_column("agent_workflow_step", "max_output_tokens_override")
    op.drop_column("agent_workflow_step", "llm_model_override")
    op.drop_column("agent_workflow_step", "llm_provider_override")
