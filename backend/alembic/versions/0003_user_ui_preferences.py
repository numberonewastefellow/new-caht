"""Per-user accent theme and pinned workflows

Revision ID: 0003_user_ui_preferences
Revises: 0002_workflow_nodes
Create Date: 2026-10-31

Additive only. These two UI preferences used to live in browser localStorage;
they now live on the user row next to font_preference / pinned_assistants.

- user.accent_theme     NULL = default accent, else ocean|emerald|violet|neonai
- user.pinned_workflows JSONB list of workflow ids, default []
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003_user_ui_preferences"
down_revision = "0002_workflow_nodes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user", sa.Column("accent_theme", sa.String(), nullable=True))
    op.add_column(
        "user",
        sa.Column(
            "pinned_workflows",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
    )


def downgrade() -> None:
    op.drop_column("user", "pinned_workflows")
    op.drop_column("user", "accent_theme")
