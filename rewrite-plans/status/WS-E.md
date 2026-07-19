# WS-E — Search / query-expansion — status log

Worktree: `.claude/worktrees/ws-e` (branch `rewrite/ws-e` off `rename_onyx_to_om`).
Depends on **Contract 2 (Access API)** (`build_access_filters_for_user`) + **Contract 3 (Tenant)**.
Clean-room replacement of the Onyx-EE search superset (query expansion + orchestration + search API).

Phase plan:
- P0 Orient: read CONTRACTS.md + WS-E; graphify-orient on access filters, tenant context, retrieval
  primitive, LLM interface, search-settings config, router wiring, SSE transport. Research query-expansion,
  RRF, SSE packet design.
- P1 Query-expansion module: keyword expansion, history-aware semantic rephrase, history-aware keyword
  expansion. LLM-backed + tracing + token budget. Review: rephrase/expansion correctness; tracing; budget.
- P2 Orchestration + fusion + streaming: parallel original+expanded queries, weighted RRF fusion,
  chunks→sections merge, optional LLM section selection, SSE packets. Review: fusion weights; packet schema;
  SSE correctness; access filters applied.
- P3 Search API + history + admin: `POST /search/search-flow-classification`,
  `POST /search/send-search-message` (SSE or full), `GET /search/search-history`; `search_query` history
  table; admin search + tag lookup on admin router. Review: endpoints; history tenant-scoped.
- P4 Delete old EE search branches + verify parity. Review: permitted, ranked results; structured logs.

---

- [P0] Started: created worktree `.claude/worktrees/ws-e`. Read CONTRACTS.md + WS-E.md in full. Confirmed
  Contract 2 (`build_access_filters_for_user` in `om.context.search.preprocessing.access_filters`, returns
  `list[str]`) and Contract 3 (import tenant primitives from `om.tenancy.context`). Clean-room: EE-origin
  expression files (`secondary_llm_flows/query_expansion.py`, `search/process_search_query.py`,
  `server/query_and_chat/{search_backend,query_backend,streaming_models}.py`, `prompts/query_expansion.py`)
  treated as black boxes — bodies not read; identified by signature/route for Phase-4 deletion.
- [P0] Research done (cited in README): weighted **RRF** `Σ α_m/(k+rank_m(d))`, k=60 default; LLM query
  expansion (keyword / history-aware semantic rephrase / history-aware keyword); SSE typed-packet transport
  (newline-delimited JSON, `type`-discriminated, data-as-JSON-string). Notes in scratchpad → folded to README.
- [P0] Integration map (via Explore subagent, structure-only): corrected assumptions — Contract-3 facade
  `om.tenancy.context` NOT yet on branch (WS-M unlanded) → added thin integrator-removable shim re-exporting
  `shared_configs.contextvars` (tenant id/contextvar) + `om.db.engine.sql_engine` (sessions). LLM factory is
  singular `get_default_llm()`/`get_llm()` (`om.llm.factory`); `LLM.invoke(msgs, max_tokens, reasoning_effort)
  -> ModelResponse`, text at `.choice.message.content`, usage at `.usage.{prompt,completion}_tokens`. Retrieval:
  build `IndexFilters` once via Contract-2 `build_access_filters_for_user` then fan out `search_chunks`
  (`context/search/retrieval/search_runner.py`) per variant → RRF-fuse `list[InferenceChunk]`. SSE via
  `get_json_line` (`om.server.utils`) + `StreamingResponse(..., media_type="text/event-stream")`. **`search_query`
  table already exists** (`models.py:2642`) with the exact target schema → REUSED, no new migration for it.
  `SearchSettings` unsuitable for expansion config → new typed table.

- [P1] DONE — Query-expansion module (`backend/om/search/`):
  - `tenancy/context.py` — Contract-3 facade shim (integrator drops for WS-M canonical).
  - `search/log_events.py` — structured OpenSearch logging (`emit_search_event` + `timed_search_event`
    ctx-mgr; fields per Standard 9; every emit try/except-wrapped; events `search.executed|expanded|
    history_saved|admin`).
  - `search/expansion/{models,prompts,config,expander}.py` — `QueryExpander.expand(query, history)` runs 3
    strategies (KEYWORD, history-aware SEMANTIC_REPHRASE, KEYWORD_HISTORY), each isolated in try/except with a
    `StrategyTrace` (tokens/latency/raw/variants/error); token-budget history truncation + `max_tokens` output
    cap; robust JSON-array-or-line parser (dedup, cap); returns `QueryExpansionResult` (rephrase + keyword
    variants + `retrieval_variants()`).
  - New typed config table `SearchExpansionSettings` (per-tenant singleton) in `models.py` under `# === WS-E`
    banner + accessor `db/search_expansion_settings.py` + Pydantic views `SearchFlowConfig`.
  - Self-review: all files `py_compile` clean; parser/dedup/history-budget logic unit-validated. Corrected LLM
    type field names against actual defs (`Usage`, `Choice.message`, `LLMConfig`). (Backend deps not installed
    in this shell → Docker build is the real import gate.)

- [P2] DONE — Orchestration + fusion + streaming (`backend/om/search/orchestration/`):
  - `fusion.py` — weighted RRF `Σ weight_m/(k+rank_m)` over `list[InferenceChunk]` (identity = `unique_id`,
    keeps best-scored instance) + `merge_chunks_into_sections` (per-doc grouping via MIT
    `inference_section_from_chunks`). Numeric unit-check passed.
  - `packets.py` — typed SSE discriminated union: start → expansion → results → [llm_selection] → done / error.
  - `section_selection.py` — optional LLM relevance pass (best-effort, never fails the flow).
  - `orchestrator.py` — `SearchOrchestrator.stream_packets()`: expand → **parallel** `search_chunks` per
    variant (`ThreadPoolExecutor` + `contextvars.copy_context()` for tenant propagation, per-worker fresh
    `get_current_tenant_session()`) → RRF-fuse → merge → optional select → history recorder (Protocol) → done.
    ACL always via Contract-2 `build_user_only_filters` (fail-closed). Fresh sessions inside the generator
    (request session is closed during streaming); per-variant failures degrade to empty list, not a hard fail.
  - Self-review vs gate (fusion weights / packet schema / SSE / access filters): all import symbols verified to
    exist; RRF+merge numerically validated; `py_compile` clean.

- [P3] DONE — Search API + history + admin + config UI:
  - Wire contract derived from the FRONTEND (`web/src/lib/search/{interfaces,svc}.ts`) — clean-room schemas
    match field-for-field. Packets rewritten to wire types: `query_expansions` / `search_docs` /
    `llm_selected_docs` / `doc_selection_reasoning` / `search_error`. `SearchDocWithContent = MIT SearchDoc +
    content` (authored from the frontend fields; EE `streaming_models.py` NOT read).
  - `api/router.py` (`APIRouter(prefix="/search")`): `POST /search-flow-classification`,
    `POST /send-search-message` (SSE via `StreamingResponse`+`get_json_line`, OR full `SearchFullResponse`
    assembled by consuming the same packet generator), `GET /search-history`, `GET|PUT /expansion-settings`
    (admin). Per-request overrides (num_hits→num_results capped 100, run_query_expansion, num_docs_fed→selection).
  - `history/{repository,service}.py` — clean-room `SearchQuery` CRUD (reuses existing table), tenant-scoped,
    `SearchHistoryService` doubles as the orchestrator `HistoryRecorder` (opens own session inside the stream).
  - `admin/service.py` — clean-room `admin_search` (keyword_retrieval + include_hidden, ACL via Contract 2) +
    `get_valid_tags` (via MIT `find_tags`).
  - `classification.py` — LLM search-vs-chat classifier, fail-open to search.
  - Config UI: self-contained `web/.../configuration/search/QueryExpansionSettings.tsx` (design-system
    `CardSection`/`Switch`/`Button`, accent via `--virtualai-accent`, theme-aware), mounted 1-line into the
    existing Search Settings page → NO new menu entry (plan's lighter-touch option).
  - Alembic `ws_e_search_expansion_settings.py` (standalone, `down_revision=None` placeholder). `search_query`
    NOT migrated (pre-existing).
  - Self-review: all backend `py_compile` clean; every backend import symbol verified present; Button/Switch
    props verified for the TSX.

- [P4] DONE — Wire + delete-old + verify:
  - `main.py`: search-router import repointed `search_backend.router` → `om.search.api.router.router` (include
    line unchanged; no double-register).
  - `query_backend.py`: `admin_search` + `get_tags` handler bodies replaced with thin delegations to
    `om.search.admin.service` (empty-query→random, dedup, include_hidden, `=`-split tags folded into the
    clean-room service); unused EE imports dropped; `get_standard_answer` (WS-D) untouched.
  - Deleted (orphaned after swap, blast-radius verified): `server/query_and_chat/search_backend.py`,
    `search/process_search_query.py`, `db/search.py`.
  - **Kept deliberately** (co-used by out-of-scope MIT code — flagged for IP review/integrator):
    `secondary_llm_flows/query_expansion.py` + `prompts/query_expansion.py` (used by chat `search_tool`),
    `server/query_and_chat/streaming_models.py` (30+ chat/tool importers; only its dead EE-search packets unused).
  - Verify: full `compileall` clean; AST unused-import check clean on all edited files; tree-wide grep → zero
    dangling refs to deleted modules/symbols; `AdminSearchRequest.filters` confirmed `BaseFilters` (compatible).
    Review gate (permitted+ranked results / structured logs): ACL always via Contract 2 (fail-closed), RRF
    ranking numerically validated, structured logs on every event (try/except-wrapped). **Runtime/parity vs a
    fixed query set needs the live Docker stack (index+LLM+DB) — the user runs that; not reproducible in this
    static shell (backend deps e.g. `braintrust` not installed here).**

- [README] DONE — `backend/om/search/README.md`: architecture, consumed contracts, expansion+RRF+SSE design
  (research cited), API table, config/UI, multi-tenant readiness, log events, how-to-extend, integrator notes.

## Summary

Clean-room WS-E complete on worktree `.claude/worktrees/ws-e` (branch `rewrite/ws-e`). 25 new backend files
under `om/search/**` + `om/tenancy/context.py` shim + 1 config table + 1 Alembic revision; 1 new web component
mounted into the existing Search Settings page; `main.py` + `query_backend.py` minimally rewired; 3 orphaned EE
files deleted. Nothing committed. Docker rebuild by the user is the real import/runtime gate; `alembic upgrade`
NOT run by hand (backend auto-applies on boot). Integrator: linearize the Alembic revision onto `0003`, drop the
tenancy shim for WS-M's canonical module, and apply the `main.py`/`query_backend.py` changes.

## [REVIEW] Rigorous self-review — gaps found + fixed

All 4 phases + P0 re-confirmed done against WS-E-search.md; every plan item present. 6 gaps fixed:

1. **Multi-tenant safety (fail-open → fail-closed)** — `search/filters.py::build_index_filters` was swallowing
   `get_current_tenant_id()` in try/except → a silent `tenant_id=None` would drop the tenant filter from the
   index query (cross-tenant risk). Now calls it directly (returns default schema single-tenant; raises/401
   fail-closed in MT), matching the codebase convention. Confirmed `get_session` FastAPI dep + the MIT chat
   streaming path (`chat_backend.py:603`) use the same tenant-bound pattern → the tenant contextvar provably
   survives into the SSE generator (my orchestrator matches it).
2. **Standard 9 gap** — the expansion-settings PUT emitted no structured log. Added
   `event=search.config_updated` (action=update, entity=search_expansion_settings, entity_id, actor_user_id,
   updated_fields) + captured the admin user for `actor_user_id`.
3. **Input validation** — `GET /search/search-history` `limit` was uncapped; now clamped to `[1, 1000]`.
4. **3 mypy type errors** (mypy 1.11.2, now CLEAN on `om/search` + `om/tenancy`): (a) expander message list
   inferred as `list[CacheableMessage]` → annotated `list[ChatCompletionMessage]`; (b) `select_relevant_documents`
   param `list[SearchDoc]` rejected `list[SearchDocWithContent]` (list invariance) → `Sequence[SearchDoc]`;
   (c) `emit_search_event.entity_id` widened `str|UUID|None` → `str|UUID|int|None` (config id is int).
5. **UI robustness** — clearing a number input in `QueryExpansionSettings.tsx` produced `NaN` (React warning +
   `null` sent); now guarded with `Number.isNaN`.
6. **Completeness** — history-aware expansion (semantic rephrase + keyword-history) was built but **unreachable**:
   `SendSearchQueryRequest` had no history field, so 2 of 3 strategies never ran via HTTP. Added optional
   `history: list[HistoryTurn] | None` to the request and wired it through both `send-search-message` paths
   (frontend omitting it still works — defaults to none).

Confirmed OK (no change needed): search_query already has `user_id` + `created_at` indexes (no N+1/index gap);
all 6 new endpoints auth-gated (user/admin/curator); all logs try/except-wrapped; ACL always via Contract 2;
`AdminSearchRequest.filters` is the same `om.context.search.models.BaseFilters` (delegation type-safe); no dead
code (DocSelectionReasoningPacket + HistoryTurn are intentional contract/public surface, now exercised);
clean-room preserved (admin parity behaviors are functional, not copied expression).

**Verification:** mypy CLEAN (0 errors, `om/search`+`om/tenancy`); `compileall` clean; `tsc --noEmit` on changed
web files clean (only pre-existing `playwright.config.ts` dotenv error remains); AST unused-import check clean;
tree-wide grep → 0 dangling refs. Nothing committed; `alembic upgrade` not run by hand.
