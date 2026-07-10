"""Every `send_task(<name>)` producer must have a registered consumer.

Tasks are dispatched by NAME string (almost always an `OnyxCeleryTask.*` constant).
If a task's module isn't discovered after the rename, the producer still "sends" but
nothing consumes it -- a failure that only shows at dispatch time. This test
AST-scans all producers, resolves each name, and asserts a consumer exists.
"""

from __future__ import annotations

import ast
import importlib

from tests.unit.migration_safety.conftest import iter_source_files
from tests.unit.migration_safety.conftest import parse_source
from tests.unit.migration_safety.conftest import qualified


def _collect_send_task_names() -> tuple[set[str], int]:
    """Return (resolved task-name strings, count of dynamic/unresolved args)."""
    constants = importlib.import_module(qualified("configs.constants"))
    onyx_celery_task = constants.OnyxCeleryTask

    resolved: set[str] = set()
    dynamic = 0

    for path in iter_source_files():
        tree = parse_source(path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not (isinstance(func, ast.Attribute) and func.attr == "send_task"):
                continue
            if not node.args:
                continue
            arg = node.args[0]
            # OnyxCeleryTask.SOME_CONST
            if (
                isinstance(arg, ast.Attribute)
                and isinstance(arg.value, ast.Name)
                and arg.value.id == "OnyxCeleryTask"
            ):
                value = getattr(onyx_celery_task, arg.attr, None)
                if isinstance(value, str):
                    resolved.add(value)
                else:
                    dynamic += 1
            elif isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                resolved.add(arg.value)
            else:
                dynamic += 1

    return resolved, dynamic


def test_send_task_producers_have_consumers(union_task_registry: set[str]) -> None:
    names, dynamic = _collect_send_task_names()
    assert names, "Found no send_task producers to check"
    print(f"[send_task] resolved={len(names)} dynamic/skipped={dynamic}")

    missing = sorted(n for n in names if n not in union_task_registry)
    assert not missing, (
        "Dispatched task names with no registered consumer "
        "(task module not autodiscovered?):\n" + "\n".join(missing)
    )
