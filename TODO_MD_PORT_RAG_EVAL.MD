# TODO — Lane L4: Our own RAG eval benchmark (RAG backlog item 15)

**Backlog:** `TODO_MD_RAG_UPGRADES_FROM_UPSTREAM.MD` item 15 (P1). It is the **gate** for items 3 (L1 tabular chunker), 14 + 6 (L2 search-scope prompts + evidence-selection model) and 7 (L3 recency/boost scoring).
**Process:** per-feature workflow, `TODO_MD_UPSTREAM_PORT_CONNECTORS_AND_FEATURES.MD` §1.5
**Status:** CODE + LOCAL TESTS DONE, offline cross-verification done (2026-10-30); live smoke (§8a.3) + baseline pending a scratch stack.

> **Resuming in a new session?** Read the "Progress tracker" (§11). Pick the first unchecked item, and tick it with the date when done.
> **Merge rule for this batch:** L1, L2 and L3 must not merge until §11 "Baseline run captured" is ticked.

---

## 1. Scope
- **What users get:** before/after numbers for every search change, per language (Telugu, Hindi, English), on a fixed synthetic gov-department corpus. No product behaviour changes.
- **Metrics:**

| Group | Metric | Needs an LLM? |
|---|---|---|
| Retrieval (doc level, chunk hits de-duplicated in rank order) | Recall@5, Recall@10, MRR, nDCG@10 (binary relevance), hit-rate@5 | No |
| Answer | Completeness (judge: fraction of `expected_facts` covered) | Answer LLM + judge |
| Answer | Exact-figure correctness (deterministic number match, see §5) | Answer LLM only |
| Answer | Faithfulness (judge: share of answer claims supported by the gold source text) | Answer LLM + judge |
| Cost/speed | p50/p95 search latency (search endpoint), p50/p95 chat latency | No / yes |
| Index | Chunk count per doc (min/median/max, by doc type), total chunks, index store size | No |

  Every metric is reported overall, **by language**, and by doc type (PDF / XLSX+CSV / DOCX) and question category.
- **Source (REFERENCE ONLY: no code, file, function or config names are taken over; see §5a for our names):**
  - `UP:om/evals/`: same as ours apart from renames and default-model bumps. **Nothing to port.**
  - `UP:scripts/benchmark_csv_retrieval.py`: search-endpoint benchmark, matches the expected file by `semantic_identifier`. Idea reused.
  - `UP:scripts/run_csv_benchmark_cycle.py`: upload a zip, then file connector, wait for indexing, benchmark, tear down. Reused as our scratch-corpus setup cycle.
  - `UP:scripts/run_enterpriserag_bench_questions.py`: search-only plus chat modes, retry/backoff on 429/5xx. Pattern reused.
  - `UP:tests/evals/connector_filter_eval/`: scope-filter regression eval. **Belongs to lane L2**, not here; listed so L2 doesn't rebuild it.
- **Target (our tree, all new):**
  - `backend/om/evals/rag_benchmark/`: `models.py`, `benchmark.py`, `benchmark_cli.py`, `api_client.py`, `corpus_setup.py`, `retrieval_metrics.py`, `figure_match.py`, `answer_judge.py`, `index_stats.py`, `delta_report.py`, `__init__.py` (names and reasons in §5a)
  - `backend/tests/rag_benchmark/`: dataset + generator (§5), plus the tool's unit tests under `backend/tests/unit/om/evals/rag_benchmark/`
  - `docs/rag-eval/README.md` (how to run), `docs/rag-eval/results/` (run outputs)
- **Dropped:** nothing enterprise. Braintrust is **optional**; local JSON always works.
- **Depends on:** nothing. pdfium (item 1) should be merged or excluded consistently (see §10 Q5).

## 2. DB migration
None. The tool only calls existing HTTP APIs. No Alembic revision; the `0001_*` head is unchanged.

## 3. Model mapping
- **APIs used (all exist; `Authorization: Bearer <admin API key>`, resolved in `om/auth/users.py` via `om/db/api_key.py`):**

| Purpose | Endpoint | Code |
|---|---|---|
| Pure retrieval (no LLM) | `POST /api/search/send-search-message` with `stream=false`, `run_query_expansion=false`, `num_hits=50` → `search_docs[]` (`document_id`, `semantic_identifier`, `score`, `chunk_ind`) | `om/search/api/router.py`, `om/search/api/schemas.py`, `om/context/search/models.py:240` |
| Product-path retrieval | same endpoint, expansion + LLM selection as configured → also `llm_selected_doc_ids` | same |
| Answer + retrieved docs | `POST /api/converse/send-chat-message` with `stream=false`, `chat_session_info`, `llm_override`, `forced_tool_id` → `ChatFullResponse.answer`, `top_documents`, `citation_info`, `tool_calls` | `om/server/query_and_chat/chat_backend.py:499`, `om/chat/models.py:74`, `om/server/query_and_chat/models.py:86` |
| SearchTool id (for `forced_tool_id`) | `GET /api/tool` | `om/server/features/tool/api.py` |
| Search settings for the run (raw mode needs LLM selection off) | `GET/PUT /api/search/expansion-settings` | `om/search/api/router.py` |
| Chunks per doc | `GET /api/document/document-size-info?document_id=` → `num_chunks`, `num_tokens` | `om/server/documents/document.py:29` |
| Doc ids of the scratch cc-pair | `GET /api/nexus/admin/cc-pair/{id}/get-docs-sync-status` | `om/server/documents/cc_pair.py:476` |
| Scratch corpus setup | `POST /api/nexus/admin/connector/file/upload`, `POST /api/nexus/admin/connector`, credential + cc-pair, `POST /api/nexus/admin/document-set`, poll `GET /api/nexus/admin/cc-pair/{id}` | `om/server/documents/connector.py:574,1434`, `om/server/features/document_set/api.py:32`; request shapes as in `tests/integration/common_utils/managers/{file,connector,cc_pair,document_set}.py` |
| Index store size (optional, scratch stack only) | OpenSearch `_cat/indices` on the scratch stack's port | `om/document_index/opensearch/client.py` (`list_indices_with_info`) |

- **Retrieval is cheap without the LLM:** `run_query_expansion=false` plus `enable_llm_section_selection=false` (set via expansion-settings on the scratch stack) gives embedding + hybrid search only, with no LLM calls. That is the default `--mode retrieval`. `--mode product` keeps the stack's expansion/selection settings, so L2's evidence-selection model is exercised. `--mode answer` runs chat.
- **Env vars** (in `om/configs/app_configs.py` inside a `# --- rag-eval ---` block, read only by the CLI): `RAG_BENCHMARK_API_BASE`, `RAG_BENCHMARK_API_KEY` (falls back to the existing `OM_EVAL_API_KEY`), `RAG_BENCHMARK_JUDGE_MODEL` (default `gpt-4.1`), `RAG_BENCHMARK_JUDGE_API_KEY`. Existing `BRAINTRUST_*` vars are reused as they are.
- **Result JSON** (`docs/rag-eval/results/<YYYY-MM-DD>_<run>.json`): `run` (label, git sha, branch, lane list, mode), `env` (search settings: embedding model + dim, rerank flags, expansion settings; answer model, judge model + prompt hash, dataset version + sha256), `index` (chunks per doc, totals, store size), `per_question[]` (ranked doc names + scores, ranks of gold docs, answer, figure hits, judge verdicts, latencies), `aggregates` (overall / by language / by doc type / by category).
- No OpenSearch fields, Celery tasks or Redis keys change. A re-index is needed only for runs of lane L1 (fresh stack per run, §9).

## 4. UI
None. The output is JSON plus a markdown delta table.

## 5. Design: dataset, reuse, new code
**Dataset: `backend/tests/rag_benchmark/datasets/gov_v1/`** (versioned; any change bumps it to `gov_v2`, and results from different versions are never compared):
- `corpus/`: about 45 files (target about 5 MB):
  - 9 departments (the ones in `gtm-government/departments/*.md`) × 4 docs:
    - **PDF**: GO/circular, 2–4 pages
    - **XLSX**: register with one **large sheet** (about 2,000 rows) + one small sheet + a Readme sheet, to exercise L1
    - **CSV**: case/beneficiary list
    - **DOCX**: SOP
  - **Telugu** PDF + DOCX for 4 departments and **Hindi** PDF + DOCX for 3, translated versions with the same figures.
  - About 8 **distractors**: the previous year's version of a GO with different figures and an older `doc_updated_at`, to exercise L3 recency; a few carry a `boost`.
- `manifest.json`: per file: `sha256`, `lang`, `doc_type`, `department`, `doc_updated_at`, `boost`. Dates go into the zip's `.om_metadata.json` (`OM_METADATA_FILENAME`, `om/configs/constants.py:52`).
- `questions.jsonl`: **150 questions**:
  - by language: 60 English, 45 Telugu, 45 Hindi (of the non-English ones, 15 are cross-lingual, e.g. a Telugu question over an English doc);
  - by doc type: about 40 PDF, 60 XLSX/CSV (20 of them aggregates such as "total by district" or "how many rows", the L1 target), 30 DOCX, 20 multi-doc / multi-part (the L2 target);
  - 10 recency questions where the newest GO is the right one (the L3 target).
  - Fields: `id`, `lang`, `question`, `category` (`lookup|aggregate|multi_part|recency|cross_lingual`), `doc_type`, `gold_docs` (file names, matched case-insensitively against `semantic_identifier`, which survives re-indexing; internal ids don't), `expected_figures` (`[{value, unit, tolerance}]`), `expected_facts` (short strings for the completeness judge).
- **Source material:** reuse the fictitious entities, IDs and column schemas from `backend/tests/workflow_creator/gen_*_testdata.py` and `test_data/<dept>/*.csv`. They are English-only, small CSVs, all mock, so they are a seed for content, not the corpus itself. The domain context comes from the `gtm-government/departments/*.md` briefs.
- **Generator: `backend/tests/rag_benchmark/gen_gov_rag_corpus.py`** (deterministic, fixed seed). It writes XLSX (openpyxl), CSV and DOCX (python-docx); all of these are already dependencies. PDFs are produced **once** from the DOCX through LibreOffice/Word export with Noto Telugu/Devanagari fonts, so Indic shaping is correct, and committed as binaries (§10 Q2). A generator self-check extracts every file with our own `extract_file_text` and asserts that each `expected_figure` appears in the text, so the gold answers can't be wrong.
- **PUBLIC repo:** all names, IDs, survey numbers and amounts are fictitious, matching the existing mock-data convention. No real citizen data, no real GO numbers. Run the naming grep on the generated text too.

**Reused, unchanged:**
- `om/evals/providers/braintrust.py` settings and the `BRAINTRUST_*` config, for the optional `--braintrust` upload of per-question rows.
- The `om/evals/eval_cli.py` conventions: logging setup and `OM_EVAL_API_KEY`.
- `om/evals/models.py::EvalTimings`.
- `tests/search_baseline/` stays as the **deterministic ranking-order gate**. It seeds pre-built chunks, which bypasses the chunker, so it can't measure L1. L3 will legitimately re-record its goldens.
- The existing tool-assertion eval (`om/evals/eval.py`, the `/api/evals/eval_run` Celery path) is untouched. It is in-process (rollback session) and measures tool choice, not retrieval quality.

**New:**
- `api_client.py` (`RagBenchmarkApiClient`): a small `requests` client for the §3 endpoints, with retry/backoff on 429/5xx (a common pattern, also seen in the upstream scripts) and a per-call wall-clock timer.
- `retrieval_metrics.py`: pure functions for recall@k, MRR, nDCG@k, hit-rate, p50/p95, plus a paired **bootstrap 95% CI** on every before/after delta (1,000 resamples, fixed seed). A delta whose CI crosses 0 is shown as "≈".
- `figure_match.py` (`match_expected_figures`): number normalisation:
  - Indian digit grouping (1,23,456);
  - lakh/crore and ₹/Rs;
  - Telugu (౦–౯) and Devanagari (०–९) digits;
  - percentages and dates.
  
  A figure counts as correct if a normalised number in the answer is within `tolerance`.
- `answer_judge.py` (`judge_answer`): one JSON-mode call per question. Temperature 0, fixed prompt (its hash is recorded); the inputs are the question, `expected_facts`, the gold source text (extracted locally from the corpus) and the answer. Output: `facts_covered[]` and `unsupported_claims[]`. It uses `litellm`, which is already a dependency, so the judge doesn't depend on the stack under test.
- `index_stats.py`: chunks per doc via `document-size-info`, store size via `_cat/indices` (optional).
- `delta_report.py` (`build_delta_report`): `compare A.json B.json [C.json…]` → markdown tables (one row per metric; columns overall / te / hi / en; Δ and CI), written next to the JSON as `<date>_<run>_vs_<baseline>.md`. It refuses to compare if the dataset sha, embedding model, answer model or judge model differ.
- `corpus_setup.py` (`setup_scratch_corpus`) and `benchmark.py` (`run_rag_benchmark`, the runner, the counterpart of `eval.py::run_eval`).
- `benchmark_cli.py` (the counterpart of `eval_cli.py`):
  - `python -m om.evals.rag_benchmark.benchmark_cli setup` (zip upload → file connector → document set `rag-benchmark-gov_v1` → wait until indexed → record doc ids);
  - `run --label <run> --mode retrieval|product|answer|all`;
  - `compare`.
  
  It runs from the host (Windows python) or any container. Requests are sequential (concurrency 1) with 3 warm-up queries excluded, so latency isn't distorted by the single-process request queueing seen in the 2026-10-29 perf work.

**Environment (never touches existing volumes or DBs):**
- **Default:** a **scratch stack**, e.g. `docker compose -p rageval-<run>`, with new named volumes, different host ports, and none of the live bind-mounts. One fresh stack per run, so index size is only the eval corpus and L1's re-index is automatic.
- Configure it with the same env file as dev (same embedding model), one LLM provider, and an admin API key.
- Scratch volumes are left in place; the user removes them.
- **Fallback (§10 Q1):** a new file connector + document set on the dev stack, with search scoped by `filters.document_set`. Index size can't be isolated in this mode, and it adds rows to the dev DB.
- In answer mode **no `internal_search_filters` are sent** on the scratch stack, so L2's "don't narrow scope" change is measured honestly. `forced_tool_id` = SearchTool by default (`--no-force-search` to let the model choose).

**Runs (same corpus, questions, answer LLM, judge every time):**
1. `baseline`: current `main_multi_agent_stable`.
2. `l1`, `l2`, `l3`: baseline + that one lane only, each on its own fresh stack (L1 needs the re-index; L3 needs the distractor dates).
3. `combined`: after integration.

Estimated cost: retrieval mode costs embeddings only. Answer mode is 150 chat turns + 150 judge calls per run, about $1–3 with mini answer + gpt-4.1 judge (§10 Q3).

## 5a. Naming & structure (ours)
Upstream benchmark/eval code is **reference only**. Every folder, file, class, function, config and CLI name below is our own. They follow the existing `om/evals/` layout: flat modules, a runner module + `*_cli.py` pair like `eval.py` / `eval_cli.py`, and a shared `models.py`.

| Reference concept | Our name | Why |
|---|---|---|
| Benchmark package | `backend/om/evals/rag_benchmark/` | A sibling of the existing tool-assertion eval in `om/evals/`. "benchmark" separates scored retrieval/answer runs from the existing pass/fail eval. |
| Benchmark runner script | `benchmark.py` → `run_rag_benchmark(...)` | Mirrors `eval.py::run_eval`. |
| CLI entry | `benchmark_cli.py`, subcommands `setup` / `run` / `compare` | Mirrors `eval_cli.py`. One entry point instead of several scripts. |
| Result/dataset schemas | `models.py`: `RagBenchmarkQuestion`, `ExpectedFigure`, `QuestionResult`, `RagBenchmarkRun`, `MetricAggregate` | Same file name and pydantic style as `om/evals/models.py`. |
| Login + HTTP calls | `api_client.py` → `RagBenchmarkApiClient` (API key, not email/password) | Our auth is the admin API key (`OM_EVAL_API_KEY` convention). |
| Upload-zip / connector / wait cycle | `corpus_setup.py` → `setup_scratch_corpus(...)` | Says what it does: builds the scratch corpus. |
| Recall / rank computation | `retrieval_metrics.py` → `recall_at_k`, `reciprocal_rank`, `ndcg_at_k`, `hit_at_k`, `percentile`, `bootstrap_delta_ci` | Pure functions named after the textbook metric. |
| Figure check | `figure_match.py` → `normalize_number`, `match_expected_figures` | Covers Indian/Indic number forms (ours, not in any reference). |
| LLM judge | `answer_judge.py` → `judge_answer` → `JudgeVerdict` | Judges answers only; the name avoids clashing with retrieval scoring. |
| Chunk / index stats | `index_stats.py` → `collect_index_stats` | Measures L1's effect. |
| Before/after report | `delta_report.py` → `build_delta_report` | The output is a delta table. |
| Question CSV | `datasets/gov_v1/questions.jsonl` + `manifest.json` | Versioned folder; JSONL allows nested gold/figure fields. |
| Corpus generator | `backend/tests/rag_benchmark/gen_gov_rag_corpus.py` | Matches the existing `gen_<dept>_testdata.py` naming in `tests/workflow_creator/`. |
| Config | `RAG_BENCHMARK_API_BASE`, `RAG_BENCHMARK_API_KEY`, `RAG_BENCHMARK_JUDGE_MODEL`, `RAG_BENCHMARK_JUDGE_API_KEY` in the `# --- rag-eval ---` block | Prefixed by the feature; `OM_EVAL_API_KEY` and `BRAINTRUST_*` are reused rather than duplicated. |
| Scratch document set | `rag-benchmark-gov_v1` | Ties the index contents to the dataset version. |
| Run outputs | `docs/rag-eval/results/<date>_<run>.json` / `.md` | The path the user asked for. |

## 6. Existing features touched (regression scope)
| Area | Change | Covered by |
|---|---|---|
| `om/configs/app_configs.py` | New `# --- rag-eval ---` block (4 env reads, no defaults that affect the server) | import check + `migration_safety` |
| `om/evals/` existing tool eval, Celery `eval_run_task`, `/api/evals/eval_run` | **None.** New subpackage `om/evals/rag_benchmark/` only | existing behaviour unchanged; import check of `om.evals.eval`, `om.evals.eval_cli` |
| Search / chat / connector APIs | Read and call only, no code change | n/a |
| Scratch stack `expansion-settings` | The tool sets LLM selection off for retrieval mode **on the scratch stack only**, then restores the recorded values | `test_benchmark_cli.py::test_restores_expansion_settings` (mocked) |

- **Not touched:** `tests/unit/migration_safety/snapshots/baseline.json`. The new `om.evals.rag.*` modules will need adding there, so the integrator regenerates it.
- **New dependencies:** none (`requests`, `litellm`, `openpyxl`, `python-docx`, `braintrust` are all already in `backend/requirements/default.txt`). LibreOffice/Word is a one-off author-side tool for the PDFs, not a dependency.

## 7. Tests (for the eval tool itself)
| File | What it covers |
|---|---|
| `tests/unit/om/evals/rag_benchmark/test_retrieval_metrics.py` | recall/MRR/nDCG/hit-rate on hand-computed rankings (ties, no gold found, multi-gold), dedupe of chunk hits to docs, p50/p95, bootstrap CI determinism |
| `tests/unit/om/evals/rag_benchmark/test_figure_match.py` | Indian grouping, lakh/crore, ₹, Telugu/Devanagari digits, tolerance, no false match on IDs like `TS-HYD-0042` |
| `tests/unit/om/evals/rag_benchmark/test_gov_dataset.py` | `questions.jsonl` schema; every `gold_docs` file exists in `manifest.json`; sha256s match; language/type quotas; no upstream names; each expected figure appears in our extracted text (generator self-check) |
| `tests/unit/om/evals/rag_benchmark/test_delta_report.py` | Result JSON round-trip; delta table golden; refuses mismatched dataset/model; language split |
| `tests/unit/om/evals/rag_benchmark/test_api_client.py` + `test_benchmark_cli.py` | Mocked HTTP: search/chat response parsing (`search_docs`, `top_documents`), retry on 429/5xx, settings restore, judge JSON parsing with a fake `litellm` |

- No live-stack test in CI. The baseline run is the integration check.

## 8. Gates
- [x] 2026-10-30 Naming grep over new files **and** generated corpus text/binaries.
- [x] 2026-10-30 `pytest backend/tests/unit/om/evals/rag_benchmark` and `backend/tests/unit/migration_safety` (the snapshot mismatch for the new modules is expected; the integrator regenerates it).
- [x] 2026-10-30 Import check + `compileall` of `om/evals`.
- [ ] `python -I rename-audit/build_inventory.py --check`: at commit time only (it rewrites the reports).
- [ ] Web `tsc`: not needed.

## 8a. Post-implementation cross-verification (after Phase B, before the baseline counts)
The goal is to prove the tool itself is correct before trusting any lane delta. Record each result (date, pass/fail, notes) in §11.
1. **Metric functions against hand-computed / textbook values**, as fixed cases in `test_retrieval_metrics.py`:
   - Ranking `[d3, d1, d7, d2, d9]` with gold `{d1, d2}`:
     - Recall@3 = 0.5; Recall@5 = 1.0
     - MRR = 1/2 = 0.5
     - hit@1 = 0, hit@5 = 1
     - nDCG@5 = (1/log2(3) + 1/log2(5)) / (1 + 1/log2(3)) = (0.6309 + 0.4307) / 1.6309 ≈ **0.6509**
   - Gold at rank 1 only: MRR = 1, nDCG = 1.
   - No gold in the list: everything 0.
   - Duplicate chunk hits of one doc count once.
   - p50/p95 on `[1..100]` = 50.5 / 95.05 (linear interpolation, the same convention as `numpy.percentile`); cross-checked once against numpy in a scratch venv.
2. **Figure matcher known cases:**
   - `₹1,23,456`, `1.23 lakh` and `౧,౨౩,౪౫౬` match 123456.
   - `TS-HYD-0042` matches nothing.
3. **Known-answer smoke run** on the scratch stack with a 6-question mini set (2 per language), where the gold doc is the only doc containing a unique token:
   - Recall@5 must be 1.0, and every figure must be found.
   - A deliberately wrong gold file must score 0, which proves misses are counted.
   - Re-running unchanged must give identical retrieval metrics (determinism).
   - The judge must give a perfect answer full completeness, and a planted wrong figure must be flagged.
4. **Diff vs the adapted reference patterns:**
   - Run the same mini set through a throwaway local re-implementation of the upstream search-endpoint benchmark's "rank of expected file" logic (`UP:scripts/benchmark_csv_retrieval.py`). It is not committed.
   - Our `hit_at_k` / `recall_at_k` (single-gold questions) must equal its Recall@k numbers exactly.
   - Document any intended difference: multi-gold recall, doc-level dedupe, API-key auth.
5. **Report sanity:** `compare baseline baseline` gives Δ = 0 with CIs containing 0 for every metric/language.

## 9. Rollout and verification (user)
1. Review and approve this plan and the open questions (§10).
2. Review the generated corpus (spot-check the Telugu/Hindi PDFs render and extract correctly).
3. Bring up the scratch stack from current main; create an admin API key; `benchmark_cli setup`, then `benchmark_cli run --label baseline --mode all`.
4. Inspect `docs/rag-eval/results/<date>_baseline.json` + `.md`. This becomes the reference for L1/L2/L3.
5. For each lane: fresh scratch stack from the lane branch → `setup` → `run --label l<N>` → `compare baseline l<N>`. Attach the delta table to the lane's TODO doc before it merges.
6. After integration: `run --label combined` → `compare baseline l1 l2 l3 combined`.

## 10. Open questions for the user
1. **Environment:** OK to spin up a separate scratch compose project per run (new volumes, extra ports, about 15 min to index)? Or do you prefer the fallback: a scratch connector + document set on the dev stack (adds DB rows, no isolated index size)?
2. **PDF generation:** OK to commit about 15 small generated PDFs (exported once with Noto fonts)? The alternative is a new dev-only PDF library, but Indic shaping is poor without extra work.
3. **Models:** which answer model (proposal: `gpt-4.1-mini`, pinned via `llm_override`) and judge model (proposal: `gpt-4.1`)? Are about $1–3 per answer-mode run and 5 runs acceptable?
4. **Size:** are 150 questions (60 en / 45 te / 45 hi) enough, or should answer mode use 2 repeats to reduce LLM noise?
5. **pdfium (item 1)** is code-complete but unmerged. Should the baseline include it (merge first) or not? It changes PDF chunks slightly, so every run must use the same choice.
6. **Pass/fail thresholds:** should a lane be **blocked** on a regression, e.g. any language's Recall@10 dropping more than 2 points with a CI below 0? Or are the numbers informational only?
7. Should `docs/rag-eval/results/*.json` be committed (it is public; the content is synthetic) or kept local?

**Decided 2026-10-30 (user-approved):**
1. Fresh scratch stack per run; never dev volumes/DBs (the dev-stack fallback is not used).
2. Committing ~15 synthetic generated test PDFs is OK (synthetic only — repo is PUBLIC).
3. Answer model `gpt-4o-mini` (pinned via `llm_override`), judge `gpt-4.1`.
4. 150 questions OK; answer mode runs twice (2 repeats, averaged).
5. A retrieval drop beyond the CI margin **blocks** a lane; answer metrics are informational only.
6. Commit results (markdown + JSON) under `docs/rag-eval/results/`.
(Q5 pdfium is still open: decide before the baseline run; every run must use the same choice.)

## 11. Progress tracker (Phase B)
- [x] 2026-10-30 Research: existing `om/evals/`, `tests/search_baseline/`, search/chat/doc-size APIs, upstream eval + benchmark scripts, synthetic data sources
- [x] 2026-10-30 User approval of this plan + answers to §10 (recorded under §10 "Decided 2026-10-30")
- [x] 2026-10-30 `app_configs.py` config block (named `# --- rag-benchmark ---` per lane rules, not `rag-eval`)
- [x] 2026-10-30 `om/evals/rag_benchmark/` `models.py` + `retrieval_metrics.py` + `figure_match.py` (+ unit tests green: 39 passed)
- [x] 2026-10-30 Corpus generator + `manifest.json` + PDFs exported; generator self-check green (58 files / 5.4 MB: 9 depts x GO-PDF/XLSX(2,000-row register + district_targets + readme)/CSV/SOP-DOCX, te GO+SOP for land/aarogyasri/epass/collectorate, hi GO+SOP for cybercrime/cid/police, 8 distractors = 2025 GOs as DOCX; 16 PDFs exported via Word with Nirmala UI (Noto not installed); te/hi docs = translated core + language-only district annex so every gold doc is unique. Finding: pypdf extraction of te/hi PDFs garbles conjuncts (digits intact), DOCX extracts cleanly)
- [x] 2026-10-30 `questions.jsonl` written (150: en60/te45/hi45; pdf40/xlsx+csv60/docx30/multi20; aggregate20/recency10/cross-lingual15; generated by the generator, aggregates carry `aggregate_check`); `test_gov_dataset.py` green (16 tests)
- [x] 2026-10-30 HTTP client + scratch `setup` command (+ mocked tests: `test_api_client.py`, 18 tests). Setup uses `connector-with-mock-credential`; doc ids mapped via `FILE_CONNECTOR__<file id>`; zip metadata carries only `doc_updated_at` (custom tags would leak into chunk text); boosts via `/nexus/admin/doc-boosts`
- [x] 2026-10-30 Judge + answer mode (+ mocked tests in `test_benchmark_cli.py`); plus `--dry-run` offline backend (deterministic BM25 over the local corpus) for stack-free verification
- [x] 2026-10-30 Report/compare + markdown delta table (+ golden test, `test_delta_report.py`); retrieval gate per decision 5 (BLOCK if a retrieval Recall@5/10, MRR or nDCG@10 drops >= 0.02 with CI fully < 0, overall or any language; `compare` exit code 2)
- [x] 2026-10-30 `docs/rag-eval/README.md` (+ `docs/rag-eval/results/README.md`)
- [x] 2026-10-30 Gates (§8): naming grep 0 hits over new files + dataset text/binaries (also a unit test); `pytest tests/unit/om/evals/rag_benchmark` 106 passed; `migration_safety` 140 passed / 1 expected fail (golden snapshot: only the 11 new `om.evals.rag_benchmark.*` modules added - integrator regenerates); import check `om.evals.eval`/`eval_cli` + compileall OK; mypy clean on new code. `build_inventory.py --check` left for commit time
- [x] 2026-10-30 Cross-verify §8a.1 metric functions vs hand-computed values (result: PASS - recall@3/5 0.5/1.0, MRR 0.5, hit@1/5 0/1, nDCG@5 0.6509, gold@1 = 1, no-gold = 0, dedupe; p50/p95 on 1..100 = 50.5/95.05 and identical to numpy.percentile on 200 random samples; fixed cases live in `test_retrieval_metrics.py`)
- [x] 2026-10-30 Cross-verify §8a.2 figure matcher known cases (result: PASS - `₹1,23,456`, `1.23 lakh`, `౧,౨౩,౪౫౬` match 123456; `TS-HYD-0042` matches nothing; also in `test_figure_match.py`)
- [ ] Cross-verify §8a.3 known-answer smoke run on scratch stack (result 2026-10-30: OFFLINE part PASS via the `--dry-run` backend on gov_v1 + 6 unique-token docs (2 per language): Recall@5 = 1.0, all figures found, a deliberately wrong gold scores 0 on every metric, a rerun gives identical retrieval metrics, a planted wrong figure is flagged by the matcher. PENDING on the scratch stack: the same mini set live + the judge full-completeness / wrong-figure check with the real gpt-4.1 judge)
- [x] 2026-10-30 Cross-verify §8a.4 diff vs adapted upstream reference pattern (result: PASS - a throwaway re-implementation of the reference "rank of expected file" logic (not committed) equals our `hit_at_k`/`recall_at_k` exactly on all 130 single-gold questions x k=1/3/5/10 (rankings from the offline backend). Intended differences: doc-level dedupe of chunk hits (the reference counts raw chunk positions, so 5 duplicate chunks push gold out of @5 while ours keeps it at rank 2), multi-gold recall, API-key auth. Optional: repeat on the live mini set)
- [x] 2026-10-30 Cross-verify §8a.5 `compare baseline baseline` = 0 (result: PASS - every retrieval + answer metric x overall/en/te/hi has delta 0 with CI containing 0, gate PASS; two independent full dry runs compared via the CLI: all deltas `≈ +0.000`, exit 0). Scratch scripts: `d:\tmp\upgrade-xverify\rag-benchmark\xverify.py`
- [ ] User: scratch stack up from current main
- [ ] **Baseline run captured** (`docs/rag-eval/results/<date>_baseline.json` + `.md`), which unblocks L1/L2/L3 merges
- [ ] Lane run L1 (tabular chunker, re-index) + delta table
- [ ] Lane run L2 (search-scope prompts + evidence-selection model) + delta table
- [ ] Lane run L3 (recency/boost) + delta table
- [ ] Combined run after integration + final delta table
- [ ] User: review + commit (run `build_inventory.py --check` first)
- [ ] Tick item 15 in `TODO_MD_RAG_UPGRADES_FROM_UPSTREAM.MD` as DONE
