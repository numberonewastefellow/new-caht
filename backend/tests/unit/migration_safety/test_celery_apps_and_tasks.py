"""Force-resolve the STRING-driven Celery machinery.

These references never fail at app startup -- they fail only when a worker
discovers tasks or beat builds its schedule. This is the core of the rename/
EE-removal safety net:

  * versioned_apps stubs resolve their real app via
    `fetch_versioned_implementation("om.background.celery.apps.X", "celery_app")`
    plus `config_from_object("onyx...configs.X")` -- both STRINGS.
  * each app's `autodiscover_tasks([...])` takes a LIST OF STRING module paths;
    finalizing the app forces every one of them to import.
  * `app_base._VECTOR_DB_TASK_MODULES` is a STRING set (currently including two
    `ee.onyx...` entries that EE-removal must drop/rename).
"""

from __future__ import annotations

import importlib

import pytest
from celery import Celery

from tests.unit.migration_safety.conftest import celery_app_from_module
from tests.unit.migration_safety.conftest import import_module_status
from tests.unit.migration_safety.conftest import qualified
from tests.unit.migration_safety.conftest import resolve_symbol
from tests.unit.migration_safety.conftest import VERSIONED_APP_MODULES


@pytest.mark.parametrize("suffix", VERSIONED_APP_MODULES)
def test_versioned_app_stub_resolves_to_celery(suffix: str) -> None:
    """Each supervisord `celery -A <stub>` entrypoint resolves a real Celery app.

    Importing the stub exercises the string module path passed to
    `fetch_versioned_implementation` (or the static import) AND the app factory's
    `config_from_object("...configs.X")` string. A missed rename here fails import.
    """
    status, result = import_module_status(qualified(suffix))
    if status == "namespace":
        raise AssertionError(f"Namespace/rename error importing {qualified(suffix)}: {result}")
    if status == "env":
        pytest.skip(f"Env gap importing {qualified(suffix)}: {result}")
    app = celery_app_from_module(result)  # type: ignore[arg-type]
    assert isinstance(app, Celery), f"{qualified(suffix)} did not expose a Celery app"


def test_autodiscover_imports_every_task_module(
    worker_celery_apps: list[tuple[str, Celery]],
) -> None:
    """Finalizing each app runs its `autodiscover_tasks([...])` string list.

    The `worker_celery_apps` fixture already finalizes; this asserts the union
    registry is populated, proving the string module paths imported and registered
    their tasks. If any autodiscover string is stale post-rename, finalize raises
    before we get here.
    """
    total = sum(len(app.tasks) for _suffix, app in worker_celery_apps)
    # Sanity floor: the primary app alone registers dozens of tasks.
    assert total > 20, f"Expected many registered tasks, got {total}"


def test_vector_db_task_modules_all_import() -> None:
    """Every string in `_VECTOR_DB_TASK_MODULES` must import.

    This set is read live from the source module, so it is rename-agnostic. After
    EE removal the two `ee.onyx...` entries must be gone/merged -- a leftover
    `ee.<root>...` string here would raise ModuleNotFoundError and fail this test.
    """
    status, app_base = import_module_status(qualified("background.celery.apps.app_base"))
    if status == "namespace":
        raise AssertionError(f"Namespace error importing app_base: {app_base}")
    if status == "env":
        pytest.skip(f"Env gap importing app_base: {app_base}")
    modules: set[str] = app_base._VECTOR_DB_TASK_MODULES  # type: ignore[attr-defined]

    namespace_failures: list[str] = []
    env_skips: list[str] = []
    for module_path in sorted(modules):
        # MIT-or-EE tolerant: some entries are EE-only task modules; on the current
        # tree they resolve via the ee mirror. A leftover onyx/om/ee string that
        # resolves to nothing post-migration is a namespace defect.
        status = resolve_symbol(module_path)
        if status == "namespace":
            namespace_failures.append(module_path)
        elif status == "env":
            env_skips.append(module_path)

    if env_skips:
        print("[vector-db-modules] env-tolerated:\n" + "\n".join(env_skips))

    assert not namespace_failures, (
        "Unresolvable _VECTOR_DB_TASK_MODULES entries (namespace/rename defect):\n"
        + "\n".join(namespace_failures)
    )
