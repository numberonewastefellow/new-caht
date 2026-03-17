# EE (Enterprise Edition) Removal — Migration Plan

## Overview

This project currently separates "Enterprise Edition" features behind an `ENABLE_PAID_ENTERPRISE_EDITION_FEATURES` environment variable. EE code lives in separate `ee/` folders and is loaded via dynamic imports at runtime.

**Goal**: Remove the EE/MIT split entirely. All features become default. Merge `ee/` code into the main codebase and eliminate all feature-gating machinery.

---

## Scope Summary

| Area | Count | Details |
|------|-------|---------|
| Backend EE Python files | **175** | `backend/ee/onyx/` — mirrors `backend/onyx/` |
| Frontend EE files | **58** | `web/src/ee/` + `web/src/app/ee/` |
| `fetch_versioned_implementation()` calls | **106** across **41 files** | Dynamic import dispatch (core mechanism) |
| `ENABLE_PAID_ENTERPRISE_EDITION_FEATURES` refs | **71** across **45 files** | Env var references |
| `is_ee_version()` checks | **9 files** | Runtime branching |
| `usePaidEnterpriseFeaturesEnabled()` (frontend) | **21 files** | UI feature gating |
| `eeGated()` wrapper | **5 files** | Component-level gating |

---

## How EE Currently Works (3 Mechanisms)

### 1. `fetch_versioned_implementation(module, attr)` — Backend dynamic dispatch

The main backend pattern. If EE is enabled, imports from `ee.{module}` instead of `{module}`. Used **106 times across 41 files**.

```python
# Example: loads ee.onyx.main.get_application when EE is on, else onyx.main.get_application
app = fetch_versioned_implementation(module="onyx.main", attribute="get_application")
```

Defined in `backend/onyx/utils/variable_functionality.py`.

### 2. `global_version.is_ee_version()` — Direct boolean checks

Used in **9 files** for conditional logic like "skip permission sync in non-EE" or "register EE celery tasks."

```python
if global_version.is_ee_version():
    logger.notice("Running Enterprise Edition")
```

### 3. Frontend gating — `usePaidEnterpriseFeaturesEnabled()` + `eeGated()`

- `usePaidEnterpriseFeaturesEnabled()` in **21 files** hides UI elements conditionally
- `eeGated()` wraps 2 providers (AppModeProvider, QueryControllerProvider) so they become no-ops in non-EE

```typescript
// Component hidden when EE is off
export const AppModeProvider = eeGated(EEAppModeProvider);
```

---

## Migration Plan (4 Phases)

### Phase 1: Backend — Merge EE code into main (biggest phase)

#### Phase 1a: Move EE-only modules (no MIT counterpart)

These are net-new features that exist only in `ee/`. Move them directly into `backend/onyx/`:

- `server/analytics/`, `server/billing/`, `server/enterprise_settings/`
- `server/license/`, `server/query_history/`, `server/reporting/`
- `server/scim/`, `server/tenants/`, `server/oauth/`
- `server/token_rate_limits/`, `server/user_group/`
- `server/middleware/license_enforcement.py`, `tenant_tracking.py`
- `external_permissions/` (all 11 connector permission syncs)
- `db/analytics.py`, `db/license.py`, `db/query_history.py`, `db/saml.py`, `db/scim.py`, `db/token_limit.py`, `db/usage_export.py`, `db/user_group.py`
- `configs/app_configs.py` (merge EE-specific vars into main configs)
- `utils/encryption.py`, `utils/license.py`, `utils/posthog_client.py`

**Action**: Move files, update all `from ee.onyx.X import Y` → `from onyx.X import Y`.

#### Phase 1b: Merge EE overrides into MIT counterparts

These exist in BOTH `backend/onyx/` and `backend/ee/onyx/` — the EE version extends or replaces the MIT one:

| EE File | MIT File | Resolution |
|---------|----------|------------|
| `ee/onyx/main.py` | `onyx/main.py` | Merge EE routers + lifespan into main `get_application()` |
| `ee/onyx/access/access.py` | `onyx/access/access.py` | Merge EE access logic (user groups, external perms) |
| `ee/onyx/auth/users.py` | `onyx/auth/users.py` | Merge admin email logic |
| `ee/onyx/db/document_set.py` | `onyx/db/document_set.py` | Merge private doc set functions |
| `ee/onyx/db/persona.py` | `onyx/db/persona.py` | Merge group-based persona access |
| `ee/onyx/db/connector.py` | `onyx/db/connector.py` | Merge permission sync fields |
| `ee/onyx/db/search.py` | `onyx/db/search.py` | Merge query classification |
| `ee/onyx/background/celery_utils.py` | `onyx/background/celery_utils.py` | Merge EE celery config |
| `ee/onyx/background/celery/tasks/` | `onyx/background/celery/tasks/` | Merge EE beat tasks |
| `ee/onyx/server/settings/api.py` | `onyx/server/settings/api.py` | Merge license status into settings |
| All 5 versioned celery apps | Same paths | Remove versioned dispatch |

**Action**: For each pair, merge EE logic into the MIT file, then delete the EE file.

#### Phase 1c: Eliminate `fetch_versioned_implementation()` (41 files, 106 calls)

After 1a+1b, every call becomes a direct import. This is purely mechanical:

```python
# BEFORE
versioned_fn = fetch_versioned_implementation("onyx.db.document_set", "get_private_doc_set")
result = versioned_fn(...)

# AFTER
from onyx.db.document_set import get_private_doc_set
result = get_private_doc_set(...)
```

#### Phase 1d: Remove `global_version` / `is_ee_version()` checks (9 files)

Replace all `if global_version.is_ee_version()` with unconditional execution.

---

### Phase 2: Frontend — Remove EE gating (26 files)

#### Phase 2a: Move `web/src/ee/` contents into main

- `ee/providers/AppModeProvider.tsx` → merge into `providers/AppModeProvider.tsx`
- `ee/providers/QueryControllerProvider.tsx` → merge into `providers/QueryControllerProvider.tsx`
- `ee/sections/SearchCard.tsx`, `SearchUI.tsx` → move to `sections/`
- `ee/lib/search/svc.ts` → move to `lib/search/`

#### Phase 2b: Move `web/src/app/ee/admin/` pages into `web/src/app/admin/`

- `ee/admin/billing/` → `admin/billing/`
- `ee/admin/groups/` → `admin/groups/`
- `ee/admin/performance/` → `admin/performance/`
- `ee/admin/standard-answer/` → `admin/standard-answer/`
- `ee/admin/theme/` → `admin/theme/`

#### Phase 2c: Remove `usePaidEnterpriseFeaturesEnabled()` (21 files)

- Replace all `isPaidEnterpriseFeaturesEnabled` checks with `true` or remove conditional branches
- Delete `web/src/components/settings/usePaidEnterpriseFeaturesEnabled.ts`

#### Phase 2d: Remove `eeGated()` wrapper (5 files)

- Replace `eeGated(Component)` with `Component` directly
- Remove `eeGated` from `web/src/ce.tsx`

#### Phase 2e: Remove `EE_ENABLED` constant

- Delete from `web/src/lib/constants.ts`

---

### Phase 3: Config & Infrastructure cleanup (15 files)

Remove `ENABLE_PAID_ENTERPRISE_EDITION_FEATURES` from:

- Docker compose files (4 files in `deployment/docker_compose/`)
- CI workflows (`.github/workflows/pr-integration-tests.yml`, `pr-playwright-tests.yml`)
- Env templates (`.vscode/env_template.txt`, `deployment/docker_compose/env.template`)
- `backend/onyx/configs/app_configs.py`

Remove `NEXT_PUBLIC_ENABLE_PAID_EE_FEATURES` from env configs.

Remove or gut these modules:

- `backend/onyx/utils/variable_functionality.py` (contains `fetch_versioned_implementation`)
- `global_version` module / `set_is_ee_based_on_env_variable()`

Update Go tooling: `tools/ods/cmd/compose.go`

---

### Phase 4: Final cleanup

- Delete empty `backend/ee/` directory tree
- Delete empty `web/src/ee/` and `web/src/app/ee/` directory trees
- Update test files (18+ integration tests reference the env var — just remove env var setup)
- Relocate `backend/tests/unit/ee/` tests to main test directories
- Remove LICENSE files from ee directories

---

## Risk Assessment

| Risk | Mitigation |
|------|-----------|
| **Import breakage** — 175 files moving, hundreds of import paths change | Phase 1a/1b can be verified with `python -c "import onyx"` and running existing tests |
| **Merge conflicts in overrides** — EE functions may have diverged from MIT | Diff each pair carefully; EE version is always the superset, so keep EE logic |
| **Frontend routing** — Moving `app/ee/admin/*` changes Next.js routes | Verify sidebar links still resolve correctly |
| **Tests** — 18+ integration tests set the env var | Simply remove the env var setup; tests work since features are always on |
| **Celery workers** — 5 versioned apps use `set_is_ee_based_on_env_variable()` | Remove the call; workers always load full functionality |

---

## Recommended Execution Order

1. **Phase 1a** (move net-new EE modules) — safest, no merge conflicts
2. **Phase 1b** (merge overrides) — requires careful review per file pair
3. **Phase 1c** (replace `fetch_versioned_implementation`) — mechanical, after 1a+1b complete
4. **Phase 2** (frontend) — independent of backend, can run in parallel with Phase 1
5. **Phase 3 + 4** (config cleanup) — last, after everything compiles and tests pass

---

## Total Files Affected

- **~233 files** to modify or move (175 backend + 58 frontend)
- **~41 files** with `fetch_versioned_implementation` to simplify
- **~45 files** with env var references to clean up
- **~21 frontend files** with feature flag checks to remove

Each individual change is mechanical and low-risk. The complexity is in the volume, not the logic.
