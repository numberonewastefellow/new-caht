"""WS-D: standard answers per-tenant config table

Revision ID: wsd_standard_answer_config
Revises: 0003_agent_rename
Create Date: 2026-07-19

Creates the dedicated typed feature-config table ``standard_answer_config`` for the
clean-room standard-answers rewrite. The answer / category / association tables
(``standard_answer``, ``standard_answer_category``,
``standard_answer__standard_answer_category``,
``slack_channel_config__standard_answer_category``, ``chat_message__standard_answer``)
already exist in the folded baseline (``0001_baseline_schema``) with the required
schema, so this revision only adds the new config table.

INTEGRATOR: ``down_revision`` is pinned to the current head as a placeholder. When
linearizing the Wave-1 migrations, re-point it to whatever ends up immediately
preceding this revision in the merged chain (per CONTRACTS.md). The table lives in
the per-tenant schema — do NOT pin it to ``public``.
"""

import sqlalchemy as sa
from alembic import op

revision = "wsd_standard_answer_config"
down_revision = "ws_c_saml_sso"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "standard_answer_config",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "max_matches_per_message",
            sa.Integer(),
            nullable=False,
            server_default="3",
        ),
        sa.Column(
            "match_input_char_limit",
            sa.Integer(),
            nullable=False,
            server_default="8000",
        ),
        sa.Column(
            "time_created",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "time_updated",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("standard_answer_config")
