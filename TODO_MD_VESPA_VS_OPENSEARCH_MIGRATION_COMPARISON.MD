# Vespa → OpenSearch: Ranking Comparison, Upstream Diff & Enterprise-Scale Gap Analysis

> **Goal of this document.** Capture exactly what the old **Vespa** search backend did for ranking
> quality, what our current **OpenSearch** implementation does, how our OpenSearch impl compares to
> the **latest upstream Onyx** OpenSearch impl, and — from the combined gap analysis — how to reach
> **best-quality vector / similarity / semantic search at enterprise scale**.
>
> Evidence basis: Vespa details recovered from git history (`2111eccf0`, `16c7781b0`; removed in
> `8d561d032`); OpenSearch details from the live trees + `git log` (ours: `backend/om/…`; upstream:
> `D:\llm\danswer07022026_original\onyx`, `backend/onyx/…`).

## Bottom line (three findings that shape everything)

1. The OpenSearch migration **kept retrieval but dropped Vespa's ranking-quality machinery** —
   per-query hybrid-alpha, **recency/time-decay scoring**, and **document-boost scoring** are gone.
2. The **cross-encoder reranker is defined but NOT wired** into the search path — in **both** our
   fork **and** the latest upstream Onyx. It is the single biggest untapped quality lever.
3. Latest upstream is **NOT ahead on ranking quality** (byte-identical logic, same `TODO(andrei)`
   markers) — it is ahead on **operational / scale maturity** (IAM+TLS auth, Terraform module,
   zero-downtime reindex/PIT, `created_at` dual time-range, benchmark tooling, opensearch-py 3.2).
   Our fork's OpenSearch code froze ~**2026-07-19** (opensearch-py **3.0.0**); upstream is at
   **3.2.0** and still moving (last change **2026-07-22**). Field names also diverged
   (`*_embedding`/`chunk_text` here vs `*_vector`/`content` upstream).

---

## PART 1 — Vespa ranking (as it was)

Recovered from git history (`2111eccf0`/`16c7781b0`, removed in `8d561d032`). Schema
`danswer_chunk.sd.jinja`; interface `document_index/vespa/index.py`; runner
`context/search/retrieval/search_runner.py`.

**Five rank-profiles (+ built-in `unranked`):**

- `default_rank` — base (inherited); helper fns `document_boost`, `document_age`,
  `aggregated_chunk_boost`, `recency_bias`.
- `hybrid_search_semantic_base_{dim}` — `first-phase = query(title_content_ratio)*closeness(title) +
  (1-ratio)*closeness(content)`; `global-phase` normalizes vector-closeness + bm25 and blends.
- `hybrid_search_keyword_base_{dim}` — same shape, bm25 variant.
- `admin_search` — plain bm25; `random_` — random ranking; `unranked` — `limit 0` count/existence.
- `{dim}` = one keyword + one semantic profile **per embedding dimension** (Vespa tensor).

**Per-query dynamic ranking (Vespa `input.query(...)`) — the key quality machinery:**

- `alpha` = `hybrid_alpha` — continuous vector/keyword blend (0.2 keyword / 0.5 semantic).
- `title_content_ratio` — title-vs-content weighting.
- `decay_factor` = `DOC_TIME_DECAY × recency_bias_multiplier` — **recency applied in scoring**.
- Two-phase ranking **inside the engine** (first-phase → normalized global-phase).
- Profile selection per query (`index.py:820-823`): `KEYWORD` → keyword profile, else semantic;
  admin → `admin_search`; random → `random_`.
- Runner fired **up to 3 parallel retrievals** per query and merged.

---

## PART 2 — OpenSearch ranking (ours, current)

`backend/om/document_index/opensearch/`.

**Index / vector:** two `knn_vector` fields **`title_embedding`** + **`content_embedding`**, HNSW /
engine `lucene` / `cosinesimil`, `ef_construction=256`, `m=32`, index `ef_search=500`; single vector
(no tensor → one index per dim, `TODO(andrei)`); `english` analyzer; **default BM25** (no custom
similarity); `"dynamic":"strict"`; shards AWS-MT 324/2, ST 3/2, local 1/1.

**Fusion:** native OpenSearch **`hybrid`** query (2–3 sub-queries) + a **normalization-processor**
search pipeline (`min_max` default / `zscore`), combined by **weighted `arithmetic_mean`** with
**static** weights (content-vector 0.5 / combined-keyword 0.5; alt config title-vec 0.1 /
content-vec 0.45 / keyword 0.45); `pagination_depth=500`. This is the analog of Vespa's global-phase,
but with static weights and no learned expression.

**What was dropped / degraded vs Vespa:**

- `query_type` **ignored** (`# noqa: ARG002`, `opensearch_document_index.py:883`) — RAG is always
  hybrid; keyword/semantic builders used only by admin + tests.
- `hybrid_alpha` **dead** in the DSL (collapses to a binary switch that changes nothing).
- title/content weighting = **static per-clause boosts** (title 0.1 / 0.2, content 1.0 / 1.5).
- recency/time-decay **not scored** — only a hard `updated_at` range filter
  (`ASSUMED_DOCUMENT_AGE_DAYS=90`); `search.py:178-181 TODO(andrei): Implement document age`.
- document `boost` **stored but not scored**; `TODO(andrei): Implement document boost`.
- cross-encoder reranker (`search_nlp_models.py`) **defined but NOT wired** into the search path.

**What OpenSearch adds:** dynamic tool-layer fan-out over LLM query variants merged by **weighted
RRF** (`RRF_K_VALUE=50`); LLM query expansion + LLM-judge section selection; z-score normalization
option; nested KG relationships. (Query-expansion admin settings live in the uncommitted WS-E work.)

**Design rationale (`opensearch/README.md`):** embedding scores cluster ~0.6–0.8; the
normalization-processor runs last over independent sub-queries, so boosts/decay inside the query
"can't introduce new docs" and aren't sortable → the deliberate design is to **apply
refinement/boosting/time-decay in application code**, not in the OpenSearch query.

---

## PART 3 — Vespa vs OpenSearch: side-by-side parity

| Capability | Vespa | OpenSearch (ours) | Verdict |
| --- | --- | --- | --- |
| Named rank-profiles | 5 + `unranked` | none — inline DSL + 2 named pipelines | Changed (arch) |
| Keyword vs semantic ranking | distinct profiles per query | collapsed; always hybrid | **Lost** |
| Hybrid vector/keyword blend | per-query continuous `alpha` | static pipeline weights | **Degraded** |
| Title vs content weighting | per-query `title_content_ratio` | static per-clause boosts | **Degraded** |
| Recency/time-decay in scoring | `decay_factor` in ranking expr | not scored — hard filter only | **Lost** |
| Document boost in scoring | `document_boost` in ranking expr | stored, not scored | **Lost** |
| Score normalization | in-engine global-phase | normalization-processor (min_max/zscore) | Parity (simpler) |
| Admin bm25 / random / count | `admin_search` / `random_` / `unranked` | keyword_retrieval / random_score / index-stats | Parity |
| Multi-retrieval fan-out | fixed 3 | dynamic N + federated, weighted RRF | Improved |
| LLM query expansion / admin knobs | — | present (WS-E, uncommitted) | Gain |
| Cross-encoder rerank | (not in-engine) | defined, **not wired** | Available, unused |

---

## PART 4 — Gap analysis: Vespa vs OpenSearch

**Quality levers Vespa had that OpenSearch lost / degraded (priority list):**

1. **Recency/time-decay scoring** — lost (only a hard cutoff filter now).
2. **Document-boost scoring** — lost (curator `boost` no longer affects ranking).
3. **Per-query hybrid alpha** — degraded to a fixed 0.5/0.5 pipeline weight.
4. **Dynamic title/content weighting** — degraded to static boosts.
5. **Query-type-specific ranking** — lost (always hybrid).
6. **Per-dimension tensor embeddings** — replaced by one index per dim.

**OpenSearch gains to keep:** dynamic weighted-RRF variant fusion, LLM expansion, LLM-judge section
selection, admin-configurable expansion (WS-E), z-score normalization, operational scale.

**Dead / orphaned code to reconcile:** `HYBRID_ALPHA_KEYWORD`, `TITLE_CONTENT_RATIO`,
`recency_bias_multiplier` (dead on the OpenSearch path), stale `QueryType` enum comment.

---

## PART 5 — Ours vs Latest Upstream Onyx OpenSearch

Upstream: `D:\llm\danswer07022026_original\onyx`.

### 5.1 Vintage & version (real `git log`, not folder names)

| Aspect | Ours (`backend/om/…`) | Latest upstream (`backend/onyx/…`) |
| --- | --- | --- |
| opensearch dir last change | **2026-07-19** (`d7b151d82` "stable") | **2026-07-22** (`4cf2a9c7e0`, `#12733`) |
| opensearch-py | **3.0.0** | **3.2.0** |
| vector field names | `title_embedding` / `content_embedding` / `chunk_text` | `title_vector` / `content_vector` / `content` |
| Status | frozen ~07-19, drifting | actively evolving |

### 5.2 Ranking quality — IDENTICAL, no upstream advancement

A full call-stack trace of upstream (`SearchTool.run → search_pipeline → search_chunks →
_embed_and_hybrid_search → OpenSearchDocumentIndex.hybrid_retrieval → DocumentQuery.get_hybrid_search_query
→ client.search`) shows the ranking path is **functionally identical to ours** on every axis: same
`hybrid` + normalization fusion and weights, `query_type` still ignored (`# noqa: ARG002`),
`hybrid_alpha` still dead, same static title/content boosts, **recency/boost still not scored** (same
`TODO(andrei)` markers verbatim), **reranker still not wired** (zero callers in `context/search/**`
or `tools/.../search/**`), same weighted RRF (`k=50`).

**There is no ranking-quality advancement to port from upstream** — the levers we want are net-new on
both sides.

### 5.3 Operational / scale / reliability advancements upstream HAS and we LACK

| # | Advancement | Upstream evidence | Tag |
| --- | --- | --- | --- |
| 1 | AWS **IAM/SigV4** auth (`es` + `aoss`) | `client.py:272-289`, `#12364` (06-26) | Enterprise |
| 2 | Server cert verify + **mutual TLS** + config validation | `client.py:254-257,294-297`, `#12301` (06-23) | Enterprise |
| 3 | **Terraform** managed-OpenSearch module (dedicated masters, Multi-AZ standby, UltraWarm/cold, KMS, FGAC, Auto-Tune, slow-logs) | `modules/aws/opensearch/*.tf` | Enterprise/Scale |
| 4 | **Reindex-port** infra: PIT scan + create-only writes + `port_copy.py` + resurrect-sweep (zero-downtime embedding-model swap) | `client.py:1713-1921,968-1102`, `port_copy.py`, `#11977`/`#12733` | Scale |
| 5 | IndexPair primary/secondary **backfill** + typed missing-doc signal | `opensearch_document_index.py:974-1067` | Scale |
| 6 | **`created_at`** field + created/updated **dual time-range** search | `#12755` / `#12757` / `#12893` | Feature |
| 7 | Benchmark + ops **debug scripts** (p50/p95 latency, health/allocation, reroute-retry, reproducible embeddings) | `scripts/debugging/opensearch/*` | Perf/ops maturity |
| 8 | Test coverage: TLS, auth, batch-flush, index-pair-secondary | `tests/.../opensearch/test_*` | Reliability |
| 9 | opensearch-py **3.0.0 → 3.2.0** | `requirements/default.txt` | Maintenance |

Already in our fork (not gaps): batch-flush code, cluster slow-log settings, both retryable-error
retries, `allocation_explain`/`reroute_retry_failed`, basic `OpenSearchIndexPair`,
`string_filtering.py`, kNN constants.

### 5.4 Schema / field divergence (integration hazard)

Field names diverged (`*_embedding`/`chunk_text` vs `*_vector`/`content`), and we lack `created_at`,
`global_boost`, `written_by_port`. Adopting upstream capabilities is therefore **not a clean
cherry-pick** — it requires reimplementing against our schema (see PART 7), plus our `onyx→om` rename
accounting. **We keep our field names; we do not adopt upstream's.**

---

## PART 6 — Enterprise-scale roadmap (two independent tracks)

> Best-quality-search work and scale/ops work are **separate tracks**: upstream offers a knowledge
> reference for the scale track, but nothing for the quality track. Gate everything behind an eval
> harness. No direct `alembic upgrade`; migrations apply via Docker rebuild.

### Track A — Search quality (NET-NEW; neither we nor upstream have it)

- **A0 (do first):** repoint the `answer_quality` eval harness off Vespa (`restart_vespa_container`,
  `DANSWER_VESPA_DATA_DIR`) to OpenSearch and build a golden relevance set — so A1–A4 are measured.
- **A1 (P0, biggest lever):** wire the **cross-encoder reranker** into a retrieve-then-rerank stage
  (retrieve top-K broad via hybrid → rerank top-N with the existing `RerankingModel`) before section
  merge, behind a setting. Directly targets "best semantic quality."
- **A2 (P1):** **recency/time-decay scoring** as a post-retrieval code pass (per the README's own
  recommended design); re-activate `DOC_TIME_DECAY` / `recency_bias_multiplier` / `RecencyBiasSetting`
  on the OpenSearch path.
- **A3 (P1):** **document-boost scoring** in code (curator `boost` as a post-retrieval multiplier) —
  today it is inert.
- **A4 (P2):** recover **tunable hybrid balance** (query-type-aware normalization weights or
  per-request hybrid weights); reconcile the dead `HYBRID_ALPHA*` / `TITLE_CONTENT_RATIO` constants.

### Track B — Adopt upstream operational/scale maturity (reimplement with OUR fields)

- **B1 (Enterprise):** IAM/SigV4 + mutual TLS auth + config validation (`#12301`, `#12364`).
- **B2 (Enterprise/Scale):** the Terraform managed-OpenSearch module (masters, Multi-AZ standby,
  UltraWarm/cold, KMS, FGAC, Auto-Tune, slow-logs).
- **B3 (Scale):** reindex-port flow — `port_copy.py` + PIT scan + create-only writes + resurrect-sweep
  → zero-downtime embedding-model swap. This is what makes deploying a *better embedding model* (a
  real semantic-quality gain) operationally safe.
- **B4 (Scale):** IndexPair primary/secondary backfill + typed missing-doc signal.
- **B5 (Feature):** `created_at` + created/updated dual time-range search (`#12755` / `12757` / `12893`).
- **B6 (Ops):** the benchmark/debug scripts (p95 latency, health/allocation, reproducible embeddings)
  — feeds A0's measurement loop.
- **B7 (Maintenance):** opensearch-py 3.0.0 → 3.2.0.

**Track interplay:** A0 + B6 give the measurement loop; A1 the quality jump; B3/B4/B5 the
reindex/scale foundation to safely ship better embedding models.

---

## PART 7 — Bringing indexing / reindex / time-range into THIS repo (with OUR fields)

> **Scope note:** this section is a **knowledge summary only**. The actual implementation is a
> **separate, carefully-scoped plan** (see "Next steps"). We **keep OUR fields** — `title_embedding`
> / `content_embedding` / `chunk_text` — and **never adopt upstream field names or copy its code
> verbatim**. Upstream is a *reference for the approach*; we reimplement it against our schema.

**Short answer: yes — feasible, and the schema additions are additive (no reindex needed to add the
fields).**

### 7.1 What our repo ALREADY has (verified in-tree)

- **Indexing — full.** `index()` with per-doc batch flush at `MAX_CHUNKS_PER_DOC_BATCH`
  (`opensearch_document_index.py:429/475/545`), `bulk_index_documents` (`client.py:827`),
  `index_raw_chunks` (`:1055`), `delete` / `update` / `bulk_update_documents` / `delete_by_query`.
- **Reindex — scaffold only.** `OpenSearchIndexPair` primary/secondary (`:1073`, with
  index/delete/update at `:1132-1145`) — the swap "pipes" exist.
- **Time-range — single.** `_get_time_cutoff_filter` ranges on `updated_at` **only**
  (`search.py:1083-1111`), with a null-tolerant `ASSUMED_DOCUMENT_AGE_DAYS` fallback.

### 7.2 What our repo LACKS (the upstream advancements to reimplement)

- **Reindex-port flow** (zero-downtime live re-embed): `port_copy.py`, PIT scan (`open_pit` /
  `close_pit` / `iter_chunks_for_doc_ids` / `fetch_chunks_for_doc_ids`), `use_create_only` bulk
  writes, resurrect-sweep (`written_by_port` + `delete_port_written`). None present.
- **IndexPair backfill safety:** `primary_backfill_in_progress` + typed
  `SecondaryIndexDocumentMissingError`. Absent.
- **`created_at` document field + dual created/updated time-range search** (`#12893`). We have only
  `updated_at` (`schema.py:41`); the `created_at` in `client.py` is index-creation metadata, not a
  doc field.

### 7.3 Translation reference (upstream concept → OUR field — we implement with OUR names)

| Upstream field (reference only) | OUR field (what we implement) |
| --- | --- |
| `title_vector` | `title_embedding` |
| `content_vector` | `content_embedding` |
| `content` | `chunk_text` |
| `global_boost` | `boost` |
| `created_at` (doc) | ADD `created_at` (new additive field) |
| `written_by_port` | ADD `written_by_port` (new additive field) |

`schema.py:73/615` confirm new fields are **additive → no reindex required** to introduce
`created_at` / `written_by_port`, so the schema changes are low-risk.

### 7.4 Effort / order (our-field variant)

1. Add additive `created_at` + `written_by_port` to `schema.py` (our names) + populate `created_at`
   at index time.
2. Extend `_get_time_cutoff_filter` (`search.py:1083`) to also range on `created_at` (dual range,
   `#12893`).
3. Reimplement PIT scan in `client.py` (`open_pit` / `iter_chunks` / `fetch_chunks` + expiry retry)
   + `use_create_only` bulk writes.
4. Reimplement the port-copy flow (re-embed live chunks PRESENT→FUTURE) adapted to our embedder + our
   fields; wire the resurrect-sweep (`delete_port_written`).
5. Upgrade `OpenSearchIndexPair` with `primary_backfill_in_progress` +
   `SecondaryIndexDocumentMissingError`.
6. Bring adapted tests (batch-flush already ours; add TLS/auth/index-pair-secondary).

This is the **indexing/scale** track — it does NOT change ranking quality (Track A). But steps 3–5
(safe reindex-port) are the prerequisite to ship a *better embedding model*, which is itself a
semantic-quality gain.

---

## Next steps

- **Deliverable 1 (this document):** the gap analysis above — documentation only, no code changes.
- **Deliverable 2 (separate plan):** a carefully-scoped implementation plan for the Track-B
  indexing / reindex / time-range work in PART 7. Ground rules: keep OUR fields exclusively; use the
  upstream repo purely as a knowledge/approach reference (no verbatim code, no upstream field names);
  schema additions are additive (no reindex to add fields); no commits and no direct
  `alembic upgrade` — migrations apply via Docker rebuild.
- **Track A (search quality)** — reranker, recency/boost scoring, eval harness — is captured in
  PART 6 for later prioritization.
