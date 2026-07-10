"""add font_preference to user

Revision ID: a1f7c3d9e2b4
Revises: g3h4i5j6k7l8
Create Date: 2026-07-10 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "a1f7c3d9e2b4"
down_revision = "g3h4i5j6k7l8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column(
            "font_preference",
            sa.String(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("user", "font_preference")
