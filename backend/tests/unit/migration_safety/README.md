# Migration-safety test suite

Before/after harness that force-resolves every **static and string/dynamic** module
reference in the backend, so the `onyx` → `om` rename + EE removal cannot silently
break a Celery worker, beat schedule, dynamic import, or versioned-dispatch call.

**Why it exists:** static `import onyx.x` breakage fails loudly at startup. The real
danger is string-quoted / dynamically-imported paths (Celery `-A` app strings,
`autodiscover_tasks([...])` lists, `fetch_versioned_implementation("onyx…")`, beat
task names, `importlib.import_module(<string>)`). Those fail only when a job runs. This
suite imports/finalizes/AST-scans all of them.

Every test is an **invariant** — true before and after the migration. Run it green now
(baseline), migrate, run it again; any missed string turns it red.

## Rename-agnostic by construction
- The root package name is **auto-detected** (`onyx` today, `om` after the rename) in
  `conftest.py::_detect_root_package` — nothing to hand-edit. If you rename to something
  other than `om`, add it to `_CANDIDATE_ROOTS`.
- AST-driven tests read the current source, so they check whatever strings exist now.

## Environment policy (important)
Failures are classified by the **top-level missing module**:
- `onyx` / `om` / `ee` missing → **real rename/EE defect → hard fail**.
- any other missing module (a third-party dep absent from a partial env) → **environment
  gap → skip, never fail**.

So on a machine without the full backend deps installed, many tests **skip**. That is
expected. **The real baseline must run inside the full backend image**, where nothing
skips:

```bash
# Fast tier (no infra) — run inside the backend image / full venv:
LICENSE_ENFORCEMENT_ENABLED=false DISABLE_TELEMETRY=true \
  py.test -xv backend/tests/unit/migration_safety
```

## Tiers
1. **Fast invariant tier** (`tests/unit/migration_safety/`, no infra):
   - `test_package_import_walk.py` — walk-import every submodule; fail on namespace errors.
   - `test_celery_apps_and_tasks.py` — versioned-app stubs resolve; autodiscover imports;
     `_VECTOR_DB_TASK_MODULES` (incl. `ee.onyx…`) resolve.
   - `test_celery_beat_schedule.py` — every scheduled task has a registered consumer.
   - `test_celery_send_task_consumers.py` — every `send_task(name)` has a consumer.
   - `test_fetch_versioned_impl_resolves.py` — every literal `fetch_versioned_*` target
     resolves (MIT-or-EE).
   - `test_importlib_factories.py` — connector/federated registry `module_path`s resolve.
   - `test_process_config_module_paths.py` — `supervisord.conf` `celery -A …` app paths +
     `python …py` scripts resolve.
   - `test_deploy_module_paths.py` — `docker-compose*.yml` `command`/`entrypoint` module
     paths (`uvicorn onyx.main:app`, `python -m onyx.mcp_server_main`, `celery -A …`) resolve.
   - `test_alembic_imports.py` — every `onyx`-namespace import in `alembic/env.py`,
     `run_multitenant_migrations.py`, `alembic/versions/*.py` (328), `alembic_tenants/**`
     resolves (these files live outside the package, so the import-walk misses them).
2. **Golden snapshot** (`test_golden_snapshot.py`): capture a root-normalized inventory
   before, compare after — proves nothing was dropped/renamed wrong, not just that things
   resolve.
   ```bash
   # BEFORE migrating (commit the file it writes):
   MIGRATION_SNAPSHOT_CAPTURE=1 py.test tests/unit/migration_safety/test_golden_snapshot.py
   # AFTER migrating — just run the suite; it diffs against snapshots/baseline.json
   ```
3. **Trigger tier** (`tests/external_dependency_unit/migration_trigger/`, Docker infra —
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
