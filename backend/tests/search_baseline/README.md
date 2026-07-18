# Search Baseline (OpenSearch)

Deterministic retrieval baseline for the **OpenSearch** document index (the only search
backend now that Vespa is removed). It replays a fixed set of searches over a fixed corpus
and diffs the ranked results against committed golden snapshots, so a ranking regression
turns a test red.

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
| `seed_search_corpus.py` | Index the corpus with **real** model-server embeddings into OpenSearch. |
| `harness.py` | `run_search()` + `get_index()` → normalized `BaselineHit`s. |
| `snapshot.py` | Save/load/assert golden snapshots under `baselines/opensearch/`. |
| `test_opensearch_baseline.py` | The baseline test cases (ranked-order goldens). |
| `test_search_tool_layer.py` | RRF / chunk-selection / LLM-selection / cross-encoder-gone tests. |
| `ingest_index_rest.py` | Two-domain ingest + retrieval sanity check (dev helper). |
| `demo_reranking_layers.py` | Layer-by-layer reranking demonstration (dev helper). |
| `baselines/opensearch/` | Golden JSON snapshots (committed). |

## Prerequisites

Dev stack running, reachable from where you run pytest: **Postgres**, **OpenSearch**, **model server**.
The suite **skips itself** if OpenSearch or the model server are unreachable (see the
`require_opensearch` fixture in `conftest.py`).

## Usage (from `backend/`)

```bash
# 1. Seed the corpus (real embeddings) into OpenSearch
python -m tests.search_baseline.seed_search_corpus

# 2. Record golden baselines the first time
BASELINE_MODE=record pytest tests/search_baseline/test_opensearch_baseline.py

# 3. Assert against goldens (CI / repeat runs)
pytest tests/search_baseline/test_opensearch_baseline.py

# 4. Deterministic reordering-layer tests (skip the LLM one by default)
pytest tests/search_baseline/test_search_tool_layer.py -m "not llm"
```

Seeding is an idempotent upsert by document id, so re-running is safe. The
`seeded_corpus_opensearch` fixture seeds once per test session automatically.
