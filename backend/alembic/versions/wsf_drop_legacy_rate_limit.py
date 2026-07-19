"""WS-F: drop the legacy EE token-rate-limit tables

Removes ``token_rate_limit`` and ``token_rate_limit__user_group`` now that the clean-room
``rate_limit_policy`` / ``rate_limit_usage`` subsystem (see ``wsf_rate_limits``) has replaced them.

Revision ID: wsf_drop_legacy_rate_limit
Revises: PLACEHOLDER  (see below)
Create Date: 2026-07-19

INTEGRATOR NOTE (Contract — shared Alembic chain):
- ``down_revision`` is a placeholder. Linearize this revision LAST in the WS-F pair — after
  ``wsf_rate_limits`` and after the new implementation is verified.
- The cloud ``tenant_usage`` meter (EE usage-metering: llm_cost_cents / chunks_indexed / api_calls) is
  NOT dropped here. It is billing/control-plane coupled and woven through indexing, LLM, api-key, and
  reporting paths (WS-A owns billing removal). See ``rewrite-plans/status/WS-F.md`` for the hand-off.
- CONFLICT with WS-B: Contract 1 lists ``token_rate_limit__user_group`` -> ``token_rate_limit__team``
  as a WS-B rename. WS-F removes these tables ENTIRELY, so that rename is redundant. Integrator: drop
  whichever name exists (``token_rate_limit__user_group`` pre-WS-B, ``token_rate_limit__team`` post-WS-B)
  and have WS-B skip renaming the two token_rate_limit tables. The drop below assumes pre-rename names.
"""

from alembic import op

revision = "wsf_drop_legacy_rate_limit"
# Placeholder — integrator linearizes after wsf_rate_limits (and after verification).
down_revision = "wsf_rate_limits"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Child (association) first, then the parent — the association FKs token_rate_limit.id.
    op.drop_table("token_rate_limit__user_group")
    op.drop_table("token_rate_limit")


def downgrade() -> None:
    # Legacy tables are intentionally not recreated (superseded by rate_limit_policy/rate_limit_usage).
    raise NotImplementedError(
        "Legacy token_rate_limit tables were removed by WS-F and are not restorable; "
        "use the rate_limit_policy / rate_limit_usage subsystem instead."
    )
