# CONTRACTS.md — shared foundation for the EE-rewrite workstreams

This file is the **single source of cross-workstream coupling**. Every workstream (`WS-*.md`) depends
on the contracts and standards below and MUST NOT diverge from them. If a contract needs to change,
change it here first and notify the integrator — do not fork it inside a workstream.

## Why this rewrite exists (read first)

The `backend/om/**` tree contains code that originated under Onyx's **Enterprise License** (not MIT),
merged in by commits `c26724925` (Stage 2.2) + `77ed3c9c2` (Stage 2.1). That license forbids
copy/merge/sublicense/sell. We are removing the Enterprise-Licensed **expression** by
**clean-room reimplementing** (or deleting) each EE-origin feature: we may re-create the same
*functionality* (not copyrightable) but must write our **own code from the behavior spec — never with
the Onyx file open beside us, never paraphrasing it**. Reference original for BEHAVIOR only via this
plan's specs; do not copy structure, names, comments, or control flow.

> Not legal advice. The rewritten set will be IP-reviewed against the provenance commits before sale.

## Deployment target

**Self-hosted, MULTI-TENANT for data isolation, NO billing.** Multi-tenancy is mandatory (isolates
each tenant's data via schema-per-tenant) but fully decoupled from Stripe / any external control plane.

---

## Contract 1 — Team model (RBAC group concept)

Onyx's `UserGroup` / `user_group` is replaced end-to-end by **`Team`**. Owned/implemented by **WS-B**;
every other workstream codes against this shape and must NOT redefine it.

- Model `Team` → `__tablename__ = "team"`: `id BIGINT PK`, `name TEXT UNIQUE NOT NULL`,
  plus lifecycle/audit columns (`is_up_to_date`, timestamps) as WS-B finalizes.
- Association tables (names are the contract): `user__team`, `team__connector_credential_pair`,
  `document_set__team`, `credential__team`, `agent__team`, `llm_provider__team`.
- External-group tables (renamed off `user_group` lineage): `user__external_team_id`,
  `public_external_team` (final names confirmed by WS-B in Phase 1; if changed, update here).
- UI label: **"Team"**; admin API base: **`/teams`** (replaces `/nexus/admin/user-group`).
- WS-F (rate limits) and WS-G (SCIM) FK to `team.id` — they depend only on `team(id BIGINT PK)`.

## Contract 2 — Access API (document ACL)

So search/standard-answers don't depend on RBAC internals, `backend/om/access/access.py` keeps these
**public function signatures stable** (WS-B rewrites the bodies clean-room):

- `get_access_for_document(document_id, db_session) -> DocumentAccess`
- `get_access_for_documents(document_ids, db_session) -> dict[str, DocumentAccess]`
- `get_acl_for_user(user, db_session) -> set[str]`
- `build_access_filters_for_user(user, db_session) -> AccessFilter`  (index ACL filter)
- `get_access_for_knowledge_files(...) -> ...`
- `source_should_fetch_permissions_during_indexing(source) -> bool`

Callers (WS-D, WS-E) import only these. The internal ACL prefix strings + the index ACL field
(Onyx's `external_user_group_ids`) are renamed to team-based names by WS-B — since the DB and index
are **fresh (no existing indexed data)**, this needs **no reindex**. WS-B updates `DO_NOT_RENAME.md`.

## Contract 3 — Tenant context (multi-tenant safety)

Owned/refactored by **WS-M**; every workstream MUST use it so nothing leaks across tenants.

- Current tenant id: read from `CURRENT_TENANT_ID_CONTEXTVAR` (contextvar set by the tenant-tracking
  middleware per request). Never hardcode a schema.
- Tenant-scoped DB session: obtain via the tenant-bound session helper (`get_session_with_tenant` /
  the WS-M-refactored equivalent) — every query runs inside the tenant's Postgres schema.
- New tables live **inside the per-tenant schema** (not `public`) unless they are genuinely global
  (WS-M documents the small set of `public`-schema tables, e.g. email→tenant mapping).
- Every log line and every metric carries `tenant_id` (see Standard 9).
- WS-M publishes, in Phase 1, the exact import paths for "get current tenant" and "get tenant session";
  all other workstreams import those, not Onyx's originals.

---

## Shared-file ownership rules (prevents merge collisions)

Agents work in **separate git worktrees**. Disjoint NEW files never conflict. The four shared files
are handled by **section-ownership + an integrator**:

- `backend/om/db/models.py` — each WS appends its models under a labeled banner
  `# === <WS-id>: <feature> models ===`; never edit another WS's block. WS-A removes only the tables it deletes.
- `backend/om/main.py` — each WS delivers, in its plan output, a **wiring snippet** (imports +
  `include_router`/`add_middleware` lines). The **integrator** applies snippets. WS-A owns the
  billing/license router removals; WS-M owns the tenant-middleware wiring.
- `backend/om/server/auth_check.py` — each WS supplies its public-endpoint spec entries; integrator merges.
- **Alembic** — each WS writes its migration as a standalone revision file with `down_revision = None`
  as a placeholder; the **integrator linearizes** the chain off the current head `0003_agent_rename`.
- `web/**` nav/menu registry — each WS delivers its menu-entry snippet; integrator applies to the
  shared admin sidebar. Each WS owns its own new page directory.

## Integration procedure

1. Wave 0: WS-B, WS-M publish their contract specifics (Team table finals, tenant import paths) here.
2. Wave 1: all 9 workstreams run in parallel worktrees against these contracts.
3. Integrator: merge worktrees → apply models.py/main.py/auth_check/menu snippets → linearize Alembic
   → boot **multi-tenant, no-billing** → run `check_ee_router_auth`, unit/integration tests, and a
   **tenant-isolation smoke test** (tenant A cannot see tenant B across every feature).
4. IP-review the full rewritten set against commits `c26724925` + `77ed3c9c2`.

---

## Engineering standards — MANDATORY for every workstream

1. **Phased + review gates.** Split work into **Phase 1, 2, …**; end each phase with a self-review
   (re-read the code, find gaps/bugs/missing error-handling, fix), THEN continue. Track with **TodoWrite**.
2. **Research first.** Use **WebSearch/WebFetch** for current best practices & reference docs
   (enterprise RBAC/ReBAC, SCIM 2.0 RFC 7643/7644, token-bucket/sliding-window rate limiting, recharts).
   Record what informed the design in the WS `README.md`.
3. **Clean-room only.** Behavior from the spec, not Onyx's source. Own module layout, own names, own control flow.
4. **Multi-tenant-safe by construction** (Contract 3). Every table/query/log tenant-scoped; no cross-tenant leaks.
5. **Per-feature config, UI-configurable.** Default to a **dedicated typed config table** (like search
   settings). Use `key_value_store` **only** for a simple singleton JSON blob where a table is overkill
   (KV optional, not default).
6. **VertualAI design system.** Reuse the existing component library + accent-theme CSS vars
   (`--theme-primary-*`, `--virtualai-accent`, `.virtualai-gradient-text`; never hardcode accent
   colors — see project CLAUDE.md). Polished screens, not bare CRUD forms.
7. **Update MENU panels.** Register each new screen in the admin/nav menu with correct role-gating;
   document the menu edit in the WS README.
8. **Analytics = lightweight React charts** (recharts), responsive + theme-aware. (WS-H specifically.)
9. **Structured logging for OpenSearch.** On every create/update/delete + significant event, emit a
   structured (JSON-friendly) log with fields: `event`, `entity`, `entity_id`, `tenant_id`,
   `actor_user_id`, `action` (create/update/delete/…), `status`, `duration_ms`, `error`. Always wrap
   in **try/except** with meaningful messages. Dashboards are out of scope; meaningful logs are in scope.
10. **Clean OOP.** services / repositories / models separation; strict typing (mypy strict; TS types);
    readable + extensible; no dead code; no copy-paste from Onyx.
11. **Delete-old-after-verify.** The FINAL phase of each WS removes the old EE-origin tables, models,
    routes, and files it replaced — only after the new impl is verified. Fresh DB → drops need no migration.
12. **Per-workstream README.** Write a `README.md` in the new module: architecture, multi-tenant
    readiness, config table/UI, structured-log events emitted, and how to extend — future reference doc.

## Provenance reference (behavior only — do NOT copy code)

Original Onyx EE tree for BEHAVIOR reference lives at the read-only checkout
`D:\llm\danswer07022026_original\onyx\backend\ee\onyx\**`. The current merged files in this repo are
listed per workstream. Use them to understand WHAT to build; write the HOW yourself.

---

## Contract 3 — FINALIZED (WS-M, Wave 0) — import these EXACT paths

Canonical facade module: **`backend/om/tenancy/context.py`** (re-exports the stable primitives so all
workstreams import from ONE place). Legacy locations still work (facade re-exports them), but NEW code
MUST import from `om.tenancy.context`.

**(a) Get current tenant id** — `from om.tenancy.context import get_current_tenant_id`
- `get_current_tenant_id() -> str` — reads `CURRENT_TENANT_ID_CONTEXTVAR`; raises in MT mode if unset,
  returns default schema single-tenant. Also exported: `CURRENT_TENANT_ID_CONTEXTVAR`.

**(b) Get tenant-scoped DB session** (all bind the tenant's Postgres schema via schema_translate_map):
- `from om.tenancy.context import get_current_tenant_session` — `@contextmanager`, tenant in contextvar
  (request-scoped default).
- `from om.tenancy.context import get_tenant_session` — `get_tenant_session(*, tenant_id: str)` explicit
  tenant (background jobs / cross-tenant loops).
- `from om.tenancy.context import get_shared_schema_session` — pinned to `public` (ONLY for global tables).
- FastAPI dep: `from om.tenancy.context import get_tenant_session_dependency` (401s unauth in MT mode).

**Public-schema (global) tables — everything else is per-tenant:**
- `user_tenant_mapping` — email→tenant login-routing map (WS-M owns). GLOBAL / `public`.
- `alembic_version` in `public` — bookkeeping for the shared/public baseline.
- DROPPED by WS-M final phase: `available_tenant`, `tenant_anonymous_user_path`.
- EVERY feature table lives INSIDE the per-tenant schema — do NOT set `{"schema": "public"}` on new models.

---

## Contract 1 — FINALIZED (WS-B, Wave 0) — Team model

`UserGroup`/`user_group` → **`Team`**/`team`. Full rename (fresh DB + fresh index, no back-compat, no reindex).
The physical baseline already has `persona`→`agent` folded in (Alembic head `0003_agent_rename`), so the current
`agent__user_group` / `llm_provider__agent` names are what WS-B renames from.

**`Team`** — `__tablename__ = "team"` (per-tenant schema):
- `id BIGINT PK` (currently `INTEGER`; widened to BIGINT per contract — WS-F/WS-G FK to `team.id`).
- `name TEXT UNIQUE NOT NULL`.
- Lifecycle/audit: `is_up_to_date BOOLEAN NOT NULL` (index-sync propagation flag),
  `is_up_for_deletion BOOLEAN NOT NULL`, `time_last_modified_by_user TIMESTAMPTZ NOT NULL DEFAULT now()`.

**Association tables (contract names — all per-tenant):**
- `user__team` (`team_id`, `user_id`, `is_curator BOOL DEFAULT false`) — membership + team-scoped curator flag.
- `team__connector_credential_pair` (`team_id`, `cc_pair_id`, `is_current BOOL`).
- `document_set__team` (`document_set_id`, `team_id`).
- `credential__team` (`credential_id`, `team_id`).
- `agent__team` (`agent_id`, `team_id`) — was `agent__user_group`.
- `llm_provider__team` (`llm_provider_id`, `team_id`).
- Also renamed (lineage tables the map surfaced, not in the original list):
  `mcp_server__team` (was `mcp_server__user_group`) and **`token_rate_limit__team`** (was
  `token_rate_limit__user_group`) — heads-up **WS-F**: FK column is now `team_id → team.id`.
- Pre-existing, NOT WS-B's (kept from `0003`): `llm_provider__agent` (`llm_provider_id`, `agent_id`).

**External-group tables (renamed off `user_group` lineage):**
- `user__external_team_id` (was `user__external_user_group_id`): `user_id`, **`external_team_id`** (was
  `external_user_group_id`), `cc_pair_id`, `stale BOOL DEFAULT false`.
- `public_external_team` (was `public_external_user_group`): **`external_team_id`**, `cc_pair_id`, `stale`.

**Hierarchy + sync-attempt tables (names KEPT — not `user_group`-lineage; only team-based columns renamed):**
- `hierarchy_node`: permission columns `is_public`, `external_user_emails` (email-list),
  **`external_team_ids`** (was `external_user_group_ids`, group-overlap array).
- `hierarchy_fetch_attempt`, `doc_permission_sync_attempt`, `external_group_permission_sync_attempt` — unchanged names.

**Roles / permissions (WS-B RBAC design — see `backend/om/access/rbac/`):** global `UserRole` enum
(`admin`/`global_curator`/`curator`/`basic`/`limited`/`slack_user`/`ext_perm_user`) is KEPT (not renamed — it is not
`user_group` lineage). Team-scoped authority = the `user__team.is_curator` flag. Fine-grained authorization is an
**enum + role→permission matrix in code** (a centralized PDP), not a new table — resource-scoped grants ARE the
association tables above. UI label: **"Team"**; admin API base: **`/teams`**.

## Contract 2 — FINALIZED (WS-B, Wave 0) — Access API + ACL rename

**Frozen public signatures** (WS-B rewrites the bodies clean-room; WS-D/WS-E import only these):
- `om.access.access.get_access_for_document(document_id: str, db_session: Session) -> DocumentAccess`
- `om.access.access.get_access_for_documents(document_ids: list[str], db_session: Session) -> dict[str, DocumentAccess]`
- `om.access.access.get_acl_for_user(user: User, db_session: Session | None = None) -> set[str]`
- `om.access.access.get_access_for_knowledge_files(knowledge_file_ids: list[str], db_session: Session) -> dict[str, DocumentAccess]`
- `om.access.access.source_should_fetch_permissions_during_indexing(source: DocumentSource) -> bool`
- `om.context.search.preprocessing.access_filters.build_access_filters_for_user(user: User, session: Session) -> list[str]`
  (index ACL filter list; corrects the CONTRACTS-draft `-> AccessFilter` — it returns `list[str]` and lives in
  `access_filters.py`, not `access.py`). `build_user_only_filters(user, db_session) -> IndexFilters` also kept.
- `DocumentAccess` / `ExternalAccess` (frozen dataclasses) kept; `DocumentAccess.build(...)` + `.to_acl()` kept. Two
  field renames (fresh DB, no back-compat): `user_groups → teams`, `external_user_group_ids → external_team_ids`
  (in `ExternalAccess`, `DocumentAccess`, and `.build()` kwargs). Callers updated by WS-B.

**ACL string encoders (`om.access.utils`) — team-based rename:**
- `prefix_user_email(email) -> "user_email:{email}"` — **UNCHANGED**.
- `prefix_user_group → prefix_team`: `"group:{name}" → "team:{name}"`.
- `prefix_external_group → prefix_external_team`: `"external_group:{name}" → "external_team:{name}"`.
- `build_ext_group_name_for_om → build_ext_team_name_for_om` (source-prefixed external id).
- Public sentinel `PUBLIC_DOC_PAT = "PUBLIC"` — unchanged.

**Index ACL field:** the OpenSearch index carries `access_control_list` (keyword list of the encoded strings above)
+ `is_public` — the field NAMES are unchanged; only the **prefixes inside** `access_control_list` change
(`team:` / `external_team:`). The per-document stored group column `document.external_user_group_ids` and
`hierarchy_node.external_user_group_ids` → **`external_team_ids`**. Fresh index ⇒ **no reindex**. Write-side
(`DocumentAccess.to_acl`) and read-side (`get_acl_for_user`→`build_access_filters_for_user`) stay in lockstep.
`DO_NOT_RENAME.md` updated with this contract.
