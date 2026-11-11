# Module-path safety suite

Force-resolves every **static and string/dynamic** module reference in the backend, so a
moved or renamed module cannot silently break a Celery worker, beat schedule, dynamic
import, or registry lookup.

**Why it exists:** a broken static `import om.x` fails loudly at startup. The real
danger is string-quoted / dynamically-imported paths (Celery `-A` app strings,
`autodiscover_tasks([...])` lists, beat task names, `importlib.import_module(<string>)`,
connector registry `module_path`s). Those fail only when a job runs. This suite
imports/finalizes/AST-scans all of them.

## Environment policy (important)
Failures are classified by the **top-level missing module**:
- `om` / `ee` missing → **real defect → hard fail**.
- any other missing module (a third-party dep absent from a partial env) → **environment
  gap → skip, never fail**.

So on a machine without the full backend deps installed, many tests **skip**. That is
expected. Run it inside the full backend image, where nothing skips:

```bash
DISABLE_TELEMETRY=true   py.test -xv backend/tests/unit/migration_safety
```

## Tiers
1. **Fast tier** (`tests/unit/migration_safety/`, no infra):
   - `test_package_import_walk.py` — walk-import every submodule; fail on namespace errors.
   - `test_celery_apps_and_tasks.py` — versioned-app stubs resolve; autodiscover imports;
     `_VECTOR_DB_TASK_MODULES` resolve.
   - `test_celery_beat_schedule.py` — every scheduled task has a registered consumer.
   - `test_celery_send_task_consumers.py` — every `send_task(name)` has a consumer.
   - `test_fetch_versioned_impl_resolves.py` — every literal `fetch_versioned_*` target
     resolves.
   - `test_importlib_factories.py` — connector/federated registry `module_path`s resolve.
   - `test_process_config_module_paths.py` — `supervisord.conf` `celery -A …` app paths +
     `python …py` scripts resolve.
   - `test_deploy_module_paths.py` — `docker-compose*.yml` `command`/`entrypoint` module
     paths (`uvicorn om.main:app`, `python -m om.mcp_server_main`, `celery -A …`) resolve.
   - `test_alembic_imports.py` — every `om` import in `alembic/env.py`,
     `run_multitenant_migrations.py`, `alembic/versions/*.py`, `alembic_tenants/**`
     resolves (these files live outside the package, so the import-walk misses them).
   - `test_patch_targets_resolve.py`, `test_test_tree_imports.py`,
     `test_no_shadowed_globals.py`, `test_baseline_sql_split.py`,
     `test_no_old_connectors_namespace.py`, `test_datasource_schema_names.py`.
2. **Trigger tier** (`tests/external_dependency_unit/migration_trigger/`, Docker infra —
   Redis/Postgres): actually dispatches tasks (eager mode) to prove name→function binding.
   Runs in the external-dependency-unit CI matrix, not the fast gate.

## Web counterpart
`web/src/__migration__/` (Jest, jsdom): `eeMoveSmoke`, `dynamicImports`, and an exhaustive
`importAll` that evaluates every first-party module and fails only on unresolved `@/…`
paths (ESM/transform noise tolerated). Primary web guard remains `tsc --noEmit` +
`next build`.

```bash
cd web && npx jest --selectProjects integration --testPathPattern "src/__migration__"
```
