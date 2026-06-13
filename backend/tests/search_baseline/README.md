# Search Baseline (Vespa → OpenSearch)

Deterministic retrieval baseline for the current **Vespa** search engine, so that after
migrating to **OpenSearch** we can replay the *same* searches and diff the results.

## What this tests

Retrieval-layer search via the production path
`search_chunks → _embed_and_search → DocumentIndex.hybrid_retrieval` (no LLM, deterministic):

- **Plain term queries** — relevance + ranked-order snapshot.
- **Keyword vs semantic ranking profile** — the live "rerank" knob, selected by `hybrid_alpha`
  (`≤ 0.3` → keyword profile, else semantic).
- **Filters** — `document_set` (knowledge base), `source_type`, `time_cutoff` (date), and combinations.
- **Keyword expansion** — explicit `query_keywords` (final_keywords).
- **Post-retrieval reordering layer** (`test_search_tool_layer.py`) — RRF fusion/dedup
  (`combine_retrieval_results`), deterministic chunk-window selection, an opt-in LLM
  selection test, and a guard that the removed cross-encoder rerank path stays gone.

## Files

| File | Purpose |
|------|---------|
| `corpus.py` | Fixed, themed document corpus across KBs / sources / dates. |
| `seed_search_corpus.py` | Index the corpus with **real** model-server embeddings (Vespa, or both engines). |
| `harness.py` | Engine-agnostic `run_search()` + `get_index()` → normalized `BaselineHit`s. |
| `snapshot.py` | Save/load/assert golden snapshots under `baselines/<engine>/`. |
| `test_vespa_baseline.py` | The baseline test cases. |
| `test_search_tool_layer.py` | RRF / chunk-selection / LLM-selection / cross-encoder-gone tests. |
| `compare_engines.py` | Vespa-vs-OpenSearch overlap@k + rank-correlation report. |
| `baselines/` | Golden JSON snapshots (committed). |

## Prerequisites

Dev stack running, reachable from where you run pytest: **Postgres**, **Vespa**, **model server**.
Relevant env (defaults to localhost): `VESPA_HOST`, `POSTGRES_*`, `MODEL_SERVER_HOST`/`MODEL_SERVER_PORT`.
The suite **skips itself** if Vespa or the model server are unreachable.

## Usage (from `backend/`)

```bash
# 1. Seed the corpus (real embeddings) into Vespa
python -m tests.search_baseline.seed_search_corpus

# 2. Record golden baselines the first time
BASELINE_MODE=record pytest tests/search_baseline/test_vespa_baseline.py

# 3. Assert against goldens (CI / repeat runs)
pytest tests/search_baseline/test_vespa_baseline.py

# 4. Deterministic reordering-layer tests (skip the LLM one by default)
pytest tests/search_baseline/test_search_tool_layer.py -m "not llm"

# 5. After OpenSearch migration: seed both, then compare
ENABLE_OPENSEARCH_INDEXING_FOR_ONYX=true python -m tests.search_baseline.seed_search_corpus
ENABLE_OPENSEARCH_INDEXING_FOR_ONYX=true python -m tests.search_baseline.compare_engines
```

Seeding is an idempotent upsert by document id, so re-running is safe. The `seeded_corpus`
fixture seeds once per test session automatically.
