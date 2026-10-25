"""Regenerate backend/alembic/versions/0001_baseline_schema.sql with the renames folded in.

The baseline must create the FINAL object names (agent, team, ombot_flow, ...) so a fresh install
needs no rename step. It is generated from a database, never edited by hand (revision 0004 also
widens team ids to BIGINT, so text substitution would miss real DDL changes).

Procedure (what produced the committed file; all on throwaway Postgres 15.2 containers):
  1. Load the PREVIOUS baseline (git show <rev>:backend/alembic/versions/0001_baseline_schema.sql).
  2. alembic stamp 0002_workspace_soft_delete; alembic upgrade 0004_team_rename
     (runs the real 0003_agent_rename and 0004_team_rename; 0002 is skipped on purpose because it
      still runs after the new baseline).
  3. psql: ALTER TABLE chat_session RENAME COLUMN onyxbot_flow TO ombot_flow   (revision 0008).
  4. pg_dump -s --no-owner --no-acl            -> schema dump
     pg_dump -a --column-inserts -t agent -t tool -t agent__tool -t search_settings -> seed rows
  5. python gen_baseline_sql.py <old_baseline.sql> <schema_dump.sql> <seed_dump.sql> <out.sql>

Output format matches the previous file: header + pg_trgm line, schema-relative DDL (no ``public.``
qualifiers, no search_path reset), then the seed INSERTs and setval() calls.
"""

import re
import sys
from pathlib import Path

import importlib.util  # noqa: E402

# Reuse the exact splitter the baseline migration itself uses (load the migration file by path).
_spec = importlib.util.spec_from_file_location(
    "baseline_migration",
    Path(__file__).resolve().parent.parent / "backend" / "alembic" / "versions" / "0001_baseline_schema.py",
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
split_sql_statements = _mod._split_statements

CHANGELOG = (
    "-- Renames folded into this baseline (so a fresh install gets the final names directly):\n"
    "--   Project->Workspace, UserFile->KnowledgeFile (earlier), Persona->Agent (0003_agent_rename),\n"
    "--   UserGroup->Team incl. BIGINT ids (0004_team_rename), chat_session.onyxbot_flow->ombot_flow (0008).\n"
    "-- Regenerated from a database with rename-audit/gen_baseline_sql.py; revisions 0003/0004_team_rename/0008\n"
    "-- detect the final names and skip themselves, so existing databases are unaffected.\n"
)


def main(old_path: str, schema_path: str, seed_path: str, out_path: str) -> None:
    old = Path(old_path).read_text(encoding="utf-8")
    schema = Path(schema_path).read_text(encoding="utf-8")
    seed = Path(seed_path).read_text(encoding="utf-8")

    # Header: everything in the old file before the (empty) schema sections.
    marker = "--\n-- Name: public; Type: SCHEMA"
    header = old[: old.index(marker)].rstrip("\n") + "\n"
    header = header.replace(
        "-- pg_trgm is used by KG trigram indexes",
        CHANGELOG + "-- pg_trgm is used by KG trigram indexes",
        1,
    )

    # Body: from the first real object (the KG trigger function) to the end of the schema dump.
    start = schema.index("--\n-- Name: update_kg_entity_name(); Type: FUNCTION")
    body = schema[start:]
    # Schema-relative DDL: drop "public." qualifiers, but leave $$ function bodies untouched
    # (the previous baseline kept e.g. public.show_trgm() inside the trigger function bodies).
    # pg_trgm objects (gin_trgm_ops, ...) live in the public schema and MUST stay qualified,
    # otherwise tenant schemas (search_path = tenant only) cannot resolve them.
    parts = re.split(r"(\$\$.*?\$\$)", body, flags=re.S)
    keep = r"(?!(?:gin|gist)_trgm_ops\b|show_trgm\b)"
    body = "".join(p if p.startswith("$$") else re.sub(r"\bpublic\." + keep, "", p) for p in parts)
    # Alembic owns alembic_version; it exists in the scratch DB only because of `alembic stamp`.
    chunks = re.split(r"(?=\n--\n-- Name: )", body)
    body = "".join(c for c in chunks if not re.match(r"\n?--\n-- Name: alembic_version", c))
    assert "alembic_version" not in body
    assert "set_config('search_path'" not in body

    # Seed rows, in the same order as the previous baseline.
    # pg_dump puts a "-- Data for Name: ..." comment in front of each table's first INSERT.
    stmts = [re.sub(r"\A(?:\s*--[^\n]*\n)+", "", s).strip() for s in split_sql_statements(seed)]
    inserts = [re.sub(r"\AINSERT INTO public\.", "INSERT INTO ", s) for s in stmts if s.upper().startswith("INSERT INTO")]
    order = {"agent": 0, "tool": 1, "agent__tool": 2, "search_settings": 3}
    inserts.sort(key=lambda s: order[re.match(r"INSERT INTO (\w+)", s).group(1)])  # stable
    seed_sql = "".join(s + ";\n" for s in inserts)

    setvals = (
        "\nSELECT setval(pg_get_serial_sequence('tool','id'), (SELECT max(id) FROM tool), true);\n"
        "SELECT setval(pg_get_serial_sequence('search_settings','id'), (SELECT max(id) FROM search_settings), true);\n"
        "SELECT setval(pg_get_serial_sequence('agent','id'), 1, false);\n"
    )

    Path(out_path).write_text(header + "\n" + body.rstrip("\n") + "\n\n" + seed_sql + setvals, encoding="utf-8", newline="\n")
    print(f"wrote {out_path}: {len(inserts)} seed rows")


if __name__ == "__main__":
    main(*sys.argv[1:5])
