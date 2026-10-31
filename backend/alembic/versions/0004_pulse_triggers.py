"""Pulse triggers: schedules and webhooks as two kinds of trigger

Revision ID: 0004_pulse_triggers
Revises: 0003_user_ui_preferences
Create Date: 2026-10-31

A schedule and a webhook are two ways to start a workflow, so what they share moves
to a parent table and each kind keeps only its own fields (joined-table inheritance,
see docs/scheduled-workflows/DESIGN.md "Triggers"):

- pulse_schedule is renamed pulse_trigger and keeps the shared columns, plus `kind`.
- a new pulse_schedule holds the timing and input-mode columns. Row ids don't change.
- pulse_run: schedule_id -> trigger_id, trigger -> fired_by.
- chat_session: pulse_schedule_id -> pulse_trigger_id.
- notifications that stored pulse_schedule_id now store pulse_trigger_id.
- a new pulse_webhook holds what a webhook needs, and pulse_run gains dedup_key and
  trigger_payload.

Downgrade restores the old shape for schedules. Rows of any other trigger kind can't
exist in the old shape, so downgrade deletes them.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004_pulse_triggers"
down_revision = "0003_user_ui_preferences"
branch_labels = None
depends_on = None

# Columns that belong to a schedule, in both directions of the migration.
_SCHEDULE_COLUMNS = (
    "schedule_type",
    "cron_expression",
    "interval_seconds",
    "run_at",
    "next_run_at",
    "last_success_scheduled_for",
    "input_mode",
    "input_prompt",
    "input_items",
    "input_item_index",
)


def _rename_notification_key(old: str, new: str) -> None:
    op.execute(
        f"""
        UPDATE notification
        SET additional_data = (additional_data - '{old}')
            || jsonb_build_object('{new}', additional_data -> '{old}')
        WHERE additional_data ? '{old}'
        """
    )


def upgrade() -> None:
    # ── pulse_trigger: the old table, renamed ──
    op.rename_table("pulse_schedule", "pulse_trigger")
    op.execute("ALTER SEQUENCE pulse_schedule_id_seq RENAME TO pulse_trigger_id_seq")
    op.execute(
        "ALTER INDEX pulse_schedule_pkey RENAME TO pulse_trigger_pkey"
    )
    op.execute("ALTER INDEX ix_pulse_schedule_user_id RENAME TO ix_pulse_trigger_user_id")
    for column in ("updated_by_id", "user_id", "workflow_id"):
        op.execute(
            f"ALTER TABLE pulse_trigger RENAME CONSTRAINT "
            f"pulse_schedule_{column}_fkey TO pulse_trigger_{column}_fkey"
        )
    op.add_column(
        "pulse_trigger",
        sa.Column("kind", sa.String(), nullable=False, server_default="schedule"),
    )
    op.alter_column("pulse_trigger", "kind", server_default=None)

    # ── pulse_schedule: only what a schedule needs ──
    op.create_table(
        "pulse_schedule",
        sa.Column(
            "id",
            sa.Integer(),
            sa.ForeignKey("pulse_trigger.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("schedule_type", sa.String(), nullable=False),
        sa.Column("cron_expression", sa.String(), nullable=True),
        sa.Column("interval_seconds", sa.Integer(), nullable=True),
        sa.Column("run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_scheduled_for", sa.DateTime(timezone=True), nullable=True),
        sa.Column("input_mode", sa.String(), nullable=False, server_default="fixed"),
        sa.Column("input_prompt", sa.Text(), nullable=True),
        sa.Column("input_items", postgresql.JSONB(), nullable=True),
        sa.Column("input_item_index", sa.Integer(), nullable=False, server_default="0"),
    )
    columns = ", ".join(_SCHEDULE_COLUMNS)
    op.execute(
        f"INSERT INTO pulse_schedule (id, {columns}) SELECT id, {columns} FROM pulse_trigger"
    )
    # Dropping next_run_at also drops ix_pulse_schedule_due, which filtered on `enabled`.
    for column in _SCHEDULE_COLUMNS:
        op.drop_column("pulse_trigger", column)
    op.create_index(
        "ix_pulse_schedule_next_run",
        "pulse_schedule",
        ["next_run_at"],
        postgresql_where=sa.text("next_run_at IS NOT NULL"),
    )

    # ── pulse_run ──
    op.alter_column("pulse_run", "schedule_id", new_column_name="trigger_id")
    op.alter_column("pulse_run", "trigger", new_column_name="fired_by")
    op.execute(
        "ALTER TABLE pulse_run RENAME CONSTRAINT "
        "pulse_run_schedule_id_fkey TO pulse_run_trigger_id_fkey"
    )
    op.execute("ALTER INDEX uq_pulse_run_schedule_slot RENAME TO uq_pulse_run_trigger_slot")
    op.execute("ALTER INDEX ix_pulse_run_schedule_created RENAME TO ix_pulse_run_trigger_created")

    # ── chat_session ──
    op.alter_column("chat_session", "pulse_schedule_id", new_column_name="pulse_trigger_id")
    op.execute(
        "ALTER TABLE chat_session RENAME CONSTRAINT "
        "chat_session_pulse_schedule_id_fkey TO chat_session_pulse_trigger_id_fkey"
    )
    op.execute(
        "ALTER INDEX ix_chat_session_pulse_schedule_id "
        "RENAME TO ix_chat_session_pulse_trigger_id"
    )

    _rename_notification_key("pulse_schedule_id", "pulse_trigger_id")

    # ── pulse_webhook: only what a webhook needs ──
    op.create_table(
        "pulse_webhook",
        sa.Column(
            "id",
            sa.Integer(),
            sa.ForeignKey("pulse_trigger.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("token_hash", sa.String(), nullable=False, unique=True),
        sa.Column("token_last4", sa.String(), nullable=False),
        sa.Column("previous_token_hash", sa.String(), nullable=True, unique=True),
        sa.Column("previous_valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("auth_mode", sa.String(), nullable=False),
        sa.Column("signing_secret", sa.LargeBinary(), nullable=False),
        sa.Column("previous_signing_secret", sa.LargeBinary(), nullable=True),
        sa.Column("header_name", sa.String(), nullable=True),
        sa.Column("dedup_source", sa.String(), nullable=False),
        sa.Column("dedup_path", sa.String(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_rejected_reason", sa.String(), nullable=True),
    )
    op.add_column("pulse_run", sa.Column("dedup_key", sa.String(), nullable=True))
    op.add_column("pulse_run", sa.Column("trigger_payload", postgresql.JSONB(), nullable=True))
    op.create_index(
        "uq_pulse_run_webhook_dedup",
        "pulse_run",
        ["trigger_id", "dedup_key"],
        unique=True,
        postgresql_where=sa.text("fired_by = 'webhook' AND dedup_key IS NOT NULL"),
    )


def downgrade() -> None:
    _rename_notification_key("pulse_trigger_id", "pulse_schedule_id")

    # Cascades to their runs; chat sessions keep existing with the link set to NULL.
    op.execute("DELETE FROM pulse_trigger WHERE kind <> 'schedule'")

    op.drop_index("uq_pulse_run_webhook_dedup", table_name="pulse_run")
    op.drop_column("pulse_run", "trigger_payload")
    op.drop_column("pulse_run", "dedup_key")
    op.drop_table("pulse_webhook")

    op.execute(
        "ALTER INDEX ix_chat_session_pulse_trigger_id "
        "RENAME TO ix_chat_session_pulse_schedule_id"
    )
    op.execute(
        "ALTER TABLE chat_session RENAME CONSTRAINT "
        "chat_session_pulse_trigger_id_fkey TO chat_session_pulse_schedule_id_fkey"
    )
    op.alter_column("chat_session", "pulse_trigger_id", new_column_name="pulse_schedule_id")

    op.execute("ALTER INDEX ix_pulse_run_trigger_created RENAME TO ix_pulse_run_schedule_created")
    op.execute("ALTER INDEX uq_pulse_run_trigger_slot RENAME TO uq_pulse_run_schedule_slot")
    op.execute(
        "ALTER TABLE pulse_run RENAME CONSTRAINT "
        "pulse_run_trigger_id_fkey TO pulse_run_schedule_id_fkey"
    )
    op.alter_column("pulse_run", "fired_by", new_column_name="trigger")
    op.alter_column("pulse_run", "trigger_id", new_column_name="schedule_id")

    # Put the schedule columns back on the parent, then rename it back.
    op.add_column("pulse_trigger", sa.Column("schedule_type", sa.String(), nullable=True))
    op.add_column("pulse_trigger", sa.Column("cron_expression", sa.String(), nullable=True))
    op.add_column("pulse_trigger", sa.Column("interval_seconds", sa.Integer(), nullable=True))
    op.add_column("pulse_trigger", sa.Column("run_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("pulse_trigger", sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "pulse_trigger",
        sa.Column("last_success_scheduled_for", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "pulse_trigger",
        sa.Column("input_mode", sa.String(), nullable=False, server_default="fixed"),
    )
    op.add_column("pulse_trigger", sa.Column("input_prompt", sa.Text(), nullable=True))
    op.add_column("pulse_trigger", sa.Column("input_items", postgresql.JSONB(), nullable=True))
    op.add_column(
        "pulse_trigger",
        sa.Column("input_item_index", sa.Integer(), nullable=False, server_default="0"),
    )
    assignments = ", ".join(f"{c} = s.{c}" for c in _SCHEDULE_COLUMNS)
    op.execute(
        f"UPDATE pulse_trigger t SET {assignments} FROM pulse_schedule s WHERE s.id = t.id"
    )
    op.drop_table("pulse_schedule")
    op.alter_column("pulse_trigger", "schedule_type", nullable=False)
    op.drop_column("pulse_trigger", "kind")

    for column in ("updated_by_id", "user_id", "workflow_id"):
        op.execute(
            f"ALTER TABLE pulse_trigger RENAME CONSTRAINT "
            f"pulse_trigger_{column}_fkey TO pulse_schedule_{column}_fkey"
        )
    op.execute("ALTER INDEX ix_pulse_trigger_user_id RENAME TO ix_pulse_schedule_user_id")
    op.execute("ALTER INDEX pulse_trigger_pkey RENAME TO pulse_schedule_pkey")
    op.execute("ALTER SEQUENCE pulse_trigger_id_seq RENAME TO pulse_schedule_id_seq")
    op.rename_table("pulse_trigger", "pulse_schedule")
    op.create_index(
        "ix_pulse_schedule_due",
        "pulse_schedule",
        ["next_run_at"],
        postgresql_where=sa.text("enabled"),
    )
