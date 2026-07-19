"""Per-tenant schema lifecycle + Alembic migration runner (clean-room).

Schema-per-tenant isolation means every tenant owns a Postgres schema and the same
migration chain is applied inside each. This module owns:

* creating / dropping a tenant schema (injection-safe, never touches ``public``),
* running ``alembic upgrade head`` against one schema or all tenant schemas,
* enumerating the existing tenant schemas.

The Alembic ``env.py`` understands the ``-x`` arguments used here
(``schemas=<csv>``, ``create_schema=<bool>``, ``upgrade_all_tenants=true``).
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import text
from sqlalchemy.schema import CreateSchema

from alembic import command
from alembic.config import Config
from om.db.engine.sql_engine import build_connection_string
from om.db.engine.sql_engine import get_sqlalchemy_engine
from om.tenancy.config import POSTGRES_DEFAULT_SCHEMA
from om.tenancy.config import TENANT_ID_PREFIX
from om.tenancy.schema import assert_tenant_id
from om.tenancy.schema import is_safe_schema_name
from om.utils.logger import setup_logger

logger = setup_logger()

# backend/ (parents: [0]=tenancy, [1]=om, [2]=backend)
_BACKEND_DIR = Path(__file__).resolve().parents[2]
_ALEMBIC_INI = _BACKEND_DIR / "alembic.ini"
_ALEMBIC_SCRIPTS = _BACKEND_DIR / "alembic"


def _build_alembic_config() -> Config:
    cfg = Config(str(_ALEMBIC_INI))
    cfg.set_main_option("sqlalchemy.url", build_connection_string())
    cfg.set_main_option("script_location", str(_ALEMBIC_SCRIPTS))
    # Don't let Alembic reconfigure the app's logging.
    cfg.attributes["configure_logger"] = False
    # env.py reads x-arguments off cmd_opts.x
    cfg.cmd_opts = SimpleNamespace()  # type: ignore[attr-defined]
    return cfg


def create_tenant_schema(tenant_id: str) -> bool:
    """Create the tenant's schema if absent. Returns True if it was created.

    Validates the id strictly first so a malformed value can never reach ``CREATE SCHEMA``.
    """
    assert_tenant_id(tenant_id)
    engine = get_sqlalchemy_engine()
    with engine.begin() as conn:
        exists = conn.execute(
            text(
                "SELECT 1 FROM information_schema.schemata WHERE schema_name = :s"
            ),
            {"s": tenant_id},
        ).scalar()
        if exists:
            return False
        conn.execute(CreateSchema(tenant_id))
        logger.info(f"Created schema for tenant {tenant_id}")
        return True


def drop_tenant_schema(tenant_id: str) -> None:
    """Drop a tenant's schema and everything in it. Strictly validated (never ``public``)."""
    assert_tenant_id(tenant_id)
    engine = get_sqlalchemy_engine()
    with engine.begin() as conn:
        conn.execute(text(f'DROP SCHEMA IF EXISTS "{tenant_id}" CASCADE'))
    logger.info(f"Dropped schema for tenant {tenant_id}")


def run_migrations_for_schema(tenant_id: str, *, create_schema: bool = True) -> None:
    """Apply the full migration chain to a single tenant schema."""
    assert_tenant_id(tenant_id)
    logger.info(f"Running migrations for schema {tenant_id}")
    cfg = _build_alembic_config()
    cfg.cmd_opts.x = [  # type: ignore[union-attr]
        f"schemas={tenant_id}",
        f"create_schema={'true' if create_schema else 'false'}",
    ]
    command.upgrade(cfg, "head")
    logger.info(f"Migrations complete for schema {tenant_id}")


def run_migrations_for_all_tenants() -> None:
    """Apply the migration chain to every tenant schema (and the default schema)."""
    logger.info("Running migrations for all tenant schemas")
    cfg = _build_alembic_config()
    cfg.cmd_opts.x = ["upgrade_all_tenants=true"]  # type: ignore[union-attr]
    command.upgrade(cfg, "head")
    logger.info("Migrations complete for all tenant schemas")


def list_tenant_schemas() -> list[str]:
    """Return every provisioned tenant schema name (excludes system + default schemas)."""
    engine = get_sqlalchemy_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT schema_name FROM information_schema.schemata "
                "WHERE schema_name NOT IN "
                "('pg_catalog', 'information_schema', 'pg_toast', :default_schema)"
            ),
            {"default_schema": POSTGRES_DEFAULT_SCHEMA},
        )
        names = [r[0] for r in rows]
    return [
        name
        for name in names
        if name.startswith(TENANT_ID_PREFIX) and is_safe_schema_name(name)
    ]
