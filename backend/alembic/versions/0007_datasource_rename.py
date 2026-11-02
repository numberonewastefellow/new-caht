"""rename connector tables, columns and related objects to datasource

Revision ID: 0007_datasource_rename
Revises: 0006_webhook_notify_on_success
Create Date: 2026-11-02

Names only: no rows move and no column types change. Postgres keeps foreign keys,
defaults and owned sequences attached across a rename, so each statement only takes a
short lock. Old and new application code can't run against the same schema, so stop the
workers before this applies.

The lists come from the catalog of the schema before this revision. Exact old names are
listed rather than derived, because names Postgres once truncated (for example
``document_set__connector_crede_...``) can't be rebuilt in reverse. The upgrade fails if
any old-style name is left, which also catches objects added on another branch.

Runs in the schema alembic selects, so tenant schemas work the same way.
"""

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = "0007_datasource_rename"
down_revision = "0006_webhook_notify_on_success"
branch_labels = None
depends_on = None

# (old, new)
_TABLES = (
    ("connector", "datasource"),
    ("connector_credential_pair", "datasource_credential_pair"),
    ("document_by_connector_credential_pair", "document_by_datasource_credential_pair"),
    ("document_set__connector_credential_pair", "document_set__datasource_credential_pair"),
    ("federated_connector", "federated_datasource"),
    ("federated_connector__document_set", "federated_datasource__document_set"),
    ("federated_connector_oauth_token", "federated_datasource_oauth_token"),
    ("team__connector_credential_pair", "team__datasource_credential_pair"),
)

# (old table name, old column, new column)
_COLUMNS = (
    ("background_error", "cc_pair_id", "datasource_credential_pair_id"),
    ("connector", "connector_specific_config", "datasource_specific_config"),
    ("connector_credential_pair", "connector_id", "datasource_id"),
    ("doc_permission_sync_attempt", "connector_credential_pair_id", "datasource_credential_pair_id"),
    ("document_by_connector_credential_pair", "connector_id", "datasource_id"),
    ("document_set__connector_credential_pair", "connector_credential_pair_id", "datasource_credential_pair_id"),
    ("external_group_permission_sync_attempt", "connector_credential_pair_id", "datasource_credential_pair_id"),
    ("federated_connector__document_set", "federated_connector_id", "federated_datasource_id"),
    ("federated_connector_oauth_token", "federated_connector_id", "federated_datasource_id"),
    ("hierarchy_fetch_attempt", "connector_credential_pair_id", "datasource_credential_pair_id"),
    ("index_attempt", "connector_credential_pair_id", "datasource_credential_pair_id"),
    ("index_attempt_errors", "connector_credential_pair_id", "datasource_credential_pair_id"),
    ("public_external_team", "cc_pair_id", "datasource_credential_pair_id"),
    ("team__connector_credential_pair", "cc_pair_id", "datasource_credential_pair_id"),
    ("user__external_team_id", "cc_pair_id", "datasource_credential_pair_id"),
)

# (old table name, old constraint, new constraint). Primary key and unique constraints
# rename their backing index with them.
_CONSTRAINTS = (
    ("background_error", "background_error_cc_pair_id_fkey", "background_error_datasource_credential_pair_id_fkey"),
    ("connector", "connector_pkey", "datasource_pkey"),
    ("connector_credential_pair", "connector_credential_pair__id__key", "datasource_credential_pair__id__key"),
    ("connector_credential_pair", "connector_credential_pair_connector_id_fkey", "datasource_credential_pair_datasource_id_fkey"),
    ("connector_credential_pair", "connector_credential_pair_credential_id_fkey", "datasource_credential_pair_credential_id_fkey"),
    ("connector_credential_pair", "connector_credential_pair_pkey", "datasource_credential_pair_pkey"),
    ("doc_permission_sync_attempt", "doc_permission_sync_attempt_connector_credential_pair_id_fkey", "doc_permission_sync_attempt_datasource_credential_pair_id_fkey"),
    ("document_by_connector_credential_pair", "document_by_connector_credential_pair_connector_id_fkey", "document_by_datasource_credential_pair_datasource_id_fkey"),
    ("document_by_connector_credential_pair", "document_by_connector_credential_pair_credential_id_fkey", "document_by_datasource_credential_pair_credential_id_fkey"),
    ("document_by_connector_credential_pair", "document_by_connector_credential_pair_id_fkey", "document_by_datasource_credential_pair_id_fkey"),
    ("document_by_connector_credential_pair", "document_by_connector_credential_pair_pkey", "document_by_datasource_credential_pair_pkey"),
    ("document_set__connector_credential_pair", "document_set__connector_crede_connector_credential_pair_id_fkey", "document_set__datasource_pair_id_fkey"),
    ("document_set__connector_credential_pair", "document_set__connector_credential_pair_document_set_id_fkey", "document_set__datasource_credential_pair_document_set_id_fkey"),
    ("document_set__connector_credential_pair", "document_set__connector_credential_pair_pkey", "document_set__datasource_credential_pair_pkey"),
    ("external_group_permission_sync_attempt", "external_group_permission_syn_connector_credential_pair_id_fkey", "external_group_permission_syn_datasource_pair_id_fkey"),
    ("federated_connector", "federated_connector_pkey", "federated_datasource_pkey"),
    ("federated_connector__document_set", "federated_connector__document_set_document_set_id_fkey", "federated_datasource__document_set_document_set_id_fkey"),
    ("federated_connector__document_set", "federated_connector__document_set_federated_connector_id_fkey", "federated_datasource__document_set_federated_datasource_id_fkey"),
    ("federated_connector__document_set", "federated_connector__document_set_pkey", "federated_datasource__document_set_pkey"),
    ("federated_connector__document_set", "uq_federated_connector_document_set", "uq_federated_datasource_document_set"),
    ("federated_connector_oauth_token", "federated_connector_oauth_token_federated_connector_id_fkey", "federated_datasource_oauth_token_federated_datasource_id_fkey"),
    ("federated_connector_oauth_token", "federated_connector_oauth_token_pkey", "federated_datasource_oauth_token_pkey"),
    ("federated_connector_oauth_token", "federated_connector_oauth_token_user_id_fkey", "federated_datasource_oauth_token_user_id_fkey"),
    ("hierarchy_fetch_attempt", "hierarchy_fetch_attempt_connector_credential_pair_id_fkey", "hierarchy_fetch_attempt_datasource_credential_pair_id_fkey"),
    ("index_attempt", "fk_index_attempt_connector_credential_pair_id", "fk_index_attempt_datasource_credential_pair_id"),
    ("index_attempt_errors", "index_attempt_errors_connector_credential_pair_id_fkey", "index_attempt_errors_datasource_credential_pair_id_fkey"),
    ("public_external_team", "public_external_team_cc_pair_id_fkey", "public_external_team_datasource_credential_pair_id_fkey"),
    ("team__connector_credential_pair", "team__connector_credential_pair_cc_pair_id_fkey", "team__datasource_pair_id_fkey"),
    ("team__connector_credential_pair", "team__connector_credential_pair_pkey", "team__datasource_credential_pair_pkey"),
    ("team__connector_credential_pair", "team__connector_credential_pair_team_id_fkey", "team__datasource_credential_pair_team_id_fkey"),
    ("user__external_team_id", "fk_user__external_team_id_cc_pair_id", "fk_user__external_team_id_datasource_credential_pair_id"),
)

# Indexes that don't back a constraint: (old, new)
_INDEXES = (
    ("idx_document_cc_pair_connector_credential", "idx_document_datasource_credential_pair_datasource_credential"),
    ("idx_document_cc_pair_counts", "idx_document_datasource_credential_pair_counts"),
    ("ix_document_by_connector_credential_pair_pkey__connecto_27dc", "ix_document_by_datasource_credential_pair_pkey_columns"),
    ("ix_group_sync_attempt_cc_pair_time", "ix_group_sync_attempt_datasource_credential_pair_time"),
    ("ix_hierarchy_fetch_attempt_cc_pair", "ix_hierarchy_fetch_attempt_datasource_credential_pair"),
    ("ix_index_attempt_cc_pair_settings_poll", "ix_index_attempt_datasource_credential_pair_settings_poll"),
    ("ix_index_attempt_ccpair_search_settings_time_updated", "ix_index_attempt_datasource_pair_search_settings_time_updated"),
    ("ix_index_attempt_latest_for_connector_credential_pair", "ix_index_attempt_latest_for_datasource_credential_pair"),
    ("ix_permission_sync_attempt_latest_for_cc_pair", "ix_permission_sync_attempt_latest_for_datasource_pair"),
    ("ix_public_external_team_cc_pair_id_stale", "ix_public_external_team_datasource_credential_pair_id_stale"),
    ("ix_user__external_team_id_cc_pair_id_stale", "ix_user__external_team_id_datasource_credential_pair_id_stale"),
)

# (old, new)
_SEQUENCES = (
    ("connector_credential_pair_id_seq", "datasource_credential_pair_id_seq"),
    ("connector_id_seq", "datasource_id_seq"),
    ("federated_connector__document_set_id_seq", "federated_datasource__document_set_id_seq"),
    ("federated_connector_id_seq", "federated_datasource_id_seq"),
    ("federated_connector_oauth_token_id_seq", "federated_datasource_oauth_token_id_seq"),
)

# "connecto" also catches names Postgres truncated, without matching "mcp_connection".
_OLD_NAME = "connecto|cc_pair|ccpair"


def _constraint_exists(name: str) -> bool:
    return bool(
        op.get_bind()
        .execute(
            text(
                "SELECT 1 FROM pg_constraint WHERE conname = :name "
                "AND connamespace = current_schema()::regnamespace"
            ),
            {"name": name},
        )
        .first()
    )


def _rename_all(forward: bool) -> None:
    """Rename everything, tables last so the other statements can use one table name."""
    new_table_names = dict(_TABLES)

    def table_now(old_table: str) -> str:
        return old_table if forward else new_table_names.get(old_table, old_table)

    for old_table, old_column, new_column in _COLUMNS:
        before, after = (old_column, new_column) if forward else (new_column, old_column)
        op.execute(
            f'ALTER TABLE "{table_now(old_table)}" '
            f'RENAME COLUMN "{before}" TO "{after}"'
        )
    for old_table, old_name, new_name in _CONSTRAINTS:
        before, after = (old_name, new_name) if forward else (new_name, old_name)
        if _constraint_exists(before):
            op.execute(
                f'ALTER TABLE "{table_now(old_table)}" '
                f'RENAME CONSTRAINT "{before}" TO "{after}"'
            )
    for old_name, new_name in _INDEXES:
        before, after = (old_name, new_name) if forward else (new_name, old_name)
        op.execute(f'ALTER INDEX IF EXISTS "{before}" RENAME TO "{after}"')
    for old_name, new_name in _SEQUENCES:
        before, after = (old_name, new_name) if forward else (new_name, old_name)
        op.execute(f'ALTER SEQUENCE IF EXISTS "{before}" RENAME TO "{after}"')
    for old_name, new_name in _TABLES:
        before, after = (old_name, new_name) if forward else (new_name, old_name)
        op.execute(f'ALTER TABLE "{before}" RENAME TO "{after}"')


def _assert_no_old_names_left() -> None:
    left = (
        op.get_bind()
        .execute(
            text(
                """
                SELECT relname FROM pg_class
                WHERE relnamespace = current_schema()::regnamespace
                  AND relkind IN ('r', 'i', 'S') AND relname ~* :pattern
                UNION ALL
                SELECT c.relname || '.' || a.attname FROM pg_attribute a
                JOIN pg_class c ON c.oid = a.attrelid
                WHERE c.relnamespace = current_schema()::regnamespace AND c.relkind = 'r'
                  AND a.attnum > 0 AND NOT a.attisdropped AND a.attname ~* :pattern
                UNION ALL
                SELECT conname FROM pg_constraint
                WHERE connamespace = current_schema()::regnamespace
                  AND conname ~* :pattern
                """
            ),
            {"pattern": _OLD_NAME},
        )
        .scalars()
        .all()
    )
    if left:
        raise RuntimeError(f"Old connector names left after the rename: {sorted(left)}")


def upgrade() -> None:
    _rename_all(forward=True)
    _assert_no_old_names_left()


def downgrade() -> None:
    _rename_all(forward=False)
