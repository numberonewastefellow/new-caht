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
from pathlib import Path

import pytest
from celery import Celery

from tests.unit.migration_safety.conftest import iter_package_modules
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
    """Root-stripped names of every submodule that imports cleanly.

    File-based walk (conftest.iter_package_modules) -- pkgutil would skip the namespace
    dirs that hold the entire background/celery tree. Includes the EE mirror, whose
    entries `strip_root` COLLAPSES onto their MIT paths (`ee.om.db.license` ->
    `<root>.db.license`), i.e. exactly where EE removal relocates them. So this set is
    a zero-diff invariant across EE removal, not just across the rename.

    Deduped: an EE *override* (a module present in both trees) normalizes to the same
    name as the MIT module it merges into, so it legitimately appears once.
    """
    names = iter_package_modules(ROOT_PACKAGE) + iter_package_modules("ee")
    ok: set[str] = set()
    for name in names:
        try:
            importlib.import_module(name)
        except Exception:  # noqa: BLE001 - env-dependent; snapshot only the importable set
            continue
        normalized = strip_root(name)
        # `ee/om/__init__.py` -> the bare `<root>` sentinel. The root package itself is
        # never enumerated (iter_package_modules skips it), so post-merge there is no
        # such entry. Drop it rather than let it read as a spurious `removed=`.
        if normalized == "<root>":
            continue
        ok.add(normalized)
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


def _beat_task_names() -> list[str]:
    """Beat entries as PRODUCTION resolves them.

    This used to have to go through `fetch_versioned_implementation(...)`, because the
    beat worker did: under EE that returned the EE OVERRIDE of `get_tasks_to_schedule`,
    which appended `ee_tasks_to_schedule` to the MIT list. Importing the MIT module
    directly and calling its `get_tasks_to_schedule` silently missed every EE-only beat
    entry (autogenerate-usage-report, check-ttl-management, export-query-history-cleanup)
    -- i.e. exactly the entries EE removal was most likely to drop on the floor.

    EE removal merged that override into the MIT module and deleted the dispatch hub, so
    the direct call IS the real schedule now. The 22-entry baseline was captured through
    the hub BEFORE the merge, so this still pins the same set: that equality is the proof
    the merge preserved every EE beat entry.
    """
    beat = importlib.import_module(
        f"{ROOT_PACKAGE}.background.celery.tasks.beat_schedule"
    )
    return sorted({e["task"] for e in beat.get_tasks_to_schedule()})


def _build_inventory(
    union_task_registry: set[str], worker_celery_apps: list[tuple[str, Celery]]
) -> dict[str, object]:
    beat_tasks = _beat_task_names()
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

    # Strict equality. `modules` is normalized so the EE mirror collapses onto the MIT
    # path it merges into, and every EE celery/beat task carries an explicit `name=`
    # (verified), so its name is independent of which package it lives in. Therefore EE
    # removal must not perturb ANY of these three -- a diff is a dropped feature.
    for key in ("modules", "celery_tasks", "beat_tasks"):
        before = set(baseline.get(key, []))
        after = set(inventory[key])  # type: ignore[arg-type]
        missing = sorted(before - after)
        added = sorted(after - before)
        if missing or added:
            diffs.append(f"[{key}] removed={missing}\n[{key}] added={added}")

    # `fetch_targets` is the one key that SHOULD shrink: deleting the dynamic-dispatch
    # hub is the point of EE removal, and it ends at zero. So assert direction, not
    # equality -- a target may disappear (converted to a direct import), but a NEW one
    # appearing means either a dispatch call was introduced or a target string was
    # rewritten to the wrong path (which shows up as removed-X + added-Y).
    new_targets = sorted(set(inventory["fetch_targets"]) - set(baseline.get("fetch_targets", [])))  # type: ignore[arg-type]
    if new_targets:
        diffs.append(f"[fetch_targets] added={new_targets} (dispatch targets may only be REMOVED)")

    assert not diffs, (
        "Normalized inventory changed across migration (something dropped/renamed "
        "wrong):\n" + "\n".join(diffs)
    )
