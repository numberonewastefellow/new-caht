"""Parsing of single cells: numbers, dates, identifiers, column names, rows.

This is the leaf level of table chunking; nothing here knows about sheets,
summaries or chunks.
"""

import calendar
import math
import re
import unicodedata
from datetime import date
from enum import Enum
from typing import TypeVar

_ISO_DATE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?)?$"
)
_YEAR_SLASH_DATE_RE = re.compile(r"^(\d{4})/(\d{1,2})/(\d{1,2})$")
# 5/3/2024 or 5.3.2024: which part is the day is decided per column.
_NUMERIC_DATE_RE = re.compile(r"^(\d{1,2})([/.])(\d{1,2})\2(\d{4})$")
# 11-Mar-2025, 11 March 2025
_DAY_MONTH_NAME_RE = re.compile(r"^(\d{1,2})[ -]([A-Za-z]{3,9})\.?,?[ -](\d{4})$")
# Mar 11, 2025
_MONTH_NAME_DAY_RE = re.compile(r"^([A-Za-z]{3,9})\.?[ -](\d{1,2}),?[ -](\d{4})$")
_YEAR_RE = re.compile(r"^(?:19|20|21)\d{2}$")
# One letter run, an optional separator, then digits: PAY-001, INV#42, A12b.
ID_VALUE_RE = re.compile(r"^[A-Za-z]{1,10}[-_ #]?\d+[A-Za-z]?$")
_NAME_WORD_RE = re.compile(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|\d+")
_NAME_SPLIT_RE = re.compile(r"[\s_\-./]+")
_DIGIT_RUN_RE = re.compile(r"(\d+)")
_LONG_DECIMAL_RE = re.compile(r"^-?\d+\.\d{7,}$")
_ID_NAME_TOKENS = ("id", "uuid", "uid", "guid", "key")

VALUE_SEPARATOR = "; "

_Comparable = TypeVar("_Comparable", float, str)


class DateOrder(str, Enum):
    """Which part of ``5/3/2024`` is the day. Learned from a column's own
    values, never assumed from a locale."""

    DAY_FIRST = "day_first"
    MONTH_FIRST = "month_first"


def _is_currency_symbol(char: str) -> bool:
    # Unicode knows every currency symbol (₹, $, €, ...), so no list is kept.
    return unicodedata.category(char) == "Sc"


def parse_number(value: str) -> float | None:
    """The number in a cell such as ``1,234.50``, ``₹4,500``, ``-$5`` or
    ``45%``; None when the cell is not a number."""
    text = value.strip().replace(",", "").removesuffix("%").strip()
    if not text:
        return None
    # The sign belongs to the whole amount: -$5, not $-5.
    sign = ""
    if text[0] in ("+", "-"):
        sign, text = text[0], text[1:].lstrip()
    if text and _is_currency_symbol(text[0]):
        text = text[1:].lstrip()
    elif text and _is_currency_symbol(text[-1]):
        text = text[:-1].rstrip()
    if not text:
        return None
    try:
        number = float(sign + text)
    except ValueError:
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def unit_marker(value: str) -> str:
    """The unit a number carries (``%`` or a currency symbol), so totals keep
    it and percentages are never summed. Empty for a bare number."""
    text = value.strip()
    if not text:
        return ""
    if text.endswith("%"):
        return "%"
    if text[0] in ("+", "-"):
        text = text[1:].lstrip()
    if not text:
        return ""
    if _is_currency_symbol(text[0]):
        return text[0]
    if _is_currency_symbol(text[-1]):
        return text[-1]
    return ""


def natural_sort_key(value: str) -> tuple[tuple[int, int, str], ...]:
    """Orders "Project 2" before "Project 10"."""
    return tuple(
        (1, int(part), "") if part.isdigit() else (0, 0, part)
        for part in _DIGIT_RUN_RE.split(value)
        if part
    )


def _month_from_name(name: str) -> int | None:
    """Month number of a written month; any prefix of three or more letters
    works (Jan, Sept, September)."""
    text = name.lower().rstrip(".")
    if len(text) < 3:
        return None
    for number in range(1, 13):
        if calendar.month_name[number].lower().startswith(text):
            return number
    return None


def _iso_day(year: int, month: int, day: int) -> str | None:
    # date() rejects 31 February and the like, which a range check would not.
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def parse_date(value: str, order: DateOrder | None = None) -> str | None:
    """The day a cell names, as ``YYYY-MM-DD``, or None.

    ``order`` settles a bare ``5/3/2024``; without it such a cell gives None
    instead of a guess. A value with a part above 12 settles itself.
    """
    text = value.strip()
    if _ISO_DATE_RE.match(text):
        return _iso_day(int(text[:4]), int(text[5:7]), int(text[8:10]))

    match = _YEAR_SLASH_DATE_RE.match(text)
    if match:
        return _iso_day(int(match[1]), int(match[2]), int(match[3]))

    match = _NUMERIC_DATE_RE.match(text)
    if match:
        first, second, year = int(match[1]), int(match[3]), int(match[4])
        if first > 12:
            return _iso_day(year, second, first)
        if second > 12:
            return _iso_day(year, first, second)
        if order is DateOrder.DAY_FIRST:
            return _iso_day(year, second, first)
        if order is DateOrder.MONTH_FIRST:
            return _iso_day(year, first, second)
        return None

    match = _DAY_MONTH_NAME_RE.match(text)
    if match:
        month = _month_from_name(match[2])
        return _iso_day(int(match[3]), month, int(match[1])) if month else None

    match = _MONTH_NAME_DAY_RE.match(text)
    if match:
        month = _month_from_name(match[1])
        return _iso_day(int(match[3]), month, int(match[2])) if month else None

    return None


def date_order_hint(value: str) -> DateOrder | None:
    """The order one value proves, when one of its parts is above 12."""
    match = _NUMERIC_DATE_RE.match(value.strip())
    if not match:
        return None
    first, second = int(match[1]), int(match[3])
    if first > 12 and second <= 12:
        return DateOrder.DAY_FIRST
    if second > 12 and first <= 12:
        return DateOrder.MONTH_FIRST
    return None


def is_id_column_name(name: str) -> bool:
    """Whether a column name reads like an identifier (``id``, ``order_uuid``)."""
    lowered = name.lower().strip().replace("-", "_")
    return lowered in _ID_NAME_TOKENS or any(
        lowered.endswith(f"_{token}") for token in _ID_NAME_TOKENS
    )


def format_number(number: float) -> str:
    if abs(number) < 1e15 and number == int(number):
        return str(int(number))
    if abs(number) >= 1000:
        return f"{number:.2f}"
    return f"{number:.4g}"


def clean_cell(value: str) -> str:
    """Shorter cell text with the same meaning: midnight timestamps become
    dates and long decimals are rounded."""
    text = value.strip()
    if (
        _ISO_DATE_RE.match(text)
        and len(text) > 10
        and text[10:].strip("T ") in ("00:00:00", "00:00")
    ):
        return text[:10]
    if _LONG_DECIMAL_RE.match(text):
        return format_number(float(text))
    return text


def _name_words(name: str) -> list[str]:
    words: list[str] = []
    for part in _NAME_SPLIT_RE.split(name):
        pending = ""
        for piece in _NAME_WORD_RE.findall(part):
            # A lone capital joins the next piece, so "MWh" stays one word.
            if len(piece) == 1 and piece.isupper():
                pending += piece
                continue
            words.append(pending + piece)
            pending = ""
        if pending:
            words.append(pending)
    return words


def column_label(name: str) -> str:
    """The column name plus a readable alias when the name is squashed
    together (``AcqPriceUSD`` -> ``AcqPriceUSD (Acq Price USD)``)."""
    stripped = name.strip()
    if not stripped:
        return ""
    if any(ch.isspace() for ch in stripped):
        return stripped
    alias = " ".join(_name_words(stripped))
    if not alias or alias == stripped:
        return stripped
    return f"{stripped} ({alias})"


def _cell_pattern(value: str) -> str:
    """A cell's pattern with digit and letter runs collapsed, so ``PAY-9`` and
    ``PAY-10`` match and a run of records is not taken for a header."""
    pattern = re.sub(r"\d+", "9", value.strip())
    return re.sub(r"[A-Za-z]+", "a", pattern)


def _reads_as_column_name(value: str) -> bool:
    """Whether a cell reads as a column name. Years count: in
    ``Region,2023,2024`` the years are column names."""
    text = value.strip()
    if _YEAR_RE.match(text):
        return True
    return parse_number(text) is None and parse_date(text) is None


def _rows_look_alike(row: list[str], next_row: list[str]) -> bool:
    """True when two rows have the same pattern in the columns holding digits
    (``PAY-001`` above ``PAY-002``): they are both data."""
    pairs = [
        (cell.strip(), below.strip())
        for cell, below in zip(row, next_row)
        if cell.strip() and below.strip() and any(ch.isdigit() for ch in cell + below)
    ]
    if not pairs:
        return False
    numbers_above = [cell for cell, _ in pairs if parse_number(cell) is not None]
    years_above = sum(1 for cell in numbers_above if _YEAR_RE.match(cell))
    years_below = sum(1 for _, below in pairs if _YEAR_RE.match(below))
    # Several year columns above rows without years is a header row. A single
    # number that happens to look like a year gets no such exemption.
    if (
        len(numbers_above) >= 2
        and years_above == len(numbers_above)
        and not years_below
    ):
        return False
    same = sum(
        1 for cell, below in pairs if _cell_pattern(cell) == _cell_pattern(below)
    )
    return same * 2 >= len(pairs)


def filled_cell_count(row: list[str]) -> int:
    return sum(1 for cell in row if cell.strip())


def find_header_row(rows: list[list[str]]) -> int | None:
    """Index of the header row among the first rows of a sheet, or None when
    there is none (a single text column, or data from the first row)."""
    widths = [filled_cell_count(row) for row in rows]
    max_width = max(widths, default=0)
    if max_width <= 1:
        return None
    min_width = max(2, math.ceil(max_width * 0.5))
    for idx, row in enumerate(rows):
        filled = [cell.strip() for cell in row if cell.strip()]
        if len(filled) < min_width:
            continue
        names = [cell for cell in filled if _reads_as_column_name(cell)]
        if len(names) < 0.6 * len(filled):
            continue
        if len(set(filled)) < 0.6 * len(filled):
            continue
        if idx + 1 < len(rows) and _rows_look_alike(row, rows[idx + 1]):
            continue
        if idx > 0 and _rows_look_alike(rows[idx - 1], row):
            continue
        return idx
    return None


def format_row(column_names: list[str], row: list[str]) -> str:
    """``name=value`` pairs; a cell without a column name keeps its value."""
    parts: list[str] = []
    for idx, raw in enumerate(row):
        value = clean_cell(raw)
        if not value:
            continue
        name = column_names[idx].strip() if idx < len(column_names) else ""
        parts.append(f"{name}={value}" if name else value)
    return ", ".join(parts)


def text_line(row: list[str]) -> str:
    return " | ".join(clean_cell(cell) for cell in row if cell.strip())


def min_or_other(a: _Comparable | None, b: _Comparable | None) -> _Comparable | None:
    if a is None:
        return b
    if b is None:
        return a
    return min(a, b)


def max_or_other(a: _Comparable | None, b: _Comparable | None) -> _Comparable | None:
    if a is None:
        return b
    if b is None:
        return a
    return max(a, b)
