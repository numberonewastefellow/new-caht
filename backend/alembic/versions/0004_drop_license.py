"""WS-A: drop the license paywall table

Revision ID: 0004_drop_license
Revises: 0003_agent_rename
Create Date: 2026-07-19

Removes the ``license`` table that backed the Enterprise-License paywall
(Cluster F). The paywall — signed-license storage, seat caps, license
enforcement middleware, and the billing half of Cluster G — was deleted in
WS-A; this migration drops the now-orphaned table so the physical schema
matches the ORM (the ``License`` model was removed from ``om.db.models``).

Billing has NO dedicated tables of its own (state lived on the external
control plane / Stripe / Redis), so ``license`` is the only table WS-A drops.
Multi-tenant isolation tables and ``tenant_usage`` are intentionally left to
WS-M / WS-F respectively.

INTEGRATOR NOTE (see CONTRACTS.md "Shared-file ownership — Alembic"):
``down_revision`` is pinned to the current head ``0003_agent_rename`` so this
worktree boots and is verifiable standalone. When linearizing the multiple
Wave-1 workstream migrations, re-point ``down_revision`` to whatever ends up
immediately preceding this revision in the merged chain.
"""

import sqlalchemy as sa
from alembic import op

revision = "0004_drop_license"
down_revision = "0004_team_rename"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Dropping the table also drops its primary key, the idx_license_singleton
    # unique index, and the license_id_seq sequence owned by license.id.
    op.drop_table("license")


def downgrade() -> None:
    # Recreate the license table as it existed in 0001_baseline_schema
    # (singleton pattern: a unique index on the constant expression (true)
    # allows only one row).
    op.create_table(
        "license",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("license_data", sa.Text(), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_license_singleton",
        "license",
        [sa.text("(true)")],
        unique=True,
    )
