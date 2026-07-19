"""WS-F: rate-limit policy + usage roll-up tables

Creates the clean-room rate-limiting schema (``rate_limit_policy`` + ``rate_limit_usage``) that
replaces the EE ``token_rate_limit`` / ``token_rate_limit__user_group`` / ``tenant_usage`` tables.

Revision ID: wsf_rate_limits
Revises: PLACEHOLDER  (see below)
Create Date: 2026-07-19

INTEGRATOR NOTE (Contract — shared Alembic chain):
- ``down_revision`` is a placeholder (``None``). Linearize this revision off the current head.
  It depends on WS-B's ``team`` table (FK ``rate_limit_policy.team_id -> team.id``), so it MUST be
  ordered AFTER WS-B's team-rename revision. It also references ``user.id`` (baseline).
- The old EE tables (``token_rate_limit``, ``token_rate_limit__user_group``, ``tenant_usage``) are
  dropped in WS-F's separate teardown revision (``wsf_drop_legacy_rate_limit``), applied last.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "wsf_rate_limits"
# Placeholder — integrator linearizes off the shared head (after WS-B's team rename).
down_revision = "ws_e_search_expansion_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rate_limit_policy",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("scope", sa.String(), nullable=False),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "team_id",
            sa.BigInteger(),
            sa.ForeignKey("team.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("token_budget", sa.BigInteger(), nullable=False),
        sa.Column("period_hours", sa.Integer(), nullable=False),
        sa.Column(
            "algorithm",
            sa.String(),
            nullable=False,
            server_default="sliding_window",
        ),
        sa.Column(
            "enabled", sa.Boolean(), nullable=False, server_default=sa.true()
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
        sa.UniqueConstraint(
            "scope",
            "user_id",
            "team_id",
            "period_hours",
            name="uq_rate_limit_policy_scope_subject_window",
        ),
    )
    op.create_index(
        "ix_rate_limit_policy_scope", "rate_limit_policy", ["scope"]
    )
    op.create_index(
        "ix_rate_limit_policy_user_id", "rate_limit_policy", ["user_id"]
    )
    op.create_index(
        "ix_rate_limit_policy_team_id", "rate_limit_policy", ["team_id"]
    )

    op.create_table(
        "rate_limit_usage",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("scope", sa.String(), nullable=False),
        sa.Column("subject_key", sa.String(), nullable=False),
        sa.Column("bucket_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "tokens_used", sa.BigInteger(), nullable=False, server_default="0"
        ),
        sa.Column(
            "allowed_count", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "throttled_count", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.UniqueConstraint(
            "scope",
            "subject_key",
            "bucket_start",
            name="uq_rate_limit_usage_scope_subject_bucket",
        ),
    )
    op.create_index(
        "ix_rate_limit_usage_scope_bucket",
        "rate_limit_usage",
        ["scope", "bucket_start"],
    )


def downgrade() -> None:
    op.drop_index("ix_rate_limit_usage_scope_bucket", table_name="rate_limit_usage")
    op.drop_table("rate_limit_usage")
    op.drop_index("ix_rate_limit_policy_team_id", table_name="rate_limit_policy")
    op.drop_index("ix_rate_limit_policy_user_id", table_name="rate_limit_policy")
    op.drop_index("ix_rate_limit_policy_scope", table_name="rate_limit_policy")
    op.drop_table("rate_limit_policy")
