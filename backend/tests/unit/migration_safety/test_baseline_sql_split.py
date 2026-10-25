"""The baseline migration sends its SQL file to Postgres one statement at a time.

Alembic runs through asyncpg, whose prepared statements accept a single command, so
``0001_baseline_schema`` carries its own splitter (migrations must not import application code).
These tests load that file by path and pin the splitter's behaviour, including a lossless
round trip of the real baseline script.
"""

import importlib.util
import re
from pathlib import Path
from types import ModuleType

VERSIONS = Path(__file__).resolve().parents[3] / "alembic" / "versions"
BASELINE_SQL = VERSIONS / "0001_baseline_schema.sql"


def _load_baseline_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "baseline_migration_under_test", VERSIONS / "0001_baseline_schema.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


split = _load_baseline_migration()._split_statements


def _norm(sql: str) -> str:
    """Whitespace- and comment-insensitive form for comparing a script with its re-joined statements."""
    return re.sub(r"\s+", "", re.sub(r"--[^\n]*", "", sql))


def test_splits_simple_statements() -> None:
    assert split("CREATE TABLE a (id int); CREATE TABLE b (id int);") == [
        "CREATE TABLE a (id int)",
        "CREATE TABLE b (id int)",
    ]


def test_semicolons_inside_strings_identifiers_and_comments_do_not_split() -> None:
    script = """
    -- leading; comment
    INSERT INTO t (a) VALUES ('x;y', 'it''s;fine');
    /* block; comment */ SELECT "we;ird" FROM t;
    """
    stmts = split(script)
    assert len(stmts) == 2
    assert "'x;y'" in stmts[0] and "'it''s;fine'" in stmts[0]
    assert '"we;ird"' in stmts[1]


def test_dollar_quoted_function_body_is_one_statement() -> None:
    script = """
    CREATE FUNCTION f() RETURNS trigger AS $$
    BEGIN
        PERFORM 1; PERFORM 2;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    CREATE TABLE after_fn (id int);
    """
    stmts = split(script)
    assert len(stmts) == 2
    assert stmts[0].count("PERFORM") == 2 and stmts[0].endswith("LANGUAGE plpgsql")
    assert stmts[1] == "CREATE TABLE after_fn (id int)"


def test_tagged_dollar_quotes_and_non_quote_dollars() -> None:
    assert split("SELECT $body$ a; b $body$; SELECT $1; SELECT 2;") == [
        "SELECT $body$ a; b $body$",
        "SELECT $1",
        "SELECT 2",
    ]


def test_comment_only_and_empty_fragments_are_dropped() -> None:
    assert split("-- nothing\n;;  ;\n/* x */;") == []


def test_real_baseline_splits_without_losing_or_cutting_anything() -> None:
    script = BASELINE_SQL.read_text(encoding="utf-8")
    stmts = split(script)
    assert len(stmts) > 200  # tables, constraints, indexes, FKs, 2 functions, seed inserts
    assert all(s.strip() for s in stmts)
    # Re-joining the statements must give back the script (modulo whitespace/comments).
    assert _norm(";".join(stmts) + ";") == _norm(script)
    # The two PL/pgSQL functions must each stay in one piece.
    functions = [s for s in stmts if re.search(r"^\s*CREATE FUNCTION", re.sub(r"--[^\n]*", "", s))]
    assert len(functions) == 2 and all("$$" in f for f in functions)
