# TODO — Port: PDFium PDF text extraction (RAG backlog item 1)

**Backlog:** `TODO_MD_RAG_UPGRADES_FROM_UPSTREAM.MD` item 1 (P1)
**Process:** per-feature workflow, `TODO_MD_UPSTREAM_PORT_CONNECTORS_AND_FEATURES.MD` §1.5
**Status:** CODE + LOCAL TESTS DONE (2026-10-29). Waiting for the user's Docker rebuild and in-container verification. **Not committed** (user commits).

> **Resuming in a new session?** Read the "Progress tracker" below. Pick the first unchecked item, and tick it with the date when done.

---

## 1. Scope
- **What users get:**
  - PDFs are parsed by PDFium (the engine Chrome uses): faster, better text order, no doubled spaces.
  - A malformed PDF can no longer crash or hang an indexing worker.
  - Owner-password-only PDFs (locked for edit/print only) are now indexed; before, they produced empty text.
- **Source:**
  - `UP:om/file_processing/extract_file_text.py` (the PDF reader part)
  - `UP:om/utils/process_isolation.py`
  - `UP:om/utils/isolated_runner.py`
- **Target (our tree):**
  - `backend/om/file_processing/extract_file_text.py`
  - `backend/om/file_processing/pdfium_text.py` (new)
  - `backend/om/utils/process_isolation.py` (new)
  - `backend/om/utils/isolated_runner.py` (new)
  - `backend/om/configs/app_configs.py`
- **Dropped:** nothing; it is all open-source code, with no enterprise, Vespa or model-server parts.
- **Out of scope:** OCR for scanned PDFs (backlog item 13); the image-extraction rewrite.

## 2. DB migration
None. No table or column changes.

## 3. Model mapping
- **New env var:** `PDF_TEXT_EXTRACTION_TIMEOUT_SECONDS`, default 120. After this many seconds the PDFium child is killed and pypdf takes over.
- **New dependency:** `pypdfium2==5.9.0`, added to `pyproject.toml`, `uv.lock` and `backend/requirements/default.txt` (regenerated with the `uv export` command in that file's header). pypdf stays.
- **API:** `read_pdf_file(...)` and `pdf_to_text(...)` gain an optional `isolate_pdfium=True` parameter. Existing callers are unchanged.

## 4. UI
None.

## 5. Design: reuse and differences from upstream
- **`om/utils/process_isolation.py` is generic.** `run_in_isolated_process(fn, *args, timeout=...)` can run **any** crash-prone native parser in a child process, so future ports should reuse it rather than write their own. It raises typed errors (`IsolatedProcessCrashed`, `IsolatedProcessTimeout`, both `IsolatedProcessError`). It uses `subprocess`, not `multiprocessing`, because Celery workers are daemons.
- **Improvements over upstream:**
  - **Fast child start-up.** The PDFium call lives in its own lightweight module (`pdfium_text.py`, which only imports pypdfium2), so the child doesn't load the whole file-processing stack for every PDF.
  - **Works from any working directory.** The child gets `PYTHONPATH` pointing at the backend package root.
  - **No truncated results.** The runner writes the result with a buffered file write. Upstream's single `os.write` can write only part of a large result.
  - **`\n` line endings.** PDFium's `\r\n` / `\r` line breaks are normalized to `\n`, matching our other extractors.
  - **Same input as before.** `read_pdf_file` rewinds seekable streams to byte 0, as pypdf did, so callers that peeked at the file header still get the whole file.
- **Fallback order:**
  1. PDFium in the isolated child.
  2. If PDFium raises an error, crashes or times out: pypdf in-process. The document is still indexed.
  3. Metadata and image extraction always use pypdf, as before.

## 6. Existing features touched (regression scope)
`read_pdf_file` / `pdf_to_text` are called by:

| Caller | Path | Covered by |
|---|---|---|
| Connectors through `extract_file_text` | airtable, confluence, dropbox, egnyte, highspot, google_drive (`connectors/*/`) | `test_pdf_entry_points.py::test_extract_file_text_*` + Docker check A |
| Connectors through `extract_text_and_images` | file, blob, sharepoint, drupal_wiki | `test_pdf_entry_points.py::test_extract_text_and_images_*` + Docker check A |
| Google Drive native-PDF path | `connectors/google_drive/doc_conversion.py` (calls `read_pdf_file` directly) | `test_pdf_extraction.py` + Docker check A |
| Chat file upload | `chat/chat_utils.py` | `test_extract_file_text_*` + Docker check B |
| Workspace knowledge files | `server/features/workspaces/workspaces_file_utils.py`, user-file processing Celery task | `test_extract_file_text_*` + Docker check B |
| Agent tool attachments | `tools/tool_implementations/agent_tool.py` | `test_extract_text_and_images_*` |
| Web search / open-URL on PDF pages | `utils/web_content.py` | `test_web_content_*` |

**Behaviour changes to be aware of (intended):**
- PDFs with only an owner password now return text instead of `""`.
- Whitespace changes: no doubled spaces and `\n` line breaks, so the chunks of already-indexed PDFs differ slightly after a re-index. No forced re-index is needed; changes apply as documents are re-indexed.
- Each PDF now starts a short-lived child process, measured at about 0.3 s on Windows (expected to be lower on Linux). The timeout bounds a hang.

## 7. Tests
**New unit tests:**

| File | What it covers |
|---|---|
| `backend/tests/unit/om/utils/test_process_isolation.py` (9) | Return values, kwargs, large results, re-raised exceptions, abort, segfault (POSIX only), timeout, any working directory, daemon caller |
| `backend/tests/unit/om/file_processing/test_pdf_extraction.py` (19) | PDFium vs in-process parity, line-ending normalization, pypdf fallback on error / crash / timeout, images survive a crash, metadata, encrypted (right / none / wrong password), owner-protected, empty, invalid, images on/off, callback, `pdf_to_text` |
| `backend/tests/unit/om/file_processing/test_pdf_entry_points.py` (9) | Regression through the public entry points the existing features use (§6) |

- **Fixtures:** `backend/tests/unit/om/file_processing/fixtures/*.pdf` (7 tiny PDFs, checked for upstream names).
- **Golden snapshot:** `tests/unit/migration_safety/snapshots/baseline.json` gained the 3 new module names.

**Local run (Windows, pypdfium2 4.30):** 46 passed, 1 skipped (segfault test, POSIX only).
- `tests/unit/migration_safety`: all passing after the snapshot update.
- `test_websearch_utils.py`: 6 failures, **pre-existing and unrelated**. Windows reads its data file as cp1252.

**Pinned version:** `pypdfium2==5.9.0`, checked in a throwaway venv: same text in-process and isolated, `PdfiumError` on invalid input, no deprecation warning.

**Real PDFs:**

| File | Old (pypdf) | New (PDFium) |
|---|---|---|
| `Sample.pdf` | 31 chars | 21 chars, same words, no doubled spaces |
| `report.pdf` | 1161 words | 1158 words |

## 8. Gates
- [x] Naming grep (no upstream name in new or changed files or fixtures).
- [x] `pytest backend/tests/unit/migration_safety`.
- [x] Import check of every caller module, plus `compileall`.
- [ ] `python -I rename-audit/build_inventory.py --check`. **Not run**, because it rewrites `rename-audit/SUMMARY.md`, `inventory.csv` and `path_renames.txt`. Run it when committing. The naming grep above covers the new files.
- [ ] Web `tsc`: not needed, since there are no web changes.

## 9. Rollout and verification (user)
> **Minimal dev check (agreed 2026-10-30):** no re-index needed, because old chunks stay valid. Do steps 1 and 2, then upload **one PDF to a workspace**, which goes through the Celery user-file task, the same reader the connectors use. Ask a question about it, then run `docker logs <background> 2>&1 | grep "PDFium text extraction failed"`, which should print nothing. Checks A and B below are optional in dev.

1. Rebuild the backend images (`api_server`, `background`) so `pypdfium2` gets installed.
2. **In-container unit tests (Linux; this also runs the POSIX segfault test):**
   `docker exec -it <background container> sh -c "cd /app && python -m pytest tests/unit/om/utils/test_process_isolation.py tests/unit/om/file_processing -q"`
   (Tests may not be in the image; if so, mount or copy `backend/tests`.)
3. **Check A, connectors:** re-index a File or Google Drive connector that has PDFs. Search for a phrase from a PDF. Check the `background` logs for `PDFium text extraction failed`; occasional fallbacks are OK, constant ones are not.
4. **Check B, chat and workspaces:** upload a PDF in chat, and add one to a workspace. Ask a question about its content.
5. **Optional:** upload an owner-password-protected PDF. It should now be searchable.

## 10. Progress tracker
- [x] 2026-10-29 Research: upstream source, our callers, our test layout, dependency tooling (uv lock/export)
- [x] 2026-10-29 Config `PDF_TEXT_EXTRACTION_TIMEOUT_SECONDS`
- [x] 2026-10-29 `om/utils/process_isolation.py` + `om/utils/isolated_runner.py`
- [x] 2026-10-29 `om/file_processing/pdfium_text.py`
- [x] 2026-10-29 `read_pdf_file` rewrite (PDFium + fallback, `""` password retry, stream rewind)
- [x] 2026-10-29 Dependency: `pyproject.toml`, `uv lock`, `uv export` → `default.txt` (only pypdfium2 added)
- [x] 2026-10-29 Unit tests + fixtures + regression entry-point tests, all green locally
- [x] 2026-10-29 Verified pinned pypdfium2 5.9.0 in a throwaway venv; real-PDF comparison
- [x] 2026-10-29 Golden snapshot updated; migration_safety green
- [ ] User: Docker rebuild + in-container tests (§9 step 2)
- [ ] User: checks A and B (§9 steps 3–4)
- [ ] User: review + commit (run `build_inventory.py --check` first)
- [ ] Tick item 1 in `TODO_MD_RAG_UPGRADES_FROM_UPSTREAM.MD` as DONE
