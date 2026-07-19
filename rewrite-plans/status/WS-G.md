# WS-G — SCIM 2.0 provisioning — status log

Worktree: `.claude/worktrees/ws-g` (branch `rewrite/ws-g` off `rename_onyx_to_om`).
Depends on **Contract 1 (Team FK → `team.id`)** + **Contract 3 (tenant context)**.

Phase plan:
- P1 Tables (`scim_token`, `scim_user_mapping`, `scim_team_mapping`) + bearer-token auth + discovery endpoints.
- P2 `/Users` + `/Groups`(→Team) CRUD + PATCH (RFC 7644 §3.5.2) + filter (§3.4.2.2).
- P3 Admin SCIM UI (token generate/revoke + status/mappings) + menu entry (admin-gated, VertualAI).
- P4 Delete old EE SCIM api/models/tables + verify (simulated IdP provisioning; structured logs).

Clean-room: NEVER opened Onyx EE source. New impl written from behavior spec + RFC 7643/7644 + Okta/Entra
docs (research report). Old merged EE files (`server/scim/*.py`, `db/scim.py`, EE scim models) are the
expression being *replaced*; only their public integration symbol names + table names (facts) were used.

---

- [P0] Read CONTRACTS.md + WS-G in full. Graphify-oriented on main.py router mounting, api-key hashing,
  tenancy primitives, auth_check. Mapped the old EE SCIM footprint (importers: main.py `scim_router`,
  auth_check `verify_scim_token`, enterprise_settings `/scim/token` endpoints; old `db/scim.py ScimDAL`;
  old tests under `tests/unit/om/server/scim/`). Researched SCIM 2.0 (RFC 7643 core schema, RFC 7644
  protocol/PATCH/filter/discovery/errors, Okta + Entra client quirks, bearer-token security) — cited in README.
- [P0] Key design decisions:
  - **Integration symbols kept** so main.py + auth_check need no import edits: `om.server.scim.api.scim_router`
    and `om.server.scim.auth.verify_scim_token`. Discovery endpoints already in auth_check public specs.
  - **Multi-tenant routing**: SCIM bearer token embeds the (URL-encoded) tenant id (same pattern as API keys);
    `verify_scim_token` parses tenant → sets `CURRENT_TENANT_ID_CONTEXTVAR` → opens tenant-bound session →
    verifies hashed token row in the per-tenant `scim_token` table. Self-routing; no dependency on WS-M
    middleware for `/scim/v2` routes. `scim_token`/`scim_user_mapping`/`scim_team_mapping` are per-tenant (Contract 3).
  - **Tenancy import** via Contract-3 facade `om.tenancy.context`; added a thin re-export shim in this worktree
    (WS-M owns the canonical module — integrator drops the shim), mirroring WS-B's approach.
  - **Groups → Team** (Contract 1): `scim_team_mapping.team_id → team.id` (BIGINT). Team model/table land via WS-B;
    my worktree base still has `user_group` → DB-integration boot verification is the integrator's step; I verify
    RFC-critical logic (token hashing, PATCH, filter, discovery, resource serialization) with standalone unit tests.

## Phase 1 — DONE (tables + token auth + discovery)
- Models: replaced EE SCIM block in `db/models.py` with WS-G banner block — `ScimToken`
  (created_by FK→user.id, hashed_token unique(64), token_display, is_active, timestamps, last_used_at),
  `ScimUserMapping` (external_id unique, user_id unique→user.id), `ScimTeamMapping` (external_id unique,
  team_id unique→**team.id BIGINT**, Contract 1). Old `scim_group_mapping` removed.
- Repository `db/scim.py` rewritten clean-room (`ScimRepository`): token + user-mapping + team-mapping CRUD
  only (no User/Team coupling — service layer owns those). Old `ScimDAL` deleted unread.
- Auth `server/scim/auth.py`: `generate_scim_token` (CSPRNG, tenant embedded in MT like API keys),
  `hash_scim_token` (sha256), `build_scim_token_display` (scim_****last4), `parse_tenant_from_token`,
  `tokens_match` (hmac.compare_digest), `verify_scim_token` (yield-dep: parse tenant → set contextvar →
  tenant-bound session → verify hashed row → touch last_used → yield ScimContext → reset in finally).
- Discovery `server/scim/discovery.py` + routes in `api.py`: `/ServiceProviderConfig`, `/ResourceTypes[/{id}]`,
  `/Schemas[/{id}]` — public, `application/scim+json`, correct URNs (RFC 7643 §5, RFC 7644 §4).
- Errors `server/scim/errors.py`: `ScimError` + `ScimRoute` (custom route class renders SCIM error bodies +
  RequestValidationError→400 invalidSyntax → **no main.py exception-handler edits needed**).
- Structured logging `server/scim/scim_logging.py` (Standard 9 fields + `scim_operation` timing ctx-mgr).
- Alembic `wsg_scim_provisioning.py` (down_revision=None placeholder): drops EE scim tables from baseline,
  creates the 3 new tables. Integrator note: linearize after `0003_agent_rename` + WS-B team rename.
- Excised old SCIM `/scim/token` endpoints + imports from `enterprise_settings/api.py` (moved to new admin router, P3).
- Integration shim `om/tenancy/context.py` (Contract-3 facade; integrator drops for WS-M canonical).
- **Review PASS**: token hashing (sha256, no-salt rationale, constant-time compare, last-4 display) ✓;
  discovery matches RFC (URNs, SPC capability flags, oauthbearertoken auth scheme, ListResponse wrap) ✓.
  Verified via TestClient (discovery 200 + scim+json + 404 SCIM-error) and direct tests (token gen/hash/
  parse incl. MT tenant-embed + url-encoding; verify_scim_token 401 on missing/wrong-scheme/empty/bad-prefix).
  Known: full DB boot needs WS-B `team` table (integrator step); Phase-1 logic verified without it.

## Phase 2 — DONE (/Users + /Groups(Team) CRUD + PATCH + filter)
- `filters.py`: full RFC 7644 §3.4.2.2 parser (eq/ne/co/sw/ew/gt/ge/lt/le/pr + and/or/not + grouping +
  value-paths `attr[...]`) → AST + case-insensitive in-memory evaluator over serialized resources.
- `patch_ops.py`: RFC 7644 §3.5.2 applier — path-less add/replace (dotted + URN keys), simple/dotted paths,
  value-filtered multi-valued ops; **both** group-member remove shapes (value-path `members[value eq "x"]`
  AND Entra legacy `members`+value-array); atomic (caller discards on raise).
- `service.py`: `ScimUserService` + `ScimGroupService`. Mapping: userName↔email, active↔is_active,
  displayName↔personal_name; Group.displayName↔Team.name, members↔`user__team` rows (Contract 1).
  externalId persisted in mapping tables; uniqueness (userName/displayName/externalId → 409). DELETE user =
  deactivate + unlink (soft deprovision). Team + `user__team` imported lazily (WS-B lands them).
- `users_api.py` / `groups_api.py`: POST/GET/GET-list/PUT/PATCH/DELETE; all guarded by `verify_scim_token`.
  Bodies parsed manually (accepts `application/scim+json`). User PATCH→200, Group PATCH→204 (Entra pref),
  DELETE→204, POST→201. `responses.py` shared helpers (scim_json/base_url/list_response/parse_body).
- `auth_check.py`: moved the 5 SCIM discovery entries into base PUBLIC_ENDPOINT_SPECS (added the two `/{id}`
  sub-routes) so boot's `check_ee_router_auth` passes; removed them from the EE block (SCIM no longer EE).
- **Review PASS**: PATCH semantics (path-less/dotted/value-filter/both member-remove shapes, op case-insens,
  active "False" coercion) ✓; filter parse+eval (eq/and/or/not/co/sw/pr, case-insens, value-path) ✓;
  external-id mapping (create/update/no-op/cross-entity 409) ✓; Team linkage via user__team (code + lazy) ✓;
  tenant-scoped (verify_scim_token binds tenant) ✓. Verified: 17 routes registered; boot auth-check passes
  (discovery public, 12 provisioning routes verify_scim_token-guarded); HTTP layer via TestClient
  (401-gating, 201/200/204, scim+json, body parse, filter/startIndex/count passthrough, malformed→400
  invalidSyntax); service serialization + mapping-conflict logic. Full DB persistence = integrator step (WS-B Team + Postgres).

## Phase 3 — DONE (admin SCIM UI + menu)
- Backend `server/scim/admin_api.py` (`scim_admin_router`, prefix `/admin/scim`, all routes
  `Depends(current_admin_user)`): `GET /status` (base_url + MT flag + active-token/user/team counts),
  `GET /tokens`, `POST /tokens` (mints token — tenant embedded in MT; returns raw once + metadata),
  `DELETE /tokens/{id}` (soft-revoke). Structured logs on token_created / token_revoked.
- Wired into `main.py`: import + `include_router_with_global_prefix_prepended(application, scim_admin_router)`.
- Web `web/src/app/admin/scim/`: `page.tsx` (SCIM base URL panel w/ copy, accent stat cards using
  `--virtualai-accent`, token table, generate flow, raw-token-shown-once modal), `CreateScimTokenModal.tsx`
  (Formik + TextFormField), `lib.ts`, `types.ts`. Reuses VertualAI components (AdminPageTitle, Modal,
  Button/CreateButton/CopyIconButton, DeleteButton, Table, Text, Separator, toast).
- Menu: added "SCIM Provisioning" (SvgArrowExchange → `/admin/scim`) to the admin-only **User Management**
  section of `AdminSidebar.tsx`.
- **Review PASS**: design-system (no hardcoded accent — `var(--virtualai-accent, var(--theme-primary-05))`,
  reused components) ✓; admin-gating (backend `current_admin_user` on all routes + admin-only sidebar
  section) ✓; token shown once (raw only in POST response + one-time modal, DB stores hash + last-4) ✓.
  Verified: admin routes all admin-gated (introspected); web `npm run types:check` exit 0.

## Phase 4 — DONE (delete old + verify)
- Deleted orphaned EE SCIM files: `server/scim/{filtering,patch,schema_definitions,models}.py` and the old
  `db/scim.py` (all unread — clean-room). Old tests removed: `tests/unit/om/server/scim/*` (whole dir),
  `tests/unit/om/db/test_scim_dal.py`, `tests/external_dependency_unit/db/conftest.py` (scim-only).
- Surgically removed SCIM from shared files: `tests/unit/om/db/conftest.py` (dropped ScimDAL import +
  scim_dal fixture; kept generic mock_db_session/model_attrs); `db/dal.py` docstring genericised.
- Old tables: the migration drops `scim_group_mapping` and drop-recreates `scim_token`/`scim_user_mapping`
  to the new schema. Grep-confirmed **no live importers** of any deleted symbol remain.
- New clean-room pytest suite `tests/unit/om/server/scim/` (**62 passed**): token auth (gen/hash/display/
  parse incl. MT + verify failure paths), filters, PATCH (all IdP shapes), discovery payloads+endpoints,
  HTTP layer (auth-gating/status/body-parse/query passthrough via TestClient+fakes), service mapping +
  external-id conflict, structured logging (Standard-9 fields on success/error).
- Verified: `check_ee_router_auth` passes for scim + scim-admin routers (no boot crash); all 16 edited/new
  modules import cleanly; web `types:check` exit 0.
- **Simulated-IdP E2E** (provision user + group→team): logic executed end-to-end against an in-memory probe
  up to the point where the real `User` ORM's transitive table graph (JSONB, oauth_account, credential,
  memory, …) requires Postgres. **Full live E2E is the integrator step** (real Postgres + WS-B `team`);
  the probe confirmed schema build + create/patch/deprovision + group→team + membership + mapping logic run
  correctly — the only blockers are environmental, not code defects.
- Structured logs present: `scim.user_provisioned|user_updated|user_deprovisioned|group_synced|
  group_deprovisioned|token_created|token_revoked` with tenant_id/actor/action/status/duration_ms/error.

### Integrator notes (snapshots to regenerate)
- `tests/unit/migration_safety/snapshots/baseline.json` and `tests/route_rename/snapshots/before/*` still
  reference the OLD scim schema/routes (scim_group_mapping, get_active_scim_token, etc.). These are
  pre-existing baseline snapshots — regenerate them during integration once the Alembic chain is linearized.

## Shared-file snippets for the integrator

### `backend/om/db/models.py`
Applied under banner `# === WS-G: SCIM 2.0 provisioning models ===` — `ScimToken`,
`ScimUserMapping`, `ScimTeamMapping` (team_id → team.id BIGINT). Old EE scim models removed.

### `backend/om/main.py`
```python
# imports (top)
from om.server.scim.api import scim_router
from om.server.scim.admin_api import scim_admin_router
# in get_application():
application.include_router(scim_router)  # /scim/v2, NO global prefix (IdPs expect it)
include_router_with_global_prefix_prepended(application, scim_admin_router)  # /admin/scim
```

### `backend/om/server/auth_check.py`
Add the 5 SCIM discovery entries to the base `PUBLIC_ENDPOINT_SPECS` (done in this worktree):
```python
("/scim/v2/ServiceProviderConfig", {"GET"}),
("/scim/v2/ResourceTypes", {"GET"}),
("/scim/v2/ResourceTypes/{resource_id}", {"GET"}),
("/scim/v2/Schemas", {"GET"}),
("/scim/v2/Schemas/{schema_id}", {"GET"}),
```
Provisioning routes carry `verify_scim_token` (already in the recognised-auth list). If the EE
`check_ee_router_auth` path is dropped by WS-A, the base `check_router_auth` already covers SCIM.

### Alembic
`alembic/versions/wsg_scim_provisioning.py` — `down_revision=None` placeholder. Linearize AFTER
`0003_agent_rename` AND after WS-B's team-rename revision (FK to `team.id`).

### `backend/om/tenancy/context.py`
Thin Contract-3 re-export shim (WS-M owns canonical) — integrator drops it.

### Web menu
`web/src/sections/sidebar/AdminSidebar.tsx` — "SCIM Provisioning" (SvgArrowExchange → `/admin/scim`)
in the admin-only User Management section. New page dir `web/src/app/admin/scim/` is WS-G-owned.

---

## WS-G COMPLETE
All 4 phases done + reviewed. Clean-room: no Onyx-EE source opened. New impl written from
RFC 7643/7644 + Okta/Entra docs. 62 backend unit tests pass; web types:check exit 0; boot auth-check
passes. Did NOT commit/push; did NOT run alembic. Full live-DB E2E provisioning + snapshot regeneration
are the integrator step (needs Postgres + WS-B `team`). README at `backend/om/server/scim/README.md`.

## [REVIEW] Rigorous self-review — gaps found + fixed
Phase checklist: P1 ✅ P2 ✅ P3 ✅ P4 ✅ (all items done). 12 standards: all met (see below).
Contracts: Contract 1 (scim_team_mapping.team_id → team.id BIGINT) ✅; Contract 3 (om.tenancy.context,
per-tenant tables, tenant in every log) ✅.

Gaps found & fixed (8):
1. **[CRITICAL, correctness] Missing `.unique()`** on `select(User).all()` in `list_users` +
   `_member_entries`. `User.oauth_accounts` is `lazy="joined"` (eager collection) → these would raise
   `InvalidRequestError` at runtime **on Postgres**, not just SQLite. Caught by the live E2E probe. Fixed.
2. **[correctness] Group PATCH wiped/re-validated members on a displayName-only change** — a benign
   displayName PATCH could 400 (if a member user was since deleted) and needlessly rewrote membership.
   Now reconciles members only when the patched member-set differs. Verified live in the probe.
3. **[perf] N+1 in `_member_ids`** (per-member `db.get`). Now a single `select(User.id).where(...in_)`.
4. **[interop+perf] `excludedAttributes=members` not honored** on Group list/get (Entra sends it; also
   the source of a group-list N+1). Now honored; group reads skip member loading when excluded.
5. **[robustness] Create race (TOCTOU)** → `IntegrityError` became a 500. Now caught → 409 uniqueness
   on both user + group create.
6. **[perf/correctness] Event-loop blocking** — mutating routes were `async def` calling sync SQLAlchemy.
   Switched to sync `def` + declarative Pydantic body params (FastAPI parses `application/scim+json`,
   runs them in a threadpool, and malformed bodies → `ScimRoute` 400 invalidSyntax). Dropped the now-dead
   `parse_body` helper + unused imports.
7. **[typing/dead-code] mypy strict cleanups** — `admin_api._to_info` typed as `ScimToken` (removed 6
   `type: ignore`); removed dead `parse_body`; renamed service `list`→`list_users`/`list_groups` (the
   `list` method name shadowed the builtin in annotations); removed a dead inner try/except in
   `verify_scim_token` (+ its now-unused `HTTPException` import); made response-only models
   (`ScimListResponse`, `ScimErrorResponse`) use `serialization_alias` only so they construct by field
   name; `User.id` query lines carry `# type: ignore` (matches the codebase — fastapi-users base isn't
   plugin-instrumented); `Team` resolved via `getattr` (no unused-ignore landmine for the integrator).
8. **[bug caught, not mine]** — the `.unique()` issue (#1) would have shipped broken; the probe made it
   reproducible.

Verification (all green):
- `python -m mypy om/server/scim/ om/db/scim.py` (project config, sqlalchemy plugin, full closure):
  **0 errors in WS-G files** (179 remaining are pre-existing, in unrelated files).
- `pytest tests/unit/om/server/scim/`: **64 passed** (added excludedAttributes + _include_members tests).
- `py_compile` all changed backend files: OK.
- Live E2E probe (real ORM + stub Team): user provision/patch/deprovision + group→team create/member/
  displayName-patch-preserves-members/excludedAttributes/remove-member/delete — **PASS**, structured
  logs emitted throughout.
- `check_ee_router_auth` over scim + scim-admin routers: **PASS** (12 provisioning routes guarded).
- web `npm run types:check`: **exit 0**.
- Did NOT commit; did NOT run `alembic upgrade`.

---

## Second self-review pass (2026-07-19, follow-up session) — 7 items, all fixed & verified

Re-reviewed the whole worktree against the plan + RFC 7643/7644 (2 Explore sub-agents on web UI + tests,
direct read of all backend modules). Verdict: solid & matches plan. Further hardening applied:

- **[correctness] PUT/PATCH uniqueness → 409 (was 500).** Only `create` guarded `IntegrityError`; the four
  User+Group `replace`/`patch` paths did not, so a `userName`→email or `displayName`→Team-name rename
  collision surfaced as a generic 500. All four now wrap mutation+commit in `try/except IntegrityError` →
  `ScimError.uniqueness` (409). (`service.py`)
- **[interop] Idempotent re-provision.** `deprovision` keeps the (deactivated, unmapped) User row, so a
  later `POST /Users` with the same `userName` used to 409 despite the "re-provisionable" docstring. Added
  `ScimUserService._reactivate`: create now reactivates that row in place (restores is_active, display,
  mapping). Active/still-mapped collisions still 409. README updated. (`service.py`, `README.md`)
- **[perf] List endpoints paged in SQL.** `list_users`/`list_groups` no-filter path now uses
  `LIMIT/OFFSET` + `func.count` and batch-loads only the page's mappings (`list_user_mappings_for`/
  `list_team_mappings_for`); `_member_entries_bulk` collapses the group-membership N+1 into 2 queries.
  Filtered path still evaluates in memory (documented). (`service.py`, `db/scim.py`)
- **[consistency] Revoke 404.** `DELETE /admin/scim/tokens/{id}` returned 204 even for a missing token
  (dead frontend error branch). Now raises 404 when `revoke_token` is False. (`admin_api.py`)
- **[log noise] 4xx not logged at ERROR.** `scim_operation` logged expected client rejections (404/409) at
  ERROR. Added `as_error` to `log_scim_event`; ScimError <500 now logs at INFO, ≥500 stays ERROR.
  (`scim_logging.py`)
- **[web] Cleanups.** Removed unused `Button` import; added `onOpenChange` to the one-time token modal so
  Esc/outside-click dismiss it. (`web/src/app/admin/scim/page.tsx`)
- **[test] Brittle assertion + new coverage.** Loosened `guarded == 12` → `>= 12`; added a `_reactivate`
  test (locks the re-provision decision) and 4 `_paginate` math tests.

Verification (all green): `pytest tests/unit/om/server/scim/` **69 passed** (+5); `mypy` **0 errors** in the
changed scim files; web `tsc --noEmit` clean. Confirmed `metadata.create_all()` fails standalone with
`NoReferencedTableError: table 'team'` — expected (WS-B lands `team`); group tests use fakes. Did NOT
commit; did NOT run `alembic upgrade`. Integrator TODOs (Alembic linearize, tenancy shim, snapshot regen)
unchanged.
