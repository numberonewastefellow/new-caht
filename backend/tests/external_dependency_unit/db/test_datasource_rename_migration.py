"""The 0007_datasource_rename migration, down and up, inside a transaction that is rolled back.

Postgres DDL is transactional, so this runs the real migration functions against whatever
rows the database holds and leaves nothing behind. Migrations are never run through the
alembic CLI: upgrades happen when a backend starts.

Requires Postgres at revision 0007 or later. No LLM calls.
"""

import importlib.util
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType

import pytest
from sqlalchemy import Connection
from sqlalchemy import inspect
from sqlalchemy import text

from alembic.migration import MigrationContext
from alembic.operations import Operations
from om.db.engine.sql_engine import get_sqlalchemy_engine
from om.db.engine.sql_engine import SqlEngine

VERSIONS = Path(__file__).resolve().parents[3] / "alembic" / "versions"

_CATALOG = text(
    """
    SELECT 'column', c.relname, a.attname, format_type(a.atttypid, a.atttypmod)
           || ' notnull=' || a.attnotnull || ' default='
           || coalesce(pg_get_expr(d.adbin, d.adrelid), '')
    FROM pg_attribute a
    JOIN pg_class c ON c.oid = a.attrelid
    LEFT JOIN pg_attrdef d ON d.adrelid = a.attrelid AND d.adnum = a.attnum
    WHERE c.relnamespace = current_schema()::regnamespace AND c.relkind = 'r'
      AND a.attnum > 0 AND NOT a.attisdropped
    UNION ALL
    SELECT 'constraint', conrelid::regclass::text, conname, pg_get_constraintdef(oid)
    FROM pg_constraint WHERE connamespace = current_schema()::regnamespace
    UNION ALL
    SELECT 'index', tablename, indexname, indexdef
    FROM pg_indexes WHERE schemaname = current_schema()
    UNION ALL
    SELECT 'sequence', relname, '', '' FROM pg_class
    WHERE relnamespace = current_schema()::regnamespace AND relkind = 'S'
    ORDER BY 1, 2, 3
    """
)


def _load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "migration_0007", VERSIONS / "0007_datasource_rename.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _row_counts(connection: Connection, tables: list[str]) -> list[int]:
    return [
        connection.execute(text(f'SELECT count(*) FROM "{table}"')).scalar_one()
        for table in tables
    ]


def _max_ids(connection: Connection, tables: list[str]) -> list[int | None]:
    return [
        connection.execute(text(f'SELECT max(id) FROM "{table}"')).scalar_one()
        for table in tables
    ]


@pytest.fixture
def connection() -> Iterator[Connection]:
    SqlEngine.init_engine(pool_size=2, max_overflow=2)
    with get_sqlalchemy_engine().connect() as conn:
        transaction = conn.begin()
        try:
            yield conn
        finally:
            transaction.rollback()


def test_downgrade_restores_old_names_and_upgrade_returns_the_same_schema(
    connection: Connection,
) -> None:
    migration = _load_migration()
    new_tables = [new for _, new in migration._TABLES]
    old_tables = [old for old, _ in migration._TABLES]
    tables_with_id = ["connector_credential_pair", "connector", "federated_connector"]
    catalog = connection.execute(_CATALOG).fetchall()
    counts = _row_counts(connection, new_tables)
    ids = _max_ids(
        connection,
        ["datasource_credential_pair", "datasource", "federated_datasource"],
    )

    with Operations.context(MigrationContext.configure(connection)):
        migration.downgrade()

    names = set(inspect(connection).get_table_names())
    assert set(old_tables) <= names
    assert not set(new_tables) & names
    assert _row_counts(connection, old_tables) == counts
    assert _max_ids(connection, tables_with_id) == ids
    columns = {c["name"] for c in inspect(connection).get_columns("connector_credential_pair")}
    assert "connector_id" in columns
    assert {c["name"] for c in inspect(connection).get_columns("background_error")} >= {
        "cc_pair_id"
    }

    with Operations.context(MigrationContext.configure(connection)):
        migration.upgrade()

    assert connection.execute(_CATALOG).fetchall() == catalog
    assert _row_counts(connection, new_tables) == counts


def test_foreign_keys_still_enforced_after_the_rename(connection: Connection) -> None:
    constraint = connection.execute(
        text(
            """
            SELECT confrelid::regclass::text FROM pg_constraint
            WHERE conname = 'fk_index_attempt_datasource_credential_pair_id'
            """
        )
    ).scalar_one()
    assert constraint == "datasource_credential_pair"


def test_new_rows_still_get_ids_from_the_renamed_sequence(connection: Connection) -> None:
    default = connection.execute(
        text(
            """
            SELECT pg_get_expr(d.adbin, d.adrelid) FROM pg_attrdef d
            JOIN pg_class c ON c.oid = d.adrelid
            JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum = d.adnum
            WHERE c.relname = 'datasource' AND a.attname = 'id'
            """
        )
    ).scalar_one()
    assert "datasource_id_seq" in default
