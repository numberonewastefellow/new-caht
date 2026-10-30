# TODO — RAG Upgrades from Upstream

**Date:** 2026-10-29
**Compared against:** upstream HEAD `73e0ae3c31`
**Our fork:** `backend/om/` on `main_multi_agent_stable`
**See also:** `TODO_MD_UPSTREAM_PORT_CONNECTORS_AND_FEATURES.MD`, for connectors and features, and the naming rules.

> **Naming rules.** Never use the upstream product name in this repo. Upstream paths are written **with our names** (for example `UP:om/utils/process_isolation.py`). We have **no EE tree**: enterprise behaviour is reimplemented clean-room inside our own `backend/om/...` folders.
>
> **Process.** Port one item at a time, using the per-feature workflow in `TODO_MD_UPSTREAM_PORT_CONNECTORS_AND_FEATURES.MD` §1.5. Before any code, each item needs its own `TODO_MD_PORT_<FEATURE>.MD` covering the DB migration in our table and column names, the model mapping, and the UI rebuilt to our design system, plus user approval.

## Summary

Both systems share the same retrieval core:

- OpenSearch-only hybrid search (BM25 + content kNN, min-max normalization, fixed 0.5/0.5).
- An agentic search tool: LLM queries + rephrase + keyword expansion, then weighted RRF, then LLM section selection, then neighbour expansion.
- 512-token chunks, streaming citations, and deep research.

Since the split they have drifted in opposite directions:

- **Ours is stronger as an application.** It has a cross-encoder reranker (Cortex, opt-in), multi-agent workflows with per-step scoped search, workspace-scoped deep research, and deeper agent loops (20 cycles vs 6).
- **Upstream is stronger as a retrieval platform.** It has better ingestion (tables, pdfium), stricter permissions, index efficiency (quantization) and operations (reindex port, durable responses).

Neither system scores recency or document boost, so thumbs-up/down feedback has **no ranking effect** in either.

> **Note:** we DO run embeddings locally via **Cortex** (`cortex/README.md`). These are vLLM/TEI containers: `cortex_embed` (default `nomic-ai/nomic-embed-text-v1`, 768-d) and `cortex_rerank` (`BAAI/bge-reranker-v2-m3`). Remote providers (OpenAI, Cohere, Voyage, Google, Azure, LiteLLM) are also supported. Only the old bespoke model-server was removed.

---

## Backlog

| # | Pri | Item | Effort | Status |
|---|-----|------|--------|--------|
| 1 | P1 | pdfium PDF extraction | S | [~] Code + local tests done, awaiting Docker verify. Tracker: `TODO_MD_PORT_PDFIUM.MD` |
| 2 | P1 | Multilingual embedding (Granite) via Cortex | M | [ ] |
| 3 | P1 | Tabular chunker | L | [ ] |
| 4 | P1 | Enable reranker by default | S | [ ] |
| 5 | P2 | Permission hardening | L | [ ] |
| 6 | P2 | Separate model for evidence selection | S | [ ] |
| 7 | P2 | Recency + document-boost scoring | M | [ ] |
| 8 | P3 | Contextual RAG toggle without re-index | M | [ ] |
| 9 | P3 | Vector quantization / drop title vector | M | [ ] |
| 10 | P3 | Zero-downtime reindex port | XL | [ ] |
| 11 | P3 | Durable chat responses + prompt-cache tuning | L | [ ] |
| 12 | P3 | Extra web search providers (Tavily, Firecrawl) | S | [ ] |
| 13 | P3 | OCR for scanned PDFs | M | [ ] |
| 14 | P1 | Search-scope + answer-completeness prompt change (upstream v4.9.0) | S | [ ] |
| 15 | P1 | Our own RAG eval benchmark | M | [ ] |

---

### 1. [P1] pdfium PDF extraction — APPROVED

> This section is the per-feature plan for pdfium. It needs no DB migration and no UI change.

**Why.** `read_pdf_file` (`backend/om/file_processing/extract_file_text.py:188`) uses pure-Python **pypdf 6.6.2**, which causes four problems:
- It is slow on large PDFs.
- It holds the GIL, which can stall the indexing heartbeat.
- It produces weaker text ordering.
- It returns empty text for **owner-password-only** encrypted PDFs (PDFs locked only against editing or printing).

**What upstream does.** It uses **pypdfium2**, Chrome's PDF engine, which releases the GIL. pdfium runs in a throwaway **subprocess** with a timeout, so a malformed PDF that crashes or hangs it kills only the child. On failure it falls back to pypdf. For encrypted PDFs it tries `pdf_pass` first, then `""`.

**Plan.**
- [ ] Add `pypdfium2==5.9.0` to `pyproject.toml` (next to `pypdf==6.6.2`) and `backend/requirements/default.txt`. Keep pypdf, which is still needed for metadata, decryption checks, image extraction, the fallback and `password_validation.py`.
- [ ] Port `UP:om/utils/process_isolation.py` (87 lines) and `UP:om/utils/isolated_runner.py` (43 lines) to `backend/om/utils/`. The runner module path is `om.utils.isolated_runner`. This gives `run_in_isolated_process`, `IsolatedProcessError`, `IsolatedProcessCrashed` and `IsolatedProcessTimeout`. It must use `subprocess`, not `multiprocessing`, because Celery workers are daemons.
- [ ] Add `PDF_TEXT_EXTRACTION_TIMEOUT_SECONDS` (env, default 120) to `backend/om/configs/app_configs.py`.
- [ ] In `extract_file_text.py`:
  - add `_extract_pdf_text_pdfium(file_bytes, password)`, which gets a textpage per page, closes native handles and joins pages with `TEXT_SECTION_SEPARATOR`;
  - change `read_pdf_file(..., isolate_pdfium=True)` to read the bytes once, try `pdf_pass` then `""` for encrypted files, and run pdfium isolated with pypdf fallback on `PdfiumError` / `IsolatedProcessError`. Keep the metadata and image extraction as they are;
  - pass `isolate_pdfium` through `pdf_to_text`. Callers (`connectors/google_drive/doc_conversion.py`, `utils/web_content.py`) need no change.
- [ ] Unit tests:
  - `tests/unit/om/file_processing/test_pdf_extraction.py`: plain PDF, owner-password-only PDF, and the pdfium-failure fallback;
  - `tests/unit/om/utils/test_process_isolation.py`: ok, raised exception, timeout, crash.
- [ ] Manual check: compare the old and new paths on real PDFs (one large, one encrypted). After the Docker rebuild, index a file connector and watch the `background` logs.

**Limitation.** Scanned PDFs still need OCR (see #13).

---

### 2. [P1] Multilingual embedding (Granite) via Cortex

**Why.** The default `nomic-embed-text-v1` is English-centric, and government documents include Telugu and Hindi.

**What upstream does.** Its default is `ibm-granite/granite-embedding-97m-multilingual-r2`.

**Plan.**
- [ ] Check GPU headroom on the Cortex host. Cortex already shares the GPU with the reranker.
- [ ] Switch the `cortex_embed` model (`EMBEDDING_MODEL`) to Granite and confirm its vector dimension.
- [ ] **A full re-index is required.** A new model means a new vector space, possibly with a different dimension, so all documents must be re-embedded through the PRESENT→FUTURE search-settings swap (`om/db/search_settings.py`). Plan for downtime or a background re-index window.
- [ ] Validate retrieval on Telugu, Hindi and English test queries before and after the switch.

---

### 3. [P1] Tabular chunker

**Current state.** `xlsx_to_text` (`extract_file_text.py:355`) flattens every sheet into comma-separated lines, which then go through the normal text chunker. This causes three problems:
- Column headers appear only in the first chunk. Every later chunk is bare values like `TS-HYD-0042,Ramesh,2025-03-11,Pending,4500`, so it matches queries poorly.
- No chunk summarises the sheet, so questions like "total by district" or "how many rows" can't be answered from a few retrieved chunks.
- One large sheet produces hundreds of chunks, flooding the index and pushing other documents out of the top results.

**What upstream does.** `UP:om/indexing/chunking/tabular_section_chunker/` (target: `backend/om/indexing/chunking/tabular_section_chunker/`) (`TabularChunker`, `workbook_chunks.py`) caps each workbook at a fixed number of chunks:
- One **overview** block: the sheets, their sizes and columns, and the text of text-only sheets such as a Readme.
- **All rows** of small sheets.
- For large sheets, a **profile**: column roles, ID ranges, totals, breakdowns by category and by month, frequent values and sample rows. Large sheets with the same columns share one profile.
- A few chunks of frequent text values.

The full data stays in the file. The chunks make the file findable, and the LLM then reads the file itself (file reader) for details.

**Plan.**
- [ ] Port the `TabularSection` connector model, `cross_connector_utils/tabular_section_utils.py`, the `tabular_section_chunker/` package and its dispatch from `document_chunker.py`.
- [ ] Config: `TABULAR_FULL_ROWS_MAX_CHUNKS`, `TABULAR_VALUE_CHUNKS_PER_SHEET`, `TABULAR_MAX_CHUNKS_PER_WORKBOOK`.
- [ ] Port the `tabular_rechunk` Celery task (`background/indexing/run_tabular_rechunk.py`) to re-chunk files that are already indexed.
- [ ] Make sure the file reader or chat can open the full CSV or XLSX when the LLM needs the rows.
- [ ] Test on real department spreadsheets.

---

### 4. [P1] Enable reranker by default

**Current state.** The reranker is wired in and fails open, but it is off by default (`RERANK_ENABLED`).

**Plan.**
- [ ] Add the Cortex `rerank` profile to the default `COMPOSE_PROFILES` and set `RERANK_ENABLED=true` for both `api_server` and `background`.
- [ ] Measure latency and quality, and tune `RERANK_TOP_N` and `RERANK_PROTECT_TOP_K`. `bge-reranker-v2-m3` is multilingual and uses about 0.30 of the GPU. If VRAM is tight, the fallback is `ms-marco-MiniLM-L-6-v2`, which is English only.

---

### 5. [P2] Permission hardening

**What upstream #15549 means.** When an admin switches an existing connector from Public to Permission-synced, the chunks already indexed still say `public=true` until the doc permission sync rewrites them, which can take hours. During that window everyone can still find documents that should now be restricted. Upstream marks the pair `perm_sync_pending_since` and hides all its chunks from everyone until a doc sync (and a group sync, if the source has one) succeeds. It fails closed.

**Our current state.**
- The access type is set only at creation (`om/db/connector_credential_pair.py:508`) and there is no edit-access-type path, so this exact gap is **not currently reachable**.
- New SYNC connectors appear fail-closed: documents indexed without permissions get an empty ACL, so only admins see them. This is read from the code and still needs a test.

**Missing vs upstream.**
- [ ] The "awaiting first perm sync" fail-closed mark (#15549). **This is mandatory if we ever add an edit-access-type feature.**
- [ ] `SYNC_RESTRICTED` access type: the user must match the source ACL **and** belong to a data-access group.
- [ ] Per-chunk `cc_pair_ids` field plus a query-time cc-pair access filter with SHADOW and ENFORCE modes (#15279, #15280, #15943). This protects against stale ACLs on chunks.
- [ ] Backoff for failing permission syncs (#16837).
- [ ] **Shared risk (ours and upstream):** a document indexed by both a PUBLIC and a SYNC connector becomes public (`om/db/document.py:617`, `bool_or`). Decide on the intended behaviour.
- [ ] Add a test: a new SYNC connector's documents must be invisible to non-admins before the first sync.

---

### 6. [P2] Separate model for evidence selection

**What upstream does (#16079).** The LLM section-selection step (`secondary_llm_flows/document_filter.py`) can be routed to its own, cheaper model.

**Plan.**
- [ ] Add a config or admin setting for the selection model and default it to the chat model. This lowers cost per search, because selection runs a parallel LLM call per document.

---

### 7. [P2] Recency and document-boost scoring

**Current state.** This is a gap in **both** systems. There are TODOs in `backend/om/document_index/opensearch/search.py` (around lines 177–179):
- `recency_bias_multiplier` is passed along but never read;
- `boost` is stored but not scored;
- `hybrid_alpha` has no effect.

**Plan.**
- [ ] Add time decay on `updated_at` and boost scoring, either as an OpenSearch `function_score` or as an app-side rescore after RRF.
- [ ] This makes thumbs-up/down (`om/db/feedback.py`) actually change ranking.
- [ ] See `TODO_MD_VESPA_VS_OPENSEARCH_MIGRATION_COMPARISON.MD` for the earlier analysis.

---

### 8. [P3] Contextual RAG toggle without re-index

**What upstream does (#15565).** It keeps `doc_summary` and `chunk_context` as separate index fields, so contextual RAG can be switched on or off without a re-index. Ours puts both into the chunk text and its embedding.

- [ ] Evaluate whether it's worth it. It is only relevant if we start using contextual RAG.

---

### 9. [P3] Vector quantization / drop title vector

**What upstream does.** Vector quantization (float32, 7-bit, 1-bit) and reduced dimensions (#15748), copying vectors instead of re-embedding when only quantization changes (#15774), and removing title embeddings (#15733, #15737).

- [ ] Benchmark index size against recall on our data. Ours keeps an optional title kNN (0.1 / 0.45 / 0.45).

---

### 10. [P3] Zero-downtime reindex port + INSTANT / ACTIVE_ONLY switchover

- [ ] Covered in the existing `TODO_MD_INDEX_REINDEX_IMPLEMENTATION_PLAN.MD`: `created_at` dual time range, IndexPair safety, reindex port with PIT. This becomes important before #2 (the Granite switch) on a large corpus.

---

### 11. [P3] Durable / replayable chat responses + prompt-cache tuning

**What upstream does.** Durable responses with replay after disconnect (#16711–16714), prompt-cache-friendly message layout (#15978, #15571, #15643) and minified tool JSON (#15627).

- [ ] Review for porting, given the long-running workflows and deep research.

---

### 12. [P3] Extra web search providers

**Current state.** Ours has Brave, Exa, Google PSE, SearXNG, Serper and SmartSearch. Upstream also has **Tavily** and **Firecrawl** (#15483).

- [ ] Add these if users ask for them.

---

### 13. [P3] OCR for scanned PDFs

**Current state.** This is a gap in **both** systems. pypdf and pdfium only extract embedded text, so scanned government documents index as empty.

- [ ] Options:
  - a vision LLM on page images (the image-summarization path already exists);
  - Tesseract or PaddleOCR (Telugu support needed);
  - the Unstructured API (already optional).
- [ ] Use OCR only when the extracted text is empty or below a threshold.

---

### 14. [P1] Search-scope and answer-completeness prompt change (upstream v4.9.0, October 2026)

Upstream changed two things after our fork:
- Search no longer narrows to a connected source just because the question names that source.
- On search-backed turns, the model is asked to address every part of the question and to carry over the exact figures its sources give.

Upstream reports this raised answer completeness on its internal RAG benchmark.

- [ ] Port from `UP:om/tools/tool_implementations/search/` and the chat prompts into `backend/om/tools/tool_implementations/search/` and `backend/om/prompts/`.

---

### 15. [P1] Our own RAG eval benchmark

Upstream's "best RAG" claim is based on an **internal** benchmark with no public numbers, so it says nothing about our system.

- [ ] Build a gov-department eval set (Telugu, Hindi and English questions over real department documents, including spreadsheets and PDFs) on `backend/om/evals/` + Braintrust.
- [ ] Measure before and after each port (pdfium, tabular chunker, Granite, reranker, #14).

---

## Appendix — comparison snapshot (2026-10-29)

| Area | Ours | Upstream | Edge |
|---|---|---|---|
| Cross-encoder reranker | Wired in, opt-in (Cortex, fail-safe) | Defined, unused | Ours |
| Multi-agent workflow RAG | Yes | No | Ours |
| Deep research in workspaces | Yes | No | Ours |
| Agent loop cycles | 20 | 6 | Ours (costlier) |
| Local embeddings | Cortex (vLLM/TEI) + remote | Model server + remote | Even |
| Default embedding | nomic (English) | Granite multilingual | Upstream |
| Spreadsheets | Flattened CSV text | Tabular chunker | Upstream |
| PDF parsing | pypdf | pdfium + isolation | Upstream |
| Permissions | ACL filter | ACL + cc-pair filter, fail-closed, restricted | Upstream |
| Quantization | No | Yes | Upstream |
| Reindex / switchover | PRESENT/FUTURE swap | + port, INSTANT, ACTIVE_ONLY | Upstream |
| Evidence-selection model | Chat model | Separate model option | Upstream |
| Recency / boost scoring | Not scored | Not scored | Neither |
| KG tool | Stubbed | Stubbed | Neither |
| Federated search | Slack only | Slack only | Even |
