"""add sandbox_session_id to chat_session

Revision ID: e0f1a2b3c4d5
Revises: d9e0f1a2b3c4
Create Date: 2026-03-04 10:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "e0f1a2b3c4d5"
down_revision = "d9e0f1a2b3c4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "chat_session",
        sa.Column("sandbox_session_id", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("chat_session", "sandbox_session_id")
