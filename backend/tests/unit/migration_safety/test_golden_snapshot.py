"""Tier 2 -- golden snapshot with root-name normalization.

Proves the migration changed NOTHING structural, not merely that things resolve.
Capture a normalized inventory on the current tree, then after the `onyx`->`om`
rename + EE removal recompute and assert equality. Normalization strips the leading
root package (`onyx.x` / `om.x` -> `<root>.x`) so the two trees compare equal; a
dropped task, un-discovered module, or dead dynamic target shows up as a diff.

Workflow:
  1. BEFORE migrating, capture the baseline (writes snapshots/baseline.json):
       MIGRATION_SNAPSHOT_CAPTURE=1 py.test tests/unit/migration_safety/test_golden_snapshot.py
     Commit snapshots/baseline.json.
  2. AFTER migrating, just run the suite -- this test recomputes and diffs.

Run inside the FULL backend image so nothing is skipped (a partial env yields a
partial inventory and the test skips rather than diffing).
"""

from __future__ import annotations

import ast
import importlib
import json
import os
import pkgutil
from pathlib import Path

import pytest
from celery import Celery

from tests.unit.migration_safety.conftest import iter_source_files
from tests.unit.migration_safety.conftest import parse_source
from tests.unit.migration_safety.conftest import ROOT_PACKAGE
from tests.unit.migration_safety.conftest import strip_root

_SNAPSHOT = Path(__file__).parent / "snapshots" / "baseline.json"
_CAPTURE = os.environ.get("MIGRATION_SNAPSHOT_CAPTURE") == "1"

# fetch_versioned function names whose (module, attribute) targets we snapshot.
_FETCH_FUNCS = {
    "fetch_versioned_implementation",
    "fetch_versioned_implementation_with_fallback",
    "fetch_ee_implementation_or_noop",
}


def _importable_module_suffixes() -> list[str]:
    """Root-stripped names of every submodule that imports cleanly."""
    root = importlib.import_module(ROOT_PACKAGE)
    ok: list[str] = []
    for _f, name, _p in pkgutil.walk_packages(root.__path__, prefix=root.__name__ + "."):
        try:
            importlib.import_module(name)
        except Exception:  # noqa: BLE001 - env-dependent; snapshot only the importable set
            continue
        ok.append(strip_root(name))
    return sorted(ok)


def _fetch_targets_normalized() -> list[str]:
    targets: set[str] = set()
    for path in iter_source_files():
        tree = parse_source(path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = getattr(func, "id", None) or getattr(func, "attr", None)
            if name not in _FETCH_FUNCS:
                continue
            kw = {k.arg: k.value for k in node.keywords if k.arg}
            m = node.args[0] if node.args else kw.get("module")
            a = node.args[1] if len(node.args) > 1 else kw.get("attribute")
            if (
                isinstance(m, ast.Constant)
                and isinstance(m.value, str)
                and isinstance(a, ast.Constant)
                and isinstance(a.value, str)
            ):
                targets.add(f"{strip_root(m.value)}.{a.value}")
    return sorted(targets)


def _build_inventory(
    union_task_registry: set[str], worker_celery_apps: list[tuple[str, Celery]]
) -> dict[str, object]:
    beat = importlib.import_module(
        f"{ROOT_PACKAGE}.background.celery.tasks.beat_schedule"
    )
    beat_tasks = sorted({e["task"] for e in beat.get_tasks_to_schedule()})
    return {
        "modules": _importable_module_suffixes(),
        "celery_tasks": sorted(union_task_registry),
        "beat_tasks": beat_tasks,
        "fetch_targets": _fetch_targets_normalized(),
    }


def test_golden_snapshot(
    union_task_registry: set[str],
    worker_celery_apps: list[tuple[str, Celery]],
) -> None:
    inventory = _build_inventory(union_task_registry, worker_celery_apps)

    if _CAPTURE:
        _SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
        _SNAPSHOT.write_text(json.dumps(inventory, indent=2, sort_keys=True) + "\n")
        pytest.skip(f"Captured baseline snapshot -> {_SNAPSHOT} (commit it)")

    if not _SNAPSHOT.exists():
        pytest.skip(
            "No baseline snapshot yet. Capture it before migrating with "
            "MIGRATION_SNAPSHOT_CAPTURE=1 (see module docstring)."
        )

    baseline = json.loads(_SNAPSHOT.read_text())
    diffs: list[str] = []
    for key in ("modules", "celery_tasks", "beat_tasks", "fetch_targets"):
        before = set(baseline.get(key, []))
        after = set(inventory[key])  # type: ignore[arg-type]
        missing = sorted(before - after)
        added = sorted(after - before)
        if missing or added:
            diffs.append(f"[{key}] removed={missing}\n[{key}] added={added}")

    assert not diffs, (
        "Normalized inventory changed across migration (something dropped/renamed "
        "wrong):\n" + "\n".join(diffs)
    )
