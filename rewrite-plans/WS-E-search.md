# WS-E — Search / query-expansion (clean-room)

## ▶ AGENT INSTRUCTIONS — START HERE (read this whole block first)

**You were pointed at this file to IMPLEMENT workstream WS-E. Do exactly this:**

0. **DUPLICATE CHECK — before anything.** If `.claude/worktrees/ws-e` already exists OR
   `rewrite-plans/status/WS-E.md` already has status lines from another agent, another agent owns WS-E:
   **STOP, report "WS-E already in progress — standing down", make NO changes.** Otherwise self-isolate:
   `git worktree add .claude/worktrees/ws-e -b rewrite/ws-e rename_onyx_to_om`
   Working root = `d:\llm\danswer20022026\.claude\worktrees\ws-e`; do ALL edits there, never the main tree.
1. **Read** `rewrite-plans/CONTRACTS.md` + the rest of THIS file. Use `build_access_filters_for_user`
   (Contract 2) — do NOT reimplement ACL. Tenant-safe (Contract 3).
2. **Legal — clean-room.** Behavior spec only. NEVER open/copy/paraphrase Onyx EE source at
   `D:\llm\danswer07022026_original\onyx\backend\ee\...`.
3. **Orient with graphify** before reading source.
4. **Phases + review gates.** TodoWrite; self-review after each phase; parity check before deleting old.
5. **Research first** (query-expansion, reciprocal-rank fusion, SSE packets); cite in README.
6. **Standards:** multi-tenant-safe; dedicated/extended search-settings config + UI; VertualAI design
   system; structured OpenSearch logs in try/except; OOP + strict typing. Do NOT double-register the
   query/admin routers — add to existing router objects.
7. **Delete old EE search branches only in the FINAL phase**, after verify.
8. **Write** `backend/om/search/README.md`.
9. **Progress:** append to `d:\llm\danswer20022026\rewrite-plans\status\WS-E.md` at each phase.
10. **Do NOT commit/push. Do NOT run `alembic upgrade` by hand.** Summarize at the end.

**Wave:** 1. **Emphasis:** search + query-expansion clean-room; new `search_query` history table.

---

> Read `CONTRACTS.md` first. Depends on **Contract 2 (Access API)** (access filters) + Contract 3
> (tenant). Follow all Engineering standards. Work in your own worktree.

## Goal
Clean-room reimplementation of the enterprise search API + LLM query-expansion, replacing the Onyx-EE
search superset.

## Research first (Standard 2)
Web-research query-expansion / rephrase patterns (history-aware rephrase, keyword vs semantic
expansion), reciprocal-rank fusion, streaming SSE packet design.

## Behavior spec (WHAT — own HOW; do not open Onyx files)
Replaces EE branches merged into: `secondary_llm_flows/query_expansion.py`,
`search/process_search_query.py`, `server/query_and_chat/{search_backend,query_backend,models,streaming_models}.py`.

- **Query expansion:** keyword expansion (BM25 keyword-only variants), history-aware semantic rephrase,
  history-aware keyword expansion. LLM-backed with tracing.
- **Search orchestration:** run original + expanded queries in parallel, fuse via weighted reciprocal-
  rank fusion, merge chunks→sections, optional LLM section selection, stream packets.
- **Search API:** `POST /search/search-flow-classification`, `POST /search/send-search-message`
  (SSE or full response), `GET /search/search-history`. Admin search + tag lookup on the admin router.
- Access filters via **Contract 2** (`build_access_filters_for_user`) — do not reimplement ACL.

## New tables (own names)
- `search_query` (id UUID, user_id FK cascade, query, query_expansions TEXT[], created_at) for history.

## Config + UI
- **Search settings** likely already has its own table — extend it or add a dedicated expansion-config
  table (toggles: enable expansion, max variants, semantic weight). UI-configurable.
- Update MENU only if a new admin screen is added (else surface under existing search settings).

## Shared-file snippets (integrator)
- `models.py`: search_query block. `main.py`: search router + admin-search additions (note: query/
  admin routers are already included once — add routes to existing objects, do NOT double-register).
- Alembic: search_query revision.

## Phases (with review gates)
- **Phase 1 — Query expansion module.** **Review:** rephrase/expansion correctness; tracing; token budget.
- **Phase 2 — Search orchestration + fusion + streaming packets.** **Review:** fusion weights; packet
  schema; SSE correctness; access filters applied.
- **Phase 3 — Search API + history + admin search.** **Review:** endpoints; history tenant-scoped.
- **Phase 4 — Delete old + verify.** Remove old EE search branches. **Review:** search returns permitted,
  ranked results; structured logs present.

## Structured logs (Standard 9)
`event=search.executed|expanded|history_saved`, `entity=search_query`, `entity_id`, `tenant_id`,
`actor_user_id`, `action`, `status`, `duration_ms`, `error`.

## Verification
- Search returns fused, permission-filtered results; expansion improves recall; history persists per user.
- Tenant-scoped; parity vs current behavior on a fixed query set before deleting old.

## README
`backend/om/search/README.md` (+ search API): expansion + fusion design (cite research), packet schema,
config/UI, log events, extension.
