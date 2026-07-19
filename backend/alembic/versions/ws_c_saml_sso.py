"""WS-C: SAML SSO clean-room tables

Revision ID: ws_c_saml_sso
Revises: None  (PLACEHOLDER — integrator linearizes off the current head)
Create Date: 2026-07-19

Replaces the legacy EE ``saml`` table (SamlAccount) with the WS-C clean-room
schema:
  * ``sso_saml_config``  — typed, admin-editable SAML configuration (per tenant).
  * ``sso_saml_session`` — cookie↔user session ledger (per tenant).

Both tables live inside the per-tenant schema (Contract 3); Alembic runs per
tenant via the schema translate map, so no explicit schema is set here.

Integrator note: ``down_revision`` is a placeholder. Set it to the real head
(currently ``0003_agent_rename``) when linearizing the migration chain.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "ws_c_saml_sso"
down_revision = "wsm_user_tenant_mapping"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Drop the legacy EE SAML table (fresh DB → safe; IF EXISTS is idempotent).
    op.execute("DROP TABLE IF EXISTS saml")

    # --- Typed SAML config table (singleton row per tenant).
    op.create_table(
        "sso_saml_config",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        # Identity Provider
        sa.Column(
            "idp_entity_id", sa.Text(), nullable=False, server_default=sa.text("''")
        ),
        sa.Column(
            "idp_sso_url", sa.Text(), nullable=False, server_default=sa.text("''")
        ),
        sa.Column("idp_slo_url", sa.Text(), nullable=True),
        sa.Column(
            "idp_x509_cert", sa.Text(), nullable=False, server_default=sa.text("''")
        ),
        # Service Provider
        sa.Column(
            "sp_entity_id", sa.Text(), nullable=False, server_default=sa.text("''")
        ),
        sa.Column(
            "sp_acs_url", sa.Text(), nullable=False, server_default=sa.text("''")
        ),
        sa.Column("sp_slo_url", sa.Text(), nullable=True),
        sa.Column("sp_x509_cert", sa.Text(), nullable=True),
        # Encrypted SP private key (EncryptedString → LargeBinary at rest).
        sa.Column("sp_private_key", sa.LargeBinary(), nullable=True),
        # Security toggles
        sa.Column(
            "want_assertions_signed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "want_messages_signed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "want_name_id_encrypted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "authn_requests_signed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        # Attribute mapping
        sa.Column("email_attribute_keys", postgresql.JSONB(), nullable=True),
        sa.Column("first_name_attribute_key", sa.Text(), nullable=True),
        sa.Column("last_name_attribute_key", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # --- Session ledger (cookie ↔ user, with expiry).
    op.create_table(
        "sso_saml_session",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("encrypted_cookie", sa.Text(), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("sso_saml_session")
    op.drop_table("sso_saml_config")

    # Recreate the legacy EE ``saml`` table so downgrade restores prior schema.
    op.create_table(
        "saml",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("encrypted_cookie", sa.Text(), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
