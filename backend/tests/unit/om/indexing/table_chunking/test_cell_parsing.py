import pytest

from om.indexing.table_chunking.cell_parsing import clean_cell
from om.indexing.table_chunking.cell_parsing import column_label
from om.indexing.table_chunking.cell_parsing import date_order_hint
from om.indexing.table_chunking.cell_parsing import DateOrder
from om.indexing.table_chunking.cell_parsing import find_header_row
from om.indexing.table_chunking.cell_parsing import format_number
from om.indexing.table_chunking.cell_parsing import format_row
from om.indexing.table_chunking.cell_parsing import ID_VALUE_RE
from om.indexing.table_chunking.cell_parsing import is_id_column_name
from om.indexing.table_chunking.cell_parsing import max_or_other
from om.indexing.table_chunking.cell_parsing import min_or_other
from om.indexing.table_chunking.cell_parsing import natural_sort_key
from om.indexing.table_chunking.cell_parsing import parse_date
from om.indexing.table_chunking.cell_parsing import parse_number
from om.indexing.table_chunking.cell_parsing import text_line
from om.indexing.table_chunking.cell_parsing import unit_marker


@pytest.mark.parametrize(
    "value,expected",
    [
        ("1,234.50", 1234.5),
        ("₹4,500", 4500.0),
        ("$5", 5.0),
        ("-$5", -5.0),
        ("5€", 5.0),
        ("45%", 45.0),
        ("-12", -12.0),
        ("  7  ", 7.0),
        ("0", 0.0),
        ("", None),
        ("abc", None),
        ("$", None),
        ("nan", None),
        ("inf", None),
        ("TS-HYD-0042", None),
    ],
)
def test_parse_number(value: str, expected: float | None) -> None:
    assert parse_number(value) == expected


@pytest.mark.parametrize(
    "value,expected",
    [("45%", "%"), ("₹4,500", "₹"), ("-$5", "$"), ("5€", "€"), ("12", ""), ("", "")],
)
def test_unit_marker(value: str, expected: str) -> None:
    assert unit_marker(value) == expected


@pytest.mark.parametrize(
    "value,order,expected",
    [
        ("2025-03-11", None, "2025-03-11"),
        ("2025-03-11 00:00:00", None, "2025-03-11"),
        ("2025/3/11", None, "2025-03-11"),
        ("11-Mar-2025", None, "2025-03-11"),
        ("11 March 2025", None, "2025-03-11"),
        ("Mar 11, 2025", None, "2025-03-11"),
        ("Sept 1, 2025", None, "2025-09-01"),
        ("25/03/2025", None, "2025-03-25"),  # day > 12 settles it
        ("03/25/2025", None, "2025-03-25"),
        ("05/03/2025", None, None),  # ambiguous without an order
        ("05/03/2025", DateOrder.DAY_FIRST, "2025-03-05"),
        ("05/03/2025", DateOrder.MONTH_FIRST, "2025-05-03"),
        ("31/02/2025", None, None),  # no such day
        ("2025-02-30", None, None),
        ("hello", None, None),
    ],
)
def test_parse_date(value: str, order: DateOrder | None, expected: str | None) -> None:
    assert parse_date(value, order) == expected


def test_date_order_hint() -> None:
    assert date_order_hint("25/03/2025") is DateOrder.DAY_FIRST
    assert date_order_hint("03/25/2025") is DateOrder.MONTH_FIRST
    assert date_order_hint("05/03/2025") is None
    assert date_order_hint("2025-03-05") is None


def test_id_values_and_names() -> None:
    assert ID_VALUE_RE.match("PAY-001")
    assert ID_VALUE_RE.match("INV#42")
    assert ID_VALUE_RE.match("D-1001")
    assert not ID_VALUE_RE.match("TS-HYD-0042")
    assert is_id_column_name("id")
    assert is_id_column_name("order_uuid")
    assert is_id_column_name("Customer-Key")
    assert not is_id_column_name("idea")


def test_natural_sort_key() -> None:
    values = ["Project 10", "Project 2", "Project 1"]
    assert sorted(values, key=natural_sort_key) == [
        "Project 1",
        "Project 2",
        "Project 10",
    ]


@pytest.mark.parametrize(
    "number,expected",
    [(4500.0, "4500"), (1234.567, "1234.57"), (0.123456, "0.1235"), (-3.0, "-3")],
)
def test_format_number(number: float, expected: str) -> None:
    assert format_number(number) == expected


def test_clean_cell() -> None:
    assert clean_cell(" 2025-03-11 00:00:00 ") == "2025-03-11"
    assert clean_cell("2025-03-11T00:00") == "2025-03-11"
    assert clean_cell("2025-03-11 10:30:00") == "2025-03-11 10:30:00"
    assert clean_cell("3.14159265359") == "3.142"
    assert clean_cell("3.14") == "3.14"


def test_column_label() -> None:
    assert column_label("AcqPriceUSD") == "AcqPriceUSD (Acq Price USD)"
    assert column_label("amount_inr") == "amount_inr (amount inr)"
    assert column_label("Total MWh") == "Total MWh"
    assert column_label("district") == "district"
    assert column_label("  ") == ""


def test_find_header_row_simple() -> None:
    rows = [["case_id", "district", "amount"], ["PAY-001", "Hyd", "10"]]
    assert find_header_row(rows) == 0


def test_find_header_row_after_preamble() -> None:
    rows = [
        ["Grievance register", "", ""],
        ["Amounts in INR", "", ""],
        ["case_id", "district", "amount"],
        ["PAY-001", "Hyd", "10"],
        ["PAY-002", "Wgl", "20"],
    ]
    assert find_header_row(rows) == 2


def test_find_header_row_years_are_names() -> None:
    rows = [["Region", "2023", "2024"], ["North", "10", "20"], ["South", "5", "7"]]
    assert find_header_row(rows) == 0


def test_find_header_row_none_for_numbers_and_records() -> None:
    assert find_header_row([["1", "2", "3"], ["4", "5", "6"]]) is None
    assert find_header_row([["only one column"], ["more text"]]) is None
    # Records of the same shape are data, not a header.
    rows = [["PAY-001", "Open"], ["PAY-002", "Open"], ["PAY-003", "Closed"]]
    assert find_header_row(rows) is None


def test_format_row_and_text_line() -> None:
    assert format_row(["a", "", "c"], ["1", "x", " ", "extra"]) == "a=1, x, extra"
    assert text_line(["Readme", " ", "2025-01-01 00:00:00"]) == "Readme | 2025-01-01"


def test_min_max_or_other() -> None:
    assert min_or_other(None, 3.0) == 3.0
    assert min_or_other(2.0, None) == 2.0
    assert min_or_other("b", "a") == "a"
    assert max_or_other(None, None) is None
    assert max_or_other(1.0, 5.0) == 5.0
