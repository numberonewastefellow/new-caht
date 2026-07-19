# WS-C — SAML SSO (clean-room)

## ▶ AGENT INSTRUCTIONS — START HERE (read this whole block first)

**You were pointed at this file to IMPLEMENT workstream WS-C. Do exactly this:**

0. **DUPLICATE CHECK — before anything.** If `.claude/worktrees/ws-c` already exists OR
   `rewrite-plans/status/WS-C.md` already has status lines from another agent, another agent owns WS-C:
   **STOP, report "WS-C already in progress — standing down", make NO changes.** Otherwise self-isolate:
   `git worktree add .claude/worktrees/ws-c -b rewrite/ws-c rename_onyx_to_om`
   Working root = `d:\llm\danswer20022026\.claude\worktrees\ws-c`; do ALL edits there, never the main tree.
1. **Read** `rewrite-plans/CONTRACTS.md` (contracts + ownership rules + 12 standards) and the rest of
   THIS file. Treat contracts as FIXED (use `get_current_tenant_id()` + tenant-scoped session).
2. **Legal — clean-room.** Behavior spec only. NEVER open/copy/paraphrase Onyx EE source at
   `D:\llm\danswer07022026_original\onyx\backend\ee\...`.
3. **Orient with graphify** before reading source.
4. **Phases + review gates.** TodoWrite; self-review after each phase.
5. **Research first** (SAML SP best practices, python3-saml, ACS bindings, assertion validation, RelayState safety); cite in README.
6. **Standards:** multi-tenant-safe; dedicated SSO config table + admin UI; VertualAI design system;
   add a "Single Sign-On" menu entry; structured OpenSearch logs on CRUD/login in try/except; OOP + strict typing.
7. **Delete old `db/saml.py` + `server/saml.py` only in the FINAL phase**, after verify.
8. **Write** `backend/om/server/sso/README.md`.
9. **Progress:** append to `d:\llm\danswer20022026\rewrite-plans\status\WS-C.md` at each phase.
10. **Do NOT commit/push. Do NOT run `alembic upgrade` by hand.** Summarize at the end.

**Wave:** 1. **Emphasis:** SAML SSO clean-room + JIT provisioning; keep `auth/users.py` edits SSO-scoped.

---

> Read `CONTRACTS.md` first. Depends on **Contract 2 (Access API)** only indirectly (auth). Follow all
> Engineering standards. Work in your own worktree.

## Goal
Clean-room reimplementation of SAML SSO + JIT provisioning, replacing the Onyx-EE SAML feature.

## Research first (Standard 2)
Web-research current SAML SP best practices (SP-initiated flow, ACS bindings, assertion validation,
RelayState open-redirect protection, `python3-saml`/`OneLogin` current API, Entra/Okta attribute
mapping). Record decisions in README.

## Behavior spec (WHAT — own HOW; do not open Onyx files)
Replaces: `db/saml.py`, `server/saml.py`, and the SSO/JWT/OIDC-expiry branches merged into
`auth/users.py`; plus `EE_PUBLIC_ENDPOINT_SPECS`/`check_ee_router_auth` entries in `auth_check.py`.

- **SP-initiated login:** `/sso/saml/authorize` → returns IdP redirect URL.
- **ACS callback** (GET + POST bindings): validate assertion, extract email (multi-key attribute
  handling for Entra/Okta), JIT-provision user (first user → admin, else member; verified; random pwd),
  issue a normal session cookie. Sanitize RelayState against open redirects.
- **Logout:** `/sso/saml/logout`.
- **Session mapping:** persist SAML session cookie → user with expiry.
- **auth/users.py SSO branch:** SSO bypasses invite-only; JWT JIT path + OIDC-expiry enforcement if used.
  (Coordinate: `auth/users.py` is also touched by nobody else critical — but keep edits SSO-scoped.)

## New tables (own names)
- SAML account/session table: `id`, `user_id FK (unique, cascade)`, `encrypted_cookie` unique,
  `expires_at`, `updated_at`. (Replaces `saml`.)

## Config + UI
- Admin **SSO settings** screen (VertualAI design system): enable SAML, IdP metadata/URL, cert,
  attribute mapping — **dedicated config table** (typed), editable from UI.
- Update MENU: "Single Sign-On" under admin/auth (admin-gated).

## Shared-file snippets (integrator)
- `main.py`: include `sso_router` only when `AUTH_TYPE == SAML`; list its paths in public-endpoint specs.
- `auth_check.py`: public-endpoint entries for `/sso/saml/*`.
- Alembic: SAML table revision.

## Phases (with review gates)
- **Phase 1 — SAML core + table + session mapping.** **Review:** assertion validation + email extraction
  robust; RelayState sanitized; error paths handled.
- **Phase 2 — auth/users.py SSO branch + JIT provisioning + config table.** **Review:** first-user-admin
  rule; invite-bypass correct; tenant-safe (Contract 3).
- **Phase 3 — SSO settings UI + menu.** **Review:** design-system + admin-gating.
- **Phase 4 — Delete old + verify.** Remove `db/saml.py`, `server/saml.py`, old specs. **Review:** login
  via SAML end-to-end (or mocked IdP) works; structured logs present.

## Structured logs (Standard 9)
`event=sso.login|logout|jit_provisioned|assertion_rejected`, `entity=saml_session|user`, `entity_id`,
`tenant_id`, `actor_user_id`, `action`, `status`, `duration_ms`, `error`.

## Verification
- SAML login flow (mock IdP acceptable) provisions + authenticates a user; logout clears session.
- Invalid assertion rejected; RelayState cannot open-redirect. Tenant-scoped.

## README
`backend/om/server/sso/README.md`: SAML flow, config table/UI, attribute mapping, log events, extension.
