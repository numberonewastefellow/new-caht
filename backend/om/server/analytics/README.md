# WS-H — Analytics / Query-History / Reporting / App-Settings

Clean-room reimplementation of the EE-origin analytics, query-history, usage-reporting,
and enterprise-settings feature set. This README covers the whole WS-H module group:

- `om/server/analytics/` — usage analytics dashboard API + aggregation service.
- `om/server/query_history/` — admin query-history browsing + CSV export (new files;
  see `admin_api.py` / `service.py` / `schemas.py`).
- `om/server/reporting/` — usage-report generation + download (new `api.py` / `service.py` /
  `models.py`).
- `om/server/app_settings/` — typed application-settings config table backing the web
  `enterpriseSettings` gating object.
- New tables in `om/db/models.py`; Alembic `0004_ws_h_analytics.py`.
- Frontend admin screens under `web/src/app/admin/performance/{analytics,query-log,reports}/`
  and `web/src/app/admin/app-settings/`, plus menu entries in `web/src/sections/sidebar/AdminSidebar.tsx`.

> **Clean-room note:** every module here was written from the behavior spec in
> `rewrite-plans/WS-H-analytics.md`, not by copying the EE originals. Own module layout,
> own names, own control flow.

---

## 1. Architecture (OOP: models / repositories / services / API)

```
Route (FastAPI, admin-gated, tenant-bound Session via Depends(get_session))
  └─ Service            (business logic, aggregation, CSV/report generation)
       └─ Repository / ORM models   (data access, per-tenant schema)
  └─ Pydantic schemas   (request/response contracts)
  └─ structured_logging (OpenSearch-friendly JSON events)
```

Services **never open their own DB session** — they operate on the tenant-bound session
injected by the route (`Depends(get_session)`), so every query runs inside the current
tenant's Postgres schema (Contract 3). No `{"schema": ...}` kwarg on any new model.

| Concern | Files |
|---|---|
| Analytics | `analytics/{admin_api,service,models,structured_logging}.py` |
| Query history | `query_history/{admin_api,service,schemas}.py` |
| Reporting | `reporting/{api,service,models}.py` |
| App settings | `app_settings/{api,service,repository,models,logo}.py` |

---

## 2. New tables (per-tenant schema)

Defined in `om/db/models.py` under the banner
`# ==== WS-H: analytics / reporting / app-settings models ====`; created by
`alembic/versions/0004_ws_h_analytics.py`.

- **`analytics_rollup`** — optional per-day materialized metric cache
  (`window_start`, `metric`, `value`), unique on `(window_start, metric)`, indexed on
  `window_start`. Cheap chart queries for large/historical ranges; live aggregation
  remains the source of truth.
- **`usage_report`** — generated-report metadata (`report_name` unique, `file_id`,
  `requestor_user_id` FK→`user` SET NULL, `period_from/to`, `created_at` indexed).
- **`app_settings`** — typed singleton (one row per tenant) backing the web
  `enterpriseSettings` object: branding + chat-customization columns + `feature_flags`
  (JSONB) + `custom_analytics_script`.

The migration also adds btree indexes on the analytics/query-history hot paths
(`chat_message(message_type, time_sent)`, `chat_message(chat_session_id)`,
`chat_feedback(chat_message_id)`, `chat_session(time_created)`, `chat_session(agent_id)`) —
previously only GIN full-text indexes existed on those tables.

The Alembic revision ships with `down_revision = None` as a placeholder; per CONTRACTS the
**integrator linearizes** it off the current head `0003_agent_rename`.

---

## 3. Metrics & aggregation model

`AnalyticsService` (`analytics/service.py`) aggregates live over `chat_message` /
`chat_feedback` / `chat_session`:

- **queries** — count of distinct `ASSISTANT` messages per day.
- **active_users** — distinct `chat_session.user_id` with an assistant message that day.
- **likes / dislikes** — `chat_feedback.is_positive` true/false counts per day. Counted in a
  *separate* query from the volume query so the one-to-many feedback join does not inflate
  message/user counts or skew the latency average.
- **avg_latency_ms** — `avg(chat_message.processing_duration_seconds) * 1000`.

`get_summary` returns window totals (KPI tiles); `get_top_agents` returns per-agent message
volume (bar chart). `refresh_rollups` / `get_rollups` materialize + read the
`analytics_rollup` cache.

---

## 4. API endpoints (all admin-gated + tenant-scoped)

Analytics (`analytics/admin_api.py`, prefix `/analytics`):
- `GET  /analytics/admin/usage` → daily time-series
- `GET  /analytics/admin/summary` → KPI totals
- `GET  /analytics/admin/top-agents` → per-agent bar data
- `GET  /analytics/admin/rollups`, `POST /analytics/admin/rollups/refresh`

Query history (`query_history/admin_api.py`, prefix `/admin/query-history`):
- `GET  /admin/query-history/sessions` → paginated (feedback filter + time range)
- `GET  /admin/query-history/sessions/{session_id}` → detail
- `GET  /admin/query-history/export` → **synchronous streaming CSV** of Q&A pairs

Reporting (`reporting/api.py`, prefix `/admin/reports`):
- `POST /admin/reports/usage` → synchronous generate (daily-usage CSV → file store + row)
- `GET  /admin/reports/usage` → list
- `GET  /admin/reports/usage/{report_id}/download` → stream stored CSV

App settings (`app_settings/api.py`, **same paths as the EE surface** so web boot/gating is
unaffected):
- `GET  /enterprise-settings` (public), `PUT /admin/enterprise-settings` (admin)
- `GET  /enterprise-settings/custom-analytics-script` (public), admin PUT
- `GET  /enterprise-settings/logo` + `/logotype` (public), admin `PUT /admin/enterprise-settings/logo`

CSV/report downloads set `Content-Disposition` so the browser downloads via an anchor.

---

## 5. Frontend screens

Under `web/src/app/admin/`:
- `performance/analytics/page.tsx` — KPI tiles + line/bar charts + date-range picker.
- `performance/query-log/page.tsx` — paginated table + feedback filter + detail modal + CSV export.
- `performance/reports/page.tsx` — generate + list + download.
- `app-settings/page.tsx` — branding + chat customization + feature toggles form.

Charts (`performance/analytics/charts.tsx`) use **recharts** with **theme-aware CSS-variable
colors** (`var(--virtualai-accent)`, `var(--theme-primary-04/05/06)`) — never hardcoded accent
colors, so they adapt to the accent theme (Default/Ocean/Emerald/Violet) and light/dark mode
automatically. Per recharts perf guidance: `ResponsiveContainer` inside an explicitly-sized
parent with a resize `debounce`, animation disabled, stable `dataKey`s, and memoized data
(`useMemo`). Tables scroll inside `overflow-x-auto`.

Menu entries added to `AdminSidebar.tsx` `collections()`: **Analytics**, **Query Logs**,
**Reports** (Performance section) and **App Settings** (Settings section) — all inside the
existing `!isCurator` admin-only block.

---

## 6. Structured log events (OpenSearch — Standard 9)

`analytics/structured_logging.py` emits JSON lines with the fixed field contract
(`event, entity, entity_id, tenant_id, actor_user_id, action, status, duration_ms, error`);
`timed_event` times a block and logs success/error. Never raises.

| event | entity | emitted by |
|---|---|---|
| `report.generated` | `usage_report` | `UsageReportService.generate` |
| `report_exported` | `usage_report` / `query_history` | report download / query-history export |
| `settings_updated` | `app_settings` | `AppSettingsService.save` / analytics-script set |
| `analytics.rollups_refreshed` | `analytics_rollup` | rollup refresh endpoint |

---

## 7. Research references (Standard 2)

Recharts performance & theming best practices that informed the chart design:
- Recharts performance guide — isolate/memoize, stable `dataKey`, disable animation:
  https://recharts.github.io/en-US/guide/performance/
- Recharts `ResponsiveContainer` (sized parent + `debounce` via ResizeObserver):
  https://recharts.github.io/en-US/api/ResponsiveContainer/
- CSS-variable theming for recharts (zero JS runtime cost, dark-mode-aware):
  https://github.com/recharts/recharts/discussions/6928
- Lightweight dashboard loading (aggregate server-side, fewer points):
  https://querio.ai/articles/build-fast-loading-dashboards-recharts

---

## 8. Integration — wiring snippets

### `om/main.py`
```python
# imports
from om.server.analytics.admin_api import router as analytics_admin_router
from om.server.query_history.admin_api import router as query_history_admin_router
from om.server.reporting.api import router as usage_reports_router
from om.server.app_settings.api import admin_router as app_settings_admin_router
from om.server.app_settings.api import basic_router as app_settings_router

# includes (alongside the other include_router_with_global_prefix_prepended calls)
include_router_with_global_prefix_prepended(application, analytics_admin_router)
include_router_with_global_prefix_prepended(application, query_history_admin_router)
include_router_with_global_prefix_prepended(application, usage_reports_router)
include_router_with_global_prefix_prepended(application, app_settings_admin_router)
include_router_with_global_prefix_prepended(application, app_settings_router)
```
When the old routers are removed (see §9), also delete the old
`analytics_router` / `query_history_router` / `usage_export_router` /
`enterprise_settings_*_router` imports + includes.

### `om/server/auth_check.py`
The app-settings public endpoints reuse the existing enterprise-settings public specs — keep
these entries in `PUBLIC_ENDPOINT_SPECS` / `EE_PUBLIC_ENDPOINT_SPECS`:
```python
("/enterprise-settings", {"GET"}),
("/enterprise-settings/logo", {"GET"}),
("/enterprise-settings/logotype", {"GET"}),
("/enterprise-settings/custom-analytics-script", {"GET"}),
```
All other new endpoints depend on `current_admin_user`, so they need no spec entry.

---

## 9. Integrator deletion checklist (delete-old-after-verify, on the fresh DB)

The new implementation lands as **new files alongside the EE originals** so this worktree
stays import-consistent (the EE originals are still wired into `main.py` and shared Celery /
branding infra). Once the new impl is verified and `main.py` is rewired (§8), the integrator
removes the EE-origin code below. Grouped by coupling so each group is deleted atomically:

**A. Analytics (safe once `main.py` uses `analytics_admin_router`):**
- delete `om/server/analytics/api.py` (old router) and `om/db/analytics.py` (old aggregation; zero other importers).

**B. Query history (delete together — the old async CSV export is replaced by the new sync one):**
- delete `om/server/query_history/api.py`, `om/db/query_history.py`,
  `om/background/celery/tasks/query_history/tasks.py`.
- in `om/background/celery/tasks/cleanup/tasks.py` remove `export_query_history_cleanup_task`
  (its only WS-H dependency is `get_all_query_history_export_tasks`).
- in `om/background/celery/tasks/beat_schedule.py` remove the `EXPORT_QUERY_HISTORY_CLEANUP_TASK` entry.
- trim `om/server/query_history/models.py` to only what non-WS-H code still needs
  (nothing after B is complete → the file can be deleted); update `scripts/chat_feedback_dump.py`
  and `tests/integration/.../query_history/*` accordingly.

**C. Reporting (delete together):**
- delete `om/server/reporting/usage_export_api.py`, `usage_export_generation.py`,
  `usage_export_models.py`, `om/db/usage_export.py`,
  `om/background/celery/tasks/usage_reporting/tasks.py`.
- in `beat_schedule.py` remove the `GENERATE_USAGE_REPORT_TASK` entry; in
  `om/background/celery/apps/primary.py` remove `"om.background.celery.tasks.usage_reporting"`
  from the task include list.
- remove the old `UsageReport` model (`usage_reports` table) from `om/db/models.py`; add
  `DROP TABLE IF EXISTS usage_reports` (fresh DB, no data). Delete
  `tests/integration/.../reporting/test_usage_export_api.py`.

**D. Enterprise settings (requires a small consumer migration first):**
- migrate the three branding consumers off `om/server/enterprise_settings/store.py` to
  `AppSettingsService`: `om/auth/email_utils.py` (`load_runtime_settings`),
  `om/server/runtime/onyx_runtime.py` (logo filenames → `app_settings/logo.py`),
  `om/server/seeding.py` (`store_analytics_script` / `upload_logo` / settings seeding).
- then delete `om/server/enterprise_settings/store.py` + `models.py`, and trim
  `om/server/enterprise_settings/api.py` to **keep only** the SCIM-token endpoints (WS-G) and
  the OAuth `refresh-token` endpoint — those are **not** WS-H's to remove.
- remove the old frontend analytics/query-history/whitelabel pages once the new screens are
  verified: `web/src/app/admin/performance/usage/`, `.../query-history/`,
  `.../custom-analytics/`, and their menu entries (Usage Statistics / old Query History /
  Custom Analytics) in `AdminSidebar.tsx`. The `theme/` whitelabel editor already PUTs
  `/admin/enterprise-settings`, which is now served by `app_settings`.

**E. Do NOT delete (out of WS-H scope — flagged):**
- `om/server/oauth/*` — this is **connector** OAuth (Slack/Confluence/Google Drive), not
  enterprise analytics/settings. The plan listed `server/oauth/api.py` under "replaces", but
  deleting it breaks connector authorization. Left intact for the connector owner.
- SCIM token management currently living inside `enterprise_settings/api.py` — owned by WS-G.

---

## 10. Extending

- **New metric:** add a query in `AnalyticsService`, expose it on `DailyUsagePoint` /
  `UsageSummary`, add a `RollupMetric` key if it should be cached, and render it in a
  `charts.tsx` series.
- **New feature toggle:** add a key to `app_settings.feature_flags` and a `Switch` in
  `app-settings/page.tsx`; read it on the web via the `/enterprise-settings` GET.
- **New report type:** add a generator method to `UsageReportService` and a button in
  `reports/page.tsx`.
