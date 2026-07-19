# WS-B — Team / RBAC — status log

Worktree: `.claude/worktrees/ws-b` (branch `rewrite/ws-b` off `rename_onyx_to_om`).
Owns **Contract 1 (Team model)** + **Contract 2 (Access API)**.

Phase plan:
- P0 Wave0: finalize Contract 1 (Team table + associations) + Contract 2 (Access API signatures + ACL rename) in CONTRACTS.md; DO_NOT_RENAME index-ACL entry.
- P1 Data model + RBAC core: models.py rename UserGroup→Team; Alembic 0004_team_rename; clean-room `om/access/rbac/` PDP + `om/db/team.py` service. Review: permission-matrix unit tests, least-privilege.
- P2 Access API + index filter: clean-room rewrite access.py/utils/models + access_filters; team ACL prefixes. Review: ACL parity diff-test.
- P3 External-perm sync + hierarchy + censoring + connectors group-sync.
- P4 Web: Teams screens + hooks + menu (role-gated, VertualAI).
- P5 Delete old user_group code/routes/hooks; verify boot + search-with-permissions + logs.

---

- [P0] Started: read CONTRACTS.md + WS-B in full; graphify-oriented on UserGroup/access/tenancy; mapped current
  RBAC/doc-access subsystem (models.py lines, access.py signatures, external_permissions, connectors, web hooks, menu)
  and the exact baseline DDL for every `user_group`* table. Researched enterprise RBAC/ReBAC (Zanzibar, NIST, OWASP,
  PDP/PEP, doc-ACL early-binding, external-group sync + fail-closed censoring) — cited in README. — now
- [P0] Key facts locked: Alembic head=`0003_agent_rename` (persona→agent already done, so `agent__user_group`,
  `llm_provider__agent` are the current physical names). Baseline=`0001_baseline_schema` (squashed `.sql`). Tenant
  primitives via Contract-3 facade `om.tenancy.context` (WS-M owns; I add a thin re-export shim so my worktree is
  coherent — integrator drops it for WS-M's canonical module). Fresh DB + fresh index → full RENAME, no reindex.
- [P0] Contract 1 + Contract 2 **FINALIZED** and appended to CONTRACTS.md (see "WS-B FINALIZED" block). DO_NOT_RENAME.md
  updated with the team-based ACL prefix + index-field contract. Naming map: user_group→team everywhere incl. the two
  extra lineage tables surfaced in the map — `token_rate_limit__user_group`→`token_rate_limit__team` (heads-up to WS-F)
  and `mcp_server__user_group`→`mcp_server__team`.

- [P1] DONE. models.py fully renamed UserGroup→Team (80 replacements, compiles + imports). Alembic
  `0004_team_rename.py` = dynamic catalog-driven metadata rename (down_revision=0003_agent_rename). Clean-room RBAC
  package `om/access/rbac/` (permissions matrix, PermissionService PDP, TeamRepository, audit) + tenancy facade shim
  `om/tenancy/context.py` (INTEGRATOR: drop for WS-M's canonical). Clean-room `om/db/team.py` service. **Review gate:
  `tests/unit/om/access/test_rbac.py` — 21 passing** (least-privilege, hierarchy, SoD, team-scoping).
- [P2] DONE. Clean-room rewrite: `access/access.py`, `access/models.py`, `access/utils.py`, `db/external_perm.py`.
  ACL prefixes now `team:` / `external_team:` (`user_email:` + `PUBLIC` unchanged). Downstream identifier sweep across
  **105 backend files** (deterministic ordered-substring script, `ExternalUserGroup` sentinel-protected) → whole
  backend compiles (`compileall` clean) and core modules import cleanly. File moves: `db/user_group.py` deleted,
  `redis/redis_usergroup.py`→`redis_team.py`, `server/user_group/`→`server/team/` (router now `/teams` + PDP-enforced),
  integration test helper/dir moved. **Review gate: `tests/unit/om/access/test_acl_parity.py` — 4 passing**
  (write/read round-trip, team prefixes, allow/deny matrix). READMEs: `om/access/README.md`, `om/access/rbac/README.md`.
  main.py wiring (`team_router` at `/teams`) applied by sweep — integrator confirm.
- [P2] Heads-up to other WS surfaced by the sweep: `TokenRateLimit__UserGroup`→`TokenRateLimit__Team` +
  `insert_user_group_token_rate_limit`→`insert_team_token_rate_limit` (WS-F); `ScimGroupMapping.user_group`→`.team`,
  `scim_group_mapping.user_group_id`→`team_id` (WS-G). Both FK `team.id`.

## REMAINING (honest hand-off) — not finished this session
- **P3 clean-room**: `access/hierarchy_access.py`, `db/hierarchy.py`, `external_permissions/post_query_censoring.py`,
  `external_permissions/sync_params.py`, `external_permissions/confluence/space_access.py` were **mechanically renamed
  by the sweep, NOT clean-room rewritten** — they keep EE-origin control flow. MUST be reimplemented from behavior
  before the IP-review. Connector group_sync files (github/gdrive/confluence/jira/sharepoint/slack) were renamed +
  compile; verify they write `external_team_id` principals end-to-end.
- **P4 web**: delegated mechanical rename (hooks `useUserGroups`→`useTeams`, URLs→`/api/teams`, menu "Access Groups"→
  "Teams", route `/admin/groups`→`/admin/teams`). VertualAI *polished* Teams screens + roles-management screen NOT built.
- **P5**: full app boot (needs braintrust/posthog optional deps + DB) + tenant-isolation search smoke NOT run here.
  Drop `om/tenancy/context.py` shim in favor of WS-M's. Route-rename snapshots under `tests/route_rename/snapshots/before/`
  still reference old user-group routes (guard-test fixtures — coordinate).

- [P4] DONE (mechanical). Web renamed User/Access Groups → Teams, repointed to `/api/teams` (+ `/teams/minimal`).
  Hooks `useUserGroups`/`useGroups`→`useTeams`, `useShareableGroups`→`useShareableTeams`; types `UserGroup`→`Team`,
  `MinimalUserGroupSnapshot`→`MinimalTeamSnapshot`; nav "Access Groups"→"Teams" at `/admin/teams`; pages `app/admin/groups`
  →`app/admin/teams` (git mv, `[groupId]`→`[teamId]`, `UserGroupsTable`→`TeamsTable`, `UserGroupCreationForm`→`TeamCreationForm`);
  user-facing copy updated. **`npx tsc --noEmit` passes** (only a pre-existing unrelated `dotenv` decl error). Route shapes
  match the backend `/teams` router exactly. Deliberately left the SEPARATE token-rate-limit `Scope.USER_GROUP` /
  `/token-rate-limits/user-group` concept alone (backend also kept that uppercase enum) — that's WS-F's to rename.
  STILL REMAINING for P4: *polished* VertualAI redesign + a dedicated roles-management screen (this was a functional
  rename, not a redesign).

## [REVIEW] Self-review pass — gaps found + fixed
Phase checklist: P0 ✅ · P1 ✅ (21 tests) · P2 ✅ (4 ACL-parity tests) · P3 🟡 (censoring + hierarchy_access
clean-room rewritten; db/hierarchy.py + sync_params.py + confluence/space_access.py still mechanically renamed) ·
P4 ✅ mechanical (tsc passes, menu role-gated) 🟡 polished screens + roles-mgmt screen not built · P5 🟡 (old code
deleted+verified; full boot needs braintrust/posthog+DB, not run).

Gaps FIXED this pass:
1. **Contract 1 deviation — `team.id` was INTEGER, contract says BIGINT.** Fixed: `Team.id` + all 9 `team_id` FK
   columns → `BigInteger` in models.py; migration `0004` now widens `team.id`(+`team_id` FKs) to BIGINT via a
   FK-preserving DO block (captures `pg_get_constraintdef`, drops, alters, re-adds — ON DELETE preserved). Verified
   `Team.id type = BIGINT`.
2. **Standard 9 — missing audit logs.** `mark_team_as_synced` (event=`team.perm_sync`) and `delete_team`
   (event=`team.deleted`) now wrapped in `audit_event`. All 7 team mutations now emit structured logs.
3. **Dead code.** Removed unused `logger`/`setup_logger` from `db/team.py`.
4. **Leftover old refs (hyphenated — missed by the underscore sweep).** `license_enforcement_config.py`
   `/nexus/admin/user-group` → `/teams`; `db/users.py` user-facing "User Group Menu" → "Teams Menu".
5. **Bug — `delete(...).where(..., True)`** raw-Python-bool coercion in `update_team`. Rewrote as a conditional
   condition-list (empty target removes all members correctly, no coercion).
6. **Clean-room (reduced debt).** Rewrote `post_query_censoring.py` (own structure; imports tenant session from the
   `om.tenancy.context` facade per Contract 3) — and in doing so **avoided a would-be leak regression**: censored
   survivors are keyed by the object the censoring func RETURNS (redaction-preserving), not the original chunk.

Verification: configure_mappers OK · py_compile OK · mypy = 0 errors in authored files (14 pre-existing third-party
stub errors elsewhere) · unit tests 25/25 pass · web tsc passes (P4) · Alembic single head `0004`.
Still REMAINING (flagged, not fixed — size/scope): clean-room rewrite of hierarchy.py/sync_params.py/space_access.py;
polished VertualAI Teams + roles screens; full boot + tenant-isolation smoke.

## [REVIEW-FIX] Remaining items resolved
- **Clean-room rewrites COMPLETE** (were mechanically-renamed EE code; now genuinely re-expressed — own structure/naming/control-flow, behavior + public signatures preserved):
  - `external_permissions/sync_params.py` — declarative builder-based registry + shared-`.get()` lookups; data parity verified (censoring={SALESFORCE}, cc-pair-agnostic={CONFLUENCE,JIRA}).
  - `external_permissions/confluence/space_access.py` — own helper decomposition (`_resolve_server_emails`, `_first_result_field`, `_prefix_groups`); Confluence cloud/server parsing behavior preserved.
  - `db/hierarchy.py` (600L) — full rewrite; mypy `Success: no issues`, `configure_mappers` OK, all public signatures preserved, 0 `user_group` leftovers. Security-critical `_visibility_predicate` verified: `or_(is_public, email∈external_user_emails, groups⊕external_team_ids)` with the varchar[] cast — exact 3-way predicate intact.
  - (`access/access.py`, `access/hierarchy_access.py`, `post_query_censoring.py` were rewritten earlier.) All 6 EE-origin files from the behavior spec are now clean-room.
- **Dead code DELETED**: `Action` enum (exported, never used) + `INSTANCE_ADMIN_ROLES`/`CURATOR_CAPABLE_ROLES` (0 uses) from `rbac/permissions.py` (+ `__init__` export); unused `logger` from `db/team.py`. AST scan → no unused imports remain. Stale integration-test filenames renamed to `test_add_users_to_team/test_team_deletion/test_team_syncing.py`.
- **Type fix**: 3 pre-existing `arg-type` errors at `validate_object_creation_for_user` call sites (`connector.py`, `document_set/api.py` x2) — non-`bool` truthy args wrapped in `bool(...)` (runtime behavior identical).
- **P4 web polish DONE**: Teams list/table/detail pages restyled to VertualAI (AdminPageTitle, Card, themed Table, member-avatar stacks, StatusBadge, empty states, ErrorCallout) — data flow untouched, theme tokens only (no hardcoded accent colors). NEW read-only **Roles & Permissions** screen at `/admin/roles` (role-tier cards + 8×5 permission matrix encoding the scope/SoD nuances). Menu "Roles" entry added **admin-only** (`!isCurator` branch). `npx tsc --noEmit` clean (only a pre-existing unrelated `dotenv` decl error).
- **Verification**: full `compileall om/` clean · `configure_mappers` OK (`Team.id = BIGINT`) · mypy = 0 errors in authored/rewritten files · 25/25 unit tests pass · web tsc clean.
- **Genuinely remaining (needs infra, cannot run here)**: full app boot (optional deps braintrust/posthog + DB) + multi-tenant isolation smoke; drop `om/tenancy/context.py` shim for WS-M's canonical facade at integration; route-rename snapshot fixtures under `tests/route_rename/`.
