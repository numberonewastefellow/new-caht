# Community 900

> 15 nodes · cohesion 0.18

## Key Concepts

- **test_deploy_module_paths.py** (5 connections) — `backend/tests/unit/migration_safety/test_deploy_module_paths.py`
- **_collect_modules()** (5 connections) — `backend/tests/unit/migration_safety/test_deploy_module_paths.py`
- **_collect_module_paths()** (5 connections) — `backend/tests/unit/migration_safety/test_process_config_module_paths.py`
- **path_to_module()** (4 connections) — `backend/tests/unit/migration_safety/conftest.py`
- **test_process_config_module_paths.py** (4 connections) — `backend/tests/unit/migration_safety/test_process_config_module_paths.py`
- **_command_strings()** (3 connections) — `backend/tests/unit/migration_safety/test_deploy_module_paths.py`
- **test_compose_module_paths_resolve()** (3 connections) — `backend/tests/unit/migration_safety/test_deploy_module_paths.py`
- **test_supervisord_module_paths_resolve()** (3 connections) — `backend/tests/unit/migration_safety/test_process_config_module_paths.py`
- **_compose_files()** (2 connections) — `backend/tests/unit/migration_safety/test_deploy_module_paths.py`
- **_command_lines()** (2 connections) — `backend/tests/unit/migration_safety/test_process_config_module_paths.py`
- **Convert a repo/backend-relative script path to a dotted module.      e.g. "onyx/** (1 connections) — `backend/tests/unit/migration_safety/conftest.py`
- **Every module path in docker-compose service commands must resolve.  Compose `com** (1 connections) — `backend/tests/unit/migration_safety/test_deploy_module_paths.py`
- **Flatten every service command/entrypoint into shell strings.** (1 connections) — `backend/tests/unit/migration_safety/test_deploy_module_paths.py`
- **Every module/script path in supervisord.conf must resolve.  `backend/supervisord** (1 connections) — `backend/tests/unit/migration_safety/test_process_config_module_paths.py`
- **Return (kind, dotted_module) pairs found in command= lines.** (1 connections) — `backend/tests/unit/migration_safety/test_process_config_module_paths.py`

## Relationships

- [[Community 526]] (3 shared connections)

## Source Files

- `backend/tests/unit/migration_safety/conftest.py`
- `backend/tests/unit/migration_safety/test_deploy_module_paths.py`
- `backend/tests/unit/migration_safety/test_process_config_module_paths.py`

## Audit Trail

- EXTRACTED: 35 (85%)
- INFERRED: 6 (15%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*