"""Every `onyx`-namespace import in Alembic files must resolve.

The 328 `alembic/versions/*.py` migration files, `alembic/env.py`,
`run_multitenant_migrations.py`, and `alembic_tenants/**` all `from onyx.… import …`.
They live OUTSIDE the `onyx` package, so `test_package_import_walk` never touches them
-- yet a missed rename here breaks `alembic upgrade` on container start. This AST-scans
those files (no migration execution) and resolves each imported root-namespace module.

Rename-agnostic (reads current imports) + env-tolerant (only onyx/om/ee failures fail).
"""

from __future__ import annotations

import ast

import pytest

from tests.unit.migration_safety.conftest import backend_root
from tests.unit.migration_safety.conftest import parse_source
from tests.unit.migration_safety.conftest import resolve_symbol

_NAMESPACE_ROOTS = ("onyx", "om", "ee")


def _alembic_files() -> list:
    root = backend_root()
    files: list = []
    for rel in ("alembic/env.py", "alembic/run_multitenant_migrations.py"):
        p = root / rel
        if p.exists():
            files.append(p)
    files.extend(sorted((root / "alembic" / "versions").glob("*.py")))
    tenants = root / "alembic_tenants"
    if tenants.exists():
        files.extend(sorted(tenants.rglob("*.py")))
    return files


def _is_namespace_module(module: str | None) -> bool:
    if not module:
        return False
    top = module.split(".")[0]
    return top in _NAMESPACE_ROOTS


def _collect_imported_modules() -> set[str]:
    modules: set[str] = set()
    for path in _alembic_files():
        tree = parse_source(path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.level == 0 and _is_namespace_module(node.module):
                    modules.add(node.module)  # type: ignore[arg-type]
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if _is_namespace_module(alias.name):
                        modules.add(alias.name)
    return modules


def test_alembic_namespace_imports_resolve() -> None:
    files = _alembic_files()
    assert files, "No alembic files found"
    modules = _collect_imported_modules()
    assert modules, "No onyx-namespace imports found in alembic files (unexpected)"

    namespace_failures: list[str] = []
    env_skips: list[str] = []
    for module in sorted(modules):
        status = resolve_symbol(module)
        if status == "namespace":
            namespace_failures.append(module)
        elif status == "env":
            env_skips.append(module)

    if env_skips:
        print(f"[alembic] env-tolerated {len(env_skips)} modules")

    assert not namespace_failures, (
        "Unresolvable alembic namespace imports (missed rename / dead string):\n"
        + "\n".join(namespace_failures)
    )
