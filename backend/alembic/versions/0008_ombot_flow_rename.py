"""rename chat_session.onyxbot_flow -> ombot_flow

Revision ID: 0008_ombot_flow_rename
Revises: 0007_team_enrichment
Create Date: 2026-10-24

Pure metadata rename (no data movement, no table rewrite). The column is NOT NULL
with no server default and is not referenced by any index, constraint or view, so
a single RENAME COLUMN is the whole change. The ORM attribute
``ChatSession.ombot_flow`` is renamed in the same release; code and schema must
ship together (the api_server container applies this revision before starting).

``0001_baseline_schema`` intentionally still creates the column under its old
name: this revision renames it afterwards on both fresh and existing databases.
"""

from alembic import op

revision = "0008_ombot_flow_rename"
down_revision = "0007_team_enrichment"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE chat_session RENAME COLUMN onyxbot_flow TO ombot_flow")


def downgrade() -> None:
    op.execute("ALTER TABLE chat_session RENAME COLUMN ombot_flow TO onyxbot_flow")
