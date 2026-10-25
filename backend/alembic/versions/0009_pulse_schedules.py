"""Pulse: scheduled workflow runs (pulse_schedule, pulse_run, chat_session.pulse_schedule_id)

Revision ID: 0009_pulse_schedules
Revises: 0008_ombot_flow_rename
Create Date: 2026-10-25

Adds the tables behind "Pulse", the scheduled-workflow engine:

* ``pulse_schedule``: one row per schedule (cron / interval / once). The row is
  the source of truth; ``pulse_scheduler`` replicas claim due rows
  (``next_run_at <= now()``, partial index on enabled rows) with
  ``FOR UPDATE SKIP LOCKED``.
* ``pulse_run``: one row per firing. A partial unique index on
  ``(schedule_id, scheduled_for) WHERE trigger = 'scheduled'`` is the
  idempotency key that makes double-firing impossible.
* ``chat_session.pulse_schedule_id``: links a run's chat session back to its
  schedule (sidebar "Scheduled" section, badge, retention).

Purely additive; no data movement.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0009_pulse_schedules"
down_revision = "0008_ombot_flow_rename"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pulse_schedule",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "workflow_id",
            sa.Integer(),
            sa.ForeignKey("agent_workflow.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("schedule_type", sa.String(), nullable=False),
        sa.Column("cron_expression", sa.String(), nullable=True),
        sa.Column("interval_seconds", sa.Integer(), nullable=True),
        sa.Column("run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("timezone", sa.String(), nullable=False, server_default="UTC"),
        sa.Column("input_message", sa.Text(), nullable=False),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_run_status", sa.String(), nullable=True),
        sa.Column(
            "last_success_scheduled_for", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column(
            "consecutive_failures", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("disabled_reason", sa.String(), nullable=True),
        sa.Column(
            "retention_count", sa.Integer(), nullable=False, server_default="50"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_pulse_schedule_user_id", "pulse_schedule", ["user_id"])
    op.create_index(
        "ix_pulse_schedule_due",
        "pulse_schedule",
        ["next_run_at"],
        postgresql_where=sa.text("enabled"),
    )

    op.create_table(
        "pulse_run",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "schedule_id",
            sa.Integer(),
            sa.ForeignKey("pulse_schedule.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "trigger", sa.String(), nullable=False, server_default="scheduled"
        ),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column(
            "chat_session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chat_session.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "workflow_execution_id",
            sa.Integer(),
            sa.ForeignKey("workflow_execution.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("last_enqueued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("worker_hostname", sa.String(), nullable=True),
        sa.Column("output_preview", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("skip_reason", sa.String(), nullable=True),
    )
    op.create_index(
        "uq_pulse_run_schedule_slot",
        "pulse_run",
        ["schedule_id", "scheduled_for"],
        unique=True,
        postgresql_where=sa.text("trigger = 'scheduled'"),
    )
    op.create_index(
        "ix_pulse_run_schedule_created", "pulse_run", ["schedule_id", "created_at"]
    )
    op.create_index(
        "ix_pulse_run_status_heartbeat", "pulse_run", ["status", "heartbeat_at"]
    )
    op.create_index("ix_pulse_run_chat_session_id", "pulse_run", ["chat_session_id"])

    op.add_column(
        "chat_session",
        sa.Column(
            "pulse_schedule_id",
            sa.Integer(),
            sa.ForeignKey("pulse_schedule.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_chat_session_pulse_schedule_id", "chat_session", ["pulse_schedule_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_chat_session_pulse_schedule_id", table_name="chat_session")
    op.drop_column("chat_session", "pulse_schedule_id")
    op.drop_index("ix_pulse_run_chat_session_id", table_name="pulse_run")
    op.drop_index("ix_pulse_run_status_heartbeat", table_name="pulse_run")
    op.drop_index("ix_pulse_run_schedule_created", table_name="pulse_run")
    op.drop_index("uq_pulse_run_schedule_slot", table_name="pulse_run")
    op.drop_table("pulse_run")
    op.drop_index("ix_pulse_schedule_due", table_name="pulse_schedule")
    op.drop_index("ix_pulse_schedule_user_id", table_name="pulse_schedule")
    op.drop_table("pulse_schedule")
