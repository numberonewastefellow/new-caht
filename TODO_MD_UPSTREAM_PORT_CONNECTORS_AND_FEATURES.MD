# TODO — Porting Upstream Connectors, Integrations and Features

**Date:** 2026-10-29
**Fork point:** upstream commit `fc6a37850` (2026-02-19, "delta sync sharepoint"), the merge-base with git remote `upstream`
**Upstream compared:** HEAD `73e0ae3c31` (2026-10-29), about 8 months of drift (503 upstream commits on connectors alone)
**Companion doc:** `TODO_MD_RAG_UPGRADES_FROM_UPSTREAM.MD` (RAG and search upgrades)

## Naming rules for this doc and for every port
- **Never use the upstream product name** in this repo: not in code, paths, docs, comments or commit messages. Always use our names (`om`, `ombot`, Agent, KnowledgeFile, Workspace, Team, VertualAI). `rename-audit/build_inventory.py --check` enforces this.
- **We have no EE tree.** Never create an `ee/` folder. Upstream enterprise features are reimplemented clean-room as normal code inside our own structure (`backend/om/...`, `web/src/app/...`), in the folder where that feature already lives in our repo. If it has no home yet, make a new folder that follows our existing layout.
- **One feature at a time.** Every item below needs its own `TODO_MD_PORT_<FEATURE>.MD`, written from the §1.5 template and approved by the user, **before any code is written**. Never bulk-port.
- Path notation used below:
  - **`UP:<path>`**: the file in the upstream checkout, **written with our names** (upstream package → `om`, bot package → `ombot`, and so on). It is a reference to read, not a place to copy from blindly. The local path of the upstream checkout is kept in Claude memory, not in this repo.
  - **`UP-EE:<path>`**: the same, but from the upstream enterprise tree. Behaviour reference only. **Clean-room reimplement, never copy** (`rewrite-plans/CONTRACTS.md`).
  - **Target**: where the code goes in **our** tree.
- Priority: **P1** = do next, **P2** = valuable, **P3** = later or optional.

---

## 1. Porting recipe

### 1.1 Ground rules
- Git history is shared, but **do not cherry-pick or merge**: every path differs. Either:
  - run `git format-patch`, translate the patch, then `git apply --3way`; or
  - copy-and-translate whole new folders (best for new connectors and modules).
- Sort every upstream change into one of three buckets:
  - **Open-source code**: translate it with §1.2.
  - **Enterprise code**: write a behaviour spec, then implement it fresh in our existing `om/` folder (see the Target column in each table).
  - **Vespa or model-server code**: drop it, or adapt it to OpenSearch or Cortex.
- **Database:**
  - We renamed both **tables and columns**, so upstream migrations and models **never map 1:1**.
  - Each feature's schema change is planned in its own per-feature doc (§1.5, step 2), then written as a **new** migration chained off our head (baseline `0001_om_baseline`).
  - Use our table and column names, and keep revision ids to 32 characters or fewer.
  - Never run alembic manually; migrations apply when the container restarts (CLAUDE.md).
- **EE gating:** upstream calls `fetch_versioned_implementation` in 72 places. We removed it, so every call becomes a direct import. A guard test fails if it comes back.

### 1.2 Translation rules (apply in this order)
The full mapping, including the upstream-side spellings, lives in `rename-audit/DECISIONS.md` and `DO_NOT_RENAME.md`. Summary of the targets:

1. **Module paths:** upstream backend package → `om`; bot package → `om/ombot`; `*_api` server package → `om/server/om_api`; enterprise modules → their existing `om/...` folder.
2. **PascalCase:**
   - Persona → Agent
   - UserFile → KnowledgeFile
   - Project → Workspace
   - UserGroup → Team
   - Never touch `personal_access_token`, `personalization`, `impersonat*` or `standardAnswer*`.
3. **snake_case and tables:**
   - `persona*` → `agent*`
   - `user_file` → `knowledge_file`
   - `user_project` → `workspace`
   - `user_group` → `team`
   - `external_user_group*` → `external_team*`
   - `assistant__user_specific_config` → `agent__user_specific_config`
   - bot flow table → `ombot_flow`
4. **Env vars:** upstream brand prefix → `OM_*`.
5. **Routes:**
   - `/chat` → `/converse`
   - `/manage` → `/nexus`
   - `/federated` → `/bridges`
   - `/notifications` → `/signals`
   - `/input_prompt` → `/prompts`
   - `/health` → `/heartbeat`
   - `/user/projects` → `/workspaces`
6. **OpenSearch fields and ACLs:** ours are `title_embedding`, `chunk_text`, `content_embedding`, `metadata_tags`, `updated_at`, `is_public`, `is_hidden`, `boost`, `display_name`, `image_id`, `user_workspaces`, `agents`, `snippet`, `document_summary`, `contextual_summary` and `metadata_text`. ACL prefixes are `team:` and `external_team:`. Ours doesn't yet have `created_at`, `cc_pair_ids` or `written_by_port`; adding them needs a re-index.
7. **Frontend:** upstream enterprise pages → `web/src/app/admin/<feature>/` or `web/src/app/<feature>/`. CSS variables are `--virtualai-*`. Follow the accent-theme rules in CLAUDE.md.
8. **Brand prose:** "VertualAI".
- **Frozen persisted or external strings** (cookies, PAT/SCIM prefixes, Redis/S3 keys, metrics, widget tags) stay exactly as listed in `DO_NOT_RENAME.md`.

### 1.3 Gates after every port
- `python -I rename-audit/build_inventory.py --check` must report 0 hits outside the allowlist. It has no `--help`; running it always regenerates the reports.
- `pytest backend/tests/unit/migration_safety` and `backend/tests/route_rename`
- `cd web && npx tsc --noEmit`
- Grep for frozen strings that were renamed by mistake.

### 1.4 Tooling TODO (do this first)
- [ ] Build `rename-audit/translate_upstream.py`. It should:
  - turn §1.2 into ordered regex rules (the upstream-side spellings come from `DECISIONS.md`), with hazard and frozen-string exclusions;
  - work on a patch file or a folder;
  - print anything it couldn't translate.
- [ ] `git fetch upstream` so the latest upstream commits are available locally for `format-patch`.

### 1.5 Per-feature port workflow (mandatory)
Before implementing **any** item in this doc or in `TODO_MD_RAG_UPGRADES_FROM_UPSTREAM.MD`:
1. Create `TODO_MD_PORT_<FEATURE>.MD` at the repo root with the sections below.
2. Get user approval.
3. Implement.

Template:

1. **Scope**
   - What the feature does for users.
   - Source `UP:om/...` → target paths in our tree.
   - What to drop: enterprise-only, Vespa, model-server, billing.
   - Dependencies on other backlog items.
2. **DB migration plan**
   - Diff upstream's schema change against `0001_om_baseline` + our current head.
   - Map every upstream table **and column** to ours: persona→agent, user_file→knowledge_file, user_project→workspace, user_group→team, external_user_group→external_team, plus renamed columns.
   - **New tables get our own names**, in our naming style, never the upstream brand.
   - Write one new Alembic migration chained off our head (revision id ≤32 chars), with upgrade and downgrade.
   - Plan any data backfill.
   - Never run alembic manually; the container applies it on restart.
3. **Model mapping**
   - SQLAlchemy models in `backend/om/db/models.py`: classes, fields, and relationships to our renamed tables.
   - Pydantic and API models; route names (`/converse`, `/nexus`, `/bridges`, `/signals`, …) and payload field names.
   - OpenSearch fields (our names), and whether a re-index is needed.
   - Env vars (`OM_*`), Celery task names, Redis keys (frozen keys stay per `DO_NOT_RENAME.md`).
4. **UI refactor (our design system)**
   - Rebuild the UI in our own components and layout. **Never paste upstream UI.**
   - Use the accent-theme CSS variables (`--theme-primary-*`, `--virtualai-accent*`, `.virtualai-gradient-text`) and support both light and dark modes. No hardcoded colours (CLAUDE.md design rules).
   - Add the admin nav entry in `web/src/components/admin/adminNavItems.ts` and the sidebar entry, if needed.
   - Workflow-related features must update **both** the Wizard editor and the Visual Builder.
5. **Enterprise parts**
   - Write a behaviour spec first, then reimplement clean-room inside our existing `om/` folder (`rewrite-plans/CONTRACTS.md`).
6. **Reuse first**
   - Before writing anything new, search for an existing helper (e.g. `om/utils/process_isolation.py` for crash-prone native parsers).
   - Put new generic logic in a shared module, not inside one feature. Note in the doc what is reusable.
7. **Existing features touched (regression scope)**
   - List every caller and feature that uses the changed code (grep the callers), with how each one is tested.
   - Add regression tests through the public entry points those features use.
   - List intended behaviour changes and the manual in-app checks the user should run.
8. **Tests**
   - Unit and integration tests under `backend/tests/...`, plus web type-checks.
   - Note pre-existing, unrelated failures separately.
9. **Gates**
   - `python -I rename-audit/build_inventory.py --check`
   - `pytest backend/tests/unit/migration_safety`
   - `backend/tests/route_rename`
   - `npx tsc --noEmit`
10. **Rollout**
    - The user reviews and rebuilds Docker. No commit unless asked.
11. **Progress tracker (mandatory, keep it current)**
    - A dated checklist of every step. **Tick each step the moment it's done**, so a new session can resume from the first unchecked item.
    - Put a "Status:" line at the top of the doc, and mirror the status in this backlog's table.

Reference example: `TODO_MD_PORT_PDFIUM.MD`.

---

## 2. Connectors

**Fork state:**
- 53 connectors are shared.
- Ours only: `om/connectors/folder/`, `om/connectors/requesttracker/` and the `EventConnector` interface.
- Federated search (Slack only) is identical in both.

### 2.1 Shared connector infrastructure (prerequisite)
| Pri | Feature | Source | Target |
|---|---|---|---|
| [ ] P1 | Section model upgrade (TabularSection, SectionType) + Resolver (re-fetch failed docs by id) | `UP:om/connectors/models.py`, `interfaces.py`, `exceptions.py`, `factory.py`, `registry.py` | same files in `backend/om/connectors/` |
| [ ] P1 | Cross-connector utilities | `UP:om/connectors/cross_connector_utils/` (`download.py`, `grouped_row_store.py`, `section_utils.py`, `server_wait.py`, `tabular_section_utils.py`) | `backend/om/connectors/cross_connector_utils/` |
| [ ] P1 | Shared Microsoft Graph / Entra / SharePoint REST layer (needed by onedrive, outlook, teams, sharepoint) | `UP:om/connectors/microsoft_utils/` | `backend/om/connectors/microsoft_utils/` (new) |
| [ ] P1 | Credential families (one Atlassian / Google / Microsoft credential shared across connectors) | `UP:om/connectors/credential_families.py`, `credential_family_base.py`, `atlassian_credential.py`, `google_credential.py`, `microsoft_credential.py` | `backend/om/connectors/` |
| [ ] P1 | Document `created_at` from connectors + UTC unification | connectors-wide | connectors-wide |
| [ ] P2 | Capability checks: named checks, draft-credential runs, run history, indexing hold until checks pass | `UP:om/connectors/capability_checks/`, `UP:om/background/celery/tasks/capability_checks/`, `UP:om/server/documents/capability_check_runs.py`, `credential_capabilities.py`, `draft_credentials.py`, `UP:web/src/lib/connectors/checks/` | same paths in our tree |
| [ ] P2 | Edit existing connectors (config diff, config hash, field policy, edit plans) | `UP:om/connectors/edit_plan/`, `config_diff.py`, `config_hash.py`, `connector_config.py`, `field_policy.py`, `UP:om/server/documents/connector_edit*.py`, `UP:web/src/lib/connectors/edit/` | same paths in our tree |
| [ ] P3 | Source-operations gateway | `UP:om/connectors/source_operations.py`, `capabilities.py`, `pairing_access.py`, `planning_rule*.py` | `backend/om/connectors/` |
| [ ] P3 | Admin ops: targeted re-index, index monitoring, throughput, runs feed, hierarchy breakdown, file staging | `UP:om/server/documents/` (`targeted_reindex.py`, `index_monitoring.py`, `cc_pair_throughput.py`, `cc_pair_runs_feed.py`, `hierarchy_breakdown.py`, `file_connector_staging.py`) | `backend/om/server/documents/` |
| [ ] P3 | OAuth with PKCE for connectors | `UP:om/oauth/` | `backend/om/server/oauth/` (our existing OAuth folder) |
| [ ] P3 | Celery tasks: `cc_pair_ids_backfill`, `index_reclaim`, `connector_edit` | `UP:om/background/celery/tasks/` | `backend/om/background/celery/tasks/` |

### 2.2 New connectors (upstream only)
Each new connector needs:
- `backend/om/connectors/<x>/`
- a `DocumentSource` entry in `backend/om/configs/constants.py`
- a `ValidSources` entry in `web/src/lib/types.ts`
- UI config in `web/src/lib/connectors/connectors.tsx`
- an icon
- **permission sync in `backend/om/external_permissions/<x>/`**, built clean-room from `UP-EE:external_permissions/<x>/`

| Pri | Connector | What it is | Source | Size | Depends on |
|---|---|---|---|---|---|
| [ ] P1 | onedrive | OneDrive via Graph delta + permission sync | `UP:om/connectors/onedrive/` | 8 files / 2.5k LOC | microsoft_utils |
| [ ] P1 | outlook | Mail, calendar, attachments; certificate credentials; Entra-group mailbox picking; permission sync | `UP:om/connectors/outlook/` | 9 / 5.3k | microsoft_utils |
| [ ] P2 | zoom | Cloud-recording transcripts for meetings and webinars; recording-share permissions | `UP:om/connectors/zoom/` | 13 / 4.4k | — |
| [ ] P2 | box | Box files + permission sync | `UP:om/connectors/box/` | 5 / 1.3k | — |
| [ ] P3 | canvas | Canvas LMS + permission sync | `UP:om/connectors/canvas/` | 5 / 1.5k | — |
| [ ] P3 | youtrack | YouTrack issues + permission sync | `UP:om/connectors/youtrack/` | 7 / 1.1k | — |
| [ ] P3 | lumapps | LumApps intranet | `UP:om/connectors/lumapps/` | 6 / 0.7k | — |
| [ ] P3 | braintrust | Braintrust eval platform | `UP:om/connectors/braintrust/` | 3 / 0.6k | — |

### 2.3 Upgrades to connectors we already have (largest drift first)
Targets are our existing `backend/om/connectors/<x>/`. "UP vs OURS" counts lines of `.py` code.

| Pri | Connector | UP vs OURS | Main upstream gains |
|---|---|---|---|
| [ ] P1 | google_drive | 8.5k vs 3.7k | Mid-crawl checkpointing, shortcut following, spreadsheet files, service-account organizer partitions, resumable permission sync, Resolver |
| [ ] P1 | sharepoint | 5.6k vs 2.2k | Delta sync, denylist filters, OneDrive-for-Business and personal sites, non-public share links, targeted re-index, full AD enumeration |
| [ ] P1 | confluence | 7.0k vs 2.8k | Attachments toggle, Resolver, scoped Atlassian token, gateway + checks |
| [ ] P2 | teams | 5.0k vs 1.1k | One module per content type, channel files, pasted images, meeting transcripts and chat, per-channel checkpoints |
| [ ] P2 | slack | 4.9k vs 2.0k | Enterprise Grid, channel exclude list with regex, match channels by id |
| [ ] P2 | github | 4.9k vs 1.1k | Repository files + specific branch, per-credential GitHub Enterprise Server URL |
| [ ] P2 | jira | 3.9k vs 1.3k | Bigger permission sync, Resolver |
| [ ] P3 | hubspot | 2.9k vs 1.1k | Permission sync from record viewers |
| [ ] P3 | linear | 1.8k vs 0.4k | Refresh tokens, team/project scoping, permission sync |
| [ ] P3 | notion, asana, gmail, gitbook | — | Checks, Resolver, page descriptions |
| [ ] P3 | salesforce | — | OAuth (PKCE) setup |
| [ ] P3 | gong | — | Converted to checkpointed |
| [ ] P3 | web | — | URL rewrite rules, Playwright retry |
| [ ] P3 | file / blob | — | Tabular section file id, staging |

**Permission-sync updates**
- Changed upstream, to redo clean-room in our existing `backend/om/external_permissions/<x>/`: confluence, google_drive, jira, slack, teams.
- New, as new folders under `backend/om/external_permissions/`: box, canvas, hubspot, linear, onedrive, outlook, youtrack, zoom, plus a shared `microsoft_utils`.
- Before touching github or sharepoint, check why **ours is larger** (824 vs 538 and 786 vs 544 LOC). It may be our own work.

### 2.4 Connector frontend
- [ ] Upstream moved source metadata into `UP:web/src/lib/connectors/` (`types/`, `components/`, `ccPair/`, `accessType.ts`, `credentialBoundFields.json`, `bindingGate.ts`, `svc.ts`). Target: `web/src/lib/connectors/`.
- [ ] New page `UP:web/src/app/admin/connectors/page.tsx`. Target: `web/src/app/admin/connectors/`.

---

## 3. Agent harness ("Craft") and agent runtime

**Yes, upstream has an agent harness.** Craft is a sandboxed coding and office agent (opencode in Kubernetes or Docker), with skills and external apps.

We already have an **older fork** of it:

| | Upstream | Ours |
|---|---|---|
| Backend | 77 files / 29.9k LOC | `backend/om/server/features/build/`: 65 files / 22.5k LOC |
| Commits since March 2026 | 436 | 11 |
| Frontend `web/src/app/craft/` | yes | yes |

| Pri | Feature | Source | Target |
|---|---|---|---|
| [ ] P2 | Sandbox core refresh: Kubernetes manager split (k8s client, sidecar client), Docker manager, opencode serve client + event bus, snapshot manager | `UP:om/server/features/build/sandbox/` (`kubernetes/`, `docker/`, `opencode/`, `snapshot_manager.py`) | `backend/om/server/features/build/sandbox/` (ours also has `local/`, `manager/`; keep them) |
| [ ] P2 | **Sandbox egress proxy** (security): mitmproxy egress, credential injection, destination policy, MCP JSON-RPC inspection | `UP:om/sandbox_proxy/` (21 files / 4.9k LOC) | `backend/om/sandbox_proxy/` (new) |
| [ ] P2 | Skills platform: registry, API, GitHub ingest, bundling. Built-ins: browser, company-search, github, gmail, google-calendar, google-drive, hubspot, linear, notion, pptx, slack, zendesk, image-generation | `UP:om/skills/`, `UP:om/server/features/skill/` | `backend/om/skills/`, `backend/om/server/features/skill/`. Merge with the skills baked into our sandbox image (`sandbox/kubernetes/docker/skills/`) |
| [ ] P2 | External apps: per-user OAuth into github, gmail, gcal, gdrive, hubspot, linear, notion, slack, zendesk, with token refresh and request matching | `UP:om/external_apps/` | `backend/om/external_apps/` (new); reuse `om/server/features/user_oauth_token/` where possible |
| [ ] P3 | Craft approvals, interactive turns, scheduled tasks, user library, webapp proxy, Craft gateway, static preview, action policies | `UP:om/server/features/build/*`, `UP:web/src/app/admin/craft/` | `backend/om/server/features/build/`, `web/src/app/admin/craft/`. Scheduled tasks: reuse our `om/pulse` |
| [ ] P3 | Shared agent runtime: runs, steps, child agents, compaction, suspension. Upstream chat doesn't use it yet | `UP:om/agents/` | **Compare with `backend/om/workflows/` first.** If adopted, extend `om/workflows/`; no parallel runtime |
| [ ] P3 | Coding-agent tool + bash tool | `UP:om/coding_agent/`, `UP:om/tools/tool_implementations/coding_agent/`, `.../bash/` | `backend/om/tools/tool_implementations/` |
| [ ] P3 | Dev-assistant tooling (repo-level skills, feature map, hooks). Developer-only | upstream `.agents/` | our `.claude/` |

---

## 4. Other features and external integrations

| Pri | Feature | Source | Target (our structure) |
|---|---|---|---|
| [ ] P1 | **LLM provider layer:** ollama, lm_studio, openai_compatible, bifrost, portkey, vercel_ai_gateway, nebius; model catalog and capabilities, price table and cost overrides, token budget, cancellation, decision models | `UP:om/llm/` (43 files / 11.5k LOC vs our 32 / 5.5k) | `backend/om/llm/` |
| [ ] P1 | **Durable / replayable chat responses** | `UP:om/db/chat_response.py`, `UP:om/chat/` (`response*.py`, `renderer.py`, `stream_buffer.py`) | `backend/om/db/`, `backend/om/chat/` |
| [ ] P2 | Hooks: document ingestion, document push, query processing | `UP:om/hooks/`, `UP:om/server/features/hooks/`, `UP-EE:hooks/` | `backend/om/hooks/` (new), `backend/om/server/features/hooks/` (new) |
| [ ] P2 | Multi-provider SSO, SSO discovery, SSO URL guard | `UP:om/server/saml_multi.py`, `oidc_multi.py`, `sso_discovery.py`, `UP:om/auth/sso_url_guard.py` | `backend/om/server/sso/`, `backend/om/auth/` |
| [ ] P2 | LLM gateway (OpenAI- and Anthropic-compatible passthrough) | `UP-EE:server/gateway/`, `UP:om/server/gateway/` | `backend/om/server/gateway/` (new) |
| [ ] P2 | Voice: speech-to-text and text-to-speech (Azure, ElevenLabs, OpenAI) | `UP:om/voice/` + admin voice page | `backend/om/voice/` (new), `web/src/app/admin/voice/` |
| [ ] P2 | MCP server expansion (agents and document-set resources) | `UP:om/mcp_server/` (1.1k vs 550 LOC) | `backend/om/mcp_server/` |
| [ ] P3 | Security settings | `UP:om/server/security/` | `backend/om/server/settings/` |
| [ ] P3 | Service accounts | upstream admin page | `backend/om/server/api_key/` |
| [ ] P3 | Admin banner | upstream admin page | `backend/om/server/enterprise_settings/` |
| [ ] P3 | Incognito chat | upstream chat | `backend/om/chat/` |
| [ ] P3 | Tracing admin page | upstream admin page | `backend/om/tracing/` |
| [ ] P3 | Error-handling and cache layers | `UP:om/error_handling/`, `UP:om/cache/` | `backend/om/utils/` or new `backend/om/cache/` |
| [ ] P3 | OAuth provider (our app acts as an authorization server) | `UP:om/oauth_provider/`, `UP:web/src/app/oauth-provider/` | `backend/om/server/oauth/provider/`, `web/src/app/oauth-provider/` |
| [ ] P3 | CLI (Go chat TUI + agent commands) | upstream `cli/` | `cli/`, binary named `om-cli` |
| [ ] P3 | Terraform provider | upstream `terraform-provider-*` folder | `terraform-provider-om/` |
| [ ] P3 | Salesforce ECA integration | upstream `integrations/salesforce/` | `integrations/salesforce/` |
| [ ] P3 (XL) | Mobile app (Expo / React Native) + mobile SSO | upstream `mobile/`, `UP:om/auth/mobile_sso/` | `mobile/`, `backend/om/auth/mobile_sso/` |
| [ ] P3 | Small refreshes: Slack/Discord bot, Chrome extension, desktop, widget, image generation, memory tool | `UP:om/ombot/`, upstream `extensions/`, `desktop/`, `widget/` | `backend/om/ombot/`, `extensions/`, `desktop/`, `widget/`, `backend/om/image_gen/` |
| Skip | Billing, license, tier gate | — | removed on purpose |

**Ours only (keep and protect when porting):**
- `om/workflows` (multi-agent workflows)
- `om/pulse` (scheduled workflows)
- `om/tenancy`
- `om/standard_answers`
- Phoenix tracing
- `http_request` and agent tools
- `office-mcp-server/`
- Cortex
- `code-interpreter/`
- Folder connector

---

## 5. Does upstream's "best RAG benchmark" claim apply to us?

Upstream publishes **no public benchmark numbers**; its README has none. The only mentions are internal, in its documentation changelog:
- v4.9.0 (October 2026): *"raised answer completeness on our enterprise RAG benchmark"*. This came from search-scope and prompt changes made **after our fork**.
- Tabular re-chunking: *"on our benchmark of 30 workbooks, 50,976 chunks became 105"*.
- Concurrent-chat first-token latency: about 354 ms down to about 54 ms.

**What that means for us:**
- Our retrieval core comes from the same codebase and is on par, plus we have a working reranker.
- Upstream's quality gains since the fork are **not** in ours: tabular chunker, search-scope prompt fix, pdfium, multilingual embedding.
- We can't inherit their claim. We need our own measurement.

- [ ] P1: Build our own RAG eval set (gov-department documents in Telugu, Hindi and English) with `backend/om/evals/` + Braintrust. Measure before and after each RAG port.
- [ ] P1: Port the v4.9.0 change: search no longer narrows to a source just because the question names it, and the "address every part, carry over exact figures" answer guidance. Source: `UP:om/tools/tool_implementations/search/` and the chat prompts. Target: `backend/om/tools/tool_implementations/search/`, `backend/om/prompts/`.

---

## 6. Suggested order
For **each** step: write that feature's `TODO_MD_PORT_<FEATURE>.MD` (§1.5), get user approval, then implement.

1. Translation script + `git fetch upstream` (§1.4).
2. RAG P1s from `TODO_MD_RAG_UPGRADES_FROM_UPSTREAM.MD` (pdfium, tabular chunker, Granite via Cortex) and our own eval set (§5).
3. Connector infrastructure + `microsoft_utils` (§2.1).
4. google_drive / sharepoint / confluence upgrades, plus the onedrive and outlook connectors.
5. LLM provider layer + durable chat responses (§4).
6. Craft security (egress proxy), then skills and external apps (§3).
7. Everything else, by priority.
