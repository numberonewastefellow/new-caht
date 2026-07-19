"""rename UserGroup -> Team (tables/columns/constraints/indexes/sequences)

Revision ID: 0004_team_rename
Revises: 0003_agent_rename
Create Date: 2026-07-19

WS-B (Team / RBAC). Pure metadata rename (no data movement), same spirit as
``0003_agent_rename``. Every physical object in the current schema whose name
contains ``user_group`` is renamed by substring-replacing ``user_group`` ->
``team``. That single rule reproduces the renamed ORM in ``models.py`` exactly:

    user_group                      -> team
    user__user_group                -> user__team
    user_group__connector_...       -> team__connector_...
    agent__user_group               -> agent__team          (already agent-* after 0003)
    llm_provider__user_group        -> llm_provider__team
    document_set__user_group        -> document_set__team
    credential__user_group          -> credential__team
    token_rate_limit__user_group    -> token_rate_limit__team   (WS-F FK target)
    mcp_server__user_group          -> mcp_server__team
    user__external_user_group_id    -> user__external_team_id
    public_external_user_group      -> public_external_team
    user_group_id (column)          -> team_id
    external_user_group_id[s]       -> external_team_id[s]   (incl. document.* / hierarchy_node.*)
    user_group_id_seq               -> team_id_seq

It runs AFTER 0003 so the persona->agent objects already exist under their
``agent__user_group`` names. Dynamic catalog-driven DO blocks are used (instead
of a hand-listed statement set) so no object can be missed and the exact
post-0003 constraint/index names never have to be predicted.

Fresh DB + fresh index -> no data migration, no reindex (search ACL prefixes
were renamed in lockstep in the app layer; see DO_NOT_RENAME.md).

INTEGRATOR: standalone WS-B revision. ``down_revision`` points at the documented
current head ``0003_agent_rename``; re-point only when linearizing sibling
Wave-0/1 revisions from other workstreams.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "0004_team_rename"
down_revision = "0003_agent_rename"
branch_labels = None
depends_on = None


# Substring both directions apply against object names in the CURRENT schema.
_FWD = ("user_group", "team")
_REV = ("team", "user_group")

# Tables that this migration owns (post-rename names). The downgrade is scoped to
# exactly this set (+ the two external-array columns below) so it can never touch
# a legitimately ``team``-named object introduced by another workstream.
_TEAM_TABLES = [
    "team",
    "user__team",
    "team__connector_credential_pair",
    "agent__team",
    "llm_provider__team",
    "document_set__team",
    "credential__team",
    "token_rate_limit__team",
    "mcp_server__team",
    "user__external_team_id",
    "public_external_team",
]

# external_user_group_ids array columns live on tables NOT renamed here.
_EXTERNAL_ARRAY_COLUMNS = [
    ("document", "external_team_id", "external_user_group_id"),  # ...ids handled by prefix match
    ("hierarchy_node", "external_team_id", "external_user_group_id"),
]


def _rename_columns(match: str, old: str, new: str) -> None:
    op.execute(
        f"""
        DO $$
        DECLARE r RECORD;
        BEGIN
          FOR r IN
            SELECT table_name, column_name
            FROM information_schema.columns
            WHERE table_schema = current_schema()
              AND column_name LIKE '%{match}%'
          LOOP
            EXECUTE format(
              'ALTER TABLE %I RENAME COLUMN %I TO %I',
              r.table_name, r.column_name, replace(r.column_name, '{old}', '{new}'));
          END LOOP;
        END $$;
        """
    )


def _rename_constraints(match: str, old: str, new: str) -> None:
    op.execute(
        f"""
        DO $$
        DECLARE r RECORD;
        BEGIN
          FOR r IN
            SELECT con.conname, rel.relname AS table_name
            FROM pg_constraint con
            JOIN pg_class rel ON rel.oid = con.conrelid
            JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
            WHERE nsp.nspname = current_schema()
              AND con.conname LIKE '%{match}%'
          LOOP
            EXECUTE format(
              'ALTER TABLE %I RENAME CONSTRAINT %I TO %I',
              r.table_name, r.conname, replace(r.conname, '{old}', '{new}'));
          END LOOP;
        END $$;
        """
    )


def _rename_indexes(match: str, old: str, new: str) -> None:
    op.execute(
        f"""
        DO $$
        DECLARE r RECORD;
        BEGIN
          FOR r IN
            SELECT indexname FROM pg_indexes
            WHERE schemaname = current_schema()
              AND indexname LIKE '%{match}%'
          LOOP
            EXECUTE format(
              'ALTER INDEX %I RENAME TO %I',
              r.indexname, replace(r.indexname, '{old}', '{new}'));
          END LOOP;
        END $$;
        """
    )


def _rename_sequences(match: str, old: str, new: str) -> None:
    op.execute(
        f"""
        DO $$
        DECLARE r RECORD;
        BEGIN
          FOR r IN
            SELECT c.relname FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = current_schema()
              AND c.relkind = 'S'
              AND c.relname LIKE '%{match}%'
          LOOP
            EXECUTE format(
              'ALTER SEQUENCE %I RENAME TO %I',
              r.relname, replace(r.relname, '{old}', '{new}'));
          END LOOP;
        END $$;
        """
    )


def _rename_tables_like(match: str, old: str, new: str) -> None:
    op.execute(
        f"""
        DO $$
        DECLARE r RECORD;
        BEGIN
          FOR r IN
            SELECT tablename FROM pg_tables
            WHERE schemaname = current_schema()
              AND tablename LIKE '%{match}%'
          LOOP
            EXECUTE format(
              'ALTER TABLE %I RENAME TO %I',
              r.tablename, replace(r.tablename, '{old}', '{new}'));
          END LOOP;
        END $$;
        """
    )


def _widen_team_ids(to_type: str) -> None:
    """Change ``team.id`` and every ``team_id`` FK column to ``to_type`` (Contract
    1: ``team.id`` is BIGINT). A referenced column's type cannot be altered while
    FKs point at it, so each FK is captured via ``pg_get_constraintdef`` (which
    preserves ON DELETE etc.), dropped, then re-added verbatim after the widen.
    ``to_type`` is a fixed literal ('bigint' / 'integer'), never user input."""
    op.execute(
        f"""
        DO $$
        DECLARE
          r RECORD;
          fkdefs text[] := '{{}}';
          d text;
        BEGIN
          FOR r IN
            SELECT rel.relname AS tbl, con.conname AS name,
                   pg_get_constraintdef(con.oid) AS def
            FROM pg_constraint con
            JOIN pg_class rel ON rel.oid = con.conrelid
            JOIN pg_class fref ON fref.oid = con.confrelid
            JOIN pg_namespace n ON n.oid = rel.relnamespace
            WHERE con.contype = 'f' AND fref.relname = 'team'
              AND n.nspname = current_schema()
          LOOP
            fkdefs := array_append(
              fkdefs, format('ALTER TABLE %I ADD CONSTRAINT %I %s', r.tbl, r.name, r.def));
            EXECUTE format('ALTER TABLE %I DROP CONSTRAINT %I', r.tbl, r.name);
          END LOOP;

          EXECUTE 'ALTER TABLE team ALTER COLUMN id TYPE {to_type}';

          FOR r IN
            SELECT table_name FROM information_schema.columns
            WHERE table_schema = current_schema() AND column_name = 'team_id'
          LOOP
            EXECUTE format('ALTER TABLE %I ALTER COLUMN team_id TYPE {to_type}', r.table_name);
          END LOOP;

          FOREACH d IN ARRAY fkdefs LOOP
            EXECUTE d;
          END LOOP;
        END $$;
        """
    )


def upgrade() -> None:
    old, new = _FWD
    # Order matters: rename dependent objects (columns/constraints/indexes/
    # sequences) while the tables still carry their old names, then the tables.
    _rename_columns("user_group", old, new)
    _rename_constraints("user_group", old, new)
    _rename_indexes("user_group", old, new)
    _rename_sequences("user_group", old, new)
    _rename_tables_like("user_group", old, new)
    # Contract 1: widen the freshly-named team.id (+ team_id FKs) to BIGINT.
    _widen_team_ids("bigint")


def downgrade() -> None:
    old, new = _REV
    # Narrow team.id (+ team_id FKs) back to INTEGER while still named `team`.
    _widen_team_ids("integer")
    # Scoped reverse: only touch this migration's own tables (+ the two external
    # array columns on document/hierarchy_node) so a ``team``-named object added
    # by another workstream is never rewritten.
    quoted = ", ".join(f"'{t}'" for t in _TEAM_TABLES)

    # 1) columns on our tables, e.g. team_id -> user_group_id, external_team_id -> external_user_group_id
    op.execute(
        f"""
        DO $$
        DECLARE r RECORD;
        BEGIN
          FOR r IN
            SELECT table_name, column_name
            FROM information_schema.columns
            WHERE table_schema = current_schema()
              AND table_name IN ({quoted})
              AND column_name LIKE '%team%'
          LOOP
            EXECUTE format('ALTER TABLE %I RENAME COLUMN %I TO %I',
                           r.table_name, r.column_name, replace(r.column_name, '{old}', '{new}'));
          END LOOP;
        END $$;
        """
    )
    # 2) external array columns on non-renamed tables
    for table, team_col_prefix, _ in _EXTERNAL_ARRAY_COLUMNS:
        op.execute(
            f"""
            DO $$
            DECLARE r RECORD;
            BEGIN
              FOR r IN
                SELECT column_name FROM information_schema.columns
                WHERE table_schema = current_schema()
                  AND table_name = '{table}'
                  AND column_name LIKE '%team%'
              LOOP
                EXECUTE format('ALTER TABLE {table} RENAME COLUMN %I TO %I',
                               r.column_name, replace(r.column_name, '{old}', '{new}'));
              END LOOP;
            END $$;
            """
        )
    # 3) constraints + indexes on our tables
    op.execute(
        f"""
        DO $$
        DECLARE r RECORD;
        BEGIN
          FOR r IN
            SELECT con.conname, rel.relname AS table_name
            FROM pg_constraint con
            JOIN pg_class rel ON rel.oid = con.conrelid
            JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
            WHERE nsp.nspname = current_schema()
              AND rel.relname IN ({quoted})
              AND con.conname LIKE '%team%'
          LOOP
            EXECUTE format('ALTER TABLE %I RENAME CONSTRAINT %I TO %I',
                           r.table_name, r.conname, replace(r.conname, '{old}', '{new}'));
          END LOOP;
        END $$;
        """
    )
    op.execute(
        f"""
        DO $$
        DECLARE r RECORD;
        BEGIN
          FOR r IN
            SELECT i.indexname FROM pg_indexes i
            WHERE i.schemaname = current_schema()
              AND i.tablename IN ({quoted})
              AND i.indexname LIKE '%team%'
          LOOP
            EXECUTE format('ALTER INDEX %I RENAME TO %I',
                           r.indexname, replace(r.indexname, '{old}', '{new}'));
          END LOOP;
        END $$;
        """
    )
    # 4) sequence team_id_seq -> user_group_id_seq
    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
                     WHERE n.nspname = current_schema() AND c.relkind = 'S'
                       AND c.relname = 'team_id_seq') THEN
            EXECUTE 'ALTER SEQUENCE team_id_seq RENAME TO user_group_id_seq';
          END IF;
        END $$;
        """
    )
    # 5) tables last
    op.execute(
        f"""
        DO $$
        DECLARE r RECORD;
        BEGIN
          FOR r IN SELECT unnest(ARRAY[{quoted}]) AS t LOOP
            IF EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = current_schema() AND tablename = r.t) THEN
              EXECUTE format('ALTER TABLE %I RENAME TO %I', r.t, replace(r.t, '{old}', '{new}'));
            END IF;
          END LOOP;
        END $$;
        """
    )
