# WS-A — Purge: delete license paywall + billing

## ▶ AGENT INSTRUCTIONS — START HERE (read this whole block first)

**You were pointed at this file to IMPLEMENT workstream WS-A. Do exactly this:**

0. **DUPLICATE CHECK — before anything.** If `.claude/worktrees/ws-a` already exists OR
   `rewrite-plans/status/WS-A.md` already has status lines from another agent, another agent owns WS-A:
   **STOP, report "WS-A already in progress — standing down", make NO changes.** Otherwise self-isolate:
   `git worktree add .claude/worktrees/ws-a -b rewrite/ws-a rename_onyx_to_om`
   Working root = `d:\llm\danswer20022026\.claude\worktrees\ws-a`; do ALL edits there, never the main tree.
1. **Read** `rewrite-plans/CONTRACTS.md` (ownership rules + 12 standards) and the rest of THIS file.
2. **Orient with graphify** (`graphify query "<q>"`) before reading source.
3. **Phases + review gates.** TodoWrite the phases; after each, self-review (grep for dangling imports
   of deleted symbols: `license`, `billing`, `stripe`, `control_plane`, `data_plane`, `hubspot`), fix, continue.
4. **Progress:** append timestamped lines to `d:\llm\danswer20022026\rewrite-plans\status\WS-A.md`.
5. **Do NOT commit/push. Do NOT run `alembic upgrade` by hand.** Summarize removals + shared-file snippets at the end.

**Wave:** 0. **Emphasis:** DELETION only — remove Cluster F (license paywall) + Cluster G **billing only**
(Stripe/HubSpot/control-plane/proxy/product-gating) + the "Running Enterprise Edition" log. **KEEP
multi-tenant data isolation** — that's WS-M's; do not touch `user_tenant_mapping`, tenant_tracking, or
provisioning's isolation core. WS-M OWNS the `main.py` tenant-middleware block — only remove the
license-enforcement middleware; hold your main.py snippet so it doesn't conflict.

---

> Read `CONTRACTS.md` first. Follow all Engineering standards. Work in your own worktree.

## Goal

Remove two encumbered/unwanted subsystems entirely: **Cluster F (license-key paywall)** and the
**billing half of Cluster G**. This is deletion + wiring cleanup only — no new features. It is the
fastest, lowest-risk risk-reduction and unblocks a clean multi-tenant-no-billing boot.

**Do NOT touch multi-tenant data isolation** — that is WS-M's domain (kept & refactored). You remove
only billing/Stripe/control-plane/license-paywall.

## Delete (files)

License paywall (Cluster F):
- `backend/om/db/license.py`, `backend/om/utils/license.py`
- `backend/om/server/license/**` (api.py, models.py)
- `backend/om/server/middleware/license_enforcement.py`
- `backend/om/configs/license_enforcement_config.py`
- `backend/keys/license_public_key.pem`
- Tests: `backend/tests/unit/om/db/test_license.py` and any license tests.

Billing (Cluster G — billing only, NOT tenant isolation):
- `backend/om/server/billing/**` (api.py, service.py, models.py)
- `backend/om/server/tenants/billing.py`, `billing_api.py`, `proxy.py`, `product_gating.py`
- Any Stripe SDK usage, HubSpot calls, control-plane/data-plane token helpers used only by billing.

## DB tables to drop (final phase, after boot verified)
- `license`. (Billing has no dedicated tables beyond license + tenant tables; tenant tables belong to WS-M.)
- Leave `tenant_usage` to **WS-F** (it redesigns usage); leave tenant isolation tables to **WS-M**.

## Shared-file edits (deliver as snippets for the integrator)
- `backend/om/main.py`:
  - Remove imports + `include_router` for `license_router`, `billing_router`, and the tenants
    billing/proxy routers.
  - Remove the `add_license_enforcement_middleware` call (the non-MULTI_TENANT branch).
  - Remove the unconditional `logger.notice("Running Enterprise Edition")` (~L715).
  - Do NOT collapse `MULTI_TENANT` (WS-M keeps multi-tenant). Coordinate with WS-M on the middleware block.
- `backend/om/server/auth_check.py`: remove the billing/license entries from `EE_PUBLIC_ENDPOINT_SPECS`
  (e.g. `/admin/billing/stripe-publishable-key`, `/proxy/*`).
- Frontend: remove billing/license admin pages + their menu entries + settings references
  (`web/src/**` billing/license screens; `combinedSettings` billing fields).

## Phases (with review gates)

- **Phase 1 — Backend delete + wiring.** Remove license + billing files; produce main.py/auth_check
  snippets. **Review:** grep for dangling imports/usages of deleted symbols (`license`, `billing`,
  `stripe`, `control_plane`, `data_plane`); ensure none remain outside WS-M's tenant-isolation code.
- **Phase 2 — Frontend delete.** Remove billing/license pages, menu entries, settings usages.
  **Review:** web build/typecheck passes; no dead imports.
- **Phase 3 — Drop tables + boot.** Add Alembic revision dropping `license`. **Review:** app boots
  multi-tenant with no billing/license routes; `check_ee_router_auth` passes; removed routes 404.

## Structured logs
N/A (deletion). Ensure no deleted module was the only emitter of a still-needed log.

## Verification
- App boots multi-tenant (WS-M present) with NO `/license`, `/admin/billing`, `/proxy`, billing routes.
- `check_ee_router_auth` passes; no import errors; `grep -ri "stripe\|license_enforcement\|billing"`
  in `backend/om` returns nothing outside intentionally-kept code.
- Web builds; no billing/license menu items.

## README
Write `rewrite-plans/notes/WS-A-README.md` (or inline in PR): what was removed, why (Enterprise-License
+ no-billing), and confirmation that multi-tenant isolation was left to WS-M.

## Coordination
- **WS-M** also touches `main.py` tenant middleware — align on the middleware block (WS-M owns it).
- Do not remove `user_tenant_mapping` or tenant provisioning — WS-M keeps/refactors those.
