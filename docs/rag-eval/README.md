# RAG benchmark (`om/evals/rag_benchmark`)

Before/after numbers for every search change, per language (Telugu, Hindi,
English), on a fixed **synthetic** government-department corpus. It talks to a
running stack over HTTP only and changes no product behaviour.

| Piece | Where |
|---|---|
| Tool | `backend/om/evals/rag_benchmark/` (`benchmark_cli.py` is the entry point) |
| Dataset `gov_v1` | `backend/tests/rag_benchmark/datasets/gov_v1/` (`corpus/`, `manifest.json`, `questions.jsonl`) |
| Generator | `backend/tests/rag_benchmark/gen_gov_rag_corpus.py` (+ `gov_v1_content.py`) |
| Unit tests | `backend/tests/unit/om/evals/rag_benchmark/` |
| Results | `docs/rag-eval/results/<date>_<label>.json` + `.md`, deltas `<date>_<runs>_vs_<baseline>.md` |

## Dataset `gov_v1`

- 58 files (5.4 MB): 9 departments x {GO as PDF, register XLSX (2,000-row
  `register` sheet + `district_targets` + `readme`), CSV list, SOP DOCX};
  Telugu GO + SOP for 4 departments, Hindi GO + SOP for 3; 8 distractors (the
  2025 version of a GO, as DOCX, older `doc_updated_at`, different figures);
  3 docs carry a boost. Translated docs share the English core and add a
  language-only district annex, so each question has exactly one right document.
- 150 questions: 60 en / 45 te / 45 hi; 40 PDF, 60 XLSX+CSV (20 aggregates),
  30 DOCX, 20 multi-doc; 10 recency, 15 cross-lingual.
- Everything is fictitious. Any change to the corpus or questions means a new
  version (`gov_v2`); runs on different versions are never compared (`compare`
  refuses).
- Regenerate (content is deterministic; PDFs are committed binaries):
  `cd backend && python tests/rag_benchmark/gen_gov_rag_corpus.py` (add
  `--export-pdfs` to re-export the PDFs via Word/LibreOffice, `--check` for the
  self-check only).
- Known property: our PDF text extraction garbles Telugu/Devanagari conjuncts
  in the PDFs (digits survive); the DOCX versions extract cleanly. That is part
  of what the benchmark measures.

## Metrics

| Mode | What | Metrics |
|---|---|---|
| `retrieval` | search endpoint, no query expansion, LLM section selection switched **off** for the run (restored afterwards) | Recall@5/10, MRR, nDCG@10, hit@5 (doc level; chunk hits de-duplicated in rank order) |
| `product` | search endpoint with the stack's own expansion/selection settings | same + `selected_recall` (LLM-selected docs) |
| `answer` | chat (`gpt-4o-mini` pinned via `llm_override`, SearchTool forced, no scope filters), run twice and averaged | figure accuracy (deterministic number match: Indian grouping, lakh/crore, Rs, Telugu/Devanagari digits, dates), completeness + faithfulness (judge `gpt-4.1`, JSON mode, temperature 0, prompt hash recorded), chat recall@10 |
| all | latency p50/p95; chunks per doc (min/median/max by type), total chunks, optional OpenSearch store size | |

Every metric is reported overall, by language, by doc type and by category.
Deltas carry a paired bootstrap 95% CI (1,000 resamples, fixed seed); `≈`
marks a CI that crosses 0.

**Gate (decided 2026-10-30):** a lane is **blocked** when a retrieval-mode
ranking metric (Recall@5, Recall@10, MRR, nDCG@10) drops by >= 0.02 with the
whole CI below 0, overall or in any language. `compare` exits with code 2.
Answer metrics are informational.

## Running

Always against a **scratch stack**: a fresh compose project (for example
`docker compose -p rageval-<label> ...`) with new named volumes, different
host ports and none of the live bind-mounts, built from the branch under
test, configured with the dev env (same embedding model), one LLM provider and
an admin API key. Never the dev stack, its volumes or its DB. Scratch volumes
are left for the user to remove.

```bash
cd backend
export RAG_BENCHMARK_API_BASE=http://localhost:<scratch-api-port>   # or http://host:<web-port>/api
export RAG_BENCHMARK_API_KEY=<admin API key of the scratch stack>
export RAG_BENCHMARK_JUDGE_API_KEY=<OpenAI key for the judge>        # judge model: RAG_BENCHMARK_JUDGE_MODEL (gpt-4.1)

# 1. upload the corpus, wait for indexing, apply boosts (state -> ~/.rag_benchmark/)
python -m om.evals.rag_benchmark.benchmark_cli setup

# 2. run everything (retrieval + product + answer x2)
python -m om.evals.rag_benchmark.benchmark_cli run --label baseline --mode all \
    --answer-model gpt-4o-mini [--answer-provider <provider name>] \
    [--opensearch-url http://localhost:<scratch-opensearch-port> --opensearch-auth admin:<pw>]

# 3. per lane, on its own fresh scratch stack: setup, run --label l1 --lanes l1, then
python -m om.evals.rag_benchmark.benchmark_cli compare \
    ../docs/rag-eval/results/<date>_baseline.json ../docs/rag-eval/results/<date>_l1.json
```

Useful flags: `--mode retrieval` (no LLM cost), `--limit N` / `--ids en-001,te-004`
/ `--questions <mini.jsonl>`, `--no-judge`, `--no-force-search`,
`--git-sha/--branch` (when the stack was built from another checkout),
`--braintrust` (also log per-question rows; uses the existing `BRAINTRUST_*` settings).

Requests are sequential with 3 warm-up queries excluded, so latency is not
distorted by request queueing. Failed calls are recorded and scored as misses.

### Offline check (no stack, no LLM)

```bash
python -m om.evals.rag_benchmark.benchmark_cli setup --dry-run
python -m om.evals.rag_benchmark.benchmark_cli run --dry-run --label dry --results-dir /tmp/rag-dry
```

`--dry-run` swaps the stack for a deterministic in-process lexical ranker over
the local corpus. Its numbers are only a pipeline check, never a baseline.

## Not covered here

- `backend/tests/search_baseline/` stays the deterministic ranking-order gate
  (pre-built chunks; it cannot see chunker changes).
- The tool-assertion eval (`om/evals/eval.py`, `/api/evals/eval_run`) is
  unchanged and measures tool choice, not retrieval quality.
