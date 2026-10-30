"""What one pass over a sheet learns: column statistics, breakdowns, samples."""

from collections import Counter
from collections.abc import Callable
from collections.abc import Iterator
from enum import Enum

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from om.indexing.table_chunking.cell_parsing import date_order_hint
from om.indexing.table_chunking.cell_parsing import DateOrder
from om.indexing.table_chunking.cell_parsing import ID_VALUE_RE
from om.indexing.table_chunking.cell_parsing import is_id_column_name
from om.indexing.table_chunking.cell_parsing import max_or_other
from om.indexing.table_chunking.cell_parsing import min_or_other
from om.indexing.table_chunking.cell_parsing import natural_sort_key
from om.indexing.table_chunking.cell_parsing import parse_date
from om.indexing.table_chunking.cell_parsing import parse_number
from om.indexing.table_chunking.cell_parsing import unit_marker

# A text column with at most this many distinct values is a category.
CATEGORY_MAX_DISTINCT = 50
# Distinct values counted per column; later new values are not counted, which
# keeps memory flat on very large sheets.
_MAX_COUNTED_VALUES = 20_000
_MAX_COUNTED_MONTHS = 1200


class ColumnRole(str, Enum):
    IDENTIFIER = "identifier"
    DATE = "date"
    NUMERIC = "numeric"
    CATEGORY = "category"
    TEXT = "text"
    CONTACT = "contact"
    EMPTY = "empty"


class SheetKind(str, Enum):
    TABLE = "table"
    TEXT = "text"
    EMPTY = "empty"


class SheetRows(BaseModel):
    """One sheet (or a CSV file). Each ``open_rows()`` call returns a fresh
    iterator over its CSV rows."""

    model_config = ConfigDict(frozen=True)

    name: str
    open_rows: Callable[[], Iterator[list[str]]]


class ColumnSummary:
    """Running statistics of one column."""

    __slots__ = (
        "name",
        "non_empty",
        "is_numeric",
        "unit",
        "units_mixed",
        "total",
        "minimum",
        "maximum",
        "is_date",
        # Both readings of 5/3/2024 are tracked until a value settles the order.
        "date_min_day_first",
        "date_max_day_first",
        "date_min_month_first",
        "date_max_month_first",
        "has_ambiguous_dates",
        "day_first_hints",
        "month_first_hints",
        "counts",
        "counts_complete",
        "id_like_values",
        "contact_values",
        "text_min",
        "text_max",
        "id_min",
        "id_max",
    )

    def __init__(self, name: str) -> None:
        self.name = name
        self.non_empty = 0
        self.is_numeric = True
        # "%", "$", "₹" or "" once a number is seen; None before.
        self.unit: str | None = None
        self.units_mixed = False
        self.total = 0.0
        self.minimum: float | None = None
        self.maximum: float | None = None
        self.is_date = True
        self.date_min_day_first: str | None = None
        self.date_max_day_first: str | None = None
        self.date_min_month_first: str | None = None
        self.date_max_month_first: str | None = None
        self.has_ambiguous_dates = False
        self.day_first_hints = 0
        self.month_first_hints = 0
        self.counts: Counter[str] = Counter()
        self.counts_complete = True
        self.id_like_values = 0
        self.contact_values = 0
        self.text_min: str | None = None
        self.text_max: str | None = None
        self.id_min: str | None = None
        self.id_max: str | None = None

    def add_value(self, value: str) -> None:
        self.non_empty += 1
        if self.is_numeric:
            number = parse_number(value)
            if number is None:
                self.is_numeric = False
            else:
                marker = unit_marker(value)
                if self.unit is None:
                    self.unit = marker
                elif self.unit != marker:
                    self.unit = ""
                    self.units_mixed = True
                self.total += number
                self.minimum = (
                    number if self.minimum is None else min(self.minimum, number)
                )
                self.maximum = (
                    number if self.maximum is None else max(self.maximum, number)
                )
        if self.is_date:
            day_first = parse_date(value, DateOrder.DAY_FIRST)
            month_first = parse_date(value, DateOrder.MONTH_FIRST)
            if day_first is None or month_first is None:
                self.is_date = False
            else:
                self.date_min_day_first = min_or_other(
                    self.date_min_day_first, day_first
                )
                self.date_max_day_first = max_or_other(
                    self.date_max_day_first, day_first
                )
                self.date_min_month_first = min_or_other(
                    self.date_min_month_first, month_first
                )
                self.date_max_month_first = max_or_other(
                    self.date_max_month_first, month_first
                )
                if day_first != month_first:
                    self.has_ambiguous_dates = True
                hint = date_order_hint(value)
                if hint is DateOrder.DAY_FIRST:
                    self.day_first_hints += 1
                elif hint is DateOrder.MONTH_FIRST:
                    self.month_first_hints += 1
        if value in self.counts or len(self.counts) < _MAX_COUNTED_VALUES:
            self.counts[value] += 1
        else:
            self.counts_complete = False
        if ID_VALUE_RE.match(value):
            self.id_like_values += 1
            if self.id_min is None or natural_sort_key(value) < natural_sort_key(
                self.id_min
            ):
                self.id_min = value
            if self.id_max is None or natural_sort_key(value) > natural_sort_key(
                self.id_max
            ):
                self.id_max = value
        if "@" in value or "://" in value:
            self.contact_values += 1
        self.text_min = value if self.text_min is None else min(self.text_min, value)
        self.text_max = value if self.text_max is None else max(self.text_max, value)

    def merge(self, other: "ColumnSummary") -> None:
        if other.non_empty == 0:
            return
        self.non_empty += other.non_empty
        self.is_numeric = self.is_numeric and other.is_numeric
        self.units_mixed = self.units_mixed or other.units_mixed
        if self.unit is None:
            self.unit = other.unit
        elif other.unit is not None and other.unit != self.unit:
            self.unit = ""
            self.units_mixed = True
        self.total += other.total
        self.minimum = min_or_other(self.minimum, other.minimum)
        self.maximum = max_or_other(self.maximum, other.maximum)
        self.is_date = self.is_date and other.is_date
        self.has_ambiguous_dates = self.has_ambiguous_dates or other.has_ambiguous_dates
        self.day_first_hints += other.day_first_hints
        self.month_first_hints += other.month_first_hints
        self.date_min_day_first = min_or_other(
            self.date_min_day_first, other.date_min_day_first
        )
        self.date_max_day_first = max_or_other(
            self.date_max_day_first, other.date_max_day_first
        )
        self.date_min_month_first = min_or_other(
            self.date_min_month_first, other.date_min_month_first
        )
        self.date_max_month_first = max_or_other(
            self.date_max_month_first, other.date_max_month_first
        )
        self.counts.update(other.counts)
        self.counts_complete = self.counts_complete and other.counts_complete
        self.id_like_values += other.id_like_values
        self.contact_values += other.contact_values
        self.text_min = min_or_other(self.text_min, other.text_min)
        self.text_max = max_or_other(self.text_max, other.text_max)
        for candidate in (other.id_min, other.id_max):
            if candidate is None:
                continue
            if self.id_min is None or natural_sort_key(candidate) < natural_sort_key(
                self.id_min
            ):
                self.id_min = candidate
            if self.id_max is None or natural_sort_key(candidate) > natural_sort_key(
                self.id_max
            ):
                self.id_max = candidate

    @property
    def summable(self) -> bool:
        """Whether adding the numbers gives a real total: percentages do not
        add up, and dollars plus euros are no total."""
        return self.unit != "%" and not self.units_mixed

    @property
    def date_order(self) -> DateOrder | None:
        """The reading this column's values prove; None when nothing settles
        it or the values disagree."""
        if self.day_first_hints and not self.month_first_hints:
            return DateOrder.DAY_FIRST
        if self.month_first_hints and not self.day_first_hints:
            return DateOrder.MONTH_FIRST
        return None

    @property
    def dates_unresolved(self) -> bool:
        """Every value is a date, but which part is the day is unknown."""
        return self.is_date and self.has_ambiguous_dates and self.date_order is None

    def _settled_date(
        self, day_first: str | None, month_first: str | None
    ) -> str | None:
        if not self.has_ambiguous_dates:
            return day_first  # both readings agree on every value
        order = self.date_order
        if order is DateOrder.DAY_FIRST:
            return day_first
        if order is DateOrder.MONTH_FIRST:
            return month_first
        return None

    @property
    def date_min(self) -> str | None:
        return self._settled_date(self.date_min_day_first, self.date_min_month_first)

    @property
    def date_max(self) -> str | None:
        return self._settled_date(self.date_max_day_first, self.date_max_month_first)

    @property
    def distinct(self) -> int:
        return len(self.counts)

    def role(self) -> ColumnRole:
        if self.non_empty == 0:
            return ColumnRole.EMPTY
        many_values = self.distinct > CATEGORY_MAX_DISTINCT or not self.counts_complete
        if many_values and (
            is_id_column_name(self.name) or self.id_like_values >= 0.8 * self.non_empty
        ):
            return ColumnRole.IDENTIFIER
        if self.is_date and self.date_min is not None:
            return ColumnRole.DATE
        if self.is_numeric:
            return ColumnRole.NUMERIC
        if self.contact_values >= 0.5 * self.non_empty:
            return ColumnRole.CONTACT
        if not many_values:
            return ColumnRole.CATEGORY
        return ColumnRole.TEXT


class ColumnTotals(BaseModel):
    """Running sum and count of each numeric column within one group."""

    sums: list[float]
    counts: list[int]

    @classmethod
    def zeros(cls, size: int) -> "ColumnTotals":
        return cls(sums=[0.0] * size, counts=[0] * size)

    def add(self, numbers: list[float | None]) -> None:
        for idx, number in enumerate(numbers):
            if number is not None:
                self.sums[idx] += number
                self.counts[idx] += 1

    def merge(self, other: "ColumnTotals") -> None:
        for idx in range(len(self.sums)):
            self.sums[idx] += other.sums[idx]
            self.counts[idx] += other.counts[idx]

    def average(self, idx: int) -> float:
        return self.sums[idx] / self.counts[idx] if self.counts[idx] else 0.0


class CategoryBreakdowns(BaseModel):
    """Totals of numeric columns grouped by category values and by month."""

    category_columns: list[int] = Field(default_factory=list)
    numeric_columns: list[int] = Field(default_factory=list)
    date_column: int | None = None
    date_order: DateOrder | None = None
    # category column -> category value -> totals aligned with numeric_columns
    by_category: dict[int, dict[str, ColumnTotals]] = Field(default_factory=dict)
    # month (YYYY-MM) -> totals aligned with numeric_columns
    by_month: dict[str, ColumnTotals] = Field(default_factory=dict)
    months_complete: bool = True

    def same_columns(self, other: "CategoryBreakdowns") -> bool:
        return (
            self.category_columns == other.category_columns
            and self.numeric_columns == other.numeric_columns
            and self.date_column == other.date_column
            and self.date_order == other.date_order
        )

    def add_row(self, cells: list[str]) -> None:
        if not self.numeric_columns:
            return
        numbers = [
            parse_number(cells[col]) if col < len(cells) else None
            for col in self.numeric_columns
        ]
        for col in self.category_columns:
            key = cells[col].strip() if col < len(cells) else ""
            if not key:
                continue
            groups = self.by_category.setdefault(col, {})
            if key not in groups:
                if len(groups) >= CATEGORY_MAX_DISTINCT:
                    continue
                groups[key] = ColumnTotals.zeros(len(self.numeric_columns))
            groups[key].add(numbers)
        if self.date_column is not None and self.date_column < len(cells):
            day = parse_date(cells[self.date_column], self.date_order)
            if day is not None:
                month = day[:7]
                if month not in self.by_month:
                    if len(self.by_month) >= _MAX_COUNTED_MONTHS:
                        self.months_complete = False
                        return
                    self.by_month[month] = ColumnTotals.zeros(len(self.numeric_columns))
                self.by_month[month].add(numbers)

    def merge(self, other: "CategoryBreakdowns") -> None:
        if not self.same_columns(other):
            # Different columns were picked: keep only this side.
            return
        for col, groups in other.by_category.items():
            mine = self.by_category.setdefault(col, {})
            for key, totals in groups.items():
                if key in mine:
                    mine[key].merge(totals)
                elif len(mine) < CATEGORY_MAX_DISTINCT:
                    mine[key] = totals.model_copy(deep=True)
        for month, totals in other.by_month.items():
            if month in self.by_month:
                self.by_month[month].merge(totals)
            elif len(self.by_month) < _MAX_COUNTED_MONTHS:
                self.by_month[month] = totals.model_copy(deep=True)
            else:
                self.months_complete = False
        self.months_complete = self.months_complete and other.months_complete


class SheetSummary(BaseModel):
    """What one streaming pass over a sheet learned about it."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Sheet names; more than one after sheets with the same columns are merged.
    names: list[str]
    kind: SheetKind
    header: list[str] = Field(default_factory=list)
    # True when the sheet has no header row and the column names are made up.
    synthetic_header: bool = False
    # Title rows above the header.
    preamble: list[str] = Field(default_factory=list)
    # Lines of a text-only sheet.
    text_lines: list[str] = Field(default_factory=list)
    row_count: int = 0
    columns: list[ColumnSummary] = Field(default_factory=list)
    breakdowns: CategoryBreakdowns = Field(default_factory=CategoryBreakdowns)
    samples: list[list[str]] = Field(default_factory=list)
    # Formatted rows while they fit the all-rows budget; None once they do not.
    all_rows: list[str] | None = Field(default_factory=list)
    # Columns whose values sit inside another column (a first name inside a
    # full name); they get no value lists.
    redundant_columns: set[int] = Field(default_factory=set)

    @property
    def is_small(self) -> bool:
        return self.all_rows is not None

    def merge(self, other: "SheetSummary") -> None:
        self.names.extend(other.names)
        self.row_count += other.row_count
        for mine, theirs in zip(self.columns, other.columns, strict=True):
            mine.merge(theirs)
        self.breakdowns.merge(other.breakdowns)
        self.all_rows = None


class ChunkBlock(BaseModel):
    """Lines that stay together. When a block needs several chunks, its first
    ``repeat`` lines start each of them."""

    lines: list[str]
    repeat: int = 1
    max_chunks: int = 1
    # Named in the log when the chunk cap drops this block.
    label: str = ""
