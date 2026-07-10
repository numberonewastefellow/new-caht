"""Every scheduled beat task must resolve to a registered task.

`beat_schedule.py` entries reference tasks by NAME string (via `OnyxCeleryTask.*`
constants). The rename doesn't change these bare names, but it CAN break the
autodiscovery of the task's module -- in which case a scheduled task would have no
registered consumer and beat would dispatch into the void. This test builds the
union task registry (from finalized worker apps) and asserts every regular beat
entry's task name is present.
"""

from __future__ import annotations

import importlib

from tests.unit.migration_safety.conftest import qualified


def _beat_module():  # type: ignore[no-untyped-def]
    return importlib.import_module(qualified("background.celery.tasks.beat_schedule"))


def test_regular_beat_tasks_have_registered_consumers(
    union_task_registry: set[str],
) -> None:
    beat = _beat_module()
    entries = beat.get_tasks_to_schedule()
    assert entries, "get_tasks_to_schedule() returned no entries"

    missing: list[str] = []
    for entry in entries:
        task_name = entry["task"]
        assert isinstance(task_name, str) and task_name, f"Bad beat entry: {entry!r}"
        if task_name not in union_task_registry:
            missing.append(f"{entry.get('name', '?')} -> {task_name}")

    assert not missing, (
        "Scheduled beat tasks with no registered consumer (module not discovered?):\n"
        + "\n".join(missing)
    )


def test_cloud_beat_schedule_builds_with_string_task_names() -> None:
    """Cloud beat tasks may live in a cloud-only app; here we just assert the
    schedule generates and every entry carries a non-empty string task name (so a
    stale/None reference surfaces)."""
    beat = _beat_module()
    cloud_entries = beat.get_cloud_tasks_to_schedule(beat_multiplier=1.0)
    assert cloud_entries, "get_cloud_tasks_to_schedule() returned no entries"
    for entry in cloud_entries:
        assert isinstance(entry.get("task"), str) and entry["task"], (
            f"Cloud beat entry missing string task name: {entry!r}"
        )
