# TODO — Lane L3: Recency decay + document-boost scoring (RAG backlog item 7)

**Backlog:** `TODO_MD_RAG_UPGRADES_FROM_UPSTREAM.MD` item 7 (P2); earlier analysis in `TODO_MD_VESPA_VS_OPENSEARCH_MIGRATION_COMPARISON.MD` (Part 2, Track A2/A3)
**Process:** per-feature workflow, `TODO_MD_UPSTREAM_PORT_CONNECTORS_AND_FEATURES.MD` §1.5
**Status:** Phase B DONE + cross-verified locally (2026-10-30). Uncommitted in the lane worktree, waiting for integrator merge. Still open: flag-on search_baseline goldens (need live stack), V3 in the container, M1–M3, L4.

> **Resuming in a new session?** Read §11 "Progress tracker". Pick the first unchecked item and tick it with the date when done.

---

## 1. Scope
- **What users get:**
  - Recently updated documents rank a little higher than stale ones (same gentle curve Vespa used: never below 0.75x).
  - Curator / feedback `boost` finally changes ranking (0.5x to 2x, sigmoid, as in Vespa). Today `boost` is written to Postgres and OpenSearch but nothing reads it.
- **Source:** nothing to port. Upstream HEAD (checked 2026-10-29 snapshot) still has the same `TODO(andrei): Implement document boost / document age` markers in `UP:om/document_index/opensearch/search.py` (~line 159); its only `function_score` is the random-search query. Net-new on both sides. Semantics are copied from **our own** Vespa history (commit `16c7781b0`, removed in `8d561d032`).
- **Target (our tree):**
  - `backend/om/document_index/opensearch/hybrid_rescore.py` (new, pure functions)
  - `backend/om/document_index/opensearch/opensearch_document_index.py` (`hybrid_retrieval` only)
  - `backend/om/document_index/opensearch/README.md` (update "On time decay and boosting")
  - `backend/om/configs/app_configs.py` (only inside a `# --- recency-boost ---` block)
- **Out of scope:** `hybrid_alpha` / per-query vector-vs-keyword weighting (Track A4), `title_content_ratio`, query-type profiles, `created_at` dual time range (Track B5), Vespa's `aggregated_chunk_boost` (we have no such field), wiring chat thumbs to doc boost (see §6, open question Q4).
- **Dependencies:** none blocking. L4 (eval) is needed to decide the default (§9).

## 2. How Vespa did it (intended semantics)
From the old chunk rank profile `default_rank` (git `16c7781b0`):
```
document_boost = boost < 0 ? 0.5 + 1/(1+exp(-boost/3))      # 0.5 .. 1.0
                           : 2   / (1+exp(-boost/3))         # 1.0 .. 2.0 (boost 0 -> 1.0)
document_age   = max(now - doc_updated_at (or 7_890_000 s ≈ 91 days if missing), 0) / 31_536_000   # years
recency_bias   = max(1 / (1 + decay_factor * document_age), 0.75)
decay_factor   = DOC_TIME_DECAY (0.5) * RECENCY_BIAS_MULTIPLIER (env, 1.0)
global-phase   = normalized_hybrid_score * document_boost * recency_bias * aggregated_chunk_boost
```
- Applied **after** normalization (global-phase), over `rerank-count: 1000` candidates.
- At fork time the Vespa path already used the **global** env multiplier, not a per-request one. The per-request `recency_bias_multiplier` and the per-agent `RecencyBiasSetting` were already dead then.
- The federated Slack path still uses the same recency formula today (`om/context/search/federated/slack_search.py:537-542`).

## 3. Current state (verified 2026-10-30)
| Item | Where | State |
|---|---|---|
| `recency_bias_multiplier` | `context/search/models.py:110` (`BasicChunkRequest`, default 1.0) → copied into `ChunkIndexRequest` at `pipeline.py:307` | **Never read.** `search_runner._embed_and_search` doesn't pass it; `DocumentIndex.hybrid_retrieval` (`interfaces_new.py:373`) has no such parameter. No caller ever sets it ≠ 1.0. |
| `RECENCY_BIAS_MULTIPLIER` | `configs/app_configs.py:809` | Defined, unused since Vespa removal. |
| `DOC_TIME_DECAY` / `FAVOR_RECENT_DECAY_MULTIPLIER` | `configs/chat_configs.py:10-16` | Only Slack federated uses `DOC_TIME_DECAY`. |
| Agent `recency_bias` (`RecencyBiasSetting`) | `db/models.py:3198`; set by agent editor UI, seeding (`AUTO`), workflows (`BASE_DECAY`), KG (`NO_DECAY`) | Stored, never used in ranking. |
| Time-filter LLM flow | `secondary_llm_flows/time_filter.py:37` | `extract_time_filter` raises `NotImplementedError`; `pipeline.py` discards `_detected_favor_recent`. Not a source of signal. |
| `boost` in index | mapping `schema.py:530` `boost: integer`; written on index (`_convert_om_chunk_to_opensearch_document`) and on `update()` (`opensearch_document_index.py:640`); read back into `InferenceChunk.boost` | **Stored, not scored** (`search.py:177-180` TODOs). |
| Doc age in index | `updated_at: date, epoch_second, doc_values: true` (`schema.py:504`); read back into `InferenceChunk.updated_at` | Used only as a hard range filter (`_get_time_cutoff_filter`, `search.py:1083`). |
| `hybrid_alpha` | `search_runner.py:57-65` | Collapses to `query_type`, which `hybrid_retrieval` ignores (`# noqa: ARG002`). Out of scope. |

**Field names (ours):** `boost` (`BOOST_FIELD_NAME`), `updated_at` (`UPDATED_AT_FIELD_NAME`). Both already in the mapping **and** already returned in `_source` (only the two vector fields are excluded). **No mapping change, no re-index.**

**How `boost` is written:**
- Admin/curator: `POST /admin/doc-boosts` (`server/manage/administrative.py:76`) → `update_document_boost_for_user` sets an absolute value (UI: `web/src/app/admin/documents/feedback/DocumentFeedbackTable.tsx`, explorer).
- Feedback: `create_doc_retrieval_feedback` (`db/feedback.py:179`) does `boost ±1` on ENDORSE/REJECT — **only called from ombot Slack buttons** (`ombot/slack/handlers/handle_buttons.py:409`). Web chat thumbs go to `create_chat_message_feedback` and do **not** touch doc boost.
- Both bump `last_modified` → the metadata-sync Celery task (`background/celery/tasks/{document_index,shared}/tasks.py`) pushes `boost=doc.boost` into OpenSearch via `update()`. So feedback reaches the index with sync-lag, then (after this lane) ranking.

## 4. Options and decision
**Option A — OpenSearch `function_score` (gauss/exp decay on `updated_at` + `field_value_factor` on `boost`) inside the hybrid query.** Rejected:
- `hybrid` must be the top-level query, so `function_score` can only wrap each **sub-query**. That multiplies raw BM25 / cosine scores **before** the normalization processor (`min_max`, weights 0.5/0.5 or 0.1/0.45/0.45). Min-max then re-stretches each sub-query to [0,1], so the top doc of each sub-query is 1.0 whatever its boost, and the effect depends on the candidate set. Our README ("On time decay and boosting") documents exactly this and the team's decision not to score in-query.
- Can't reproduce Vespa's "multiply the fused score" semantics; z-score pipeline makes it worse. Vespa's sigmoid boost would need a `script_score` (Painless) per sub-query, which is slower and harder to unit-test.
- OpenSearch `rescore` runs before normalization too (README, "Other concepts"). Not useful.

**Option B — app-side rescore after normalization, inside `OpenSearchDocumentIndex.hybrid_retrieval` (CHOSEN).**
- **Correct with hybrid normalization:** multiplies the final normalized hybrid score, exactly Vespa's global-phase. With `min_max` the base is in [0,1] so multiplication is safe.
- **Placed in the index layer, before any RRF:** the chat search tool (weighted RRF k=50 over query variants, `search_tool.py:724`) and the search page orchestrator (`search/orchestration/orchestrator.py:190`) fuse **ranks**. Rescoring each variant's list before it leaves `hybrid_retrieval` makes boost/recency flow through every RRF caller automatically, with **zero edits** in L2's `tools/tool_implementations/search/`. Rescoring after RRF would need per-caller edits and would multiply RRF scores (wrong scale).
- **Latency:** pure Python over ≤ a few hundred hits (µs-ms). Only cost is over-fetch (more `_source` returned).
- **Testable:** pure functions with an injected `now`; no cluster needed for unit tests.
- **Limitation (accepted, as in README):** it can only reorder candidates OpenSearch returned. Mitigation: over-fetch `ceil(num_to_retrieve × OVERFETCH)` (default 2.0, capped at `DEFAULT_NUM_HYBRID_SUBQUERY_CANDIDATES`=500 and the 10k window), rescore, stable-sort, truncate to `num_to_retrieve`. Max swing is 0.5×0.75 vs 2.0×1.0, so a 2x window covers realistic promotions.

### Design details (Phase B)
- `hybrid_rescore.py` (pure, reusable — federated Slack could later import `freshness_multiplier` instead of its inline copy; not done in this lane):
  - `feedback_boost_multiplier(boost: int) -> float` — Vespa piecewise sigmoid above.
  - `freshness_multiplier(updated_at: datetime | None, now: datetime, decay_per_year: float, floor: float) -> float` — missing `updated_at` → `ASSUMED_DOCUMENT_AGE_DAYS` (90, existing constant in `opensearch/constants.py`; Vespa used ~91.3). Future dates clamp to age 0. `decay <= 0` → 1.0.
  - `rescore_hybrid_chunks(chunks, *, now, settings: HybridRescoreSettings) -> list[InferenceChunk]` — returns new list, sorted by adjusted score desc, stable on ties; `score=None` chunks keep relative order at the end.
  - `HybridRescoreSettings` (frozen dataclass) + `load_hybrid_rescore_settings()`, which reads the config at call time.
- Note: with decay 0.5/yr the 0.75 floor is reached at ~243 days, so freshness only separates docs younger than ~8 months (same as the reference).

### Naming & structure (ours)
Upstream and old-Vespa code are **reference only**. Every folder, file, identifier and env name below is ours, chosen to match the conventions already in `om/document_index/opensearch/` and `app_configs.py`.

| Reference concept | OUR name | Reason |
|---|---|---|
| Vespa `global-phase` multiply step | module `om/document_index/opensearch/hybrid_rescore.py` | Our existing folder; says what it does (rescores hybrid hits) and sits next to `search.py` / `opensearch_document_index.py` |
| `document_boost` rank function | `feedback_boost_multiplier(boost)` | Our `boost` comes from feedback/curators; "multiplier" says how it's applied |
| `document_age` + `recency_bias` | `freshness_multiplier(updated_at, now, decay_per_year, floor)` | One function on our `updated_at` field; "freshness" avoids confusion with the dead `recency_bias_multiplier` request field |
| `decay_factor` query input | `HybridRescoreSettings.freshness_decay_per_year` (= `DOC_TIME_DECAY × RECENCY_BIAS_MULTIPLIER`) | Unit in the name; reuses our existing env vars |
| rank-profile inputs as a bundle | `HybridRescoreSettings` dataclass + `load_hybrid_rescore_settings()` | Typed, testable, no globals read deep inside |
| applying all factors | `rescore_hybrid_chunks(chunks, now=, settings=)` | Works on our `InferenceChunk` |
| `doc_updated_at` / `boost` attributes | our fields `updated_at` / `boost` (`UPDATED_AT_FIELD_NAME`, `BOOST_FIELD_NAME`) | Already in our mapping; no new fields |
| 7_890_000 s default age | existing `ASSUMED_DOCUMENT_AGE_DAYS` (90) | Reuse our constant (the 1.3-day difference is recorded in §9a) |
| `rerank-count` | `OPENSEARCH_RESCORE_OVERFETCH_FACTOR` | Relative to `num_to_retrieve`, not a fixed count |
| on/off | `OPENSEARCH_HYBRID_RESCORE_ENABLED` + `OPENSEARCH_RESCORE_{FRESHNESS,FEEDBACK_BOOST}_ENABLED`, `OPENSEARCH_RESCORE_FRESHNESS_FLOOR` | Follows the `OPENSEARCH_EXPLAIN_ENABLED` / `OPENSEARCH_MATCH_HIGHLIGHTS_DISABLED` family and the `*_ENABLED` pattern (`RERANK_ENABLED`); `app_configs.py` has only 4 `OM_*` names, so unprefixed is the local convention |
| tests | `tests/unit/om/document_index/opensearch/test_hybrid_rescore.py`, `test_hybrid_retrieval_rescore.py`, `test_hybrid_rescore_reference_parity.py`; goldens `tests/search_baseline/baselines/opensearch/hybrid_rescore/` | Mirror the module name |
- **z-score pipeline:** scores can be negative, so multiplying would invert. When `HYBRID_SEARCH_NORMALIZATION_PIPELINE is ZSCORE`, shift base scores by `-min(batch)` (+1e-6) before multiplying. Unit-tested.
- **Score field:** `InferenceChunk.score` becomes the adjusted score (as with Vespa). The raw score is only logged at debug level (adding a field would touch shared `context/search/models.py`).
- **Not applied** to `keyword_retrieval` / `random_retrieval` (admin explorer; Vespa's `admin_search` had no boost), `semantic_retrieval` (tests only), `id_based_retrieval`. `OpenSearchIndexPair.hybrid_retrieval` delegates to the primary, so it is covered.
- **Per-request multiplier:** v1 uses the global `DOC_TIME_DECAY × RECENCY_BIAS_MULTIPLIER`, which is exact parity with the fork-time Vespa path. Per-agent `RecencyBiasSetting` is optional step B8 (Q2) and needs touch points outside the lane:
  1. `om/document_index/interfaces_new.py` `hybrid_retrieval(..., recency_bias_multiplier: float = 1.0)` (default keeps `disabled.py` and others valid; add the same to `disabled.py`).
  2. `om/context/search/retrieval/search_runner.py:67` pass `query_request.recency_bias_multiplier`.
  3. `om/context/search/pipeline.py` (agent already loaded there): FAVOR_RECENT→`FAVOR_RECENT_DECAY_MULTIPLIER` (2.0), BASE_DECAY/AUTO→1.0, NO_DECAY→0.0. **No edit in `tools/tool_implementations/search/` or `om/prompts/`.**

## 5. Config (`om/configs/app_configs.py`, inside `# --- recency-boost ---` block)
| Env var | Default | Meaning |
|---|---|---|
| `OPENSEARCH_HYBRID_RESCORE_ENABLED` | `false` | **Kill switch.** Off = byte-identical behaviour to today (no over-fetch, no rescore). |
| `OPENSEARCH_RESCORE_FRESHNESS_ENABLED` | `true` | Sub-toggle; effective only when the master is on (lets L4 measure recency alone). |
| `OPENSEARCH_RESCORE_FEEDBACK_BOOST_ENABLED` | `true` | Sub-toggle for boost alone. |
| `OPENSEARCH_RESCORE_FRESHNESS_FLOOR` | `0.75` | Minimum recency factor (Vespa value). Clamped to [0,1]. |
| `OPENSEARCH_RESCORE_OVERFETCH_FACTOR` | `2.0` | Candidate multiplier before truncation. Clamped to [1, 5]. |
Reused, not redefined: `DOC_TIME_DECAY` (chat_configs, 0.5), `RECENCY_BIAS_MULTIPLIER` (app_configs, 1.0). Read the values at call time via module attributes so tests can monkeypatch them. No new dependencies. No Alembic migration. No DB, model or API change. No UI.

## 6. Existing features touched (regression scope)
Everything that reaches `DocumentIndex.hybrid_retrieval` (via `search_runner.search_chunks` / `_embed_and_search`):

| Caller | Path | Effect | Covered by |
|---|---|---|---|
| Chat search tool (agents, default assistant) | `tools/.../search/search_tool.py:444` → `context/search/pipeline.search_pipeline` → `search_chunks` | Each variant list reordered before weighted RRF | new `test_hybrid_retrieval_rescore.py` + `tests/unit/om/tools/test_search_utils.py` (RRF unchanged) + manual check M1 |
| Workflows (agent steps with search) | `tools/tool_constructor.py:179/443` builds the same `SearchTool` | same as above | covered by the chat-tool path; manual M3 (one gov workflow test, e.g. `test_<dept>.py`) |
| ombot (Slack / Discord) | chat flow → `SearchTool` | same | chat-tool path; `tests/external_dependency_unit/slack_bot/test_slack_bot_federated_search.py` |
| Search page (`/search/send-search-message`) | `search/api/router.py:76` → `SearchOrchestrator` → `search_chunks` → RRF → optional rerank | same | `tests/search_baseline/*` (flag off = goldens unchanged) |
| MCP server search tool | `mcp_server/tools/search.py:124` → HTTP `/search/send-search-message` | same as search page | search-page path; manual M2 |
| Federated (Slack) | `search_runner.combine_retrieval_results` merges federated chunks with ours **by raw score** | Our scores may now reach up to 2.0 vs federated ≤1 → federated could be crowded out | new test in `test_hybrid_retrieval_rescore.py` documenting the mix; Q3 |
| Admin search / document explorer | `search/admin/service.py:49/54` (`keyword_retrieval`, `random_retrieval`) | **Unchanged** (not rescored) | assertion test: keyword/random results identical with flag on |
| Cross-encoder rerank (`RERANK_ENABLED`, `cortex_rerank`) | `context/search/rerank.py`, applied after RRF in tool and orchestrator | Reorders top `RERANK_TOP_N`=20 purely by relevance. Boost/recency decide **which** chunks enter the head, not the order inside it | documented; Q1 |
| LLM section selection, `RERANK_PROTECT_TOP_K` | after rerank | unchanged | — |
| Indexing / `update()` / feedback sync | write path | unchanged | existing `tests/external_dependency_unit/opensearch/*` |

No absolute score thresholds exist in `om/` (grepped), so the score-scale change only affects the federated merge.

**Intended behaviour changes (flag on):** stale docs drop slightly (≥0.75x); `boost` −3 → ~0.77x, +3 → ~1.46x, +10 → ~1.93x; result order differs from today's goldens.

## 7. Tests (Phase B)
- `backend/tests/unit/om/document_index/opensearch/test_hybrid_rescore.py`: boost curve (0→1.0, ±values, bounds 0.5/2.0, monotonic); recency (age 0→1.0, floor, missing date→90d, future date, decay 0); z-score shift; stable ties; `score=None`; sub-toggles.
- `.../opensearch/test_hybrid_retrieval_rescore.py` (mock `OpenSearchClient.search`): flag off → identical body (`size` unchanged) and order; flag on → `size` = over-fetched, result truncated, boosted doc promoted, old doc demoted; IndexPair delegates; keyword/random untouched; federated-merge behaviour pinned.
- `tests/search_baseline`: flag off → all goldens pass unchanged; flag on → separate goldens `baselines/opensearch/hybrid_rescore/` (corpus already has dated docs), plus one boosted-doc case.
- Gates: naming grep; `pytest backend/tests/unit/migration_safety` (do **not** edit `snapshots/baseline.json`; if the new module trips the snapshot, stop and ask); compileall + import check; `build_inventory.py --check` left for commit time (it rewrites files).

## 8. Files and ownership
- **Exclusive to this lane:** `backend/om/document_index/opensearch/` (+ its tests).
- **Shared hot file:** `om/configs/app_configs.py`, `# --- recency-boost ---` block only.
- **Not touched:** `tools/tool_implementations/search/`, `om/prompts/` (lane L2), `context/search/rerank.py`, `migration_safety/snapshots/baseline.json`, Alembic, Docker volumes.
- **Only if Q2 approved (B8):** the three minimal touch points in §4.

## 9. Metric hook (L4) and rollout
- Measure **against the baseline alone**: same eval set and model, `RERANK_ENABLED` and query expansion fixed, only `OPENSEARCH_HYBRID_RESCORE_ENABLED` flipped (then each sub-toggle alone). Never measure together with other lanes' changes.
- Metrics that should move:
  - recall@k / nDCG@k on **time-sensitive questions** (where the newer of two conflicting docs is the gold) — should rise;
  - after seeding boosts (+/−) on gold/distractor docs, **MRR of gold doc** should rise;
  - overall recall@k / nDCG on time-neutral questions — must not drop beyond noise (guard metric);
  - p95 retrieval latency — expect a small rise from over-fetch.
- Default stays `false` until L4 shows a win; then the user flips the env var (no rebuild needed beyond restart).
- User checks (flag on, after Docker rebuild): **M1** chat question where two docs disagree and the newer one should win; **M2** same query via MCP search tool; **M3** boost a doc in Admin → Document feedback, wait for sync, confirm it rises; then flip the flag off and confirm the old order returns.

## 9a. Post-implementation cross-verification (after Phase B)
Goal: prove our clean-room code reproduces the reference semantics (old Vespa rank expression, commit `16c7781b0`, see §2). In `test_hybrid_rescore_reference_parity.py`, transcribe the reference expression **independently** as a test oracle (written from §2, not imported from our module). Compare it with ours on a fixed `now`, `abs_tol=1e-6`.

**Feedback boost** (reference: `b<0 → 0.5+1/(1+e^(−b/3))`, else `2/(1+e^(−b/3))`):

| boost | −10 | −3 | −2 | 0 | +2 | +3 | +10 |
|---|---|---|---|---|---|---|---|
| expected | 0.53445 | 0.76894 | 0.83924 | 1.00000 | 1.32151 | 1.46212 | 1.93111 |

**Freshness** (reference: `max(1/(1+decay·age_years), 0.75)`, decay = 0.5 × multiplier, age = days/365):

| multiplier \ age (days) | 0 | 30 | 365 | 3650 |
|---|---|---|---|---|
| 0 (NO_DECAY) | 1.00000 | 1.00000 | 1.00000 | 1.00000 |
| 1 (default) | 1.00000 | 0.96053 | 0.75000 (floor) | 0.75000 |
| 2 (FAVOR_RECENT) | 1.00000 | 0.92405 | 0.75000 | 0.75000 |

- **Missing `updated_at`:** reference 0.88881 (7_890_000 s) vs ours 0.89024 (90 days). This is a **known, accepted delta** of 0.0014. The test asserts ours = 0.89024 and documents the reference value.
- **Edge cases:** future `updated_at` → 1.0 (reference: `max(...,0)`), floor override 0.5 → 365 d gives 0.66667.
- **Combined:** base 0.8, boost +2, 30 d, multiplier 1 → 0.8 × 1.32151 × 0.96053 = 1.01548.
- **Ordering test:** 4 chunks with base scores [0.90, 0.85, 0.80, 0.70], (boost, age_d) = [(−2, 3650), (0, 365), (+2, 30), (0, 0)]. Reference products are 0.56649, 0.63750, 1.01548, 0.70, so the expected order is **C, D, B, A**. Assert the order and scores of `rescore_hybrid_chunks` equal the oracle's. With every toggle off, the order stays A, B, C, D.
- **Through the index:** the same 4 chunks returned from a mocked `OpenSearchClient.search` via `OpenSearchDocumentIndex.hybrid_retrieval` (flag on) → same order; flag off → original order and the original `size`.
- **How to run:** `cd backend && python -m pytest tests/unit/om/document_index/opensearch/test_hybrid_rescore_reference_parity.py -q` (local Windows), then the same inside the `background` container after the rebuild. Optional live check: `tests/search_baseline` with `OPENSEARCH_HYBRID_RESCORE_ENABLED=true`, compared against the `hybrid_rescore/` goldens.
- **Record:** tick tracker steps V1–V3 with the date, pass count, and any delta beyond the known missing-date one.

## 10. Open questions
1. **Q1 Rerank interplay:** keep v1 as "boost/recency pick the head, cross-encoder orders it", or also multiply cross-encoder scores by the same factors (needs a touch in `context/search/rerank.py`, outside the lane)?
2. **Q2 Per-agent recency:** do B8 (wire `RecencyBiasSetting` via three shared touch points), or keep the global multiplier only?
3. **Q3 Federated mix:** accept the score-scale shift (as Vespa had), or renormalize adjusted scores to [0,1] before returning (loses absolute meaning, protects federated)?
4. **Q4 Web feedback:** web chat thumbs don't change doc boost today (only Slack buttons and the admin page do). Wire it in a separate lane, or leave as is?
5. **Q5 Env naming:** proposed `OPENSEARCH_HYBRID_RESCORE_*` / `OPENSEARCH_RESCORE_*` (matches the existing `OPENSEARCH_*_ENABLED` family; see the naming table). OK, or do you want `OM_*` per the §1.5 template?
6. **Q6 Default:** ship `false` (recommended) or `true` with Vespa parity values?

### Decided 2026-10-30 (user-approved answers)
1. **Default (Q6):** ship `OPENSEARCH_HYBRID_RESCORE_ENABLED` default **OFF**; turn on after L4 metrics.
2. **Rerank (Q1):** YES — also apply the boost/freshness factors after the cross-encoder rerank (minimal touch in `context/search/rerank.py`, no-op while the switch is off).
3. **Per-agent recency (Q2):** YES — B8 via the minimal touches (`interfaces_new.py`, `search_runner.py`, `pipeline.py`; plus the matching signature in `disabled.py` / `OpenSearchIndexPair`), clearly commented (`# --- hybrid-rescore (lane L3) ---`).
4. **Federated (Q3):** renormalize so our rescored scores cannot crowd federated results out (batch rescaled so its max equals the original max base score; order unchanged).
5. **Web chat thumbs (Q4):** NOT in this lane (later).
6. **Env naming (Q5):** `OPENSEARCH_HYBRID_RESCORE_ENABLED` / `OPENSEARCH_RESCORE_*` approved.
7. **Undated docs:** match the reference formula exactly (7_890_000 s → 0.88881), **not** our 90-day constant. (Supersedes the §9a "known delta" note.)
- Config block name: `# --- hybrid-rescore ---` (per the lane brief; supersedes `# --- recency-boost ---` above).

## 11. Progress tracker
- [x] 2026-10-30 Research: Vespa semantics from git history, upstream HEAD check, our mapping/fields, callers, RRF/rerank/federated interplay, boost write paths
- [x] 2026-10-30 Plan doc written (this file)
- [x] 2026-10-30 User approval + answers to Q1–Q6 (+ undated-doc rule), see "Decided 2026-10-30"
- [x] 2026-10-30 B1 Config block `# --- hybrid-rescore ---` in `app_configs.py` (5 env vars, defaults per §5)
- [x] 2026-10-30 B2 `opensearch/hybrid_rescore.py` + unit tests (`test_hybrid_rescore.py`, 34 passed). Negative-score shift is applied whenever a batch has a negative score (z-score or cross-encoder logits), not keyed on the pipeline enum
- [x] 2026-10-30 B3 Wire into `OpenSearchDocumentIndex.hybrid_retrieval` (over-fetch, rescore, truncate, negative-score shift, federated-safe rescale) + mock-client tests (`test_hybrid_retrieval_rescore.py`, incl. flag-off byte-identical body+output); Q1 rerank touch in `context/search/rerank.py` (`rescore_cross_encoder_scores`, no-op when off) tested there too
- [x] 2026-10-30 B4 Admin keyword/random untouched test (flag on+off); federated-merge test (0.95 federated hit stays first)
- [x] 2026-10-30 B5 `opensearch/README.md`: new subsection "How it is implemented (`hybrid_rescore.py`)"; the two boost/age `TODO(andrei)` lines in `search.py` replaced by a NOTE
- [~] 2026-10-30 B6 `tests/search_baseline`: flag-off goldens untouched (no code path change when off; byte-identical unit test); flag-on test file `test_opensearch_hybrid_rescore_baseline.py` added (clock frozen at 2026-02-01 so goldens don't drift — the corpus RECENT_DATE 2026-01-15 is already past the ~243-day floor today). **Goldens NOT recorded** (needs live stack + seeding into OpenSearch; not done from the lane) — tests skip until `BASELINE_MODE=record`. Boosted-doc golden case left to manual M3 (would mutate the shared index)
- [x] 2026-10-30 B7 Gates: naming grep 0; compileall + imports OK; `migration_safety/test_golden_snapshot` trips ONLY on the new module `<root>.document_index.opensearch.hybrid_rescore` (expected; `baseline.json` not edited — integrator regenerates). Pre-existing unrelated failures (same on clean HEAD): `tools/test_tool_runner_chat_files.py`, `tools/test_tool_utils.py`, `websearch/test_websearch_utils.py`; collection errors from missing `mcp` pkg / cp1252 decode
- [x] 2026-10-30 B8 per-agent `RecencyBiasSetting` plumbing: `interfaces_new.py` + `disabled.py` + `OpenSearchIndexPair` signature (`recency_bias_multiplier: float = 1.0`), `search_runner._embed_and_search` passes it, `pipeline.search_pipeline` folds `recency_bias_multiplier_for_setting(agent.recency_bias)` in. Cross-encoder rerank path uses the global decay (agent not available there)
- [x] 2026-10-30 V1 Cross-verification: `test_hybrid_rescore_reference_parity.py` **28 passed** locally (boost + freshness tables, combined 1.01548, edge cases). Undated docs now **match the reference exactly** (0.88881, decision 7), so there is no missing-date delta. Scratch `d:/tmp/upgrade-xverify/hybrid-rescore/xverify.py`: independent oracle vs ours on a 341-point grid (boost -50..50; multiplier 0/0.5/1/2/3 x 12 ages incl. future/missing x floors 0/0.5/0.75/1) -> max abs diff **0.0**; every §9a table value reproduced
- [x] 2026-10-30 V2 Cross-verification: ordering C, D, B, A (oracle 1.01548 / 0.70 / 0.63750 / 0.56649) through `rescore_hybrid_chunks` (raw score diff 0.0) and through mocked `hybrid_retrieval` (size 8, scores = oracle x 0.90/1.01548 because of the federated-safe rescale); flag off -> A, B, C, D, size 4, original scores
- [ ] V3 Cross-verification: parity tests re-run in the `background` container after the rebuild; record any delta
- [ ] User: Docker rebuild; checks M1–M3
- [ ] L4: baseline vs flag-on eval run; decide default
- [ ] User: review + commit (run `build_inventory.py --check` first); tick item 7 in `TODO_MD_RAG_UPGRADES_FROM_UPSTREAM.MD`
