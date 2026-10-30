# TODO — Port: Table chunker for spreadsheets and CSVs (RAG backlog item 3, lane L1)

**Backlog:** `TODO_MD_RAG_UPGRADES_FROM_UPSTREAM.MD` item 3 (P1)
**Process:** per-feature workflow, `TODO_MD_UPSTREAM_PORT_CONNECTORS_AND_FEATURES.MD` §1.5
**Status:** Phase B CODE DONE (2026-10-30). Uncommitted in worktree `agent-a695ca44a2c2c7c0b`. Unit tests are green, and cross-verification found 72/72 runs byte-identical. Waiting on user Docker checks and commit.

> **Resuming in a new session?** Read the "Progress tracker" (§13). Pick the first unchecked item and tick it with the date when done.

> **Start condition for code:** the pdfium port (`TODO_MD_PORT_PDFIUM.MD`) touched `backend/om/file_processing/extract_file_text.py`. On 2026-10-30 the working tree was clean and that work is in commit `2fa6ebfc3` ("pdf utils upgraded"). Before Phase B, run `git status` again: if that file shows local changes, stop and ask. L1 touches **only** the xlsx/csv part of that file, and only by adding a new function.

> **Naming rule (2026-10-30):** upstream code is **reference only**. Every folder, file, class, function and config name in this lane is **ours** (§5), chosen to fit our existing layout and names (`om/indexing/chunker.py`, `TextSection` / `ImageSection`, `MINI_CHUNK_SIZE`-style configs). Upstream names appear in this doc only as `UP:` references.

---

## 1. Scope
- **What users get:**
  - Spreadsheets (`.xlsx`) and CSV/TSV files are indexed as a **small, fixed number of chunks per file**: an overview (sheets, sizes, columns, text-only sheets such as a Readme), all rows of small sheets, and for large sheets a summary (column roles, ID ranges, totals, breakdowns by category and by month, frequent values, sample rows).
  - Every chunk names its file, sheet and columns. Later chunks are no longer bare values like `TS-HYD-0042,Ramesh,2025-03-11,Pending,4500` with no header.
  - Questions like "total by district" or "how many rows" can be answered from one or two retrieved chunks.
  - A single huge sheet no longer produces hundreds of chunks that push other documents out of the top results. Upstream measured 30 workbooks going from 50,976 chunks to 105.
- **Upstream reference (read only; behaviour is re-implemented under our names, see §5):**
  - `UP:om/indexing/chunking/tabular_section_chunker/` (`cell_values.py`, `models.py`, `workbook_chunks.py`, `tabular_section_chunker.py`)
  - `UP:om/indexing/chunking/document_chunker.py`: only the "group sections by link, chunk each workbook once" loop
  - `UP:om/connectors/models.py`: the section discriminator and the tabular section model
  - `UP:om/connectors/cross_connector_utils/tabular_section_utils.py`
  - `UP:om/utils/csv_utils.py`: the field-size-safe reader only
  - `UP:om/natural_language_processing/utils.py`: two token helpers
  - `UP:om/configs/app_configs.py`: the chunk caps
  - `UP:om/connectors/file/connector.py` and `UP:om/connectors/blob/connector.py`: the tabular branch
- **Target (our tree; the names are explained in §5):**
  - `backend/om/indexing/table_chunking/` (new package)
  - `backend/om/indexing/chunker.py`: one new branch
  - `backend/om/connectors/models.py`
  - `backend/om/connectors/cross_connector_utils/table_file_sections.py` (new)
  - `backend/om/utils/csv_parsing.py` (new)
  - `backend/om/natural_language_processing/utils.py`: two new functions added, nothing existing changed
  - `backend/om/file_processing/extract_file_text.py`: new `xlsx_sheets_to_csv()`; `xlsx_to_text` is **unchanged**
  - `backend/om/configs/app_configs.py`: inside a `# --- tabular-chunker ---` block
  - `backend/om/connectors/file/utils.py` (`_process_file`), `backend/om/connectors/blob/connector.py`
  - `backend/om/indexing/indexing_pipeline.py`, `backend/om/background/indexing/run_docfetching.py`: section-type checks only
- **Dropped or deferred (see §6.4–6.6):**
  - Upstream's **file-backed staging** (a staged CSV file id, a staging module, an indexing-staging file origin, promotion and an orphan janitor). We have none of it.
  - The upstream refactor that turns the chunker into a per-section-type dispatcher package.
  - The upstream re-chunk task.
  - The python-tool bridge for connector files.
  - The chat-file `csv`→`tabular` type rename.
- **Nothing enterprise-only, Vespa or model-server** is involved.
- **Dependencies:** none blocking. L4 (eval benchmark, backlog item 15) supplies the before/after metrics (§11).

## 2. DB migration
**None.** Evidence:
- None of the upstream tabular commits touch alembic, `db/models.py` or the OpenSearch schema: "Add TabularSection", "Connectors output TabularSections", "file-backed TabularSection", "require csv_file_id", and "chunk spreadsheets strategy w/ less chunks" (checked with `git show --stat`).
- Chunks are still ordinary chunks. Their text goes into the existing `chunk_text` / `content_embedding` / `title_embedding` fields, so there is **no OpenSearch mapping change** and no forced re-index.
- When a document is re-indexed, `OpenSearchDocumentIndex` (around line 487) deletes the document's old chunks first, so a spreadsheet that drops from 300 chunks to 8 leaves no stragglers behind.
- Upstream migration `8188861f4e92_csv_to_tabular_chat_file_type` rewrites `chat_message.files[].type` from `csv` to `tabular`. It belongs to upstream's chat-upload change and has nothing to do with indexing. Our `ChatFileType` still has `CSV = "csv"` (`om/file_store/models.py`), and chat never goes through the indexing chunker. **Out of scope; we need no equivalent now.** If that chat change is ported later, its own doc must add an equivalent migration under our names.

## 3. Model mapping
- **`om/connectors/models.py`** (owned by this lane for this batch):
  - New `class SectionKind(str, Enum)` with `TEXT = "text"`, `IMAGE = "image"`, `TABLE = "table"`.
  - `TextSection` gets `kind: Literal[SectionKind.TEXT] = SectionKind.TEXT`, and `ImageSection` gets `kind: Literal[SectionKind.IMAGE] = SectionKind.IMAGE`. Both have defaults, so every existing constructor call and old serialized JSON without `kind` still validates exactly as it does today.
  - New `TableSection(Section)` with:
    - `kind: Literal[SectionKind.TABLE] = SectionKind.TABLE`
    - `text: str`: the CSV of **one** sheet, or of the whole csv/tsv file, kept **inline**
    - `link: str`
    - `sheet_name: str | None = None`
    - `__sizeof__`
  - Base `Section` gets no new fields. Our pipeline and the Slack federated search build bare `Section(...)` objects, and adding fields there would change them.
  - `Document.sections: list[TextSection | ImageSection | TableSection]`.
  - **Why the discriminator is required:** documents round-trip through JSON in `file_store/document_batch_storage.py` (`model_dump(mode="json")` → `Document.model_validate`). The pipeline also rebuilds them with `IndexingDocument(**document.model_dump(), ...)`. Without the `Literal` field, a dumped `TableSection` could re-validate as a `TextSection`, which would silently fall back to the old chunking.
- **Pydantic/API:** the public ingestion API accepts `Document` JSON. Payloads without `kind` parse exactly as before; a client *may* now send a `"kind": "table"` section. No route changes.
- **Env vars**, in the `# --- tabular-chunker ---` block of `app_configs.py`. Our names follow the `MINI_CHUNK_SIZE` / `LARGE_CHUNK_RATIO` style:

  | Var (ours) | Default | Meaning |
  |---|---|---|
  | `TABLE_CHUNKING_ENABLED` | `true` | Kill switch. `false` makes connectors emit the old single TextSection |
  | `TABLE_FULL_ROWS_MAX_CHUNKS` | 12 (reference: 3; raised 2026-10-30 after the live test, see §13) | A sheet whose rows fit in this many chunks keeps all rows verbatim; bigger sheets get a summary |
  | `TABLE_VALUE_CHUNKS_PER_SHEET` | 2 | Chunks of frequent text values per large sheet |
  | `TABLE_MAX_CHUNKS_PER_FILE` | 24 | Hard cap of chunks per spreadsheet or CSV file |

- **No new Celery tasks, Redis keys, or file origins.**
- **New dependencies: none.** `openpyxl`, `chonkie` and the stdlib `csv` module are already present.

## 4. UI
None. Spreadsheets keep showing up as normal search results and citations. Their chunk text now looks like "File X, sheet Y, columns …" rather than raw CSV lines.

## 5. Naming & structure (ours)
`om/indexing/` is our home for chunking, so the new package goes there next to `chunker.py`. We say "table" throughout to match `TextSection` / `ImageSection` and because it covers both CSV and xlsx.

| Upstream reference concept | Ours (folder / file / class / function / config) | Reason |
|---|---|---|
| Chunking package with per-type chunkers (`UP:om/indexing/chunking/`) | No new top-level package; `om/indexing/chunker.py` stays the entry point | We keep our single `Chunker` (§6.1) |
| Tabular chunker subpackage | `om/indexing/table_chunking/` | Sits beside `chunker.py`; one word for what it does |
| `tabular_section_chunker.py` / `TabularChunker` | `table_chunking/table_chunker.py` / `TableChunker.chunk_table_file(sections, content_token_limit, file_name)` | Works on one file, which may hold many sheets |
| `workbook_chunks.py` / `build_workbook_chunks` | `table_chunking/chunk_builder.py` / `build_table_file_chunks(...)` | It builds the chunk texts for one table file |
| `models.py` (`SheetSource`, `SheetProfile`, `ColumnStats`, `Breakdowns`, `Sums`, `ColumnRole`, `SheetKind`, `Block`) | `table_chunking/sheet_summary.py` (`SheetRows`, `SheetSummary`, `ColumnSummary`, `CategoryBreakdowns`, `ColumnTotals`, `ColumnRole`, `SheetKind`, `ChunkBlock`) | Named for what they hold: a summary of a sheet |
| Packer class | `ChunkPacker` in `chunk_builder.py` | Says what it packs |
| `cell_values.py` (number and date parsing, header detection) | `table_chunking/cell_parsing.py` | Parsing of cell strings |
| Overview / full-rows / profile / value blocks | `_overview_block`, `_all_rows_block`, `_summary_block`, `_frequent_values_block` | Our words for the four chunk kinds |
| Section type enum + tabular section model | `SectionKind` + `TableSection` in `om/connectors/models.py` | Matches `TextSection` / `ImageSection`; `kind` doesn't clash with `type` in our code |
| Heading `"file :: sheet"` packed into the heading | `TableSection.sheet_name` (file name comes from `document.semantic_identifier`) | An explicit field instead of a string to parse |
| `tabular_section_utils.py` (`is_tabular_file`, `tabular_file_to_sections`) | `cross_connector_utils/table_file_sections.py` (`is_table_file`, `table_file_to_sections`) | Our existing folder for helpers shared by connectors |
| `csv_utils.csv_reader` | `om/utils/csv_parsing.py::read_csv_rows` | Our `om/utils` naming |
| Token-count and token-split helpers | `om/natural_language_processing/utils.py::count_tokens_safely`, `split_by_token_limit` | Next to our existing `tokenizer_trim_*` helpers |
| Sheet-to-CSV staging for xlsx | `extract_file_text.py::xlsx_sheets_to_csv` | Beside our `xlsx_to_text` |
| Chunker dispatch loop | `Chunker._chunk_table_sections(...)`, called from `_chunk_document_with_sections` | A private method in our existing class |
| Tabular chunk-cap configs | `TABLE_CHUNKING_ENABLED`, `TABLE_FULL_ROWS_MAX_CHUNKS`, `TABLE_VALUE_CHUNKS_PER_SHEET`, `TABLE_MAX_CHUNKS_PER_FILE` | Our config style; "file" because a CSV is not a workbook |

## 6. Design: reuse and differences from upstream

### 6.1 Keep `chunker.py`; add the table chunker beside it (chosen)
- **Options considered:**
  - (a) Port upstream's dispatcher refactor (a per-section-type chunker package).
  - (b) Keep our `chunker.py` and add one table branch that calls `om/indexing/table_chunking/`.
- **Pick (b).** Reasons:
  - Our `chunker.py` (532 lines) has its own behaviour that upstream's refactored text chunker does not reproduce byte-for-byte: `STRICT_CHUNK_TOKEN_LIMIT`, `_split_oversized_chunk`, `shared_precompare_cleanup`, and the image-section case. Option (a) would re-implement text chunking, so the chunks of every non-tabular document could change. That is exactly the regression we must not cause.
  - Option (b) leaves the text and image code paths byte-identical. A golden test proves it (§8).
- **`Chunker._chunk_table_sections`:**
  1. Before the loop, group `TableSection`s by `link` (one file per link).
  2. At the first `TableSection` of a group:
     - flush the current text chunk, exactly as the image case does;
     - call `TableChunker.chunk_table_file(sections, content_token_limit, file_name=document.semantic_identifier)`;
     - turn each returned text into a chunk with `self._create_chunk(...)`: `links={0: link}`, `is_continuation = i > 0`.
  3. Skip later sections of the same group.
  4. Continue the loop.
- Title prefix, metadata suffix, blurb, mini-chunks, large chunks and contextual RAG all apply unchanged, because they work on `DocAwareChunk`s after this step.
- **`TableChunker` takes rows, not a file store.** `SheetRows.open_rows` is a callable, `lambda: read_csv_rows(io.StringIO(section.text))`, so each call gets a fresh iterator.
- The summary and chunk-building logic (`chunk_builder.py`, `sheet_summary.py`, `cell_parsing.py`) re-implements upstream's behaviour with our names. It imports only pydantic, the stdlib, our tokenizer helpers and our logger.

### 6.2 Inline CSV instead of file-backed staging
- Upstream later moved the CSV out of the `Document` into a staged file, so a huge sheet never sits on the worker heap. That needs a staging subsystem we don't have; it is a separate backlog row ("file / blob — Tabular section file id, staging", P3).
- **Inline is no worse than today.** Today the same CSV text already sits inline in a TextSection. Memory, batch-storage size and the `MAX_DOCUMENT_CHARS` skip therefore stay as they are.
- Forward path: when staging is ported, add `staged_csv_file_id: str | None` and a second `open_rows` source. Only `table_file_sections.py` and `TableChunker` change.

### 6.3 Extraction
- **New `xlsx_sheets_to_csv(file, file_name) -> list[tuple[str, str]]`** (sheet name, CSV text), next to `xlsx_to_text`:
  - Writes each sheet with `csv.writer`, so commas and newlines inside cells are quoted. Today's `",".join` does not quote them.
  - Writes `None` as `""` and every other value as `str(v)`. Today's `str(cell or "")` turns `0` into `""`.
  - Drops empty rows, and keeps our existing guard that stops after 100 consecutive empty rows.
  - Reuses the existing `openpyxl.load_workbook(read_only=True)`, `BadZipFile`, `~`-file and `KNOWN_OPENPYXL_BUGS` handling.
- **`xlsx_to_text` is not touched.** Chat uploads, workspace plaintext, `read_file` and Google Drive keep getting exactly the same text.
- **`table_file_sections.py`:**
  - `TABLE_FILE_EXTENSIONS = {".xlsx", ".csv", ".tsv"}`. `.xls` and `.xlsm` are not in our allowed upload extensions.
  - `is_table_file(name)`
  - `table_file_to_sections(file, file_name, link) -> list[TableSection]`:
    - xlsx: one section per non-empty sheet;
    - csv/tsv: one section for the file, with TSV re-written as CSV;
    - empty input: `[]`.
  - **Reuse:** any connector that has the bytes and a file name can call this. Later connectors (§6.4) need only a few lines each.
- **`om/utils/csv_parsing.py::read_csv_rows()`:** raises the csv field-size limit at the point of use (128 MiB). Reusable by Salesforce and the reporting code later; they are not changed now.
- **Python 3.11:**
  - The upstream reference targets 3.13 and uses PEP 695 generics (`def f[T: ...]`), which are a syntax error on our `python:3.11.7` image.
  - Use `TypeVar`, and avoid other 3.12+ features (`itertools.batched`, the `type X =` statement, `typing.override`). The `compileall` gate (§9) checks this.

### 6.4 Connectors switched in this lane, and later
- **This lane:**
  - **File connector** (`connectors/file/utils.py::_process_file`): put a table branch before `extract_text_and_images`. It also covers:
    - **workspace knowledge files**, because the Celery user-file task uses `LocalFileConnector`;
    - the **folder connector**, because it reuses `_process_file`.
  - **Blob connector** (S3/GCS/R2/OCI): the same branch before `extract_text_and_images`.
  - If `table_file_to_sections` raises or returns `[]`, fall back to the current TextSection path, so a document is never lost.
  - If `TABLE_CHUNKING_ENABLED=false`, skip the branch entirely.
- **Later (one line each in the backlog, same helper):**
  - Google Drive (xlsx and native Sheets export in `doc_conversion.py`)
  - SharePoint / OneDrive
  - Drupal wiki attachments, Dropbox, Egnyte, Confluence/Jira attachments
  - Salesforce CSV export: it is already structured, so leave it.
- **Intended side effect:** when an Unstructured API key is set, the file and blob connectors no longer send xlsx/csv to Unstructured. Upstream does the same. See open question 3.

### 6.5 How the LLM reads full rows (what exists today)
- **Workspace knowledge files and chat files:** `read_file` (`om/tools/tool_implementations/file_reader/file_reader_tool.py`) pages through the file's extracted text, up to 16,000 characters per call. That text comes from the unchanged `xlsx_to_text`. So "the chunk finds the file, the LLM reads it" works for workspace files today. Upstream's file reader has the same scope.
- **Chat CSV/XLSX uploads:** `chat_utils._extract_tabular_metadata` injects the headers and sample rows when the Python tool is available, and the Python tool loads the full file. This doesn't change.
- **Connector-indexed spreadsheets:** today the LLM sees only the chunks. A full-file bridge needs the staged raw file, so it is **deferred** with staging. The overview and summary chunks are designed to answer aggregate questions without it.

### 6.6 Re-chunking already-indexed files: later
- Upstream's re-chunk task needs the staged raw file, a reindex port and new document queries, none of which we have. **Deferred.**
- For now: new and changed files get the new chunks automatically. To convert old ones:
  - connectors: run the admin **"Re-index from beginning"**;
  - workspace files: re-upload them.
- This is the same "no forced re-index" policy as pdfium.

## 7. Existing features touched (regression scope)

| Caller / feature | Path | What changes | Covered by |
|---|---|---|---|
| All connector indexing and knowledge files | `indexing/indexing_pipeline.py:869` → `Chunker.chunk` | New branch only for `TableSection` | Golden text-chunk test + `test_chunker.py` (existing) + new pipeline tests |
| Slack federated search | `context/search/federated/slack_search.py:1164` (`Chunker`) | None (text-only Sections) | Golden test (same `Chunker` code path) |
| Section → processed Section | `indexing_pipeline.process_image_sections` (both the no-LLM and the LLM branch) | Must pass `TableSection` through as-is. Today a non-Text section becomes `Section(text="")`, which would **lose the sheet** | `test_process_image_sections_keeps_table` (both branches) |
| Empty-doc filter and size limit | `indexing_pipeline.filter_documents` | Count `TableSection.text` like TextSection, so behaviour stays the same | `test_filter_documents_table_*` |
| NUL cleanup and size warning | `background/indexing/run_docfetching.py:184,661` | Treat `TableSection` like TextSection | Unit test on the cleanup helper |
| `IndexingDocument.get_total_char_length`, `get_text_content` | `connectors/models.py` | Include `TableSection` text | Model unit test |
| Batch storage round-trip | `file_store/document_batch_storage.py` | None; relies on the discriminator | `test_table_section_roundtrip` (dump/validate and batch-storage serialize/deserialize; old JSON without `kind`) |
| File connector, workspace files, folder connector | `connectors/file/utils.py::_process_file`; `connectors/folder/connector.py` | xlsx/csv/tsv → `TableSection`s | New `test_file_table_sections.py` + existing `tests/unit/om/connectors/folder/test_folder_connector.py` (it already writes a `data.csv`) |
| Blob connector | `connectors/blob/connector.py` | Same | New unit test with a mocked `_download_object` |
| `xlsx_to_text` users: chat upload, workspace plaintext, `read_file`, Google Drive, `extract_file_text`, agent tool, SharePoint, Drupal | `file_processing/extract_file_text.py` | **None** (function untouched) | Existing tests + a byte-equality assertion on a fixture |
| Public ingestion API | `server/om_api/ingestion.py` | Accepts an optional `kind` | Existing tests; a payload without `kind` still parses |
| Gov dept workflows (`tests/workflow_creator/test_*.py`) | — | **None.** They paste CSV inline into the chat message (`load_case_data`), with no indexing | Not needed; optional smoke run of `test_cid.py` |

**Intended behaviour changes:**
- xlsx/csv/tsv from the file, blob, folder and workspace sources produce at most 24 chunks per file, with different chunk text.
- Proper CSV quoting and `0` values are kept.
- Unstructured is bypassed for these types.

## 8. Tests (Phase B)
**First step, before any code change:** capture `tests/unit/om/indexing/fixtures/golden_text_chunks.json`. It holds the chunk content, links and continuation flags of about 10 varied non-tabular documents (long text, many small sections, an image section, an oversized section, multipass on), produced by the **current** `Chunker`. `test_chunker_golden.py` must stay byte-identical afterwards.

| New file | What it covers |
|---|---|
| `tests/unit/om/indexing/table_chunking/test_chunk_builder.py` | Header detection, small vs large sheets, summaries, merging of same-header sheets, caps, text sheets, dates and numbers. Written by us from the behaviour list in §10; it mirrors the upstream test intent, not its code |
| `tests/unit/om/indexing/table_chunking/test_cell_parsing.py` | Numbers, dates, ID values, unit markers |
| `tests/unit/om/indexing/test_chunker_table_sections.py` | `Chunker._chunk_table_sections`: grouping by link, mixed text+table doc, chunk-id order, the cap, an empty sheet, multipass on, contextual RAG on |
| `tests/unit/om/indexing/test_chunker_golden.py` | Non-tabular output unchanged |
| `tests/unit/om/connectors/cross_connector_utils/test_table_file_sections.py` | xlsx multi-sheet, csv, tsv→csv, empty, quoting, the `0` cell, a corrupt xlsx |
| `tests/unit/om/connectors/test_table_section_model.py` | Discriminator round-trip, old JSON without `kind`, `__sizeof__` |
| `tests/unit/om/connectors/file/test_file_table_sections.py` | `_process_file` with xlsx/csv: `TableSection`s; the kill switch gives a TextSection; an extraction failure falls back |
| `tests/unit/om/indexing/test_indexing_pipeline.py` (extend) | **Public entry point:** `process_image_sections` + `filter_documents` + `Chunker` on a table doc, end to end with a mocked embedder |

- **Fixtures:** a 3-sheet `.xlsx` (built with openpyxl in a conftest, nothing binary committed) and copies of 2–3 dept CSVs from `tests/workflow_creator/test_data/` (aarogyasri, cid). These are synthetic gov data; check them for upstream names.
- **Real-data check:** run `build_table_file_chunks` on `tests/external_dependency_unit/tools/data/financial-sample.xlsx` and on the dept CSVs. Record the chunk counts before (old text chunker) and after in §13.

## 9. Gates
- [x] Naming grep on all new and changed files and fixtures (no upstream name, and no upstream identifiers left over from §5's left column)
- [x] `pytest backend/tests/unit/om/indexing backend/tests/unit/om/connectors` green; golden test byte-identical
- [x] `pytest backend/tests/unit/migration_safety`:
  - the golden snapshot **will** list the new modules;
  - **do not edit** `tests/unit/migration_safety/snapshots/baseline.json` (the integrator regenerates it);
  - record the expected diff here.
- [x] Import check of every caller module, plus `compileall` on 3.11 (catches PEP 695 leftovers)
- [ ] `python -I rename-audit/build_inventory.py --check`: **at commit time only**, because it rewrites the report files
- [x] Web `tsc`: not needed

## 10. Post-implementation cross-verification (behavioural diff against the upstream reference)
**Goal:** show that our re-implementation behaves like the reference for the same input, and list and justify every difference.

### 10.1 How to run it
- **Never import, vendor or copy upstream code into our repo.**
- The harness lives in a scratch folder **outside the repo**. The upstream checkout path is passed on the command line (it is in Claude memory; never write it into a repo file).
- **Inputs:** shared row fixtures as JSON (`{"file_name", "sheets": [{"name", "rows": [[...]]}]}`), generated from our test fixtures (§8) plus the cases below.
- **Reference side:** run with the upstream checkout's own Python 3.13 environment and `PYTHONPATH`. Call its pure chunk-building function directly on the rows, bypassing its file store, and write `ref_<case>.json` (the list of chunk texts).
- **Our side:** run in our backend env. Call `build_table_file_chunks` on the same rows and write `ours_<case>.json`.
- **Same settings on both sides:** the same tokenizer (tiktoken `cl100k_base`), the same `max_tokens` (512 and 2048), caps 3/2/24, and also caps 1/0/5 to stress the limits.
- **Diff script** (also in the scratch folder) reports, per case:
  - the chunk count;
  - byte-equality per chunk;
  - for unequal chunks, a unified diff plus a classification: **identical** / **intended** (listed in §10.3) / **bug**.
- Copy only the summary table into §13. The scratch folder is deleted afterwards.

### 10.2 Cases (input → what to compare)

| # | Input | Compare |
|---|---|---|
| 1 | Empty file, or only empty sheets | Both give `[]` |
| 2 | One small sheet (20 rows × 5 cols) | Same chunk count; overview + every row present; header repeated |
| 3 | One large sheet (5,000 rows) | Chunk count ≤ cap; summary content (column roles, ID range, totals, top categories, monthly breakdown, sample rows) |
| 4 | 3 sheets with the same header (monthly tabs) | Merged into one summary; same merged row count |
| 5 | Text-only "Readme" sheet + data sheet | Readme text in the overview; no duplicate block |
| 6 | 40 sheets (cap pressure) | Total = `TABLE_MAX_CHUNKS_PER_FILE`; every sheet keeps its first block (fair truncation) |
| 7 | Preamble rows (title, blank lines) above the header | Same detected header row |
| 8 | No detectable header (all numeric) | Same fallback handling |
| 9 | Dates: ISO, `dd/mm/yyyy`, `mm/dd/yyyy`, `11-Mar-2025`, ambiguous | Same date order chosen; same month buckets |
| 10 | Numbers: `1,234.50`, `₹4,500`, `45%`, long decimals, negatives | Same totals and unit markers |
| 11 | ID-like columns (`TS-HYD-0042`) | Classified as ID; same min/max range |
| 12 | Wide sheet (> 40 columns) | Same redundant-column handling |
| 13 | Telugu/Hindi text values, duplicate or blank header cells | Same column labels and frequent values |
| 14 | Cells with commas/newlines/quotes; cell > 128 KiB | Parsed the same; no csv field-limit error |
| 15 | Dept CSVs (aarogyasri, cid) + `financial-sample.xlsx` | Chunk count and overview text; results recorded as the real-data baseline |

- **Pipeline level** (our side only, since the reference uses a different pipeline):
  - a document with text + one file;
  - a document with two files (grouped by link);
  - chunk ids and continuation flags;
  - title/metadata prefix on table chunks.
- Assert these in `test_chunker_table_sections.py`.

### 10.3 Expected, intended differences (not bugs)
- **Our extraction:** the 100-consecutive-empty-rows guard in `xlsx_sheets_to_csv` (cross-verification feeds rows directly, so this shows up only in end-to-end runs).
- **Labels:** wording of sheet titles uses `sheet_name` instead of a parsed heading. That is allowed only if the information is the same.
- Anything else counts as a bug. Fix it, or add it here with a reason, before ticking the step.

## 11. Metric hook (L4 eval, backlog item 15)
- **Should move:**
  - **chunks per file** (target ≤ `TABLE_MAX_CHUNKS_PER_FILE`; report the total index chunk count before and after);
  - **recall@k on spreadsheet questions** ("which file has the X register", "what columns does Y have");
  - **correctness on aggregate questions** (row counts, totals, top categories, monthly totals) answered from the chunks alone;
  - share of top-10 results taken up by spreadsheet chunks on **non-spreadsheet** queries (should drop).
- **Must not move:** recall and answer scores on the non-spreadsheet question set (the regression guard).
- **Known weak spot to measure:** lookups of a single specific row in a large connector-indexed sheet. The summary shows sample and frequent values, not every row, and there is no full-file reader for connector docs yet (§6.5).

## 12. Files this lane owns / shared hot files
- **Owns:**
  - `om/indexing/table_chunking/**`
  - `om/connectors/cross_connector_utils/table_file_sections.py`
  - `om/utils/csv_parsing.py`
  - the new tests and fixtures
  - `om/connectors/models.py` (this batch)
- **Shared, minimal and additive edits:**
  - `om/indexing/chunker.py` (one branch + one private method)
  - `om/indexing/indexing_pipeline.py` and `om/background/indexing/run_docfetching.py` (section-type checks)
  - `om/connectors/file/utils.py` and `om/connectors/blob/connector.py` (table branch)
  - `om/file_processing/extract_file_text.py` (new function only)
  - `om/natural_language_processing/utils.py` (two new functions)
  - `om/configs/app_configs.py` (**only** inside `# --- tabular-chunker ---`)
- **Not touched:** `tests/unit/migration_safety/snapshots/baseline.json` (the integrator regenerates it). **No new dependencies.**

## 13. Progress tracker
- [x] 2026-10-30 Research: upstream package and history, our chunker and callers, Section model and serialization, extraction, connectors, file reader, migrations, Python version
- [x] 2026-10-30 Naming & structure table (§5) and cross-verification plan (§10) added
- [x] 2026-10-30 User approval of this plan (and answers to §14)
- [x] 2026-10-30 Check that `extract_file_text.py` has no uncommitted changes (pdfium committed; worktree fast-forwarded to `2fa6ebfc3`). Baseline `pytest tests/unit/om/indexing tests/unit/om/connectors`: 231 passed, 5 pre-existing failures (3× `test_censoring` salesforce, `test_confluence_checkpointing::test_retrieve_all_slim_docs_perm_sync`, `test_connector_factory::test_all_connector_mappings_exist`) + mediawiki collection errors (missing `pywikibot` module) — all unrelated
- [x] 2026-10-30 Capture the golden non-tabular chunk fixture with the **unchanged** code (`tests/unit/om/indexing/fixtures/golden_text_chunks.json`, 12 cases / 47 chunks, e5-base-v2 tokenizer; captured at `2fa6ebfc3` before any source edit)
- [x] 2026-10-30 `connectors/models.py`: `SectionKind`, discriminators, `TableSection`; model round-trip tests
- [x] 2026-10-30 `utils/csv_parsing.py`; `count_tokens_safely` / `split_by_token_limit`
- [x] 2026-10-30 `om/indexing/table_chunking/` (`cell_parsing.py`, `sheet_summary.py`, `chunk_builder.py`, `table_chunker.py`) + tests (77 tests: `test_cell_parsing.py`, `test_chunk_builder.py`; dept CSVs embedded as strings in `sample_tables.py` because `*.csv` is git-ignored)
- [x] 2026-10-30 `Chunker._chunk_table_sections` + tests (`test_chunker_table_sections.py`, 7); golden test green — fixture byte-identical (sha256 `c0cbd143…36b1` unchanged)
- [x] 2026-10-30 Config block (4 vars) — named `# --- table-chunking ---` / `# --- end table-chunking ---` per the Phase B brief (doc said `tabular-chunker`)
- [x] 2026-10-30 `xlsx_sheets_to_csv` + `table_file_sections.py` + tests (`test_table_file_sections.py`, 11, incl. `xlsx_to_text` byte-equality)
- [x] 2026-10-30 Pipeline/docfetching section-type checks (`process_image_sections` both branches, `filter_documents`, NUL cleanup, size warning, `IndexingDocument`) + tests (`test_indexing_pipeline.py` +6, `test_table_section_model.py` 8)
- [x] 2026-10-30 File connector `_process_file` branch (+ workspaces, folder) and blob connector branch + tests (`connectors/file/test_file_table_sections.py`, 10, incl. Unstructured bypass)
- [x] 2026-10-30 Real-data chunk-count comparison (e5-base-v2 tokenizer, default 512-token chunks; old = `xlsx_to_text`/text → TextSection, new = TableSections):

  | File | Old chunks | New chunks |
  |---|---|---|
  | aarogyasri AR1 benefit / checklist / master / preauth .csv | 1 each | 1 each |
  | cid CID1 bank_statements / depositors / fir / shell_entities .csv | 1 each | 1 each |
  | `financial-sample.xlsx` (700 rows × 16 cols) | 81 | 3 |

- [x] 2026-10-30 Gates (§9):
  - Naming grep: 0 hits for upstream names in new and changed sources, tests and fixtures. 0 left-over upstream identifiers from §5.
  - `pytest tests/unit/om/indexing tests/unit/om/connectors`: 351 passed, 4 skipped. The same 5 pre-existing failures as baseline. The golden test is byte-identical.
  - Full `tests/unit`: 1783 passed. 20 failures, all pre-existing: the same set fails on a pristine export of `2fa6ebfc3` (chat_utils, llm model map, websearch snippets, discord, tool_utils, plus the 5 above). There are 2 pre-existing collection errors: `mcp.types` missing, and a cp1252 decode error in `test_snippet_finding`.
  - `migration_safety`: the only diff is `[modules] added=` the 7 new modules `<root>.connectors.cross_connector_utils.table_file_sections`, `<root>.indexing.table_chunking` (+ `.cell_parsing`, `.chunk_builder`, `.sheet_summary`, `.table_chunker`) and `<root>.utils.csv_parsing`. `baseline.json` was NOT edited; the integrator regenerates it.
  - Import check of the caller modules passes, and `compileall` passes on Python 3.11.7.
  - `build_inventory.py` was not run; it runs at commit time.
- [x] 2026-10-30 **Cross-verification (§10):** built the scratch harness and fixtures outside the repo. The reference side ran in a scratch Python 3.12 venv with pydantic and tiktoken; 3.12 also supports PEP 695. It loads only the leaf modules by file path, and stubs the two token helpers (verbatim logic) and the logger.
- [x] 2026-10-30 **Cross-verification:** ran 18 inputs (cases 1–14; case 15 split into dept workbook, 2 dept CSVs and `financial-sample.xlsx`). Each ran at 512 and 2048 tokens with caps 3/2/24 and 1/0/5, so 72 runs. Tokenizer: cl100k_base. Result: **72/72 byte-identical, 0 intended, 0 bugs.**

  | # | Case | Chunks ref = ours (512 / 2048, caps 3/2/24) | Result |
  |---|---|---|---|
  | 1 | empty / empty sheets | 0 / 0 | identical |
  | 2 | small 20×5 | 3 / 1 | identical |
  | 3 | large 5,000 rows | 5 / 3 | identical |
  | 4 | 3 monthly tabs (merged) | 5 / 3 | identical |
  | 5 | Readme + data | 5 / 3 | identical |
  | 6 | 40 sheets (cap) | 24 / 24 | identical |
  | 7 | preamble rows | 5 / 3 | identical |
  | 8 | no header, numeric | 1 / 1 | identical |
  | 9 | date formats + ambiguous | 3 / 1 | identical |
  | 10 | numbers/units | 1 / 1 | identical |
  | 11 | ID-like columns | 1 / 1 | identical |
  | 12 | wide (55 cols) | 5 / 5 | identical |
  | 13 | Telugu/Hindi, dup/blank headers | 5 / 3 | identical |
  | 14 | quotes/newlines, >128 KiB cell | 3 / 1 | identical |
  | 15 | dept CSVs workbook / preauth / depositors / financial-sample | 5,1,1,3 / 1,1,1,1 | identical |

  (Caps 1/0/5 were also identical in every case.)
- [x] 2026-10-30 **Cross-verification:** there were no bug rows. Scratch folder deleted.
- [x] 2026-10-30 **Live test (workspace smoke, `backend/tests/workspace_rag_smoke/`) found a regression with the reference default `TABLE_FULL_ROWS_MAX_CHUNKS=3`.**
  - A 16-row xlsx (3,310 tokens, long "Notes" cells) counted as "large" and was indexed as 3 summary chunks with no rows.
  - xlsx row questions went from 10/12 correct (old chunker) to **0/12**. The model said values were "not mentioned", or mixed rows up.
  - **Fix: the default is now 12.** Sheets up to about 6k tokens keep every row, written as `Column=value` with the header repeated in each chunk (11 chunks here).
  - The unit tests still pass. A re-test is pending (next item).
- [ ] Live re-test with default 12 (new workspace, same 12 questions)
- [ ] User: Docker rebuild + checks A/B (§15)
- [ ] User: review + commit (run `build_inventory.py --check` first)
- [ ] Tick item 3 in `TODO_MD_RAG_UPGRADES_FROM_UPSTREAM.MD`; add the deferred rows (staging, re-chunk task, more connectors, python-tool bridge)

## 14. Open questions for the user
1. **Inline CSV vs staging:** OK to ship inline `TableSection`s now (same memory profile as today) and leave file-backed staging for later?
2. **Kill switch default:** `TABLE_CHUNKING_ENABLED=true` by default?
3. **Unstructured:** if you use an Unstructured API key, should xlsx/csv still bypass it (upstream behaviour), or should the table branch run only when no key is set?
4. **Connectors:** file + blob (+ workspaces and folder for free) in this lane, and Google Drive next. Is Google Drive Sheets important enough to pull into this lane?
5. **Re-chunk:** is "Re-index from beginning" or re-upload acceptable for existing spreadsheets, or do you want a small admin-triggered re-index of table docs sooner?
6. **Names:** OK with "table" naming (`TableSection`, `om/indexing/table_chunking/`, `TABLE_*`) in §5?

**Decided 2026-10-30 (user):**
1. Keep the CSV inline in the document for now (no staging).
2. `TABLE_CHUNKING_ENABLED` is on by default.
3. Spreadsheets bypass Unstructured even when its key is set.
4. Google Drive is NOT in this lane (next batch).
5. Existing spreadsheets get the new chunks via "Re-index from beginning" (no re-chunk task now).
6. "table" naming approved.

## 15. Rollout and verification (user)
1. Rebuild `api_server` and `background`. No new dependency and no migration.
2. In-container: `python -m pytest tests/unit/om/indexing tests/unit/om/connectors/cross_connector_utils -q`.
3. **Check A, workspace:**
   - Upload a multi-sheet xlsx (for example a dept register) to a workspace.
   - Ask "how many rows / total X by district".
   - In OpenSearch, the document's chunk count should be ≤ 24.
4. **Check B, file connector:**
   - Run "Re-index from beginning" on a file connector that has a big CSV.
   - Compare its chunk count with before.
   - Search for a value from row 500; the summary or value chunks should surface the file.
5. **Rollback:** `TABLE_CHUNKING_ENABLED=false`, then re-index.

## 16. Phase B notes / deviations (2026-10-30)
- **`TableSection.link` stays optional (`str | None`).** It is not `link or file_name` as upstream does. Keeping it optional means file-connector citations stay `""` exactly as today, with no fake file-name link. Grouping uses the link (None included). Our connectors emit one file per document, so sections are never merged wrongly.
- **Table branch placement.** The table branch runs *before* `extract_text_and_images`, so Unstructured is bypassed (decision 3). CSV and TSV are decoded with our `extract_result_from_text_file`, so encoding detection and an `#OM_METADATA=` first line still work. If extraction fails or finds nothing, the code falls back to the old text path.
- **New helper.** `table_file_sections.extract_table_file()` returns sections together with metadata. `table_file_to_sections()` is a thin wrapper around it.
- **Config block name.** The config block is named `# --- table-chunking ---` per the Phase B brief, not `tabular-chunker`.
- **Sheet titles.** Sheet titles keep the `file :: sheet` wording, so the output matches the reference byte for byte.
- **Fixture location.** The dept CSVs are git-ignored (`*.csv`), so test copies live as strings in `tests/unit/om/indexing/table_chunking/sample_tables.py`.
- **mypy.** The `Document.sections` list union now has 3 members. Existing `cast(list[TextSection | ImageSection], ...)` call sites may draw mypy list-invariance notes. mypy is not enforced in pre-commit, and those call sites are unchanged.
