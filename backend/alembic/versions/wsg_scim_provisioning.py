"""WS-G: SCIM 2.0 provisioning tables (clean-room rewrite)

Revision ID: wsg_scim_provisioning
Revises: None  (PLACEHOLDER — see integrator note)
Create Date: 2026-07-19

Replaces the Onyx-EE SCIM tables with a clean-room schema:

* drops the EE ``scim_group_mapping`` (user_group lineage) and re-creates
  ``scim_token`` / ``scim_user_mapping`` so their columns match the WS-G ORM
  models exactly (e.g. ``scim_token.created_by`` — the EE column was
  ``created_by_id``);
* adds ``scim_team_mapping`` mapping a SCIM Group ``externalId`` to a Team
  (Contract 1) via ``team_id -> team.id`` (BIGINT).

The DB + index are fresh (no existing SCIM rows), so drop-and-recreate is safe.
All DDL is schema-relative (unqualified) so it applies into the tenant schema on
the per-tenant migration pass (Contract 3), matching the baseline migration style.

INTEGRATOR NOTE (Contract — shared-file rule): ``down_revision`` is a placeholder.
Linearize this revision **after** ``0003_agent_rename`` AND **after WS-B's team
rename** (``user_group`` -> ``team``), because ``scim_team_mapping.team_id``
references ``team.id``. If WS-B's rename revision is e.g. ``0004_team_rename``,
set ``down_revision = "0004_team_rename"``.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "wsg_scim_provisioning"
down_revision = None  # PLACEHOLDER — integrator linearizes (see module docstring)
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1) Remove EE SCIM tables (created by the squashed baseline). CASCADE drops
    #    their owned sequences and constraints. Fresh DB => no data to preserve.
    op.execute("DROP TABLE IF EXISTS scim_group_mapping CASCADE")
    op.execute("DROP TABLE IF EXISTS scim_user_mapping CASCADE")
    op.execute("DROP TABLE IF EXISTS scim_token CASCADE")

    # 2) scim_token — hashed bearer tokens.
    op.create_table(
        "scim_token",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("hashed_token", sa.String(length=64), nullable=False),
        sa.Column("token_display", sa.String(), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["created_by"], ["user.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint("hashed_token", name="uq_scim_token_hashed_token"),
    )

    # 3) scim_user_mapping — externalId -> User.
    op.create_table(
        "scim_user_mapping",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("external_id", sa.String(), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("external_id", name="uq_scim_user_mapping_external_id"),
        sa.UniqueConstraint("user_id", name="uq_scim_user_mapping_user_id"),
    )

    # 4) scim_team_mapping — SCIM Group externalId -> Team (Contract 1).
    op.create_table(
        "scim_team_mapping",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("external_id", sa.String(), nullable=False),
        sa.Column("team_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["team_id"], ["team.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("external_id", name="uq_scim_team_mapping_external_id"),
        sa.UniqueConstraint("team_id", name="uq_scim_team_mapping_team_id"),
    )


def downgrade() -> None:
    op.drop_table("scim_team_mapping")
    op.drop_table("scim_user_mapping")
    op.drop_table("scim_token")
