"""Enrich Team + membership for the Teams & Members redesign

Revision ID: 0007_team_enrichment
Revises: 0006_drop_ee_cloud_tenants
Create Date: 2026-07-26

Adds the fields the Teams & Members UI needs so the frontend can render a team in
one request:

``team``:
- ``description`` (TEXT, null) — free-text blurb
- ``is_public`` (BOOL, not null, default false) — discoverable/joinable flag
- ``tags`` (JSONB, null) — free-form labels
- ``owner_id`` (FK user.id, null, ON DELETE SET NULL) — the team creator
- ``default_member_role`` (VARCHAR, not null, default 'MEMBER')
- ``allow_guest_access`` (BOOL, not null, default false)

``user__team``:
- ``role`` (VARCHAR, not null, default 'MEMBER') — OWNER/ADMIN/MEMBER, kept in
  sync with ``is_curator`` by the app layer
- ``joined_at`` (TIMESTAMPTZ, null, default now())
- ``source`` (VARCHAR, not null, default 'MANUAL') — SSO/MANUAL

Fresh DB: no data backfill needed (the server-side defaults cover any rows).
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0007_team_enrichment"
down_revision = "0006_drop_ee_cloud_tenants"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- team ---------------------------------------------------------------
    op.add_column("team", sa.Column("description", sa.Text(), nullable=True))
    op.add_column(
        "team",
        sa.Column(
            "is_public",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "team", sa.Column("tags", postgresql.JSONB(), nullable=True)
    )
    op.add_column(
        "team",
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "team_owner_id_fkey",
        "team",
        "user",
        ["owner_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column(
        "team",
        sa.Column(
            "default_member_role",
            sa.String(),
            nullable=False,
            server_default="MEMBER",
        ),
    )
    op.add_column(
        "team",
        sa.Column(
            "allow_guest_access",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )

    # --- user__team ---------------------------------------------------------
    op.add_column(
        "user__team",
        sa.Column(
            "role", sa.String(), nullable=False, server_default="MEMBER"
        ),
    )
    op.add_column(
        "user__team",
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.func.now(),
        ),
    )
    op.add_column(
        "user__team",
        sa.Column(
            "source", sa.String(), nullable=False, server_default="MANUAL"
        ),
    )


def downgrade() -> None:
    op.drop_column("user__team", "source")
    op.drop_column("user__team", "joined_at")
    op.drop_column("user__team", "role")

    op.drop_constraint("team_owner_id_fkey", "team", type_="foreignkey")
    op.drop_column("team", "allow_guest_access")
    op.drop_column("team", "default_member_role")
    op.drop_column("team", "owner_id")
    op.drop_column("team", "tags")
    op.drop_column("team", "is_public")
    op.drop_column("team", "description")
