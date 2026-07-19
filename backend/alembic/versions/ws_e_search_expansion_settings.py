"""WS-E: create search_expansion_settings (per-tenant query-expansion config)

Revision ID: ws_e_search_expansion_settings
Revises: (placeholder — integrator linearizes onto head 0003_agent_rename)
Create Date: 2026-07-19

Standalone revision per the CONTRACTS.md shared-Alembic rule: ``down_revision`` is
a ``None`` placeholder; the integrator re-points it onto the current head when
merging worktrees. Per-tenant table (no schema kwarg) — the tenant Alembic env
applies it inside each tenant schema via schema_translate_map.

Note: the ``search_query`` history table is NOT created here — it already exists
in the baseline schema and WS-E reuses it unchanged.
"""

import sqlalchemy as sa
from alembic import op

revision = "ws_e_search_expansion_settings"
# Placeholder: integrator linearizes onto the current head (0003_agent_rename).
down_revision = "wsd_standard_answer_config"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "search_expansion_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "singleton",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "enable_expansion",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "enable_keyword_expansion",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "enable_semantic_rephrase",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "enable_keyword_history_expansion",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "max_variants", sa.Integer(), nullable=False, server_default=sa.text("3")
        ),
        sa.Column(
            "num_results", sa.Integer(), nullable=False, server_default=sa.text("25")
        ),
        sa.Column(
            "num_retrieved_per_query",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("30"),
        ),
        sa.Column(
            "rrf_k", sa.Integer(), nullable=False, server_default=sa.text("60")
        ),
        sa.Column(
            "original_query_weight",
            sa.Float(),
            nullable=False,
            server_default=sa.text("2.0"),
        ),
        sa.Column(
            "semantic_variant_weight",
            sa.Float(),
            nullable=False,
            server_default=sa.text("1.0"),
        ),
        sa.Column(
            "keyword_variant_weight",
            sa.Float(),
            nullable=False,
            server_default=sa.text("1.0"),
        ),
        sa.Column(
            "enable_llm_section_selection",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("singleton", name="uq_search_expansion_settings_singleton"),
    )


def downgrade() -> None:
    op.drop_table("search_expansion_settings")
