"""Pulse: input modes for schedules (fixed / window / ask / list)

Revision ID: 0010_pulse_input_modes
Revises: 0009_pulse_schedules
Create Date: 2026-10-27

What each scheduled run receives is now explicit:

* ``fixed``  — the same request every run (``input_message``)
* ``window`` — "new information since the last run" template (``{{window_start}}``…)
* ``ask``    — the run opens the workflow chat and waits for the user's input
               (``input_prompt`` is what we ask)
* ``list``   — the next item of ``input_items`` each run (``{{item}}``),
               cycling via ``input_item_index``

Existing schedules: a message equal to the old silent UI default becomes
``window`` (behaviour unchanged), everything else becomes ``fixed``.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0010_pulse_input_modes"
down_revision = "0009_pulse_schedules"
branch_labels = None
depends_on = None

OLD_UI_DEFAULT = "Run for {{date}}. Only include what changed since {{window_start}}."


def upgrade() -> None:
    op.add_column(
        "pulse_schedule",
        sa.Column("input_mode", sa.String(), nullable=False, server_default="fixed"),
    )
    op.add_column("pulse_schedule", sa.Column("input_prompt", sa.Text(), nullable=True))
    op.add_column(
        "pulse_schedule",
        sa.Column("input_items", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "pulse_schedule",
        sa.Column(
            "input_item_index", sa.Integer(), nullable=False, server_default="0"
        ),
    )
    op.execute(
        sa.text(
            "UPDATE pulse_schedule SET input_mode = 'window' WHERE input_message = :d"
        ).bindparams(d=OLD_UI_DEFAULT)
    )


def downgrade() -> None:
    op.drop_column("pulse_schedule", "input_item_index")
    op.drop_column("pulse_schedule", "input_items")
    op.drop_column("pulse_schedule", "input_prompt")
    op.drop_column("pulse_schedule", "input_mode")
