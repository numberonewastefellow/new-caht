# Implementation Plan — Indexing / Reindex / Time-Range (OUR fields, upstream as knowledge only)

> **Companion to** `TODO_MD_VESPA_VS_OPENSEARCH_MIGRATION_COMPARISON.MD` (PART 7). This plan is
> **Deliverable 2**: bring the upstream Onyx indexing/reindex/time-range capabilities into our repo
> **reimplemented against our schema**. Decide the scope slice after reading — see §7.

## Ground rules (non-negotiable)

- **Keep OUR field names exclusively**: `title_embedding`, `content_embedding`, `chunk_text`, `boost`.
  New additive fields use our conventions: `created_at`, `written_by_port`.
- **Upstream = knowledge reference only** (`D:\llm\danswer07022026_original\onyx`). No verbatim code
  copy, no upstream field names (`title_vector`/`content_vector`/`content`/`global_boost`).
- **No commits** until asked; **no direct `alembic upgrade`** — migrations apply via Docker rebuild.
- Additive mapping fields require **no reindex** (`schema.py:73/615`).

## Field-name translation (upstream concept → what we build)

| Upstream (reference) | OURS |
| --- | --- |
| `content` | `chunk_text` |
| `title_vector` | `title_embedding` |
| `content_vector` | `content_embedding` |
| `global_boost` | `boost` |
| `created_at` (doc) | `created_at` (new, our naming) |
| `written_by_port` | `written_by_port` (new) |
| `last_updated` | `updated_at` (our existing name) |

---

## §1 Prerequisites status (verified in our tree)

**Already present (reuse):**

- Embedder: `backend/om/indexing/embedder.py` exists (the FUTURE-model embedder a port needs).
- Source time fields: `doc_created_at` / `doc_updated_at` already on our document models
  (`om/connectors/models.py`, `om/db/models.py`); index populate already reads
  `source_document.doc_updated_at` (`opensearch_document_index.py:275`).
- Chunk model + UTC helper: `DocumentChunk` model with `updated_at` + `@field_serializer`/
  `@field_validator` using `set_or_convert_timezone_to_utc` (`schema.py:208, 284-318`) — our
  equivalent of upstream's `datetime_to_utc`.
- IndexPair scaffold: `OpenSearchIndexPair` primary/secondary (`opensearch_document_index.py:1073`).
- Batch flush: `index()` + `_flush_chunks` at `MAX_CHUNKS_PER_DOC_BATCH`
  (`opensearch_document_index.py:429/475/545`).
- A `backend/om/document_index/FILTER_SEMANTICS.md` already exists — **verify** whether it is
  aspirational or partially implemented (our `search.py` currently ranges on `updated_at` only).

**Absent (must build):**

- `created_at` document field + dual created/updated time-range search.
- `use_create_only` bulk writes + benign-409 handling; `ignore_missing`/`surface_document_missing`
  + `OpenSearchDocumentMissingError`; PIT scan (`open_pit`/`close_pit`/`iter_chunks_for_doc_ids`).
- `written_by_port` marker + resurrection sweep (`delete_port_written_chunks` + delete-by-query).
- `primary_backfill_in_progress` + `SecondaryIndexDocumentMissingError` on IndexPair.
- **Re-embed engine** (`port_reembed`: MODEL_ONLY + AUGMENTATION) — NOT present in `om/indexing/`.
- **DB**: `PortAttempt` + `PortOrphanCandidate` tables; search-settings columns `use_port_flow`,
  `port_backfill_source_id`, `switchover_type`.
- Celery driver task + beat scheduler; admin endpoint + swap-index integration.

---

## §2 Phase 0 — datetime UTC convention (XS, low risk)

Confirm every datetime crossing the index boundary goes through `set_or_convert_timezone_to_utc`
before `int(.timestamp())`, and reads reconstruct aware-UTC via
`datetime.fromtimestamp(v, tz=timezone.utc)`. We already do this for `updated_at`; Phase 1 just
extends the same helper to `created_at`. **Mostly a verification step.**

## §3 Phase 1 — `created_at` field + dual created/updated time-range (S–M, LOW risk) ⭐ recommended first

Self-contained, additive (no reindex), and it is also a prerequisite the reindex-port needs.

**Landing sites & work:**

1. `schema.py:36-46` — add `CREATED_AT_FIELD_NAME = "created_at"` (and, if doing Phase 3 later,
   `WRITTEN_BY_PORT_FIELD_NAME`). Add the mapping block (`date` / `epoch_second` / `doc_values:true`),
   mirroring `updated_at`.
2. `schema.py:208` — add `created_at: datetime | None = None` to the `DocumentChunk` model; extend
   the `@field_serializer(...)`/`@field_validator(...)` to cover both `updated_at` **and**
   `created_at` (they share identical epoch-seconds logic).
3. `opensearch_document_index.py:275` — populate `created_at=index_chunk.source_document.doc_created_at`
   alongside the existing `updated_at=...doc_updated_at`. Null source → field omitted (serializer
   already drops None), no synthetic fallback.
4. Metadata-update backfill: add `created_at: datetime | None` to our `MetadataUpdateRequest`
   equivalent + an update branch that writes epoch-seconds (for connectors that learn creation time
   after indexing) — mirrors upstream `opensearch_document_index.py:634-638`.
5. `search.py:1083` — replace the single-field `_get_time_cutoff_filter` with a dual builder:
   - per-field clause = `bool.should[ {range: field gte/lte epoch-UTC}, (optional) {must_not:{exists:field}} ]`,
     `minimum_should_match:1`;
   - **AND** the `created_at` and `updated_at` clauses;
   - **undated-tolerance asymmetry**: `created_at` always `include_undated=True`; `updated_at`
     includes undated **only** for an old open-ended lower bound (start set, end None, start older
     than `ASSUMED_DOCUMENT_AGE_DAYS=90`).
6. Thread `created_at_range` + `updated_at_range` (`TimeRange | None`) through our `IndexFilters` and
   every retrieval builder; keep back-compat with the current single `time_cutoff`.
7. Update/confirm `FILTER_SEMANTICS.md` matches the implemented predicate.

**Tests:** unit tests on the filter DSL (range-vs-missing, asymmetry, AND across fields) + a
serialize/validate round-trip for `created_at`. **Risk:** low — additive schema, isolated filter
change. **Effort:** S–M.

## §4 Phase 2 — IndexPair backfill safety + missing-doc surfacing (M, MEDIUM risk)

Foundation for Phase 3; also hardens metadata sync during any secondary-index backfill.

**Work:**

1. `client.py:827/1068` — add `use_create_only` to `bulk_index_documents` (op_type `create`,
   `raise_on_error=False`, `_benign_create_conflict_count` for 409 `version_conflict_engine_exception`);
   add `ignore_missing` + `surface_document_missing` to `bulk_update_documents` (classify per-item
   404 `document_missing_exception`).
2. Add `OpenSearchDocumentMissingError` (carries missing chunk-ids → doc-ids) and
   `SecondaryIndexDocumentMissingError` (doc-ids) to our interfaces.
3. `opensearch_document_index.py` update layer — map chunk-ids→doc-ids, keep processing remaining
   requests, raise the typed error.
4. `OpenSearchIndexPair` (`:1073`) — add `primary_backfill_in_progress`; write PRESENT→FUTURE order;
   convert both indices' 404s to `SecondaryIndexDocumentMissingError`; validate secondary params
   all-set-or-all-none. **Invariant:** never clear `needs_sync` for a doc reported missing (avoids a
   later port reinstating a stale ACL).

**Tests:** the index-pair-secondary scenarios (continue-past-missing, precise attribution,
backfill-off legacy). **Risk:** medium — touches update/delete paths. **Effort:** M.

## §5 Phase 3 — Zero-downtime reindex-port (embedding-model swap) (XL, HIGH risk)

The full "safely swap the embedding model without re-fetching connectors or downtime" capability.
Depends on Phases 1 + 2. **This is a major, multi-week effort** and warrants its own sub-plan; the
critical unknown is how closely our chunker / search-settings / swap-index / celery infra mirrors
upstream (a discovery spike below is step 0).

**Sub-components (each a workstream):**

1. **PIT scan** (`client.py`): `open_pit`/`close_pit`/`fetch_chunks_for_doc_ids`/
   `iter_chunks_for_doc_ids` — keep-alive ~5m, page ~1000, stable sort `(document_id, chunk_index)`,
   exclude vectors, filter to regular chunks (`max_chunk_size == DEFAULT_MAX_CHUNK_SIZE`), expiry →
   reopen+retry once, server-timeout → fail batch, always close in `finally`.
2. **Re-embed engine** (`om/indexing/port_reembed.py`, NEW): `select_reembed_strategy` (MODEL_ONLY
   vs AUGMENTATION), `re_embed_chunks`. MODEL_ONLY rebuilds the exact embedded text (metadata-tail
   reproduction using the **PRESENT** tokenizer) and re-embeds; AUGMENTATION strips to bare text,
   reconstructs the doc, re-enriches under the FUTURE contextual LLM, re-embeds. Match embeddings
   **by identity** `(document_id, chunk_index)`, never by position. **This is the hardest part** —
   it is tightly coupled to our chunker, contextual-RAG, tokenizers, and embedder.
3. **Copy loop** (`om/document_index/opensearch/port_copy.py`, NEW): PIT-page → abort-check →
   re-embed → stamp `written_by_port=True` → sub-page (1000) create-only writes, with
   `surviving_doc_ids` re-checked before each sub-page.
4. **Resurrection safety**: `written_by_port` marker; `delete_port_written_chunks` (delete-by-query
   on `written_by_port=true AND document_id in [...]`, batched 1000); orphan-candidate recording at
   every delete choke point **before** the index delete.
5. **DB**: `PortAttempt` (status, `last_processed_doc_id` cursor, `up_to_doc_id` snapshot bound,
   scope = cc_pair xor user, `docs_ported`, `cancel_requested`, active-unique index),
   `PortOrphanCandidate` (per-scope partial-unique); search-settings columns `use_port_flow`,
   `port_backfill_source_id`, `switchover_type`. **Alembic migration** (applied via Docker rebuild).
6. **Driver + scheduler**: `run_port_attempt` task (fresh session per batch, heartbeat via
   `touch_port_progress`, soft time limit, idempotent retry, cursor advances only after a fully
   written batch) + a beat/cron `check_for_port` (stall-fail, target resolution, concurrency caps).
7. **Triggers/switchover**: admin "set new search settings" (`use_port_flow=True`) + `swap_index`
   promotion (INSTANT records `port_backfill_source_id`).

**Load-bearing invariants to reproduce:** create-only (stale can't clobber fresh); `written_by_port`
+ pre-delete orphan-candidate + post-loop sweep (delete-vs-resurrect race); `surviving_doc_ids`;
cursor never past a partial batch; snapshot upper bound; PIT consistency; heartbeat/abort brackets;
match-by-identity; correct-tokenizer metadata-tail skip.

**Step 0 (discovery spike, ~1–2 days):** confirm our equivalents exist for the upstream deps —
`SearchSettings` fields (model_name/provider_type/index_name/enable_contextual_rag/
contextual_rag_model_configuration_id), `DefaultIndexingEmbedder.from_db_search_settings`,
chunker budgets (`DEFAULT_CONTEXTUAL_RAG_RESERVED_TOKENS`, `MAX_METADATA_PERCENTAGE`,
`get_metadata_suffix_for_document_index`), `add_contextual_summaries`, `get_tokenizer`, swap-index
flow. Gaps here expand Phase 3 materially.

**Tests:** port-copy round-trip (MODEL_ONLY + AUGMENTATION), create-only benign-409, PIT expiry/
timeout, resurrection sweep, cursor-resume, cancel/abort. **Risk:** high (concurrency, data-safety,
migrations, celery). **Effort:** XL.

---

## §6 Effort / risk summary

| Phase | Scope | Effort | Risk | Depends on | Reindex needed? |
| --- | --- | --- | --- | --- | --- |
| 0 | datetime UTC convention (verify) | XS | Low | — | No |
| 1 | `created_at` + dual time-range search | S–M | Low | 0 | No (additive) |
| 2 | IndexPair backfill safety + missing-doc surfacing | M | Medium | — | No |
| 3 | Zero-downtime reindex-port (model swap) | XL | High | 1, 2 | Migration (Docker) |

## §7 Recommended sequencing & scope options (pick one)

- **Option A — Quick win (recommended start):** Phases 0 + 1 only. Low risk, self-contained, ships
  `created_at` + dual created/updated time-range filtering. Also lays the field groundwork Phase 3
  will reuse. Best effort-to-value.
- **Option B — Foundation:** A + Phase 2. Adds the create-only / missing-doc / IndexPair-safety
  primitives — valuable on their own and required before any reindex-port.
- **Option C — Full capability:** A + B + Phase 3 (start with the Step-0 discovery spike). The
  complete zero-downtime embedding-model-swap — the operational prerequisite to ship a *better
  embedding model*, which is itself a semantic-quality gain (ties back to Track A in the companion
  doc). Largest, highest-risk; do only after A/B land and the spike sizes the coupling.

**My recommendation:** do **Option A** now (fast, low-risk, unblocks better time filtering and seeds
Phase 3), then run the **Phase-3 Step-0 spike** to accurately size Option C before committing to it.

## §8 Open questions to resolve before/within implementation

1. Is `FILTER_SEMANTICS.md` in our tree aspirational or partly implemented? (confirms Phase 1 delta)
2. Does our `MetadataUpdateRequest` / `IndexFilters` already carry any `created_at` plumbing?
3. Phase 3 coupling: how much of our chunker / contextual-RAG / search-settings / swap-index matches
   upstream's assumptions (Step-0 spike answers this).

## §9 Verification

- Phase 1/2: unit tests on filter DSL + serialize round-trip + index-pair scenarios (adapted, OUR
  fields). Run from `backend/`.
- Phase 3: port round-trip + safety-invariant tests against a live OpenSearch; migration applies via
  Docker rebuild only.
- No commits until you ask.
