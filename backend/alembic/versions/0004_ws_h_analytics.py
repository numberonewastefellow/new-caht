"""WS-H: analytics rollups + usage_report + app_settings tables

Revision ID: 0004_ws_h_analytics
Revises: (integrator: linearize off the current head — 0003_agent_rename)
Create Date: 2026-07-19

Clean-room reimplementation of the analytics / query-history / usage-reporting /
enterprise-settings feature set. Adds three NEW per-tenant tables:

- ``analytics_rollup``  — optional per-day materialized usage metrics (cheap charts).
- ``usage_report``      — metadata for generated usage-report CSV bundles.
- ``app_settings``      — typed singleton backing the web ``enterpriseSettings`` gating.

All statements use unqualified (schema-relative) object names so they apply into
whichever schema ``search_path`` / ``schema_translate_map`` points at (the public
schema single-tenant, or the per-tenant schema in multi-tenant mode) — matching the
convention of the existing migrations. ``"user"`` is quoted because it is a reserved
word. The old EE ``usage_reports`` table is dropped by WS-H's final phase (separate
revision / drop), not here.

NOTE (shared-file rule): this revision ships standalone with ``down_revision = None``
as a placeholder; the integrator linearizes the Alembic chain off the current head
``0003_agent_rename``.
"""

from alembic import op

revision = "0004_ws_h_analytics"
# Placeholder per CONTRACTS.md shared-file rule — integrator sets this to the
# current head ("0003_agent_rename") when linearizing the migration chain.
down_revision = "wsg_scim_provisioning"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- analytics_rollup ---------------------------------------------------
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS analytics_rollup (
            id SERIAL PRIMARY KEY,
            window_start DATE NOT NULL,
            metric VARCHAR NOT NULL,
            value DOUBLE PRECISION NOT NULL DEFAULT 0,
            computed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_analytics_rollup_day_metric UNIQUE (window_start, metric)
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_analytics_rollup_window_start "
        "ON analytics_rollup (window_start)"
    )

    # --- usage_report -------------------------------------------------------
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS usage_report (
            id SERIAL PRIMARY KEY,
            report_name VARCHAR NOT NULL,
            file_id VARCHAR NOT NULL,
            requestor_user_id UUID NULL REFERENCES "user" (id) ON DELETE SET NULL,
            period_from TIMESTAMPTZ NULL,
            period_to TIMESTAMPTZ NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_usage_report_report_name UNIQUE (report_name)
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_usage_report_created_at "
        "ON usage_report (created_at)"
    )

    # --- app_settings (typed singleton) ------------------------------------
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS app_settings (
            id SERIAL PRIMARY KEY,
            application_name VARCHAR NULL,
            use_custom_logo BOOLEAN NOT NULL DEFAULT FALSE,
            use_custom_logotype BOOLEAN NOT NULL DEFAULT FALSE,
            logo_display_style VARCHAR NULL,
            custom_nav_items JSONB NULL,
            two_lines_for_chat_header BOOLEAN NULL,
            custom_lower_disclaimer_content TEXT NULL,
            custom_header_content TEXT NULL,
            custom_popup_header TEXT NULL,
            custom_popup_content TEXT NULL,
            enable_consent_screen BOOLEAN NULL,
            consent_screen_prompt TEXT NULL,
            show_first_visit_notice BOOLEAN NULL,
            custom_greeting_message TEXT NULL,
            feature_flags JSONB NULL,
            custom_analytics_script TEXT NULL,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )

    # --- performance indexes for analytics / query-history hot paths --------
    # The aggregations filter every query on (message_type, time_sent) and join
    # chat_message -> chat_session / chat_feedback; the base tables previously
    # had only GIN full-text indexes on these columns. These btree indexes turn
    # the daily roll-ups and the query-history time-range scans from seq scans
    # into index scans. Idempotent so they no-op if an equivalent index exists.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_chat_message_msgtype_time_sent "
        "ON chat_message (message_type, time_sent)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_chat_message_chat_session_id "
        "ON chat_message (chat_session_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_chat_feedback_chat_message_id "
        "ON chat_feedback (chat_message_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_chat_session_time_created "
        "ON chat_session (time_created)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_chat_session_agent_id "
        "ON chat_session (agent_id)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_chat_session_agent_id")
    op.execute("DROP INDEX IF EXISTS ix_chat_session_time_created")
    op.execute("DROP INDEX IF EXISTS ix_chat_feedback_chat_message_id")
    op.execute("DROP INDEX IF EXISTS ix_chat_message_chat_session_id")
    op.execute("DROP INDEX IF EXISTS ix_chat_message_msgtype_time_sent")
    op.execute("DROP TABLE IF EXISTS app_settings")
    op.execute("DROP TABLE IF EXISTS usage_report")
    op.execute("DROP TABLE IF EXISTS analytics_rollup")
