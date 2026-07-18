"""workspace soft delete

Revision ID: 0002_workspace_soft_delete
Revises: 0001_baseline_schema
Create Date: 2026-07-18

Adds a boolean ``deleted`` soft-delete flag to the ``workspace`` table. Soft-deleted
workspaces are hidden from the workspaces dashboard and return 404 when accessed
directly, but the row (and its chat/file associations) is retained so it can be
restored later. Mirrors the existing ``ChatSession.deleted`` / ``Agent.deleted``
convention.

The ``ALTER TABLE`` is unqualified (schema-relative) so it applies into whatever
schema Alembic's ``search_path`` points at (public for single-tenant, the tenant
schema for multi-tenant), matching the baseline migration's style.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "0002_workspace_soft_delete"
down_revision = "0001_baseline_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE workspace "
        "ADD COLUMN IF NOT EXISTS deleted BOOLEAN NOT NULL DEFAULT FALSE"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE workspace DROP COLUMN IF EXISTS deleted")
