# `om.search` — Enterprise search + LLM query expansion (WS-E)

Clean-room reimplementation of the enterprise search API and its LLM
query-expansion superset. Replaces the Onyx-EE search branches that had been
merged into `secondary_llm_flows/query_expansion.py`,
`search/process_search_query.py`, and
`server/query_and_chat/{search_backend,query_backend}.py`.

> **Clean-room provenance.** Every module here was written from the behavior spec
> in `rewrite-plans/WS-E-search.md` + the frontend wire contract + the research
> cited below — **not** by reading the Onyx-EE expression. The retrieval
> primitives, access API, LLM interface, and tenant primitives are the repo's
> existing MIT/contract surfaces (see below), consumed, not reimplemented.

---

## Architecture

```
om/search/
  log_events.py          structured (OpenSearch) logging: emit_search_event + timed_search_event
  results.py             SearchDocWithContent (= MIT SearchDoc + content)
  filters.py             build_index_filters — ACL (Contract 2) + user filters, fail-closed
  classification.py      classify_search_flow — LLM search-vs-chat, fail-open to search
  expansion/             ── Phase 1: query expansion
    models.py            ExpansionStrategy, ExpandedQuery, StrategyTrace, ExpansionTrace, QueryExpansionResult
    prompts.py           clean-room prompt templates
    config.py            QueryExpansionConfig / FusionConfig / SearchFlowConfig (ORM-decoupled views)
    expander.py          QueryExpander.expand(query, history) -> QueryExpansionResult
  orchestration/         ── Phase 2: orchestration + fusion + streaming
    fusion.py            weighted_reciprocal_rank_fusion + merge_chunks_into_sections
    packets.py           SSE typed packets (wire contract)
    section_selection.py optional LLM relevance selection
    orchestrator.py      SearchOrchestrator.stream_packets(...) — the search flow
  history/               ── Phase 3: per-user history
    repository.py        SearchQueryRepository (tenant-scoped CRUD over existing `search_query`)
    service.py           SearchHistoryService (HistoryRecorder) + list_search_history
  admin/
    service.py           admin_search (hidden docs) + get_valid_tags
  api/
    schemas.py           request/response models (match frontend interfaces.ts)
    router.py            APIRouter(prefix="/search") + expansion-settings config endpoints
```

Layering is **models → services → api** with strict typing. The orchestrator
composes the expander, retrieval, fusion, and selection; the API layer adapts it
to SSE or a full response.

### Consumed contracts / MIT surfaces (not reimplemented)

| Concern | Import |
|---|---|
| Access filters (Contract 2) | `om.context.search.preprocessing.access_filters.build_user_only_filters` |
| Tenant context (Contract 3) | `om.tenancy.context` facade (see shim note below) |
| Retrieval primitive | `om.context.search.retrieval.search_runner.search_chunks` |
| Document index | `om.document_index.factory.get_default_document_index` (+ `keyword_retrieval`, `random_retrieval`) |
| Section merge | `om.context.search.utils.inference_section_from_chunks` |
| LLM | `om.llm.factory.get_default_llm` / `LLM.invoke` |
| SSE serialization | `om.server.utils.get_json_line` |
| Tag lookup | `om.db.tag.find_tags` |

---

## Design (with research basis)

### Query expansion

Three complementary transforms run per query (all LLM-backed, all individually
traced, each isolated in try/except so a failure degrades to the original query):

1. **Keyword expansion** — history-independent keyword-only (BM25) reformulations
   (synonyms, related terms) to widen vocabulary coverage.
2. **History-aware semantic rephrase** — rewrites the latest turn into one
   standalone, context-resolved question (resolves pronouns / omitted context).
3. **History-aware keyword expansion** — keyword variants that fold in
   conversation context.

Guardrails: variants are bounded (`max_variants`), history is truncated to a
token budget before prompting, output is capped via `max_tokens`, and the JSON
parser tolerates code fences / prose / line lists. Increasing LLM samples helps
recall but expansion noise pollutes RAG evidence, so variants stay bounded and
the original query is fusion-weighted above them.

- Best Practices of Query Expansion with LLMs — https://arxiv.org/pdf/2401.06311
- Query Expansion in the Age of LLMs (survey) — https://arxiv.org/pdf/2509.07794
- LLM-Assisted Query Understanding for Live RAG — https://arxiv.org/pdf/2506.21384
- Searching for Best Practices in RAG — https://arxiv.org/pdf/2407.01219

### Retrieval + weighted reciprocal-rank fusion

The original query and each expansion variant are retrieved **in parallel**
(`ThreadPoolExecutor`, one tenant session per worker), then fused with weighted
RRF:

```
score(d) = Σ_m  weight_m / (k + rank_m(d))          (rank 1-indexed)
```

RRF fuses lists with incomparable score scales (keyword vs semantic) using rank
alone — no score normalization. `k` (default **60**, robust across k∈[40,80])
dampens top-rank dominance; per-list `weight` values the original query
(`original_query_weight`) above semantic (`semantic_variant_weight`) and keyword
(`keyword_variant_weight`) variants. Fused chunks are grouped into per-document
sections; the best-fused chunk is the section center.

- OpenSearch — Introducing RRF for hybrid search — https://opensearch.org/blog/introducing-reciprocal-rank-fusion-hybrid-search/
- Azure AI Search — hybrid ranking (RRF) — https://learn.microsoft.com/en-us/azure/search/hybrid-search-ranking
- AI21 — What is RRF — https://www.ai21.com/glossary/tech/what-is-reciprocal-rank-fusion-rrf/

### Streaming packet schema (SSE)

`POST /search/send-search-message` streams **newline-delimited JSON** over
`text/event-stream` (each line = one `packet.model_dump()` via `get_json_line`,
data-as-JSON-string per the SSE contract). Packets are a discriminated union on
`type`, matching `web/src/lib/search/interfaces.ts`:

```
query_expansions -> search_docs -> [doc_selection_reasoning, llm_selected_docs]
                                 \-> search_error   (terminal, on failure)
```

Typed events (Anthropic-style) let the UI switch on one field and render
progressively; `search_docs` is emitted before the optional relevance pass so
results appear first. The non-streaming mode consumes the *same* generator and
assembles `SearchFullResponse` — one flow, two adapters.

- MDN — Using server-sent events — https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events
- Streaming AI responses (SSE vs WebSockets) — https://www.channel.tel/blog/streaming-ai-responses-sse-websockets-real-time

---

## API

All endpoints require auth. Router prefix `/search` (registered once in `main.py`).

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/search/search-flow-classification` | user | classify search vs chat |
| POST | `/search/send-search-message` | user + vector-db | run search (SSE or full) |
| GET | `/search/search-history` | user | caller's history (`limit`, `filter_days`) |
| GET | `/search/expansion-settings` | admin | read expansion config |
| PUT | `/search/expansion-settings` | admin | update expansion config |

Admin document search (`POST /admin/search`) and tag lookup
(`GET /query/valid-tags`) keep their existing paths on the shared `/admin` and
`/query` routers — their handlers in `server/query_and_chat/query_backend.py`
now delegate to `om.search.admin.service` (clean-room). `GET /query/standard-answer`
(WS-D) is untouched.

`num_hits` (capped 100) → results; `run_query_expansion=false` disables expansion;
`num_docs_fed_to_llm_selection` enables + sizes the LLM relevance pass;
`include_content` populates `SearchDocWithContent.content`.

---

## Configuration + UI

Per-tenant typed config table **`search_expansion_settings`** (singleton; model
in `db/models.py`, accessor `db/search_expansion_settings.py`). Toggles for each
expansion strategy + LLM selection, bounds (`max_variants`, `num_results`,
`num_retrieved_per_query`), and fusion knobs (`rrf_k`, three weights).

UI: `web/src/app/admin/configuration/search/QueryExpansionSettings.tsx`, mounted
into the existing **Search Settings** admin page (`configuration/search`). Uses
the VertualAI design system (`CardSection`, `Switch`, `Button`), accent via
`--virtualai-accent`, theme-aware. **No new menu entry** — it lives under the
existing Search Settings screen (per the plan's lighter-touch option).

`SearchSettings` (embedding lifecycle) was intentionally NOT extended — it is
guarded by unique indexes on `status` and is the wrong home for tuning config.

---

## Multi-tenant readiness (Contract 3)

- Every new table lives in the per-tenant schema (no `{"schema": "public"}`).
- Sessions come from the tenant-bound helpers via the `om.tenancy.context` facade;
  the streaming generator opens **fresh** tenant sessions (the request session is
  closed before a `StreamingResponse` body runs).
- Parallel retrieval threads receive `contextvars.copy_context()` so the tenant
  contextvar propagates; each worker opens its own session.
- History + config queries are tenant-scoped by the bound session; history is
  additionally `user_id`-scoped. Every log line carries `tenant_id`.

> **Shim note:** `om/tenancy/context.py` here is a thin, integrator-removable
> facade re-exporting the real primitives (`shared_configs.contextvars` +
> `om.db.engine.sql_engine`) under the Contract-3 names, because WS-M's canonical
> module has not landed on this branch. The integrator deletes it when WS-M's
> canonical `om.tenancy.context` is merged.

---

## Structured log events (Standard 9)

Emitted via `emit_search_event` / `timed_search_event`, every call wrapped in
try/except (logging never breaks a request). Fields: `event`, `entity`,
`entity_id`, `tenant_id`, `actor_user_id`, `action`, `status`, `duration_ms`,
`error` (+ feature fields).

| event | when |
|---|---|
| `search.executed` | a full search flow ran (timed) |
| `search.expanded` | query expansion produced variants |
| `search.flow_classified` | search-vs-chat classification |
| `search.history_saved` / `search.history_read` | history persisted / listed |
| `search.admin` | admin/curator search ran (timed) |
| `search.tags_read` | valid-tags lookup |

---

## How to extend

- **New expansion strategy:** add to `ExpansionStrategy`, a prompt in
  `prompts.py`, a `_..._expand` method in `expander.py` recording a `StrategyTrace`.
- **New fusion policy:** `fusion.py` is pure and unit-testable; swap the scorer
  or add per-source weights.
- **New packet:** add a Pydantic model in `packets.py` (with a `type` literal),
  extend `SearchStreamPacket`, yield it from `orchestrator.stream_packets`, and
  mirror the type in `web/src/lib/search/interfaces.ts`.
- **New config knob:** add a column to `SearchExpansionSettings` (+ migration),
  surface it in `config.py`, the API schemas, and `QueryExpansionSettings.tsx`.

---

## Integrator notes (shared files)

1. **`main.py`** — the search-router import was repointed:
   `from om.search.api.router import router as search_router`
   (the `include_router_with_global_prefix_prepended(application, search_router)`
   line is unchanged — **no double-registration**). If integrating as a snippet
   instead, apply only that import swap.
2. **`server/query_and_chat/query_backend.py`** — `admin_search` and `get_tags`
   handler bodies now delegate to `om.search.admin.service`; unused EE imports
   dropped; `get_standard_answer` (WS-D) untouched.
3. **`db/models.py`** — new `SearchExpansionSettings` under
   `# === WS-E: Search / query-expansion models ===`. The `search_query` history
   table (`SearchQuery`) **already existed** with WS-E's exact schema and is
   reused — no model/migration change for it.
4. **Alembic** — `alembic/versions/ws_e_search_expansion_settings.py` has
   `down_revision = None` as a placeholder; linearize it onto the current head
   (`0003_agent_rename`). Only `search_expansion_settings` is created.
5. **Deletions** — `server/query_and_chat/search_backend.py`,
   `search/process_search_query.py`, `db/search.py` (all orphaned after the swap).
6. **Kept deliberately** (co-used by out-of-scope MIT code; flagged for IP review):
   `secondary_llm_flows/query_expansion.py` + `prompts/query_expansion.py` (chat
   `search_tool`), and `server/query_and_chat/streaming_models.py` (30+ chat/tool
   importers) — only its now-dead EE search packet classes are unused here.
