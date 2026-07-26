# Community 1512

> 6 nodes · cohesion 0.47

## Key Concepts

- **test_celery_beat_schedule.py** (4 connections) — `backend/tests/unit/migration_safety/test_celery_beat_schedule.py`
- **_beat_module()** (4 connections) — `backend/tests/unit/migration_safety/test_celery_beat_schedule.py`
- **test_cloud_beat_schedule_builds_with_string_task_names()** (3 connections) — `backend/tests/unit/migration_safety/test_celery_beat_schedule.py`
- **test_regular_beat_tasks_have_registered_consumers()** (2 connections) — `backend/tests/unit/migration_safety/test_celery_beat_schedule.py`
- **Every scheduled beat task must resolve to a registered task.  `beat_schedule.py`** (1 connections) — `backend/tests/unit/migration_safety/test_celery_beat_schedule.py`
- **Cloud beat tasks may live in a cloud-only app; here we just assert the     sched** (1 connections) — `backend/tests/unit/migration_safety/test_celery_beat_schedule.py`

## Relationships

- [[Community 526]] (1 shared connections)

## Source Files

- `backend/tests/unit/migration_safety/test_celery_beat_schedule.py`

## Audit Trail

- EXTRACTED: 14 (93%)
- INFERRED: 1 (7%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*