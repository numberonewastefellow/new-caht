"""Pulse: record who last updated a schedule (pulse_schedule.updated_by_id)

Revision ID: 0011_pulse_updated_by
Revises: 0010_pulse_input_modes
Create Date: 2026-10-27

Admins can now edit any user's schedule. Ownership never changes: `user_id` stays
the creator (runs keep executing as them and they keep full access). The new
`updated_by_id` records who made the latest change, for the UI and audit trail.
Existing rows are backfilled with their creator.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0011_pulse_updated_by"
down_revision = "0010_pulse_input_modes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "pulse_schedule",
        sa.Column(
            "updated_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.execute("UPDATE pulse_schedule SET updated_by_id = user_id")


def downgrade() -> None:
    op.drop_column("pulse_schedule", "updated_by_id")
