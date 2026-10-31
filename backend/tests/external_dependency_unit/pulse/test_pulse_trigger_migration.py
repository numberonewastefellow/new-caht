"""The 0004_pulse_triggers migration, down and up, inside a transaction that is rolled back.

Postgres DDL is transactional, so this exercises the real migration functions against
whatever rows the database holds and leaves nothing behind. Migrations are never run
through the alembic CLI: upgrades happen when a backend starts.

Requires Postgres. No LLM calls.
"""

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import Connection
from sqlalchemy import inspect
from sqlalchemy import text

from om.db.engine.sql_engine import get_sqlalchemy_engine
from om.db.engine.sql_engine import SqlEngine

VERSIONS = Path(__file__).resolve().parents[3] / "alembic" / "versions"

_TRIGGER_SNAPSHOT = text(
    """
    SELECT t.id, t.workflow_id, t.user_id, t.name, t.enabled, t.timezone, t.input_message,
           t.retention_count, t.last_run_status, t.consecutive_failures,
           s.schedule_type, s.cron_expression, s.interval_seconds, s.next_run_at,
           s.last_success_scheduled_for, s.input_mode, s.input_prompt, s.input_item_index
    FROM pulse_trigger t JOIN pulse_schedule s ON s.id = t.id
    ORDER BY t.id
    """
)
_OLD_SCHEDULE_SNAPSHOT = text(
    """
    SELECT id, workflow_id, user_id, name, enabled, timezone, input_message,
           retention_count, last_run_status, consecutive_failures,
           schedule_type, cron_expression, interval_seconds, next_run_at,
           last_success_scheduled_for, input_mode, input_prompt, input_item_index
    FROM pulse_schedule
    ORDER BY id
    """
)
# Only schedules exist in the old shape, so downgrade removes other kinds' rows on purpose.
_RUNS = text(
    """
    SELECT count(*), count(DISTINCT r.trigger_id)
    FROM pulse_run r JOIN pulse_trigger t ON t.id = r.trigger_id
    WHERE t.kind = 'schedule'
    """
)
_OLD_RUNS = text("SELECT count(*), count(DISTINCT schedule_id) FROM pulse_run")


def _load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "migration_0004", VERSIONS / "0004_pulse_triggers.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _columns(connection: Connection, table: str) -> set[str]:
    return {c["name"] for c in inspect(connection).get_columns(table)}


def _index_names(connection: Connection, table: str) -> set[str]:
    return {i["name"] for i in inspect(connection).get_indexes(table)}


@pytest.fixture
def connection() -> Connection:
    SqlEngine.init_engine(pool_size=2, max_overflow=2)
    with get_sqlalchemy_engine().connect() as conn:
        transaction = conn.begin()
        try:
            yield conn
        finally:
            transaction.rollback()


def test_downgrade_then_upgrade_keeps_every_schedule_and_run(connection: Connection) -> None:
    migration = _load_migration()
    # A webhook, so this also covers downgrade with a kind the old shape can't hold.
    owner = connection.execute(text('SELECT id FROM "user" LIMIT 1')).scalar_one()
    workflow = connection.execute(text("SELECT id FROM agent_workflow LIMIT 1")).scalar_one()
    webhook_id = connection.execute(
        text(
            """
            INSERT INTO pulse_trigger (kind, workflow_id, user_id, name, input_message)
            VALUES ('webhook', :workflow, :owner, 'migration-test', 'x') RETURNING id
            """
        ),
        {"workflow": workflow, "owner": owner},
    ).scalar_one()
    connection.execute(
        text(
            """
            INSERT INTO pulse_webhook (id, token_hash, token_last4, auth_mode, signing_secret, dedup_source)
            VALUES (:id, 'migration-test-hash', 'abcd', 'standard_webhooks', 'x', 'none')
            """
        ),
        {"id": webhook_id},
    )

    triggers = connection.execute(_TRIGGER_SNAPSHOT).fetchall()
    runs = connection.execute(_RUNS).fetchone()
    linked_chats = connection.execute(
        text(
            """
            SELECT count(*) FROM chat_session c JOIN pulse_trigger t ON t.id = c.pulse_trigger_id
            WHERE t.kind = 'schedule'
            """
        )
    ).scalar_one()
    notifications = connection.execute(
        text("SELECT count(*) FROM notification WHERE additional_data ? 'pulse_trigger_id'")
    ).scalar_one()

    context = MigrationContext.configure(connection)
    with Operations.context(context):
        migration.downgrade()

    # The old shape, with the same data.
    assert "pulse_trigger" not in inspect(connection).get_table_names()
    assert "pulse_webhook" not in inspect(connection).get_table_names()
    assert {"dedup_key", "trigger_payload"}.isdisjoint(_columns(connection, "pulse_run"))
    assert {"schedule_type", "next_run_at", "input_mode"} <= _columns(connection, "pulse_schedule")
    assert "kind" not in _columns(connection, "pulse_schedule")
    assert "ix_pulse_schedule_due" in _index_names(connection, "pulse_schedule")
    assert connection.execute(_OLD_SCHEDULE_SNAPSHOT).fetchall() == triggers
    assert connection.execute(_OLD_RUNS).fetchone() == runs
    assert {"schedule_id", "trigger"} <= _columns(connection, "pulse_run")
    assert (
        connection.execute(
            text("SELECT count(*) FROM chat_session WHERE pulse_schedule_id IS NOT NULL")
        ).scalar_one()
        == linked_chats
    )
    assert (
        connection.execute(
            text("SELECT count(*) FROM notification WHERE additional_data ? 'pulse_schedule_id'")
        ).scalar_one()
        == notifications
    )

    with Operations.context(context):
        migration.upgrade()

    # Back to the new shape, with the same data.
    assert connection.execute(_TRIGGER_SNAPSHOT).fetchall() == triggers
    assert connection.execute(_RUNS).fetchone() == runs
    assert "next_run_at" not in _columns(connection, "pulse_trigger")
    assert "dedup_key" in _columns(connection, "pulse_run")
    assert "ix_pulse_schedule_next_run" in _index_names(connection, "pulse_schedule")
