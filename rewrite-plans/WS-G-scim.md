# WS-G — SCIM 2.0 provisioning (clean-room redesign)

## ▶ AGENT INSTRUCTIONS — START HERE (read this whole block first)

**You were pointed at this file to IMPLEMENT workstream WS-G. Do exactly this:**

0. **DUPLICATE CHECK — before anything.** If `.claude/worktrees/ws-g` already exists OR
   `rewrite-plans/status/WS-G.md` already has status lines from another agent, another agent owns WS-G:
   **STOP, report "WS-G already in progress — standing down", make NO changes.** Otherwise self-isolate:
   `git worktree add .claude/worktrees/ws-g -b rewrite/ws-g rename_onyx_to_om`
   Working root = `d:\llm\danswer20022026\.claude\worktrees\ws-g`; do ALL edits there, never the main tree.
1. **Read** `rewrite-plans/CONTRACTS.md` + the rest of THIS file. SCIM groups map to `Team` (Contract 1,
   FK `team.id`); tenant-safe (Contract 3).
2. **Legal — clean-room.** NEVER open/copy/paraphrase Onyx EE source at
   `D:\llm\danswer07022026_original\onyx\backend\ee\...`.
3. **Orient with graphify** before reading source.
4. **Phases + review gates.** TodoWrite; self-review after each phase.
5. **Research first** — SCIM 2.0 **RFC 7643 + RFC 7644** (schema, PATCH semantics, filtering, discovery,
   bearer auth, Okta/Entra quirks); cite in README.
6. **Standards:** multi-tenant-safe; dedicated config + admin "SCIM Provisioning" UI (token
   generate/revoke, status); VertualAI design system; menu entry; structured OpenSearch logs on
   provisioning events in try/except; OOP + strict typing. Mount `/scim/v2` WITHOUT the global prefix;
   discovery endpoints public, provisioning behind `verify_scim_token` (auth_check snippet).
7. **Delete old SCIM api/models/tables only in the FINAL phase**, after verify.
8. **Write** `backend/om/server/scim/README.md`. **Progress:** append to `...\status\WS-G.md`.
9. **Do NOT commit/push. Do NOT run `alembic upgrade` by hand.** Summarize at the end.

**Wave:** 1. **Emphasis:** SCIM 2.0 per RFC; users → `User`, groups → `Team`.

---

> Read `CONTRACTS.md` first. Depends on **Contract 1 (Team FK)** + **Contract 3 (tenant)**. Follow all
> Engineering standards. Work in your own worktree.

## Goal
Clean-room reimplementation of SCIM 2.0 user/group provisioning, replacing Onyx-EE SCIM, with new
tables and new admin pages. SCIM groups map to **Teams** (Contract 1).

## Research first (Standard 2)
Web-research SCIM 2.0 — **RFC 7643 (core schema)** + **RFC 7644 (protocol)**: `/Users`, `/Groups`,
`/ServiceProviderConfig`, `/ResourceTypes`, `/Schemas`; PATCH semantics (RFC 7644 §3.5.2); filtering;
bearer-token auth; Okta/Entra SCIM client quirks. Cite in README.

## Behavior spec (WHAT — own HOW; do not open Onyx files)
Replaces: `server/scim/api.py` and the SCIM models. Tables `scim_token`, `scim_user_mapping`,
`scim_group_mapping`.

- **Auth:** bearer SCIM token (hashed, display last-4), admin-managed.
- **/Users:** create/read/update(PATCH)/delete/list(filter) → maps to `User`.
- **/Groups:** create/read/update(PATCH)/delete/list → maps to **Team** (Contract 1) via a group-mapping.
- **Discovery:** `/ServiceProviderConfig`, `/ResourceTypes`, `/Schemas` (public per SCIM).
- External-id ↔ internal-id mappings for users + teams.

## New tables (own names, typed)
- `scim_token` (hashed_token unique, display, created_by FK, is_active, timestamps).
- `scim_user_mapping` (external_id unique, user_id FK unique, timestamps).
- `scim_team_mapping` (external_id unique, team_id FK unique, timestamps).

## Config + UI
- Admin **SCIM** screen (VertualAI design system): generate/revoke SCIM tokens, view provisioning
  status/mappings. Endpoint base URL shown for IdP setup. Settings in a **dedicated config table**.
- Update MENU: "SCIM Provisioning" under admin/auth (admin-gated).

## Shared-file snippets (integrator)
- `models.py`: SCIM model block. `main.py`: `/scim/v2` router (mounted without global prefix, per SCIM).
- `auth_check.py`: SCIM discovery endpoints public; provisioning endpoints behind `verify_scim_token`.
- Alembic: SCIM tables revision.

## Phases (with review gates)
- **Phase 1 — Tables + token auth + discovery endpoints.** **Review:** token hashing; discovery matches RFC.
- **Phase 2 — /Users + /Groups(Team) CRUD + PATCH + filter.** **Review:** PATCH semantics correct;
  external-id mapping; Team linkage (Contract 1); tenant-scoped.
- **Phase 3 — Admin UI (tokens + status) + menu.** **Review:** design-system; admin-gating; token shown once.
- **Phase 4 — Delete old + verify.** Remove old SCIM api/models/tables. **Review:** an IdP SCIM client
  (or simulated requests) can provision a user + group→team; structured logs present.

## Structured logs (Standard 9)
`event=scim.user_provisioned|user_updated|user_deprovisioned|group_synced|token_created|token_revoked`,
`entity=scim_user|scim_team|scim_token`, `entity_id`, `tenant_id`, `actor_user_id`, `action`, `status`,
`duration_ms`, `error`.

## Verification
- Simulated SCIM requests (curl/Postman per RFC) create/update/delete users + groups; group maps to a
  Team; discovery endpoints valid; bearer auth enforced; tenant-scoped.

## README
`backend/om/server/scim/README.md`: SCIM endpoints + RFC references, token model, user/team mapping,
config/UI, log events, extension.
