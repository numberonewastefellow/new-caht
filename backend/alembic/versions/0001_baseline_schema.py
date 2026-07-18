"""baseline schema (squashed)

Revision ID: 0001_baseline_schema
Revises:
Create Date: 2026-07-18

Single baseline that reproduces the full application schema plus the built-in
seed data (built-in tools, the default assistant + its tool links, and the
default search settings). It replaces the entire prior migration history.

`down_revision = None` -- this is the new base of the public Alembic tree.

The DDL + seed SQL lives in the sibling ``0001_baseline_schema.sql`` (a
schema-relative pg_dump of the migrated schema, verified byte-identical to the
old chain's output). It is executed via ``exec_driver_sql`` so the whole
multi-statement script -- including ``$$``-quoted PL/pgSQL function bodies --
runs verbatim without Python-string escaping. The DDL is schema-relative
(unqualified object names) so it applies into whatever schema Alembic's
``search_path`` points at (public for single-tenant, the tenant schema for MT).
"""

from pathlib import Path

from alembic import op

# revision identifiers, used by Alembic.
revision = "0001_baseline_schema"
down_revision = None
branch_labels = None
depends_on = None

_SQL_FILE = Path(__file__).with_suffix(".sql")


def upgrade() -> None:
    op.get_bind().exec_driver_sql(_SQL_FILE.read_text(encoding="utf-8"))


def downgrade() -> None:
    # Tear the schema back down to base: drop every table in the current schema
    # (CASCADE handles FKs/sequences/triggers), then the KG functions and the
    # pg_trgm extension. Leaves only ``alembic_version`` (Alembic owns that).
    op.get_bind().exec_driver_sql(
        """
        DO $$
        DECLARE r RECORD;
        BEGIN
          FOR r IN SELECT tablename FROM pg_tables
                   WHERE schemaname = current_schema()
                     AND tablename <> 'alembic_version' LOOP
            EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
          END LOOP;
        END $$;
        DROP FUNCTION IF EXISTS update_kg_entity_name() CASCADE;
        DROP FUNCTION IF EXISTS update_kg_entity_name_from_doc() CASCADE;
        DROP EXTENSION IF EXISTS pg_trgm;
        """
    )
