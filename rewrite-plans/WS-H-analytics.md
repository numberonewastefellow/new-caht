# WS-H — Analytics / query-history / reporting (clean-room + React charts)

## ▶ AGENT INSTRUCTIONS — START HERE (read this whole block first)

**You were pointed at this file to IMPLEMENT workstream WS-H. Do exactly this:**

0. **DUPLICATE CHECK — before anything.** If `.claude/worktrees/ws-h` already exists OR
   `rewrite-plans/status/WS-H.md` already has status lines from another agent, another agent owns WS-H:
   **STOP, report "WS-H already in progress — standing down", make NO changes.** Otherwise self-isolate:
   `git worktree add .claude/worktrees/ws-h -b rewrite/ws-h rename_onyx_to_om`
   Working root = `d:\llm\danswer20022026\.claude\worktrees\ws-h`; do ALL edits there, never the main tree.
1. **Read** `rewrite-plans/CONTRACTS.md` + the rest of THIS file. Tenant-safe (Contract 3).
2. **Legal — clean-room.** NEVER open/copy/paraphrase Onyx EE source at
   `D:\llm\danswer07022026_original\onyx\backend\ee\...`.
3. **Orient with graphify** before reading source.
4. **Phases + review gates.** TodoWrite; self-review after each phase.
5. **Research first** (lightweight dashboards + recharts best practices); cite in README.
6. **Standards:** multi-tenant-safe (tenant-scoped, indexed queries); new `app_settings` config table
   backing the web `enterpriseSettings` gating; admin Analytics/Query-History/Reports/Settings screens
   using VertualAI design system + **recharts** (responsive, theme-aware via accent CSS vars, NO
   hardcoded colors); menu entries; CSV export; structured OpenSearch logs on report/settings events in
   try/except; OOP + strict typing.
7. **Delete old EE analytics/history/reporting/enterprise-settings/oauth routers + `usage_reports` only
   in the FINAL phase**, after verify.
8. **Write** a module README. **Progress:** append to `d:\llm\danswer20022026\rewrite-plans\status\WS-H.md`.
9. **Do NOT commit/push. Do NOT run `alembic upgrade` by hand.** Summarize at the end.

**Wave:** 1. **Emphasis:** analytics with lightweight recharts graphs; new tables + admin pages.

---

> Read `CONTRACTS.md` first. Depends on **Contract 3 (tenant)**. Follow all Engineering standards.
> Work in your own worktree.

## Goal
Clean-room reimplementation of analytics, query-history, usage-reporting, and enterprise-settings
routers, with **new tables and new admin pages using lightweight React (recharts) charts**.

## Research first (Standard 2)
Web-research lightweight dashboard UX + recharts best practices (responsive, accessible, theme-aware
charts; avoiding heavy re-renders). Confirm recharts is the project's charting lib.

## Behavior spec (WHAT — own HOW; do not open Onyx files)
Replaces (EE routers mounted in main.py): `server/analytics/api.py`, `server/query_history/api.py`,
`server/reporting/usage_export_api.py`, `server/enterprise_settings/*`, `server/oauth/api.py`.
Table: `usage_reports`.

- **Analytics:** usage metrics over time (queries, active users, feedback, latency) — aggregate from
  existing chat/query data + this workstream's roll-ups.
- **Query history:** admin view of past queries/sessions (tenant-scoped, permission-gated).
- **Usage reporting:** generate/export usage reports (CSV) over a period.
- **Enterprise settings:** app-level settings (branding, feature toggles) via a **dedicated config table**
  (this is the `enterpriseSettings` object the web reads for gating).

## New tables (own names, typed)
- `usage_report` (name, requestor FK, period_from, period_to, created_at, file ref).
- Optional `analytics_rollup` (window_start, metric, value, tenant-scoped) for cheap chart queries.
- `app_settings` (or extend existing) for enterprise/branding settings.

## Config + UI
- Admin **Analytics dashboard** (VertualAI design system + **recharts**): time-series + bar charts for
  usage/active-users/feedback/latency; date-range picker; theme-aware colors (accent CSS vars).
- Admin **Query History** table screen. **Reports** screen (generate + download CSV).
- **App Settings** screen (branding/toggles) — the config table backing `enterpriseSettings`.
- Update MENU: "Analytics", "Query History", "Reports", "Settings" under admin (admin-gated).

## Shared-file snippets (integrator)
- `models.py`: analytics/report/settings model block. `main.py`: analytics/query-history/reporting/
  settings routers.
- `auth_check.py`: settings basic router may be public (feature-gating read).
- Alembic: revisions for new tables.
- Menu registry: the four entries.

## Phases (with review gates)
- **Phase 1 — Tables + aggregation queries + settings config table.** **Review:** queries tenant-scoped +
  efficient (indexes); settings drive web gating.
- **Phase 2 — Analytics/history/reporting APIs.** **Review:** correctness; CSV export; permission-gating.
- **Phase 3 — React dashboards (recharts) + history/reports/settings screens + menu.** **Review:**
  charts responsive + theme-aware (no hardcoded accent colors); design-system compliance.
- **Phase 4 — Delete old + verify.** Remove old EE analytics/history/reporting/enterprise-settings/oauth
  routers + `usage_reports`. **Review:** dashboards render real data; structured logs present.

## Structured logs (Standard 9)
`event=report.generated|report_exported|settings_updated`, `entity=usage_report|app_settings`,
`entity_id`, `tenant_id`, `actor_user_id`, `action`, `status`, `duration_ms`, `error`.

## Verification
- Analytics dashboard renders lightweight recharts graphs from real tenant-scoped data; query-history +
  reports work; CSV export downloads; settings drive frontend gating. Tenant isolated.

## README
`backend/om/server/analytics/README.md` (+ web dashboard notes): metrics + aggregation model, chart
components used, config/settings table, log events, extension.
