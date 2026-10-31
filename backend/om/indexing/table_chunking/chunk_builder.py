"""A bounded set of chunk texts for one spreadsheet or CSV file.

A table file becomes these blocks:

- an overview: the sheets, their size and columns, and the text of text-only
  sheets such as a "Readme";
- all rows of each small sheet (rows that fit in a few chunks);
- a summary of each large sheet: column roles, identifier ranges, totals,
  breakdowns by category and by month, frequent values and sample rows;
- a few chunks of frequent text values of each large sheet.

Large sheets with the same columns share one summary. Blocks are packed
greedily, so small blocks share chunks, and a file never gets more than
``max_chunks`` chunks. The data stays in the file; the chunks make the file
findable and describe what it holds.
"""

import math
from collections.abc import Iterable
from itertools import chain

from om.indexing.table_chunking.cell_parsing import clean_cell
from om.indexing.table_chunking.cell_parsing import column_label
from om.indexing.table_chunking.cell_parsing import DateOrder
from om.indexing.table_chunking.cell_parsing import filled_cell_count
from om.indexing.table_chunking.cell_parsing import find_header_row
from om.indexing.table_chunking.cell_parsing import format_number
from om.indexing.table_chunking.cell_parsing import format_row
from om.indexing.table_chunking.cell_parsing import is_id_column_name
from om.indexing.table_chunking.cell_parsing import text_line
from om.indexing.table_chunking.cell_parsing import VALUE_SEPARATOR
from om.indexing.table_chunking.sheet_summary import CATEGORY_MAX_DISTINCT
from om.indexing.table_chunking.sheet_summary import CategoryBreakdowns
from om.indexing.table_chunking.sheet_summary import ChunkBlock
from om.indexing.table_chunking.sheet_summary import ColumnRole
from om.indexing.table_chunking.sheet_summary import ColumnSummary
from om.indexing.table_chunking.sheet_summary import SheetKind
from om.indexing.table_chunking.sheet_summary import SheetRows
from om.indexing.table_chunking.sheet_summary import SheetSummary
from om.natural_language_processing.utils import BaseTokenizer
from om.natural_language_processing.utils import count_tokens_safely
from om.natural_language_processing.utils import split_by_token_limit
from om.utils.logger import setup_logger

logger = setup_logger()

# Rows examined for the header, from the first row wide enough to be one.
_HEADER_SCAN_ROWS = 20
# Narrow rows skipped to get past a title block. A sheet with nothing wider
# than one column in this many rows is text, not a table.
_MAX_PREAMBLE_ROWS = 200
# Rows read before the breakdown columns are picked.
_PROBE_ROWS = 200
# Columns compared for redundancy; the check is quadratic.
_MAX_REDUNDANCY_COLUMNS = 40
_MAX_BREAKDOWN_CATEGORY_COLUMNS = 3
_MAX_BREAKDOWN_NUMERIC_COLUMNS = 4
_MAX_BREAKDOWN_LINES = 6
_MAX_MONTHLY_NUMERIC_COLUMNS = 2
# Frequent values shown in a summary line, and sample rows in a summary.
_SUMMARY_TEXT_VALUES = 12
_SUMMARY_SAMPLE_ROWS = 2
_SUMMARY_MAX_CHUNKS = 2
# Tokens of text-only sheets copied into the overview.
_OVERVIEW_ABOUT_TOKENS = 150
# The overview is the one place that names every sheet, so it may use more
# than one chunk and a many-sheet workbook keeps its tail.
_OVERVIEW_MAX_CHUNKS = 3


def _count(text: str, tokenizer: BaseTokenizer) -> int:
    return count_tokens_safely(text, tokenizer)


# ---------------------------------------------------------------------------
# One streaming pass over a sheet
# ---------------------------------------------------------------------------


def _pick_breakdown_columns(columns: list[ColumnSummary]) -> CategoryBreakdowns:
    categories: list[int] = []
    numerics: list[int] = []
    date_column: int | None = None
    date_order: DateOrder | None = None
    for idx, col in enumerate(columns):
        if col.non_empty == 0:
            continue
        # A date column whose order is unknown would file rows under the
        # wrong month, so it needs a settled date_min.
        if col.is_date and col.date_min is not None and date_column is None:
            date_column = idx
            date_order = col.date_order
        elif col.is_numeric and not is_id_column_name(col.name):
            if len(numerics) < _MAX_BREAKDOWN_NUMERIC_COLUMNS:
                numerics.append(idx)
        elif (
            not col.is_numeric
            and not col.is_date
            and 1 < col.distinct <= CATEGORY_MAX_DISTINCT // 2
            and col.contact_values == 0
            and len(categories) < _MAX_BREAKDOWN_CATEGORY_COLUMNS
        ):
            categories.append(idx)
    return CategoryBreakdowns(
        category_columns=categories,
        numeric_columns=numerics,
        date_column=date_column,
        date_order=date_order,
    )


def _find_redundant_columns(
    columns: list[ColumnSummary], probe: list[list[str]]
) -> set[int]:
    text_columns = [
        idx for idx, col in enumerate(columns) if col.non_empty and not col.is_numeric
    ][:_MAX_REDUNDANCY_COLUMNS]
    redundant: set[int] = set()
    for idx in text_columns:
        for other in text_columns:
            if other == idx or other in redundant:
                continue
            both = 0
            contained = 0
            for row in probe:
                if idx >= len(row) or other >= len(row):
                    continue
                value = row[idx].strip().lower()
                container = row[other].strip().lower()
                if not value or not container:
                    continue
                both += 1
                if value in container:
                    contained += 1
            if both >= 10 and contained >= 0.8 * both:
                redundant.add(idx)
                break
    return redundant


class _SheetScanner:
    """Builds the summary of one table sheet, row by row."""

    def __init__(
        self,
        summary: SheetSummary,
        tokenizer: BaseTokenizer,
        all_rows_token_budget: int,
    ) -> None:
        self._summary = summary
        self._tokenizer = tokenizer
        self._all_rows_token_budget = all_rows_token_budget
        self._all_rows_tokens = 0
        self._row_names = (
            [""] * len(summary.header) if summary.synthetic_header else summary.header
        )
        self._header_key = [cell.strip().lower() for cell in summary.header]
        # Rows kept until the breakdown columns are picked; None afterwards.
        self._probe: list[list[str]] | None = []

    def add_row(self, cells: list[str]) -> None:
        summary = self._summary
        if [
            cell.strip().lower() for cell in cells[: len(summary.header)]
        ] == self._header_key:
            return  # the header row repeated further down
        summary.row_count += 1
        for idx, col in enumerate(summary.columns):
            value = cells[idx].strip() if idx < len(cells) else ""
            if value:
                col.add_value(value)
        if len(summary.samples) < _SUMMARY_SAMPLE_ROWS:
            summary.samples.append(cells)
        self._keep_row_if_small(cells)
        if self._probe is None:
            summary.breakdowns.add_row(cells)
            return
        self._probe.append(cells)
        if len(self._probe) >= _PROBE_ROWS:
            self._end_probe()

    def _keep_row_if_small(self, cells: list[str]) -> None:
        if self._summary.all_rows is None:
            return
        line = format_row(self._row_names, cells)
        self._all_rows_tokens += _count(line, self._tokenizer) + 1
        if self._all_rows_tokens > self._all_rows_token_budget:
            self._summary.all_rows = None
        else:
            self._summary.all_rows.append(line)

    def _end_probe(self) -> None:
        if self._probe is None:
            return
        summary = self._summary
        summary.redundant_columns = _find_redundant_columns(
            summary.columns, self._probe
        )
        summary.breakdowns = _pick_breakdown_columns(summary.columns)
        for buffered in self._probe:
            summary.breakdowns.add_row(buffered)
        self._probe = None

    def finish(self) -> SheetSummary:
        self._end_probe()
        summary = self._summary
        unresolved = [col.name for col in summary.columns if col.dates_unresolved]
        if unresolved:
            logger.warning(
                "Sheet %r: columns %s hold dates like 5/3/2024 and no value shows "
                "whether the day or the month comes first; they get no time range "
                "or monthly totals.",
                summary.names[0] if summary.names else "",
                ", ".join(unresolved),
            )
        return summary


def _summarize_text_sheet(
    name: str,
    rows: Iterable[list[str]],
    tokenizer: BaseTokenizer,
    token_budget: int,
) -> SheetSummary:
    lines: list[str] = []
    used = 0
    for row in rows:
        line = text_line(row)
        cost = _count(line, tokenizer) + 1
        if used + cost > token_budget:
            # Keep the start of an overlong first cell rather than nothing.
            remaining = token_budget - used - 1
            if not lines and remaining > 0:
                pieces = split_by_token_limit(line, tokenizer, remaining)
                if pieces and pieces[0]:
                    lines.append(pieces[0])
            break
        used += cost
        lines.append(line)
    return SheetSummary(names=[name], kind=SheetKind.TEXT, text_lines=lines)


def summarize_sheet(
    name: str,
    rows: Iterable[list[str]],
    tokenizer: BaseTokenizer,
    all_rows_token_budget: int,
) -> SheetSummary:
    """One streaming pass over a sheet. Memory stays bounded: formatted rows
    are kept only while they fit ``all_rows_token_budget``."""
    row_iter = (row for row in rows if any(cell.strip() for cell in row))
    # Skip a narrow title block to reach the table; keep it as preamble.
    title_rows: list[list[str]] = []
    head: list[list[str]] = []
    for row in row_iter:
        if (
            not head
            and filled_cell_count(row) < 2
            and len(title_rows) < _MAX_PREAMBLE_ROWS
        ):
            title_rows.append(row)
            continue
        head.append(row)
        if len(head) >= _HEADER_SCAN_ROWS:
            break
    if not head:
        if not title_rows:
            return SheetSummary(names=[name], kind=SheetKind.EMPTY)
        return _summarize_text_sheet(
            name, chain(title_rows, row_iter), tokenizer, all_rows_token_budget
        )

    header_idx = find_header_row(head)
    widest = max(filled_cell_count(row) for row in head)
    if header_idx is None and widest <= 1:
        return _summarize_text_sheet(
            name,
            chain(title_rows, head, row_iter),
            tokenizer,
            all_rows_token_budget,
        )

    if header_idx is None:
        logger.debug(
            "Sheet %r: no header row in the first %s rows; columns are unnamed.",
            name,
            _HEADER_SCAN_ROWS,
        )
        header = [f"Column {idx + 1}" for idx in range(max(len(r) for r in head))]
        preamble = [text_line(r) for r in title_rows]
        data_head = head
    else:
        header = [cell.strip() for cell in head[header_idx]]
        preamble = [text_line(r) for r in chain(title_rows, head[:header_idx])]
        data_head = head[header_idx + 1 :]

    scanner = _SheetScanner(
        SheetSummary(
            names=[name],
            kind=SheetKind.TABLE,
            header=header,
            synthetic_header=header_idx is None,
            preamble=preamble,
            columns=[ColumnSummary(col) for col in header],
        ),
        tokenizer=tokenizer,
        all_rows_token_budget=all_rows_token_budget,
    )
    for cells in chain(data_head, row_iter):
        scanner.add_row(cells)
    return scanner.finish()


# ---------------------------------------------------------------------------
# Packing blocks into chunks
# ---------------------------------------------------------------------------


class ChunkPacker:
    """Packs blocks greedily into at most ``max_chunks`` chunk texts of at most
    ``max_tokens`` tokens each."""

    def __init__(
        self, tokenizer: BaseTokenizer, max_tokens: int, max_chunks: int
    ) -> None:
        self._tokenizer = tokenizer
        self._max_tokens = max_tokens
        self._max_chunks = max_chunks
        self.chunks: list[str] = []
        self._lines: list[str] = []
        self._tokens = 0
        self._pending_labels: list[str] = []
        self._dropped: list[str] = []

    def _fit_line(self, line: str, budget: int) -> tuple[str, int]:
        tokens = _count(line, self._tokenizer)
        budget = max(1, budget)
        if tokens <= budget:
            return line, tokens
        pieces = split_by_token_limit(line, self._tokenizer, budget)
        trimmed = pieces[0] if pieces else ""
        return trimmed, _count(trimmed, self._tokenizer)

    def _flush(self) -> None:
        if self._lines:
            if self.full:
                self._dropped.extend(self._pending_labels)
            else:
                self.chunks.append("\n".join(self._lines))
        self._lines = []
        self._pending_labels = []
        self._tokens = 0

    @property
    def full(self) -> bool:
        return len(self.chunks) >= self._max_chunks

    def add(self, block: ChunkBlock) -> None:
        label = block.label or "(unnamed block)"
        if not block.lines:
            return
        if self.full:
            self._dropped.append(label)
            return
        fitted = [self._fit_line(line, self._max_tokens) for line in block.lines]
        block_tokens = sum(tokens for _, tokens in fitted) + len(fitted) - 1
        separator = 1 if self._lines else 0
        if self._tokens + separator + block_tokens <= self._max_tokens:
            self._lines.extend(line for line, _ in fitted)
            self._tokens += separator + block_tokens
            self._pending_labels.append(label)
            return
        self._flush()
        # The flush may have used the last chunk, so check again.
        if self.full:
            self._dropped.append(label)
            return
        if block_tokens <= self._max_tokens:
            self._lines = [line for line, _ in fitted]
            self._tokens = block_tokens
            self._pending_labels = [label]
            return

        # The block needs several chunks and its head starts each of them, so
        # the head must leave room for a body. Drop trailing head lines until
        # it does; the first line names the sheet, so it goes last. The head is
        # never trimmed: for the overview, the head is the sheet list itself.
        head = fitted[: block.repeat]
        head_tokens = sum(tokens for _, tokens in head) + len(head) - 1
        while head and head_tokens > self._max_tokens // 2:
            head = head[:-1]
            head_tokens = sum(tokens for _, tokens in head) + len(head) - 1
        body_start = len(head)
        body_budget = self._max_tokens - head_tokens - 1
        used = 0
        piece = [line for line, _ in head]
        piece_tokens = head_tokens
        for line, _ in fitted[body_start:]:
            line, tokens = self._fit_line(line, body_budget)
            if piece_tokens + 1 + tokens > self._max_tokens:
                if self.full:
                    self._dropped.append(label)
                    return
                self.chunks.append("\n".join(piece))
                used += 1
                if used >= block.max_chunks:
                    self._dropped.append(label)
                    return
                piece = [entry for entry, _ in head]
                piece_tokens = head_tokens
            piece.append(line)
            piece_tokens += 1 + tokens
        self._lines = piece
        self._tokens = piece_tokens
        self._pending_labels = [label]

    def finish(self) -> list[str]:
        self._flush()
        if self._dropped:
            logger.warning(
                "Table chunk cap of %s reached; these were dropped or cut short: "
                "%s. Raise TABLE_MAX_CHUNKS_PER_FILE to keep them.",
                self._max_chunks,
                ", ".join(dict.fromkeys(self._dropped)),
            )
        return self.chunks


# ---------------------------------------------------------------------------
# Blocks
# ---------------------------------------------------------------------------


def _join_within_budget(
    items: list[str], tokenizer: BaseTokenizer, budget: int
) -> tuple[str, int]:
    """Items joined with the value separator until ``budget`` tokens are used;
    returns the text and how many items it holds (always at least one)."""
    separator_tokens = _count(VALUE_SEPARATOR, tokenizer)
    text = ""
    used = 0
    tokens = 0
    for item in items:
        item_tokens = _count(item, tokenizer) + (separator_tokens if used else 0)
        if tokens + item_tokens > budget and used > 0:
            break
        text = f"{text}{VALUE_SEPARATOR}{item}" if text else item
        tokens += item_tokens
        used += 1
    return text, used


def _sheet_title(file_name: str, summary: SheetSummary) -> str:
    names = [n for n in summary.names if n]
    if not names:
        return file_name
    if len(names) == 1:
        return f"{file_name} :: {names[0]}"
    return f"{file_name} :: sheets {', '.join(names)} (same columns)"


def _record_key_column(summary: SheetSummary) -> ColumnSummary | None:
    """The first column when it numbers the records (Serial#, S.No, an ID):
    unique values that are numbers or ids, in at least half of the rows."""
    if summary.synthetic_header or not summary.columns:
        return None
    col = summary.columns[0]
    if not col.name.strip() or col.non_empty < 0.5 * summary.row_count:
        return None
    unique = col.counts_complete and col.distinct == col.non_empty
    id_like = (
        is_id_column_name(col.name)
        or col.is_numeric
        or col.id_like_values == col.non_empty
    )
    return col if unique and id_like else None


def _records_note(summary: SheetSummary) -> str:
    """'16 with a Serial# value' when some rows (a note, a total line) leave
    the record-number column empty; '' otherwise. Without it, "17 rows" of
    16 records and one note is read as 17 records."""
    key = _record_key_column(summary)
    if key is None or key.non_empty >= summary.row_count:
        return ""
    return f"{key.non_empty} with a {key.name.strip()} value"


def _rows_text(summary: SheetSummary) -> str:
    note = _records_note(summary)
    return f"{summary.row_count} rows" + (f" ({note})" if note else "")


def _columns_line(summary: SheetSummary) -> str:
    if summary.synthetic_header:
        return f"Columns: {len(summary.header)} unnamed columns"
    labels = [column_label(name) for name in summary.header if name.strip()]
    return "Columns: " + ", ".join(labels)


def _overview_about_lines(
    summaries: list[SheetSummary], tokenizer: BaseTokenizer
) -> list[str]:
    """The text-sheet and title lines that fit in the overview. The caller
    checks which survived before deciding a text sheet needs no own block."""
    about: list[str] = []
    for summary in summaries:
        about.extend(line for line in summary.text_lines + summary.preamble if line)
    kept: list[str] = []
    used = 0
    for line in about:
        used += _count(line, tokenizer) + 1
        if used > _OVERVIEW_ABOUT_TOKENS and kept:
            break
        kept.append(line)
    return kept


def _overview_block(
    file_name: str, summaries: list[SheetSummary], tokenizer: BaseTokenizer
) -> ChunkBlock:
    sheet_names = [name for s in summaries for name in s.names if name]
    if sheet_names:
        lines = [
            f"Spreadsheet {file_name}: {len(sheet_names)} sheet"
            f"{'s' if len(sheet_names) != 1 else ''} ({', '.join(sheet_names)})"
        ]
    else:
        lines = [f"Spreadsheet {file_name}"]
    about = _overview_about_lines(summaries, tokenizer)
    if about:
        lines.append("About: " + " ".join(about))
    for summary in summaries:
        if summary.kind != SheetKind.TABLE:
            continue
        label = ", ".join(summary.names) if any(summary.names) else "Data"
        lines.append(
            f"Sheet {label}: {_rows_text(summary)}; " + _columns_line(summary)
        )
    return ChunkBlock(lines=lines, repeat=1, max_chunks=_OVERVIEW_MAX_CHUNKS)


def _all_rows_block(
    file_name: str,
    summary: SheetSummary,
    tokenizer: BaseTokenizer,
    max_tokens: int,
    max_chunks: int,
) -> ChunkBlock | None:
    if not summary.all_rows:
        return None
    repeat = 2
    note = _records_note(summary)
    lines = [
        f"{_sheet_title(file_name, summary)} (all {summary.row_count} rows"
        f"{', ' + note if note else ''})",
        _columns_line(summary),
        *summary.all_rows,
    ]
    # The repeated head starts every chunk, so the rows get less room than the
    # budget that made this sheet "small". Allow the chunks they really need,
    # or "all N rows" would not be true.
    head_tokens = sum(_count(line, tokenizer) + 1 for line in lines[:repeat])
    row_tokens = sum(_count(line, tokenizer) + 1 for line in lines[repeat:])
    per_chunk = max(1, max_tokens - head_tokens)
    needed = math.ceil(row_tokens / per_chunk)
    return ChunkBlock(lines=lines, repeat=repeat, max_chunks=max(max_chunks, needed))


def _value_range(col: ColumnSummary) -> str:
    if col.is_numeric and col.minimum is not None and col.maximum is not None:
        return f"{format_number(col.minimum)} ... {format_number(col.maximum)}"
    if col.id_min is not None and col.id_max is not None:
        return f"{col.id_min} ... {col.id_max}"
    return f"{col.text_min} ... {col.text_max}"


def _partial_suffix(used: int, total: int, complete: bool, noun: str) -> str:
    """Say so when a line lists only part of the values; a clipped breakdown
    that looks complete is worse than a short one that admits it."""
    if used >= total and complete:
        return ""
    return f" ({used} of {total}{'' if complete else '+'} {noun} shown)"


def _breakdown_lines(
    summary: SheetSummary,
    roles: list[ColumnRole],
    tokenizer: BaseTokenizer,
    line_budget: int,
) -> list[str]:
    breakdowns = summary.breakdowns
    numeric_columns = [
        (pos, col)
        for pos, col in enumerate(breakdowns.numeric_columns)
        if col < len(roles) and roles[col] == ColumnRole.NUMERIC
    ]
    lines: list[str] = []
    for category_col in breakdowns.category_columns:
        if category_col >= len(roles) or roles[category_col] != ColumnRole.CATEGORY:
            continue
        groups = breakdowns.by_category.get(category_col, {})
        if len(groups) < 2:
            continue
        category_name = summary.header[category_col]
        for pos, numeric_col in numeric_columns:
            if len(lines) >= _MAX_BREAKDOWN_LINES:
                return lines
            stats = summary.columns[numeric_col]
            unit = stats.unit or ""
            summable = stats.summable
            ranked = sorted(
                groups.items(),
                key=lambda kv: kv[1].sums[pos] if summable else kv[1].average(pos),
                reverse=True,
            )
            if summable:
                items = [
                    f"{key} {format_number(totals.sums[pos])}{unit} "
                    f"(avg {format_number(totals.average(pos))}{unit})"
                    for key, totals in ranked
                ]
                measure = "Total"
            else:
                items = [
                    f"{key} {format_number(totals.average(pos))}{unit}"
                    for key, totals in ranked
                ]
                measure = "Average"
            text, used = _join_within_budget(items, tokenizer, line_budget)
            lines.append(
                f"{measure} {summary.header[numeric_col]} by {category_name} "
                f"(highest first): {text}"
                f"{_partial_suffix(used, len(items), True, 'values')}"
            )
    date_column = breakdowns.date_column
    date_settled = (
        date_column is not None
        and date_column < len(roles)
        and roles[date_column] == ColumnRole.DATE
        and summary.columns[date_column].date_order == breakdowns.date_order
    )
    if date_settled and len(breakdowns.by_month) >= 2:
        months = sorted(breakdowns.by_month.items())
        for pos, numeric_col in numeric_columns[:_MAX_MONTHLY_NUMERIC_COLUMNS]:
            stats = summary.columns[numeric_col]
            unit = stats.unit or ""
            summable = stats.summable
            items = [
                f"{month} "
                f"{format_number(totals.sums[pos] if summable else totals.average(pos))}"
                f"{unit}"
                for month, totals in months
            ]
            text, used = _join_within_budget(items, tokenizer, line_budget)
            measure = "Total" if summable else "Average"
            lines.append(
                f"{measure} {summary.header[numeric_col]} by month: {text}"
                f"{_partial_suffix(used, len(items), breakdowns.months_complete, 'months')}"
            )
    return lines


def _summary_block(
    file_name: str,
    summary: SheetSummary,
    tokenizer: BaseTokenizer,
    line_budget: int,
) -> ChunkBlock:
    header = summary.header
    roles = [col.role() for col in summary.columns]
    lines = [
        f"{_sheet_title(file_name, summary)}: {_rows_text(summary)} x "
        f"{sum(1 for h in header if h.strip())} columns "
        "(summary; not every row is shown)",
        _columns_line(summary),
    ]

    dated = [
        (col.name, col.date_min, col.date_max)
        for col, role in zip(summary.columns, roles, strict=True)
        if role == ColumnRole.DATE and col.date_min and col.date_max
    ]
    if dated:
        lines.append(
            "Time range: "
            + VALUE_SEPARATOR.join(f"{name} {lo} to {hi}" for name, lo, hi in dated)
        )

    identifiers = [
        f"{column_label(col.name)} {_value_range(col)} "
        f"({col.distinct}{'+' if not col.counts_complete else ''} distinct)"
        for col, role in zip(summary.columns, roles, strict=True)
        if role == ColumnRole.IDENTIFIER
    ]
    if identifiers:
        lines.append("Identifiers: " + VALUE_SEPARATOR.join(identifiers))

    for col, role in zip(summary.columns, roles, strict=True):
        if role != ColumnRole.CATEGORY:
            continue
        ranked = col.counts.most_common()
        if ranked and ranked[0][1] > 1:
            items = [f"{clean_cell(value)} ({count})" for value, count in ranked]
            label = f"{column_label(col.name)} values (count)"
        else:
            items = [clean_cell(value) for value, _ in ranked]
            label = f"{column_label(col.name)} values"
        text, _ = _join_within_budget(items, tokenizer, line_budget)
        lines.append(f"{label}: {text}")

    numeric = [
        col
        for col, role in zip(summary.columns, roles, strict=True)
        if role == ColumnRole.NUMERIC
    ]
    if numeric:
        lines.append("Totals across all rows:")
        for col in numeric:
            average = col.total / col.non_empty if col.non_empty else 0.0
            unit = col.unit or ""
            figures = (
                [f"total {format_number(col.total)}{unit}"] if col.summable else []
            )
            figures += [
                f"average {format_number(average)}{unit}",
                f"min {format_number(col.minimum or 0.0)}{unit}",
                f"max {format_number(col.maximum or 0.0)}{unit}",
                f"count {col.non_empty}",
            ]
            lines.append(f"{column_label(col.name)}: " + "; ".join(figures))

    lines.extend(_breakdown_lines(summary, roles, tokenizer, line_budget))

    for idx, (col, role) in enumerate(zip(summary.columns, roles, strict=True)):
        if role != ColumnRole.TEXT or idx in summary.redundant_columns:
            continue
        values = [
            clean_cell(value)
            for value, _ in col.counts.most_common(_SUMMARY_TEXT_VALUES)
        ]
        text, _ = _join_within_budget(values, tokenizer, line_budget)
        lines.append(
            f"{column_label(col.name)} ({col.distinct}"
            f"{'+' if not col.counts_complete else ''} distinct; "
            f"most common first): {text}"
        )

    if summary.samples:
        names = [""] * len(header) if summary.synthetic_header else header
        lines.extend(f"Sample row: {format_row(names, row)}" for row in summary.samples)
    return ChunkBlock(lines=lines, repeat=1, max_chunks=_SUMMARY_MAX_CHUNKS)


def _frequent_values_blocks(
    file_name: str,
    summary: SheetSummary,
    tokenizer: BaseTokenizer,
    max_tokens: int,
    max_chunks: int,
) -> list[ChunkBlock]:
    """Further frequent values of the free-text columns the summary could only
    sample, round-robin, so every chunk covers every such column."""
    columns = [
        col
        for idx, col in enumerate(summary.columns)
        if col.role() == ColumnRole.TEXT and idx not in summary.redundant_columns
    ]
    if not columns or max_chunks <= 0:
        return []
    queues = [
        [clean_cell(value) for value, _ in col.counts.most_common()][
            _SUMMARY_TEXT_VALUES:
        ]
        for col in columns
    ]
    heading = f"{_sheet_title(file_name, summary)}: more values"
    # Each column line also costs a newline.
    share = max(
        1,
        (max_tokens - _count(heading, tokenizer) - len(columns)) // len(columns),
    )
    blocks: list[ChunkBlock] = []
    for _ in range(max_chunks):
        lines = [heading]
        for col, queue in zip(columns, queues, strict=True):
            if not queue:
                continue
            label = column_label(col.name)
            budget = share - _count(f"{label}: ", tokenizer)
            text, used = _join_within_budget(queue, tokenizer, budget)
            if used == 0:
                continue
            del queue[:used]
            lines.append(f"{label}: {text}")
        if len(lines) == 1:
            break
        blocks.append(ChunkBlock(lines=lines, repeat=1, max_chunks=1))
    return blocks


def _can_merge(into: SheetSummary, other: SheetSummary) -> bool:
    """Whether merging two same-header sheets keeps the breakdowns each has.

    Pooling values can push a category column past ``CATEGORY_MAX_DISTINCT``
    and cost the merged summary a breakdown each sheet had alone; two
    summaries are better than one that says less.
    """
    if not into.breakdowns.same_columns(other.breakdowns):
        return False
    for idx in into.breakdowns.category_columns:
        if idx >= len(into.columns) or idx >= len(other.columns):
            return False
        pooled = set(into.columns[idx].counts) | set(other.columns[idx].counts)
        if len(pooled) > CATEGORY_MAX_DISTINCT:
            return False
    # Dollars on one sheet and euros on the other do not add up.
    for mine, theirs in zip(into.columns, other.columns):
        if mine.unit and theirs.unit and mine.unit != theirs.unit:
            return False
    return True


def _merge_same_header_sheets(summaries: list[SheetSummary]) -> list[SheetSummary]:
    """Merge large sheets with the same columns (monthly tabs, for example)
    into one summary, when that loses no information."""
    merged: list[SheetSummary] = []
    by_header: dict[tuple[str, ...], SheetSummary] = {}
    for summary in summaries:
        if summary.kind != SheetKind.TABLE or summary.is_small:
            merged.append(summary)
            continue
        key = tuple(name.strip().lower() for name in summary.header)
        target = by_header.get(key)
        if target is not None and _can_merge(target, summary):
            target.merge(summary)
            continue
        if target is not None:
            logger.debug(
                "Sheets %s and %s share columns but are summarized separately: "
                "merging them would drop a breakdown.",
                target.names,
                summary.names,
            )
        by_header.setdefault(key, summary)
        merged.append(summary)
    return merged


def build_table_file_chunks(
    file_name: str,
    sheets: list[SheetRows],
    tokenizer: BaseTokenizer,
    max_tokens: int,
    full_rows_max_chunks: int,
    value_chunks_per_sheet: int,
    max_chunks: int,
) -> list[str]:
    """Chunk texts for one table file (all sheets of a workbook, or a CSV)."""
    summaries = [
        summarize_sheet(
            name=sheet.name,
            rows=sheet.open_rows(),
            tokenizer=tokenizer,
            all_rows_token_budget=full_rows_max_chunks * max_tokens,
        )
        for sheet in sheets
    ]
    summaries = _merge_same_header_sheets(
        [s for s in summaries if s.kind != SheetKind.EMPTY]
    )
    if not summaries:
        return []

    line_budget = max(1, max_tokens // 2)
    blocks: list[ChunkBlock] = [_overview_block(file_name, summaries, tokenizer)]
    in_overview = set(_overview_about_lines(summaries, tokenizer))
    # One block per sheet first, so hitting the cap costs every sheet its
    # extras instead of costing the last sheets everything.
    for summary in summaries:
        label = _sheet_title(file_name, summary)
        if summary.kind == SheetKind.TEXT:
            # Skip the block only when every line already reached the
            # overview; otherwise its text would appear nowhere.
            if any(line not in in_overview for line in summary.text_lines):
                blocks.append(
                    ChunkBlock(
                        lines=[label, *summary.text_lines],
                        repeat=1,
                        max_chunks=full_rows_max_chunks,
                    )
                )
        elif summary.is_small:
            block = _all_rows_block(
                file_name, summary, tokenizer, max_tokens, full_rows_max_chunks
            )
            if block is not None:
                blocks.append(block)
        else:
            blocks.append(_summary_block(file_name, summary, tokenizer, line_budget))
        if blocks and not blocks[-1].label:
            blocks[-1].label = label
    for summary in summaries:
        if summary.kind == SheetKind.TABLE and not summary.is_small:
            blocks.extend(
                _frequent_values_blocks(
                    file_name, summary, tokenizer, max_tokens, value_chunks_per_sheet
                )
            )

    packer = ChunkPacker(
        tokenizer=tokenizer, max_tokens=max_tokens, max_chunks=max_chunks
    )
    for block in blocks:
        packer.add(block)
    return packer.finish()
