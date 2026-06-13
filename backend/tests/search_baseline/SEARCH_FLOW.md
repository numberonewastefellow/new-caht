# How Search Works — Onyx/Danswer (Vespa) — Detailed Reference

A single, example-driven explanation of the whole search flow: **keyword (BM25)**,
**semantic (vector/similarity)**, **hybrid**, the **Vespa ranking profiles**, the engine
**rerank** (first-phase → global-phase), the **weighted RRF fusion**, and the **LLM
selection/classification** layers — with method/variable quick-reference and a map to the
tests in this folder.

Everything here is verified against the source in this repo and against real runs of
[demo_reranking_layers.py](demo_reranking_layers.py) on the two-domain `index_rest` data
(Sports / WorldNews). Embedding model in this deployment: **`nomic-embed-text-v1`, 768-dim**.

---

## 0. The big picture — two altitudes

There are **two** levels at which "search" happens. Knowing which one you're looking at
removes 90% of the confusion.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ A) RETRIEVAL LAYER  (deterministic, NO LLM)  ← the baseline tests use this      │
│                                                                                │
│   search_chunks(ChunkIndexRequest)            search_runner.py:77              │
│     └─ _embed_and_search()                     search_runner.py:50             │
│          ├─ get_query_embedding()              context/search/utils.py:82      │
│          └─ document_index.hybrid_retrieval()  vespa_document_index.py:547     │
│                 └─ build_vespa_filters() + YQL + query_vespa()  → VESPA        │
│                        (Vespa does first-phase → global-phase ranking)          │
└──────────────────────────────────────────────────────────────────────────────┘
                                   ▲ returns ranked list[InferenceChunk]
┌──────────────────────────────────────────────────────────────────────────────┐
│ B) FULL CHAT PATH  (adds LLM)  ← SearchTool.run, used in real chat              │
│                                                                                │
│   Layer 0  query expansion (LLM): semantic rephrase + keyword variants         │
│   Layer 1  run retrieval (A) once PER query variant                            │
│   Layer 2  weighted RRF fusion across the variants  (algorithmic)              │
│   Layer 3  LLM relevance SELECTION (one batched call)                          │
│   Layer 4  per-selected-section LLM context classification                     │
│                                                                                │
│   SearchTool.run()                             search_tool.py:531             │
└──────────────────────────────────────────────────────────────────────────────┘
```

- **Baseline tests** ([test_vespa_baseline.py](test_vespa_baseline.py)) exercise **A** only →
  deterministic, snapshot-stable.
- **Reranking demo/tests** ([demo_reranking_layers.py](demo_reranking_layers.py),
  [test_reranking_demo.py](test_reranking_demo.py)) exercise **B** end to end.

---

## 1. Core concepts (with examples)

### 1.1 Keyword / lexical search (BM25)

Matches on **words/tokens**. Vespa scores lexical overlap with **BM25** over the `content`
and `title` fields. In the YQL the lexical clause is
`{grammar:"weakAnd"}userInput(@query)` plus a `content_summary` clause for highlighting.

- Functions in ranking: `bm25(content)`, `bm25(title)`.
- A **pure-keyword** profile exists: `admin_search` → `bm25(content) + 5*bm25(title)`
  (title-heavy; used by the admin doc explorer). See danswer_chunk.sd.jinja:368.

**Example.** Query `"JCPOA terms"` against the Iran article scores high on BM25 because the
exact tokens appear in the text; a football chunk scores ~0 (no token overlap).

### 1.2 Semantic / vector / similarity search

Matches on **meaning**, not exact words. The query and every chunk are turned into a 768-dim
embedding vector; similarity = **cosine closeness** of the vectors. Vespa retrieves nearest
vectors with `nearestNeighbor(embeddings, query_embedding)` and scores with
`closeness(field, embeddings)` (and `closeness(field, title_embedding)`).

- Query embedding: `get_query_embedding()` → `EmbeddingModel.encode(text_type=QUERY)`.
- Passage embedding (at index time): `EmbeddingModel.encode(text_type=PASSAGE)`.
- "Similarity" = `closeness(...)` ∈ [0,1] (higher = more similar).

**Example.** Query `"Will Vinicius shine for Brazil at the 2026 World Cup?"` retrieves the
football chunks even though it doesn't repeat their exact wording — the *meaning* is close.
(Observed: `foot_bal` chunk 0 → semantic score **0.969**.)

### 1.3 Hybrid search (combine keyword + semantic via `alpha`)

Hybrid = a weighted blend of the **vector** score and the **BM25** score. The blend weight is
`alpha` (`input.query(alpha)`):

```
hybrid ≈ alpha * (vector similarity) + (1 - alpha) * (BM25 keyword)
```

- `alpha = 1.0` → pure semantic;  `alpha = 0.0` → pure keyword;  in between → hybrid.
- **Important (this codebase):** you do not pass a free alpha through `search_chunks`. The
  per-request `hybrid_alpha` only *picks a profile* — see 1.4. Effective alpha is **0.2 or 0.5**.

### 1.4 Ranking profiles & how `alpha` is chosen

`_embed_and_search` (search_runner.py:57-71) converts the request's `hybrid_alpha` into a
discrete **profile choice**:

| request `hybrid_alpha` | profile | effective Vespa `alpha` | constant |
|---|---|---|---|
| `<= 0.3` | `hybrid_search_keyword_base_768` | `0.2` | `KEYWORD_QUERY_HYBRID_ALPHA` |
| `> 0.3` (or `None`) | `hybrid_search_semantic_base_768` | `0.5` | `HYBRID_ALPHA` |

`title_content_ratio` (`TITLE_CONTENT_RATIO = 0.10`) weights title vs content (10% / 90%)
inside both profiles. The two profiles differ **only in first-phase** (see 1.5).

### 1.5 The engine "rerank": first-phase → global-phase

This is Vespa's own two-stage ranking — it is what people loosely call the engine "rerank",
and it is **always on** (there is no cross-encoder; that was removed — see §3). Formulas are
the exact expressions from `danswer_chunk.sd.jinja`.

**First-phase** (cheap, run on all matches to pick the top `rerank-count: 1000`):
- semantic profile: `tcr*closeness(title_embedding) + (1-tcr)*closeness(embeddings)`
- keyword profile:  `tcr*bm25(title) + (1-tcr)*bm25(content)`
  (where `tcr` = `query(title_content_ratio)` = 0.10)

**Global-phase** (the real "rerank" — re-scores those top 1000, identical formula in both profiles):

```
score =
  [ alpha * ( tcr*norm(title_vector_score) + (1-tcr)*norm(closeness(embeddings)) )
  + (1-alpha) * ( tcr*norm(bm25(title))     + (1-tcr)*norm(bm25(content)) ) ]
  * document_boost      # user feedback, 0.5x–2x (piecewise sigmoid)
  * recency_bias        # max(1 / (1 + decay_factor * document_age_years), 0.75)
  * aggregated_chunk_boost   # info-content factor, default 1.0
```
- `norm(...)` = `normalize_linear` across the candidate set.
- `title_vector_score = max(closeness(embeddings), closeness(title_embedding))`.
- `document_age` defaults to ~0.25yr when `doc_updated_at` is missing.
- `decay_factor = DOC_TIME_DECAY * RECENCY_BIAS_MULTIPLIER` (both **constants** → recency is
  not per-request tunable here).

The `relevance` value returned per hit (what we store as `score`) is this global-phase score.

### 1.6 Filters → YQL (`build_vespa_filters`)

Filters are turned into a Vespa `WHERE` clause (vespa_request_builders.py). They restrict
*which* documents are eligible; they do not change ranking math.

| Filter (IndexFilters) | becomes (Vespa) | our test |
|---|---|---|
| `document_set=["Sports"]` (knowledge base) | `document_sets contains "Sports"` | `test_filter_document_set_*` |
| `source_type=[FILE]` | `source_type contains "file"` | `test_filter_source_type_*` |
| `time_cutoff=<dt>` | `doc_updated_at >= <unix>` | `test_filter_time_cutoff_recent_only` |
| `access_control_list=[...]` | `access_control_list contains ...` (omitted when `None`) | baseline uses `None` (public) |

The full query body is assembled in `hybrid_retrieval` (`YQL_BASE` + filters + the
nearestNeighbor/userInput clauses) and sent by `query_vespa()`.

---

## 2. The 4 SearchTool layers (full chat path, with real numbers)

Numbers below are from an actual `demo_reranking_layers.py` run on the `index_rest` data,
query **"What are the terms of the Iran nuclear deal with the US?"** (domains scoped to
`Sports`, `WorldNews`).

### Layer 0 — query expansion (LLM)
The user query is rephrased and expanded into variants (2 parallel LLM calls):
- `semantic_query_rephrase()` → `"What are the terms of the 2015 Iran nuclear deal (JCPOA) with the United States?"`
- `keyword_query_expansion()` → `['JCPOA terms', 'Iran nuclear deal provisions', '2015 Iran US nuclear agreement terms']`

Each variant gets a **weight**: semantic rephrase `1.3` (`LLM_SEMANTIC_QUERY_WEIGHT`),
original `0.5` (`ORIGINAL_QUERY_WEIGHT`), each keyword `1.0` (`LLM_KEYWORD_QUERY_WEIGHT`).

### Layer 1 — per-query Vespa ranking (retrieval layer A, once per variant)
Each variant is retrieved independently (semantic variants use the semantic profile; keyword
variants use `KEYWORD_QUERY_HYBRID_ALPHA=0.2` → keyword profile). Observed top scores:

```
semantic "…2015 JCPOA…":   news1 chunk0 0.9991, chunk1 0.8466, chunk2 0.6275, foot_bal 0.21
keyword "JCPOA terms":      news1 chunk0 0.8990, …                foot_bal ~0.14
keyword "…2015 …terms":     news1 chunk0 0.9991, chunk2 0.7293,  foot_bal ~0.02
```
News chunks dominate every variant; football chunks score near zero (correct domain separation).

### Layer 2 — weighted RRF fusion (algorithmic, NO LLM)
`weighted_reciprocal_rank_fusion()` merges the per-variant ranked lists. Each item's score:

```
RRF_score(item) = Σ over variants:  weight / (RRF_K_VALUE + rank_in_that_variant)
```
Items appearing high across many variants rise to the top. Observed fused order:
`news1 chunk0 → news1 chunk1 → news1 chunk2 → foot_bal chunk3 → foot_bal chunk5`.
(This is the main cross-query "reranking".) Chunks are then merged into **sections** with
`merge_individual_chunks()`.

### Layer 3 — LLM relevance selection (ONE batched call — NOT per-chunk)
`select_sections_for_expansion()` packs **all** candidate sections (token-trimmed, ≤
`MAX_CHUNKS_FOR_RELEVANCE=3` chunks each) into a **single** prompt and asks the LLM to return
the list of relevant section IDs.
```
candidate sections : ['news1', 'foot_bal']
LLM-selected       : ['news1']          ← off-domain football section dropped
```
This is selection/filtering, not a per-chunk score. (The LLM is **not** a cross-encoder.)

### Layer 4 — per-section context classification (LLM, only selected sections)
For each *selected* section, `classify_section_relevance()` decides how much surrounding text
to include: `NOT_RELEVANT / MAIN_SECTION_ONLY / INCLUDE_ADJACENT_SECTIONS / FULL_DOCUMENT`.
```
news1: main_section_only
```
It can drop a section (NOT_RELEVANT), but its job is context *depth*, not base ranking.

---

## 3. Cross-encoder reranking — removed

A cross-encoder reranker is a model that scores each (query, passage) **pair** individually
and re-sorts. It was **removed** from this codebase (alembic migration `78ebc66946a0`):
`SearchSettings` has no rerank columns, and no cross-encoder model is invoked in retrieval.
Test guard: `test_no_cross_encoder_rerank_columns`.

So "reranking" today = **Vespa global-phase (§1.5) + weighted RRF (Layer 2) + LLM selection
(Layer 3)** — none of which is a cross-encoder, and none asks the LLM about chunks one-by-one.

---

## 4. End-to-end worked example (sports query)

Query: **"Will Vinicius shine for Brazil at the 2026 World Cup?"** (domains `Sports`,`WorldNews`)

1. **L0 expand:** keyword variants like `"Vinicius Junior 2026 World Cup prediction"`.
2. **L1 retrieve (semantic profile):** `foot_bal` chunk0 **0.969**, chunk2 0.912, chunk5 0.896 …
   (news chunks far below). This is §1.5 global-phase scoring at `alpha=0.5`.
3. **L2 RRF fuse:** `foot_bal` chunks occupy the top of the fused list.
4. **L3 LLM select:** from `[foot_bal, news1]` → selects `['foot_bal']` (drops off-domain news).
5. **L4 classify:** `foot_bal → main_section_only`.

Retrieval-layer only (baseline test `test_query_kubernetes_deploy`-style), the same scoring
gives `eng-k8s-deploy` **0.83** as #1 for the kubernetes query — pure §1.5, no LLM.

---

## 5. Quick reference — functions

| Function | Location | Purpose |
|---|---|---|
| `search_chunks` | context/search/retrieval/search_runner.py:77 | Retrieval entry; federated + `_embed_and_search`; dedups/sorts |
| `_embed_and_search` | search_runner.py:50 | Embeds query; maps `hybrid_alpha`→profile; calls `hybrid_retrieval` |
| `combine_retrieval_results` | search_runner.py:26 | Dedup by (doc,chunk) keep max score (retrieval-layer merge) |
| `get_query_embedding` | context/search/utils.py:82 | Query → 768-d vector via model server |
| `hybrid_retrieval` | document_index/vespa/vespa_document_index.py:547 | Builds YQL + params; runs Vespa; returns chunks |
| `build_vespa_filters` | vespa/shared_utils/vespa_request_builders.py | IndexFilters → Vespa WHERE clause |
| `query_vespa` | vespa/chunk_retrieval.py | HTTP POST to Vespa `/search/`; parse hits |
| `_vespa_hit_to_inference_chunk` | vespa/chunk_retrieval.py:104 | Vespa hit JSON → InferenceChunk |
| `SearchTool.run` | tools/.../search/search_tool.py:531 | Full chat path (Layers 0–4) |
| `semantic_query_rephrase` | secondary_llm_flows/query_expansion.py:67 | L0: LLM standalone rephrase |
| `keyword_query_expansion` | secondary_llm_flows/query_expansion.py:149 | L0: LLM keyword variants (≤3) |
| `weighted_reciprocal_rank_fusion` | tools/.../search/search_utils.py:30 | L2: weighted RRF across variants |
| `merge_individual_chunks` | context/search/pipeline.py:127 | Adjacent chunks → InferenceSection |
| `select_sections_for_expansion` | secondary_llm_flows/document_filter.py:180 | L3: ONE batched LLM relevance selection |
| `select_chunks_for_relevance` | document_filter.py:23 | Pick chunk window around center (no LLM) |
| `classify_section_relevance` | document_filter.py:94 | L4: per-section LLM context-depth label |
| `expand_section_with_context` | search/search_utils.py:354 | Applies L4 classification to expand a section |

## 6. Quick reference — constants

| Constant | Value | Where | Meaning |
|---|---|---|---|
| `HYBRID_ALPHA` | 0.5 | configs/chat_configs.py | Semantic-profile alpha |
| `KEYWORD_QUERY_HYBRID_ALPHA` | 0.2 | tools/.../search/constants.py | Keyword-profile alpha |
| `TITLE_CONTENT_RATIO` | 0.10 | chat_configs.py | Title vs content weight |
| `DOC_TIME_DECAY` | 0.5 | chat_configs.py | Recency decay factor |
| `RECENCY_BIAS_MULTIPLIER` | 1.0 | app_configs.py | Recency multiplier (constant) |
| `RERANK_COUNT` | 1000 | app_configs.py + schema `rerank-count` | Global-phase candidate count |
| `NUM_RETURNED_HITS` | 50 | chat_configs.py | Default hits returned |
| `LLM_SEMANTIC_QUERY_WEIGHT` | 1.3 | search/constants.py | RRF weight: semantic rephrase |
| `LLM_KEYWORD_QUERY_WEIGHT` | 1.0 | search/constants.py | RRF weight: keyword variant |
| `LLM_NON_CUSTOM_QUERY_WEIGHT` | 0.7 | search/constants.py | RRF weight: LLM tool query |
| `ORIGINAL_QUERY_WEIGHT` | 0.5 | search/constants.py | RRF weight: original query |
| `RRF_K_VALUE` | 50 | search/constants.py | RRF `k` (dampens top ranks) |
| `MAX_CHUNKS_FOR_RELEVANCE` | 3 | search/constants.py | Max chunks/section to LLM |

## 7. Quick reference — Vespa query params (`query_vespa`)

| Param | Meaning |
|---|---|
| `yql` | `YQL_BASE` + filters + nearestNeighbor/userInput clauses |
| `query` | text (joined `final_keywords` or original) |
| `input.query(query_embedding)` | 768-d query vector |
| `input.query(alpha)` | 0.2 (keyword) or 0.5 (semantic) |
| `input.query(title_content_ratio)` | 0.10 |
| `input.query(decay_factor)` | `DOC_TIME_DECAY * RECENCY_BIAS_MULTIPLIER` |
| `ranking.profile` | `hybrid_search_{semantic|keyword}_base_768` |
| `hits` | num_to_retrieve |

---

## 8. Search scenarios → which test demonstrates it

| Scenario | Test |
|---|---|
| Plain semantic term query | `test_vespa_baseline.py::test_query_*` |
| Keyword vs semantic profile (the alpha knob) | `test_vespa_baseline.py::test_keyword_vs_semantic_profile` |
| Knowledge-base (document_set) filter | `test_vespa_baseline.py::test_filter_document_set_*` |
| source_type filter | `test_vespa_baseline.py::test_filter_source_type_*` |
| time_cutoff (date) filter | `test_vespa_baseline.py::test_filter_time_cutoff_recent_only` |
| Combined filters | `test_vespa_baseline.py::test_combined_filters` |
| Keyword expansion (`query_keywords`) | `test_vespa_baseline.py::test_keyword_expansion` |
| RRF fusion / dedup | `test_search_tool_layer.py::test_combine_*` |
| Chunk-window selection | `test_search_tool_layer.py::test_select_chunks_*` |
| LLM relevance selection (Layer 3) | `test_search_tool_layer.py::test_llm_section_selection_plumbing`; `test_reranking_demo.py` |
| Cross-encoder removed (guard) | `test_search_tool_layer.py::test_no_cross_encoder_rerank_columns` |
| Full 4-layer pipeline, real numbers | `demo_reranking_layers.py`; `test_reranking_demo.py` |
| Ingest + verify + two-domain retrieval | `ingest_index_rest.py` |

---

## 9. Glossary

- **BM25** — classic keyword relevance score (term frequency × inverse doc frequency, length-normalized).
- **Embedding** — a fixed-length vector (768-d here) representing meaning; produced by the model server.
- **closeness** — Vespa's cosine-based vector similarity ∈ [0,1].
- **alpha** — hybrid blend weight: `alpha·vector + (1-alpha)·BM25`.
- **first-phase / global-phase** — Vespa's cheap pre-rank then expensive re-rank of the top `rerank-count`.
- **RRF** — Reciprocal Rank Fusion; merges multiple ranked lists by `Σ weight/(k+rank)`.
- **chunk vs section** — a *chunk* is one indexed piece of a doc; a *section* is one or more
  adjacent chunks merged (`merge_individual_chunks`).
- **document_set** — a named knowledge base; the unit of the KB filter.
- **cross-encoder** — a model scoring (query, passage) pairs to re-rank. **Removed** in this repo.
