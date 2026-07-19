"""WS-M: user_tenant_mapping (public, global email -> tenant routing)

Revision ID: wsm_user_tenant_mapping
Revises: None  # PLACEHOLDER — integrator linearizes off current head 0003_agent_rename
Create Date: 2026-07-19

The ``user_tenant_mapping`` table answers "which tenant does this email log in to?"
during authentication, so it MUST live in the global ``public`` schema — it is read
before any tenant schema is bound. The squashed baseline (``0001_baseline_schema``) is a
schema-relative dump applied *per tenant schema*, so it intentionally cannot create a
public-only global table; WS-M owns this one instead (Contract 3 public-schema table
list).

Per the CONTRACTS.md Alembic ownership rule this file ships as a standalone revision with
``down_revision = None`` as a placeholder; the integrator rewrites ``down_revision`` to
chain it onto the linearized public history. The DDL is written ``public``-qualified and
fully idempotent (``IF NOT EXISTS``) so it is safe no matter which schema the linearized
chain happens to execute it against.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "wsm_user_tenant_mapping"
# PLACEHOLDER per CONTRACTS.md (shared-file Alembic rule): integrator linearizes off
# the current head ``0003_agent_rename``.
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Global routing table: (email, tenant_id) composite PK, an ``active`` flag so a user
    # can be moved/deactivated without losing history. ``public``-qualified + idempotent.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS public.user_tenant_mapping (
            email VARCHAR NOT NULL,
            tenant_id VARCHAR NOT NULL,
            active BOOLEAN NOT NULL DEFAULT TRUE,
            CONSTRAINT user_tenant_mapping_pkey PRIMARY KEY (email, tenant_id)
        )
        """
    )
    # Supports "list / count users for a tenant" and "deactivate a whole tenant" without a
    # full-table scan (the composite PK already covers email-prefixed login lookups).
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_user_tenant_mapping_tenant_id "
        "ON public.user_tenant_mapping (tenant_id)"
    )
    # Partial index for the hot login-routing path: active mapping for an email.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_user_tenant_mapping_email_active "
        "ON public.user_tenant_mapping (email) WHERE active"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS public.ix_user_tenant_mapping_email_active")
    op.execute("DROP INDEX IF EXISTS public.ix_user_tenant_mapping_tenant_id")
    op.execute("DROP TABLE IF EXISTS public.user_tenant_mapping")
