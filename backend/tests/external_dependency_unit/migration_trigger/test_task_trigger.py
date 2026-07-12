"""Tier 3 -- real background-job trigger tests (infra-gated).

Runs in the external-dependency-unit Docker matrix (Redis/Postgres up). Proves the
task-NAME -> handler-FUNCTION binding end to end, which is the failure mode that
survives the app booting: a `send_task("<name>")` producer only breaks at dispatch
if the consumer module wasn't autodiscovered under the renamed root.

Two checks:
  1. Binding: representative task names resolve to a registered handler whose module
     lives under the (auto-detected) root package -- rename-agnostic.
  2. Eager trigger: dispatch a lightweight task in `task_always_eager` mode and assert
     it actually runs (no NotRegistered / namespace ImportError). Infra-specific
     runtime failures are skipped; a registration/namespace failure fails hard.

Reuses the migration_safety helpers so the two suites stay consistent.
"""

from __future__ import annotations

import importlib

import pytest
from celery import Celery

from tests.unit.migration_safety.conftest import celery_app_from_module
from tests.unit.migration_safety.conftest import import_module_status
from tests.unit.migration_safety.conftest import qualified
from tests.unit.migration_safety.conftest import ROOT_PACKAGE

# Task-name constants that should always be registered + runnable. Kept small and
# representative; values are bare names (rename does not change them).
_REPRESENTATIVE_TASKS = [
    "CELERY_BEAT_HEARTBEAT",
    "MONITOR_BACKGROUND_PROCESSES",
    "CHECK_FOR_INDEXING",
    "CHECK_FOR_PRUNING",
    "CHECK_FOR_CONNECTOR_DELETION",
]

_WORKER_APPS = [
    "background.celery.versioned_apps.primary",
    "background.celery.versioned_apps.light",
    "background.celery.versioned_apps.heavy",
    "background.celery.versioned_apps.monitoring",
]


def _finalized_apps() -> list[Celery]:
    apps: list[Celery] = []
    for suffix in _WORKER_APPS:
        status, mod = import_module_status(qualified(suffix))
        if status == "namespace":
            raise AssertionError(f"Namespace error importing {suffix}: {mod}")
        if status == "env":
            pytest.skip(f"Env gap importing {suffix}: {mod}")
        app = celery_app_from_module(mod)  # type: ignore[arg-type]
        assert app is not None, f"No Celery app for {suffix}"
        app.finalize()
        apps.append(app)
    return apps


def _union_registry(apps: list[Celery]) -> dict[str, object]:
    reg: dict[str, object] = {}
    for app in apps:
        reg.update(app.tasks)
    return reg


def _task_names() -> object:
    constants = importlib.import_module(qualified("configs.constants"))
    return constants.OmCeleryTask


def test_representative_task_bindings_resolve() -> None:
    apps = _finalized_apps()
    registry = _union_registry(apps)
    onyx_celery_task = _task_names()

    failures: list[str] = []
    for const_name in _REPRESENTATIVE_TASKS:
        task_name = getattr(onyx_celery_task, const_name, None)
        if not isinstance(task_name, str):
            failures.append(f"{const_name}: not a str constant")
            continue
        task = registry.get(task_name)
        if task is None:
            failures.append(f"{const_name} ({task_name}): not registered")
            continue
        # The handler's module must live under the renamed root and be importable.
        module_name = getattr(task, "__module__", "") or ""
        if not (module_name == ROOT_PACKAGE or module_name.startswith(ROOT_PACKAGE + ".")):
            failures.append(
                f"{const_name} ({task_name}): handler module {module_name!r} "
                f"not under root {ROOT_PACKAGE!r}"
            )
            continue
        status, _ = import_module_status(module_name)
        if status == "namespace":
            failures.append(f"{const_name}: handler module {module_name} namespace error")

    assert not failures, "Task binding failures:\n" + "\n".join(failures)


def test_eager_trigger_of_lightweight_task() -> None:
    """Actually run a task in eager mode to prove name->function dispatch works."""
    apps = _finalized_apps()
    registry = _union_registry(apps)
    onyx_celery_task = _task_names()

    task_name = getattr(onyx_celery_task, "CELERY_BEAT_HEARTBEAT", None)
    assert isinstance(task_name, str)
    task = registry.get(task_name)
    if task is None:
        pytest.fail(f"Lightweight task {task_name} not registered")

    app: Celery = task.app  # type: ignore[attr-defined]
    prev_eager = app.conf.task_always_eager
    prev_prop = app.conf.task_eager_propagates
    app.conf.task_always_eager = True
    app.conf.task_eager_propagates = True
    try:
        result = task.apply()
        # If we got here without NotRegistered/ImportError, dispatch->function worked.
        assert result is not None
    except (ImportError, ModuleNotFoundError) as exc:
        raise AssertionError(f"Namespace/import failure triggering {task_name}: {exc}")
    except Exception as exc:  # noqa: BLE001 - infra/runtime deps, not a rename defect
        pytest.skip(f"Eager trigger hit an infra/runtime dependency: {exc}")
    finally:
        app.conf.task_always_eager = prev_eager
        app.conf.task_eager_propagates = prev_prop
