"""No function may shadow a module-level name it also reads before assigning.

This is the UnboundLocalError class, and it is invisible to every other test in this
suite: the module imports fine, the task registers fine, mypy is happy. It only blows up
when that specific branch executes -- which for a Celery task can be long after deploy.

It shipped for real. Stage 2.3 inlined `fetch_versioned_implementation(...)` call sites
by replacing the CALL with the target's name. Where a call site was SELF-referential --
the target lived in the same module as the caller -- and the result was assigned to a
variable of the SAME NAME as the target:

    monitor_usergroup_taskset = fetch_versioned_implementation(
        "om.background.celery.tasks.vespa.tasks", "monitor_usergroup_taskset"
    )

the rewrite produced `monitor_usergroup_taskset = monitor_usergroup_taskset`. That
assignment makes the name LOCAL to the enclosing function, so the read on its
right-hand side no longer resolves to the module-level function:

    UnboundLocalError: cannot access local variable 'monitor_usergroup_taskset'
                       where it is not associated with a value

check_for_vespa_sync_task raised this on every beat tick until it was caught in the
deploy logs. The suite was 25/25 green the whole time.
"""

from __future__ import annotations

import ast

from tests.unit.migration_safety.conftest import iter_source_files
from tests.unit.migration_safety.conftest import parse_source


def _module_level_names(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                names.add(alias.asname or alias.name.split(".")[0])
    return names


def _offenders_in_function(
    fn: ast.FunctionDef | ast.AsyncFunctionDef, globals_: set[str]
) -> list[tuple[int, str]]:
    """Names made local by an assignment but read at/before that assignment."""
    declared_global = {
        name
        for node in ast.walk(fn)
        if isinstance(node, (ast.Global, ast.Nonlocal))
        for name in node.names
    }

    first_store: dict[str, int] = {}
    first_load: dict[str, int] = {}
    for node in ast.walk(fn):
        if not isinstance(node, ast.Name):
            continue
        if isinstance(node.ctx, ast.Store):
            first_store.setdefault(node.id, node.lineno)
        elif isinstance(node.ctx, ast.Load):
            first_load.setdefault(node.id, node.lineno)

    out: list[tuple[int, str]] = []
    for name, store_line in first_store.items():
        if name in declared_global or name not in globals_:
            continue
        load_line = first_load.get(name)
        # Read at or before the line that makes it local -> UnboundLocalError.
        if load_line is not None and load_line <= store_line:
            out.append((store_line, name))
    return out


def test_no_function_shadows_a_global_it_reads_first() -> None:
    offenders: list[str] = []
    scanned = 0

    for path in iter_source_files():
        tree = parse_source(path)
        if tree is None:
            continue
        scanned += 1
        globals_ = _module_level_names(tree)
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for lineno, name in _offenders_in_function(node, globals_):
                offenders.append(
                    f"{path.name}:{lineno}: {node.name}() assigns {name!r}, making it "
                    f"local, but reads it at/before that line -- UnboundLocalError"
                )

    assert scanned > 100, f"Expected to scan the package, only saw {scanned} files"
    assert not offenders, (
        "Function shadows a module-level name it reads first. Nothing else catches "
        "this: the module imports, the task registers, mypy passes -- it fails only "
        "when the branch runs.\n" + "\n".join(sorted(offenders))
    )
