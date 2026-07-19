# WS-M — Multi-tenant data isolation (keep + refactor, no billing)

## ▶ AGENT INSTRUCTIONS — START HERE (read this whole block first)

**You were pointed at this file to IMPLEMENT workstream WS-M. Do exactly this:**

0. **DONE/DUPLICATE CHECK — before anything.** If `rewrite-plans/status/WS-M.md` shows
   "WS-M COMPLETE", this workstream is already finished — **STOP and report "WS-M already complete —
   standing down"; make NO changes.** Otherwise, **RESUME in the EXISTING worktree — do NOT create a
   new one.** Your working root is `d:\llm\danswer20022026\.claude\worktrees\agent-aa85bc62ad66a2e0c`.
   It already contains partial Phase-1 work: `backend/om/tenancy/` (`context.py`, `config.py`,
   `events.py`, `migrations.py`, `models.py`, `repository.py`). **Review those files first**, then
   CONTINUE from Phase 1. Do ALL edits inside that worktree (absolute paths). Contract 3 is already
   finalized + published to CONTRACTS.md.
1. **Read** `rewrite-plans/CONTRACTS.md` (contracts + ownership rules + 12 engineering standards) and
   the rest of THIS file. You OWN Contract 3 — keep it in sync if you refine it.
2. **Legal — clean-room.** Behavior spec only. NEVER open/copy/paraphrase Onyx EE source at
   `D:\llm\danswer07022026_original\onyx\backend\ee\...`. Own module layout, names, control flow.
3. **Orient with graphify** (`graphify query "<q>"`) before reading source.
4. **Phases + review gates.** TodoWrite the phases below; after each phase self-review (re-read, find
   gaps/bugs/missing error-handling, fix), THEN continue.
5. **Research first** (multi-tenant schema isolation, Postgres search_path, contextvars); cite in README.
6. **Standards** (CONTRACTS.md): dedicated config table + UI where settings apply; VertualAI design
   system (no hardcoded accent colors); add a "Tenants" admin menu entry; structured OpenSearch logs on
   every create/update/delete in try/except; full OOP + strict typing.
7. **Delete old EE remnants only in the FINAL phase**, after verify.
8. **Write** `backend/om/tenancy/README.md`.
9. **Progress:** append a timestamped line to `d:\llm\danswer20022026\rewrite-plans\status\WS-M.md` at
   each phase start, phase-gate pass, and completion.
10. **Do NOT commit/push. Do NOT run `alembic upgrade` by hand.** Summarize what you built at the end.

**Wave:** 0 (foundation). **Emphasis:** keep multi-tenant DATA ISOLATION (schema-per-tenant); strip ALL
billing/Stripe/control-plane/HubSpot; provision on demand; self-hosted tenant-admin UI. You own the
`main.py` tenant-middleware wiring (coordinate with WS-A which removes license-enforcement middleware).

---

> Read `CONTRACTS.md` first (esp. **Contract 3 — Tenant context**). You OWN Contract 3. Follow all
> Engineering standards. Work in your own worktree. **Foundation workstream** — publish your contract
> specifics in Phase 1 so other workstreams can code against them.

## Goal

Multi-tenancy is **mandatory** for data isolation (schema-per-tenant), but must be **fully decoupled
from billing / Stripe / external control plane**. The isolation code is Onyx-EE-origin, so
**reimplement it clean-room**: keep the isolation mechanism, strip the cloud-business coupling, add a
self-hosted tenant-admin experience.

## Behavior spec (WHAT — implement your own HOW)

Keep the isolation core:
- **Schema-per-tenant** Postgres isolation. Tenant id resolved per request into
  `CURRENT_TENANT_ID_CONTEXTVAR`; DB sessions bound to the tenant schema (search_path) via a
  tenant-scoped session helper.
- **Tenant-tracking middleware** (`server/middleware/tenant_tracking.py` behavior): resolve tenant
  from API-key/PAT → auth token → cookie → default schema; validate schema name. Rewrite clean-room.
- **Per-tenant Alembic migration runner** — apply migrations across all tenant schemas.
- **email→tenant mapping** table (`user_tenant_mapping` behavior) in the `public` schema, for login
  routing (which tenant does this email belong to).

Refactor provisioning (`server/tenants/provisioning.py` behavior) — KEEP vs REMOVE:
- KEEP: create schema, run per-schema migrations, seed default setup, assign tenant to user.
- REMOVE: `notify_control_plane`, HubSpot submit, Stripe, data-plane tokens, the `available_tenant`
  pre-provision pool (provision **on demand** instead).

Self-hosted tenant admin:
- New admin UI screen: create tenant, list tenants, assign/move users to a tenant, deactivate tenant.
- Backend service + routes for the above (superuser-gated). No billing anywhere.
- `tenant_anonymous_user_path` behavior: keep ONLY if anonymous access is desired; otherwise drop.

## New / refactored files (your own layout, e.g.)
- `backend/om/tenancy/` — `context.py` (current-tenant + session helpers = Contract 3 exports),
  `provisioning.py` (billing-free), `middleware.py`, `migrations.py`, `service.py`, `models.py`, `README.md`.
- `backend/om/server/tenancy/api.py` — tenant-admin routes.
- `web/src/app/admin/tenants/**` — tenant-admin screen (VertualAI design system).

## Config
Tenant-admin settings (e.g. default tenant, anonymous-access toggle) → dedicated config table or KV
(simple singleton) per Standard 5.

## DB tables
- Keep (refactored, own names): email→tenant mapping (`public` schema).
- Drop: `available_tenant` (cloud pool), and `tenant_anonymous_user_path` unless anonymous access kept.

## Shared-file snippets (for integrator)
- `backend/om/main.py`: register the tenant-tracking middleware (you OWN this block; coordinate with
  WS-A which removes the license-enforcement middleware from the same area) and the tenant-admin router.
- Alembic: revision for the refactored mapping table (standalone; integrator linearizes).
- Web menu: add "Tenants" admin entry (superuser-gated).

## Phases (with review gates)
- **Phase 0 (Wave 0):** Publish Contract 3 specifics in `CONTRACTS.md` — exact import paths for
  "get current tenant" and "get tenant-scoped session", and the list of `public`-schema tables.
  Other workstreams block on this. Keep it tiny and fast.
- **Phase 1 — Isolation core.** Clean-room `context.py` + middleware + per-tenant migration runner +
  mapping table. **Review:** two tenants' sessions never cross schemas; middleware resolution order correct.
- **Phase 2 — Provisioning (billing-free).** Refactor provisioning; remove control-plane/Stripe/HubSpot/pool.
  **Review:** provisioning works offline with no external calls; on-demand create succeeds.
- **Phase 3 — Tenant-admin UI + routes.** Superuser CRUD screen. **Review:** role-gating correct;
  structured logs on create/update/delete tenant.
- **Phase 4 — Delete old + verify.** Remove Onyx tenant/cloud provisioning remnants (that WS-A didn't).
  **Review:** tenant-isolation smoke test passes.

## Structured logs (Standard 9)
`event=tenant.created|updated|deleted|user_assigned`, `entity=tenant`, `entity_id=<tenant_id>`,
`tenant_id`, `actor_user_id`, `action`, `status`, `duration_ms`, `error`.

## Verification
- Tenant-isolation smoke test: create tenant A + B, data written under A is invisible under B across a
  representative query; middleware sets the right schema; migrations apply to all schemas.
- No Stripe/HubSpot/control-plane calls remain (`grep`), app boots multi-tenant.

## README
`backend/om/tenancy/README.md`: isolation model, request→tenant resolution, how to add a tenant-scoped
table, how other features must use Contract 3, and the (now-removed) billing coupling for history.

## Coordination
- Publish Contract 3 EARLY (Phase 0) — WS-F/WS-H/WS-B/etc. depend on tenant-scoped sessions.
- Align with **WS-A** on the `main.py` middleware block.
