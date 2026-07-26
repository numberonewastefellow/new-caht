# Community 526

> 29 nodes · cohesion 0.11

## Key Concepts

- **conftest.py** (20 connections) — `backend/tests/unit/migration_safety/conftest.py`
- **import_module_status()** (11 connections) — `backend/tests/unit/migration_safety/conftest.py`
- **qualified()** (10 connections) — `backend/tests/unit/migration_safety/conftest.py`
- **resolve_symbol()** (10 connections) — `backend/tests/unit/migration_safety/conftest.py`
- **celery_app_from_module()** (7 connections) — `backend/tests/unit/migration_safety/conftest.py`
- **worker_celery_apps()** (7 connections) — `backend/tests/unit/migration_safety/conftest.py`
- **is_namespace_import_error()** (6 connections) — `backend/tests/unit/migration_safety/conftest.py`
- **test_vector_db_task_modules_all_import()** (5 connections) — `backend/tests/unit/migration_safety/test_celery_apps_and_tasks.py`
- **test_versioned_app_stub_resolves_to_celery()** (5 connections) — `backend/tests/unit/migration_safety/test_celery_apps_and_tasks.py`
- **Celery** (4 connections) — `backend/tests/unit/migration_safety/conftest.py`
- **test_factory_module_paths_resolve()** (4 connections) — `backend/tests/unit/migration_safety/test_importlib_factories.py`
- **missing_top_module()** (3 connections) — `backend/tests/unit/migration_safety/conftest.py`
- **_mit_and_ee_variants()** (3 connections) — `backend/tests/unit/migration_safety/conftest.py`
- **union_task_registry()** (3 connections) — `backend/tests/unit/migration_safety/conftest.py`
- **BaseException** (2 connections) — `backend/tests/unit/migration_safety/conftest.py`
- **_detect_root_package()** (2 connections) — `backend/tests/unit/migration_safety/conftest.py`
- **test_importlib_factories.py** (2 connections) — `backend/tests/unit/migration_safety/test_importlib_factories.py`
- **ModuleType** (1 connections) — `backend/tests/unit/migration_safety/conftest.py`
- **Shared fixtures/helpers for the migration-safety suite.  This suite verifies tha** (1 connections) — `backend/tests/unit/migration_safety/conftest.py`
- **Return ("ok", module) | ("namespace", exc) | ("env", exc).      "namespace" = a** (1 connections) — `backend/tests/unit/migration_safety/conftest.py`
- **Candidate real modules for a versioned string.      A `fetch_versioned_implement** (1 connections) — `backend/tests/unit/migration_safety/conftest.py`
- **Return "ok" | "missing_attr" | "namespace" | "env" using MIT-or-EE variants.** (1 connections) — `backend/tests/unit/migration_safety/conftest.py`
- **Prefix a package-relative dotted path with the detected root.** (1 connections) — `backend/tests/unit/migration_safety/conftest.py`
- **Extract the Celery instance a versioned-app stub exposes.      Stubs expose the** (1 connections) — `backend/tests/unit/migration_safety/conftest.py`
- **Import every versioned-app stub, finalize it (forces autodiscovery imports),** (1 connections) — `backend/tests/unit/migration_safety/conftest.py`
- *... and 4 more nodes in this community*

## Relationships

- [[Community 817]] (5 shared connections)
- [[Community 1198]] (5 shared connections)
- [[Community 968]] (3 shared connections)
- [[Community 900]] (3 shared connections)
- [[Community 1549]] (2 shared connections)
- [[Community 923]] (1 shared connections)
- [[Community 1027]] (1 shared connections)
- [[Salesforce Connector]] (1 shared connections)
- [[Community 1409]] (1 shared connections)
- [[Community 1512]] (1 shared connections)
- [[Community 1199]] (1 shared connections)

## Source Files

- `backend/tests/unit/migration_safety/conftest.py`
- `backend/tests/unit/migration_safety/test_celery_apps_and_tasks.py`
- `backend/tests/unit/migration_safety/test_importlib_factories.py`

## Audit Trail

- EXTRACTED: 84 (72%)
- INFERRED: 32 (28%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*