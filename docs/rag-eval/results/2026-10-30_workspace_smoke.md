# Workspace smoke test: batch 1 before/after (2026-10-30)

These are live runs against the dev stack. The tool is `backend/tests/workspace_rag_smoke/`: `run_workspace_qa.py`, `chunk_dump.py` and `questions_workspace4.json`.

**Setup:**
- 12 questions, each run twice, with `gpt-4o-mini` at temperature 0.
- Every question gets a fresh workspace chat, through `/converse/send-chat-message`.
- Scoring is deterministic: expected figures or strings must appear in the answer. For the absent-information question, the answer must say the information isn't there.
- Two files: `Consolidated-IT-Conferences-2026-2027.xlsx` (1 sheet, 16 conferences plus 1 note row, long text cells, 3,310 tokens) and `LP_Assignment_IT_Software.pdf` (7 pages).

**Code under test:**
- BEFORE: `main_multi_agent_stable` at `2fa6ebfc3`, which includes pdfium.
- AFTER: `upgrade/batch1-review` at `21d16de6d`, plus the L1 default fix described below.

## Results
| Question | BEFORE, ws4 | L2 only (old chunks), ws4 | L1 default 3 + L2, ws5 | L1 default 12 + L2, ws6 |
|---|---|---|---|---|
| x1 KubeCon cost | 2/2 | 2/2 | 0/2 | 2/2 |
| x2 Dell global index | 2/2 | 2/2 | 0/2 | 2/2 |
| x3 AI Engineer WF resources + team | 1/2 | 2/2 | 0/2 | 2/2 |
| x4 conferences in Germany | 0/2 | 0/2 | 0/2 | 1/2 |
| x5 how many conferences | 2/2 (35–72 s, via Python tool) | 2/2 (~72 s, via Python tool) | 0/2 | 0/2 (4 s; says 17 = row count incl. a note row) |
| x6 TC World venue + early-bird price | 2/2 | 2/2 | 0/2 | 2/2 |
| p1–p5 PDF figures / two-part | 10/10 | 10/10 | 10/10 | 10/10 |
| n1 absent info (PyCon) | 2/2 | 2/2 | 2/2 | 2/2 |
| **Total** | **21/24** | **22/24** | **12/24** | **21/24** |
| xlsx only | 9/12 | 10/12 | **0/12** | 9/12 |
| p50 latency | 3.9 s | 3.9 s | 3.8 s | 4.5 s |
| Mean answer length | 248 chars | 304 chars | 379 chars | 321 chars |

**Chunks:**
- xlsx: 7 with the old chunker (headers in chunk 0 only, rows cut mid-row); 3 with L1 at default 3 (summaries only, no rows); 13 with L1 at default 12 (every row as `Column=value`, headers in each chunk).
- PDF: 9 in every run.

## Findings
1. **An L1 regression, fixed.**
   - With the reference default `TABLE_FULL_ROWS_MAX_CHUNKS=3`, a short sheet with long text cells counts as "large" and is indexed as summaries only.
   - The model then can't tell which value belongs to which row: xlsx questions scored 0/12, with "not mentioned" answers and rows mixed up.
   - The default is raised to **12** in `app_configs.py`. The xlsx score is back to 9/12, and row lookups are now 6/6, against 5/6 before.
2. **The count question** now takes 4 s instead of 35–72 s, because the agent no longer falls back to the Python tool, but it is off by one.
   - The sheet summary says "17 rows", which includes a trailing note row, and the model reads that as 17 conferences.
   - Possible follow-up: have the summary report non-empty identifier values (Serial# 1–16), separately from the raw row count.
3. **L2 alone (prompts and evidence budget):** 22/24 against 21/24. Answers are about 20% longer, with no latency change, and no regressions on PDF or absent-information questions.
4. **x4 (Germany)** misses APEX Connect, whose venue is "Cinedom Köln (Cologne, Germany)", in most runs both before and after. This is a model recall limit, not a batch-1 change.

## Department workflow guard-rail suites (API key, `backend/tests/workflow_creator/`)
| Suite | BEFORE | AFTER |
|---|---|---|
| `test_epass.py` (wf 45, sequential) | 5/5 | 5/5 |
| `test_cybercrime.py` (wf 37, `llm_decision`, documented as non-deterministic) | 5/5 | 4/5. CC1 Extractor false-pause; CC1 re-runs 2/3 PASS |
| `test_cybercrime_seq.py` (wf 46, sequential, the canonical one) | — | 5/5 |

The L2 text is added only on search-backed turns (`om/chat/prompt_utils.py`). Workflow steps receive their case data inline, so the wf 37 flake matches its documented `llm_decision` behaviour.

## L5 / frontend (Admin → LLM)
- **New provider routes:**
  - `lm-studio`, `openai-compatible` and `ollama` `/available-models` return a clean 400 with a readable message for an unreachable or empty URL.
  - The existing `gpt` provider is listed as the default, and `test/default` returns 200.
- **Screenshots** (Playwright, in `d:/tmp/batch1-live/shots/`):
  - The new LM Studio and OpenAI-Compatible tiles follow the accent theme in light and dark mode (Default, Ocean, Emerald, Violet).
  - The LM Studio form auto-fetches and shows the error inline; the OpenAI-Compatible form has the manual model-id field.
  - Nit: the "API Key (Optional)" input text is larger than the other inputs.

## Logs
- No `PDFium text extraction failed` lines.
- No new error types. `No active trace … NoOpSpan` and the background `monitor_process_memory` errors also appear on `main`.
- Celery beat reports a "corrupted schedule file" after each restart; it recreates the file itself.
