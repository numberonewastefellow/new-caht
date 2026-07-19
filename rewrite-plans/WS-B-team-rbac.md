# WS-B — Team / RBAC (best-practice enterprise access control)

## ▶ AGENT INSTRUCTIONS — START HERE (read this whole block first)

**You were pointed at this file to IMPLEMENT workstream WS-B. Do exactly this:**

0. **DUPLICATE CHECK — before anything.** If `.claude/worktrees/ws-b` already exists OR
   `rewrite-plans/status/WS-B.md` already has status lines from another agent, another agent owns WS-B:
   **STOP, report "WS-B already in progress — standing down", make NO changes.** Otherwise self-isolate:
   `git worktree add .claude/worktrees/ws-b -b rewrite/ws-b rename_onyx_to_om`
   Working root = `d:\llm\danswer20022026\.claude\worktrees\ws-b`; do ALL edits there, never the main tree.
1. **Read** `rewrite-plans/CONTRACTS.md` (contracts + ownership rules + 12 standards) and the rest of
   THIS file. You OWN **Contract 1 (Team model)** and **Contract 2 (Access API)** — confirm/finalize them;
   if you change any name/signature, update `CONTRACTS.md` in the main tree and note it.
2. **Legal — clean-room.** Behavior spec only. NEVER open/copy/paraphrase Onyx EE source at
   `D:\llm\danswer07022026_original\onyx\backend\ee\...`.
3. **Orient with graphify** before reading source.
4. **Phases + review gates.** TodoWrite; self-review after each phase; ACL parity diff-test before deleting old.
5. **Research first** (RBAC/ReBAC, Zanzibar, least-privilege, resource-scoped grants); cite in README.
6. **Standards:** multi-tenant-safe (Contract 3); dedicated config tables + UI; VertualAI design system;
   rename the "User Groups" menu → "Teams"; structured OpenSearch logs on every CRUD in try/except; OOP + strict typing.
7. **Delete old `user_group` tables/code only in the FINAL phase**, after ACL parity verified.
8. **Write** a module README (access + rbac).
9. **Progress:** append to `d:\llm\danswer20022026\rewrite-plans\status\WS-B.md` at each phase.
10. **Do NOT commit/push. Do NOT run `alembic upgrade` by hand.** Summarize + confirm Contracts 1 & 2 at the end.

**Wave:** 0 (foundation). **Emphasis:** best-in-class enterprise RBAC around **Teams**; full rename
`UserGroup`→`Team` across DB, index ACL fields/prefixes (fresh index → NO reindex), connectors
external-group-sync, knowledge base, and web hooks. Update `DO_NOT_RENAME.md` for the new index contract.

---

> Read `CONTRACTS.md` first. You OWN **Contract 1 (Team model)** and **Contract 2 (Access API)**.
> Foundation workstream — publish contract finals in Phase 1. Follow all Engineering standards.

## Goal

Replace Onyx's `UserGroup`/`user_group` RBAC + document-ACL system with a **clean-room, best-in-class
enterprise RBAC** built around **Teams**. This is the load-bearing subsystem: document access
filtering for search depends on it. Full rename across DB, index ACL fields, connectors, knowledge
base, and web. **Fresh DB + fresh index → full rename, no reindex, no back-compat.**

## Research first (Standard 2)
Web-research modern access-control before designing: RBAC vs ReBAC (Google Zanzibar / relationship
tuples), least-privilege role hierarchies, resource-scoped permissions, policy-check centralization.
Record decisions in the README. Aim for: **Roles** (e.g. admin / curator / member / limited) +
**Teams** (grouping of users) + **resource-scoped grants** (docs, document-sets, connectors, agents,
LLM providers scoped to teams), with a single centralized, testable permission-check layer.

## Behavior spec (WHAT — write your own HOW; do NOT open Onyx files)
Replaces (current EE-origin files): `access/access.py` [MERGED], `access/hierarchy_access.py`,
`db/hierarchy.py` [MERGED], `external_permissions/{post_query_censoring,sync_params}.py`,
`external_permissions/confluence/space_access.py`.

- **DocumentAccess resolution:** per document → set of principals (internal users, teams, external
  groups, public). Per user → ACL entry set for building the index access filter.
- **Team membership + curator flag**, team↔(cc_pair, document_set, credential, agent, llm_provider) grants.
- **External-group permission sync:** connectors that sync external groups/emails → team-mapped ACLs.
- **Post-query censoring:** for censoring sources, drop chunks a user may not see (preserve ordering).
- **Hierarchy nodes** with permission columns (public / email-list / group-overlap) for browse filters.
- **Sync-attempt tracking** tables for doc-permission-sync and external-group-sync.

## New tables (Contract 1 — finalize names in Phase 1)
`team` + `user__team`, `team__connector_credential_pair`, `document_set__team`, `credential__team`,
`agent__team`, `llm_provider__team`, `llm_provider__agent`; external-group: `user__external_team_id`,
`public_external_team`; `hierarchy_node` (renamed team-based permission cols); sync-attempt tables.
Add a **roles/permissions** representation per your researched RBAC design (table or enum + grants).

## Index ACL rename (Contract 2)
Rename the index ACL field (`external_user_group_ids` → team-based) and the internal ACL prefix
strings in the access filter. No reindex (fresh index). Update `DO_NOT_RENAME.md` to the new contract.

## Config + UI
- Admin **Teams** screens (VertualAI design system): list/create/edit team, manage members + curators,
  manage team resource grants. Roles management screen. **API base `/teams`.**
- Update MENU: replace "User Groups" nav entry with "Teams" (role-gated).
- Rename web hooks `useUserGroups`/`useGroups`/`useShareableGroups` → team equivalents.

## Shared-file snippets (integrator)
- `models.py`: team + association + hierarchy + sync-attempt model block.
- `main.py`: `/teams` router include (replaces `/nexus/admin/user-group`).
- Alembic: revisions for all new tables.
- Menu registry: Teams entry.

## Phases (with review gates)
- **Phase 0 (Wave 0):** publish Contract 1 finals + Contract 2 signatures in `CONTRACTS.md`.
- **Phase 1 — Data model + RBAC core.** Team tables, roles/permissions, centralized permission-check
  service (multi-tenant-safe, Contract 3). **Review:** permission matrix unit-tested; least-privilege holds.
- **Phase 2 — Access API + index filter.** Rewrite `access.py` bodies behind the frozen signatures;
  team-based ACL prefixes + index field. **Review:** ACL parity diff-test vs current allow/deny on a
  fixed corpus + user/team set.
- **Phase 3 — External-perm sync + hierarchy + censoring + connectors.** **Review:** group-sync writes
  team ACLs; censoring drops correctly; connector group-sync updated.
- **Phase 4 — Web (Teams screens + hooks + menu).** **Review:** design-system compliance; role-gating.
- **Phase 5 — Delete old + verify.** Remove `user_group` tables/code, old hooks, `/nexus` group routes.
  **Review:** full app boot + search-with-permissions works; structured logs present.

## Structured logs (Standard 9)
`event=team.created|updated|deleted|member_added|member_removed|grant_changed|perm_sync`,
`entity=team|team_membership|external_group_sync`, `entity_id`, `tenant_id`, `actor_user_id`,
`action`, `status`, `duration_ms`, `error`.

## Verification
- ACL parity diff-test (new vs old allow/deny) before deleting old code.
- Role checks enforce least-privilege (unit tests). Search returns only permitted docs per user/team.
- Tenant isolation: team data never crosses tenants.

## README
`backend/om/access/README.md` (+ rbac module README): RBAC model + why (cite research), Team schema,
Access-API contract, index ACL fields, how to add a new resource-scoped permission, log events.
