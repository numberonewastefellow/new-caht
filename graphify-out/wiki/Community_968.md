# Community 968

> 13 nodes · cohesion 0.22

## Key Concepts

- **parse_source()** (8 connections) — `backend/tests/unit/migration_safety/conftest.py`
- **_collect_send_task_names()** (6 connections) — `backend/tests/unit/migration_safety/test_celery_send_task_consumers.py`
- **test_alembic_imports.py** (5 connections) — `backend/tests/unit/migration_safety/test_alembic_imports.py`
- **_collect_imported_modules()** (5 connections) — `backend/tests/unit/migration_safety/test_alembic_imports.py`
- **_alembic_files()** (4 connections) — `backend/tests/unit/migration_safety/test_alembic_imports.py`
- **test_alembic_namespace_imports_resolve()** (4 connections) — `backend/tests/unit/migration_safety/test_alembic_imports.py`
- **test_celery_send_task_consumers.py** (3 connections) — `backend/tests/unit/migration_safety/test_celery_send_task_consumers.py`
- **_is_namespace_module()** (2 connections) — `backend/tests/unit/migration_safety/test_alembic_imports.py`
- **test_send_task_producers_have_consumers()** (2 connections) — `backend/tests/unit/migration_safety/test_celery_send_task_consumers.py`
- **Module** (1 connections) — `backend/tests/unit/migration_safety/conftest.py`
- **Every `onyx`-namespace import in Alembic files must resolve.  The `alembic/versi** (1 connections) — `backend/tests/unit/migration_safety/test_alembic_imports.py`
- **Every `send_task(<name>)` producer must have a registered consumer.  Tasks are d** (1 connections) — `backend/tests/unit/migration_safety/test_celery_send_task_consumers.py`
- **Return (resolved task-name strings, count of dynamic/unresolved args).** (1 connections) — `backend/tests/unit/migration_safety/test_celery_send_task_consumers.py`

## Relationships

- [[Community 526]] (3 shared connections)
- [[Community 817]] (3 shared connections)
- [[Community 1199]] (1 shared connections)
- [[Community 1027]] (1 shared connections)
- [[Community 1200]] (1 shared connections)

## Source Files

- `backend/tests/unit/migration_safety/conftest.py`
- `backend/tests/unit/migration_safety/test_alembic_imports.py`
- `backend/tests/unit/migration_safety/test_celery_send_task_consumers.py`

## Audit Trail

- EXTRACTED: 32 (74%)
- INFERRED: 11 (26%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*