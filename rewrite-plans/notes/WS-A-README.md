# WS-A — Purge: license paywall + billing (README / hand-off)

**Branch:** `rewrite/ws-a` (worktree `.claude/worktrees/ws-a`, off `rename_onyx_to_om`)
**Wave:** 0 · **Type:** deletion + wiring cleanup only (no new features)
**Changeset:** 45 files deleted · 23 modified · 1 added (Alembic revision)

## What was removed and why

The `backend/om/**` tree carried two encumbered/unwanted subsystems that originated
under Onyx's **Enterprise License**:

- **Cluster F — license-key paywall:** signed-license storage, license enforcement
  middleware, seat caps, license-expiry gating.
- **Cluster G — billing half only:** Stripe checkout/subscriptions, HubSpot-billing,
  control-plane/data-plane billing proxy, and product gating.

Deployment target is **self-hosted, MULTI-TENANT for data isolation, NO billing**
(see `CONTRACTS.md`). The paywall and billing are therefore deleted outright rather
than reimplemented. This is the fastest, lowest-risk risk-reduction and unblocks a
clean multi-tenant-no-billing boot.

**Multi-tenant data isolation was left entirely to WS-M.** WS-A did not touch
`user_tenant_mapping`, tenant tracking, schema-per-tenant provisioning, or any
tenant-isolation table/module. `tenant_usage` / `tenant_usage_limits.py` were left to
WS-F (usage redesign).

## Files deleted

**License paywall (Cluster F)**
- `backend/om/db/license.py`, `backend/om/utils/license.py`
- `backend/om/server/license/` (`api.py`, `models.py`)
- `backend/om/server/middleware/license_enforcement.py`
- `backend/om/configs/license_enforcement_config.py`
- `backend/keys/license_public_key.pem`

**Billing (Cluster G — billing only)**
- `backend/om/server/billing/` (`__init__.py`, `api.py`, `service.py`, `models.py`)
- `backend/om/server/tenants/billing.py`, `billing_api.py`, `proxy.py`, `product_gating.py`

**Tests** (dedicated to the above, deleted wholesale): `test_license.py`,
`test_license_utils.py`, `server/license/test_api.py`, `test_license_enforcement.py`,
`test_license_enforcement_settings.py`, `server/billing/*`, `tenants/test_billing_api.py`,
`tenants/test_proxy.py`, `tenants/test_product_gating.py`, `onyxbot/test_slack_gating.py`,
integration `users/test_seat_limit.py`.

**Frontend**
- `web/src/app/admin/billing/` (page + PlansView/CheckoutView/BillingDetailsView/LicenseActivationCard + css)
- `web/src/lib/billing/` (index/interfaces/svc/svc.test)
- `web/src/hooks/useBillingInformation.ts`, `web/src/hooks/useLicense.ts`
- `web/src/components/GatedContentWrapper.tsx`, `web/src/components/errorPages/AccessRestrictedPage.tsx`
- `web/src/sections/sidebar/AdminSidebar.tsx` (dead legacy sidebar)

## Kept / neutralized (NOT deleted)

Billing/license code was referenced by several **kept** files. Rather than delete those
(they own non-billing behavior), the billing/license calls were removed or neutralized:

| File | Change |
|---|---|
| `om/auth/users.py` | `enforce_seat_limit()` → **no-op** (seat caps were license-tied). Signature kept so call sites stay valid. |
| `om/server/scim/api.py` | `_check_seat_availability()` → **returns None** (never blocks). Call-site 403 logic retained. |
| `om/server/manage/users.py` | Removed `register_tenant_users` control-plane seat sync + `invalidate_license_cache` from invite/remove/activate/deactivate/delete. Removed now-unused `DEV_MODE`/`get_live_users_count` imports. |
| `om/onyxbot/slack/listener.py` | `_check_tenant_gated()` → **returns False**; `acquire_tenants` no longer excludes gated tenants; deleted orphaned `_extract_channel_from_request`. |
| `om/onyxbot/slack/handlers/handle_message.py` | Removed the new-user seat-limit block. |
| `om/onyxbot/discord/cache.py` | `refresh_all()` no longer consults `get_gated_tenants` (all tenants refreshed). |
| `om/server/usage_limits.py` | `is_tenant_on_trial()` → **returns False** (no billing ⇒ no trial). **WS-F owns this module** — minimal edit only to unbreak the deleted `fetch_billing_information` import. |
| `om/server/settings/api.py` | Removed `apply_license_status_to_settings` + dead `check_ee_features_enabled`; `GET /settings` no longer applies license gating. |
| `om/server/settings/models.py` | Removed `ee_features_enabled` (license-driven, never consumed). |
| `om/db/models.py` | Removed the `License` ORM model. |
| `om/configs/app_configs.py` | Removed dead `STRIPE_*`, `GATED_TENANTS_KEY`, `LICENSE_ENFORCEMENT_ENABLED`. |
| `om/background/celery/tasks/cloud/tasks.py` | Removed stale commented gating references. |

### Design decisions
- **`application_status` + `ApplicationStatus` enum are KEPT** (backend `settings/models.py` +
  frontend `settings/interfaces.ts`), defaulting to `ACTIVE`. They are general-purpose Settings
  fields; only the *gating behavior* that set them to gated values was removed. This keeps the
  Settings contract aligned across backend/frontend with minimal blast radius.
- **`enforce_seat_limit` / `_check_seat_availability` kept as no-op stubs** so their many call
  sites (and the SCIM 403 path) stay structurally intact for a future re-add if ever needed.
- **Trial invite cap in `bulk_invite_users`** (`is_tenant_on_trial_fn` + `NUM_FREE_TRIAL_USER_INVITES`)
  is **left inert** — it now never triggers (`is_tenant_on_trial` returns False). Left for **WS-F**
  (usage/trial redesign) rather than removed, to avoid touching WS-F territory.

## Out of scope (intentionally untouched)
- **Craft "message limit" usage paywall** (`web/src/app/craft/**` UpgradePlanModal / useUsageLimits):
  a cloud message-rate gate that touches **no** billing/license/Stripe endpoints → WS-F usage territory.
- Tenant data-isolation core (WS-M); `tenant_usage` / `tenant_usage_limits.py` (WS-F).
- `HUBSPOT_TRACKING_URL` + `provisioning.submit_to_hubspot()` — signup **marketing**, not billing (kept).
- control-plane/data-plane token helpers in `tenants/access.py` (`generate_data_plane_token`,
  `control_plane_dep`) — **shared** with kept provisioning/usage code (kept).

---

## Shared-file changes for the INTEGRATOR

These are already applied in the `rewrite/ws-a` worktree. Presented here as the WS-A-owned
edits to the shared files so the integrator can merge them alongside other workstreams.

### 1. `backend/om/main.py` (WS-A owns the billing/license router removals)
Remove imports + registrations; **WS-M owns the tenant-middleware block** — WS-A only removes
the license-enforcement `else` branch (do NOT collapse `MULTI_TENANT`).

```diff
- from om.server.billing.api import router as billing_router
- from om.server.license.api import router as license_router
- from om.server.middleware.license_enforcement import (
-     add_license_enforcement_middleware,
- )
```
```diff
  include_router_with_global_prefix_prepended(application, usage_export_router)
- # License management
- include_router_with_global_prefix_prepended(application, license_router)
-
- # Unified billing API - always registered so frontend doesn't get 404.
- # Works for both self-hosted and cloud deployments.
- include_router_with_global_prefix_prepended(application, billing_router)

  if MULTI_TENANT:
      # Tenant management
      include_router_with_global_prefix_prepended(application, tenants_router)
```
```diff
  # Merged from the former ee/om/main.py.
  if MULTI_TENANT:
      add_api_server_tenant_id_middleware(application, logger)
- else:
-     # License enforcement middleware for self-hosted deployments only.
-     add_license_enforcement_middleware(application, logger)
```
```diff
- logger.notice("Running Enterprise Edition")
-
  uvicorn.run(app, host=APP_HOST, port=APP_PORT)
```

### 2. `backend/om/server/auth_check.py`
Remove the billing/proxy public-endpoint specs from `EE_PUBLIC_ENDPOINT_SPECS` (keep SCIM +
enterprise-settings entries). `control_plane_dep` recognition in `check_router_auth` is KEPT.

```diff
    ("/enterprise-settings/custom-analytics-script", {"GET"}),
-   # Stripe publishable key is safe to expose publicly
-   ("/tenants/stripe-publishable-key", {"GET"}),
-   ("/admin/billing/stripe-publishable-key", {"GET"}),
-   # Proxy endpoints use license-based auth, not user auth
-   ("/proxy/create-checkout-session", {"POST"}),
-   ("/proxy/claim-license", {"POST"}),
-   ("/proxy/create-customer-portal-session", {"POST"}),
-   ("/proxy/billing-information", {"GET"}),
-   ("/proxy/license/{tenant_id}", {"GET"}),
-   ("/proxy/seats/update", {"POST"}),
  ]
```

### 3. `backend/om/server/tenants/api.py` (WS-M-owned aggregator; WS-A removes billing/proxy sub-routers)
```diff
- from om.server.tenants.billing_api import router as billing_router
- from om.server.tenants.proxy import router as proxy_router
```
```diff
  router.include_router(admin_router)
  router.include_router(anonymous_users_router)
- router.include_router(billing_router)
  router.include_router(team_membership_router)
  router.include_router(tenant_management_router)
  router.include_router(user_invitations_router)
- router.include_router(proxy_router)
```

### 4. Frontend menu / settings snippets
- `web/src/components/admin/adminNavItems.ts` — removed the `"Plan & Billing"` nav item, the
  `hasSubscription` param, its `ADMIN_ROUTE_LABELS` + `PATH_GROUP_COLORS` entries, and the
  `SvgWallet` import.
- `web/src/components/admin/ClientLayout.tsx` — removed billing/license hooks, `hasSubscription`,
  the `PAYMENT_REMINDER` banner.
- `web/src/app/layout.tsx` — removed `GatedContentWrapper` gating (children always render).
- `web/src/app/admin/settings/interfaces.ts` — removed `ee_features_enabled`.
- `web/src/components/header/AnnouncementBanner.tsx` — removed the `two_day_trial_ending` billing banner.

### 5. Database migration
`backend/alembic/versions/0004_drop_license.py` (revision `0004_drop_license`,
`down_revision = "0003_agent_rename"`) drops the `license` table.

> **Integrator:** `down_revision` is pinned to the current head so this worktree boots
> standalone. When linearizing the Wave-1 migrations, re-point `down_revision` to whatever
> ends up immediately preceding this revision in the merged chain (per CONTRACTS.md).

Billing has **no dedicated tables** (state lived on the control plane / Stripe / Redis), so
`license` is the only table dropped. Do **not** run `alembic upgrade` by hand — the backend
applies pending migrations on restart.

---

## Verification performed (Wave-0 worktree)
- All 19 changed `.py` files (18 modified + the migration) `py_compile` clean.
- Comprehensive grep: **zero** active imports of deleted modules in `backend/om`; **zero**
  references to removed symbols; no `import stripe`; no `License` model refs.
- Direct import: `settings.models`, `usage_limits`, `scim.api`, `discord.cache` import fully
  clean; the remaining wiring modules fail only on missing 3rd-party pkgs in the partial local
  Python (`sendgrid`/`puremagic`/`braintrust`/`posthog`), never on WS-A changes.
- Frontend: comprehensive grep over `web/src` — zero refs to deleted modules/symbols
  (`useLicense`, `useBillingInformation`, `hasSubscription`, `GatedContentWrapper`, `@stripe`, …).
- Alembic revision chain verified linear/single-head (0001→0002→0003→0004).

## Integrator gates (need the full environment / Docker)
- **Backend:** boot multi-tenant, run `check_ee_router_auth`; confirm `/license*`,
  `/admin/billing*`, `/proxy/*`, `/tenants/stripe-publishable-key` all **404**.
- **Frontend:** `next build` / `tsc --noEmit` (a fresh worktree has no `node_modules`, so WS-A
  could not run it locally).

## Dead-dependency + snapshot cleanup (DONE in review-fix pass)
- **Python `stripe` SDK dep — REMOVED.** Deleted `"stripe==10.12.0"` from the source-of-truth
  root `pyproject.toml` (`backend` extra) AND from `backend/requirements/default.txt` (the file the
  backend Dockerfile installs via `uv pip install -r`), plus its two stale `#   stripe` annotations.
  `hubspot-api-client` kept (data-source connector). **`uv.lock` NOT regenerated here:** `uv lock`
  fails in this detached worktree on a *pre-existing* workspace-member error (`om` referenced in
  `backend/pyproject.toml` `[tool.uv.sources]` but not a workspace member — unrelated to this change),
  and Docker reads `default.txt`, not `uv.lock`. Regenerate `uv.lock` via the `uv-lock` pre-commit
  hook / `uv lock` in a normal checkout (self-heals on commit); it also prunes stripe's transitive deps.
- **npm `@stripe/stripe-js` + `stripe` deps — REMOVED.** Deleted from `web/package.json` and
  regenerated `web/package-lock.json` with `npm install --package-lock-only` (verified diff is
  stripe-only, no unrelated version bumps). `web/Dockerfile` uses `npm ci`, so package.json + lock
  are back in sync — the build is unaffected.
- **Migration-safety golden snapshot — FIXED.** `backend/tests/unit/migration_safety/snapshots/baseline.json`:
  removed exactly the 14 deleted-module entries from `modules`, re-serialized in the test's exact
  capture format (`json.dumps(indent=2, sort_keys=True)+"\n"`). Verified `celery_tasks`/`beat_tasks`/
  `fetch_targets` are UNCHANGED by WS-A (0 billing/license entries in each), so a module-list edit is
  the complete, deterministic equivalent of a `MIGRATION_SNAPSHOT_CAPTURE=1` recapture — this CI unit
  test now passes.

## Follow-ups still for the integrator (need the full/live environment)
- **`backend/tests/route_rename/snapshots/before/`** — this is a **live-only** (`--api-mode=live`,
  not CI) rename-verification harness whose `before/` set is a coherent 480-endpoint point-in-time
  capture (per-endpoint `*.json` + `_summary.json` + `_openapi_schema.json`). 11 entries are for
  WS-A-deleted routes. Left intact deliberately: a partial hand-edit would corrupt the baseline's
  coherence, and the harness recaptures `before/` wholesale on each run — recapture live if it is re-run.
- **Backend boot gate:** boot multi-tenant, run `check_ee_router_auth`; confirm `/license*`,
  `/admin/billing*`, `/proxy/*`, `/tenants/stripe-publishable-key` all **404**.
- **Frontend gate:** `next build` / `tsc --noEmit` (a fresh worktree has no `node_modules`).
- **`uv.lock` regen** (see above) — via the normal `uv lock` / pre-commit hook.
