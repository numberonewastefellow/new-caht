import pytest

from om.evals.rag_benchmark.figure_match import find_dates
from om.evals.rag_benchmark.figure_match import find_numbers
from om.evals.rag_benchmark.figure_match import match_expected_figures
from om.evals.rag_benchmark.figure_match import normalize_number
from om.evals.rag_benchmark.models import ExpectedFigure


def _matches(text: str, value: float | str, **kwargs: object) -> bool:
    return match_expected_figures(text, [ExpectedFigure(value=value, **kwargs)])[0]  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "text",
    [
        "₹1,23,456",
        "Rs 1,23,456",
        "Rs.1,23,456",
        "INR 123,456",
        "123456",
        "1.23 lakh",
        "1.23 lakhs",
        "౧,౨౩,౪౫౬",
        "१,२३,४५६",
        "రూ.1,23,456",
    ],
)
def test_known_forms_match_123456(text: str) -> None:
    assert _matches(f"The sanctioned amount is {text} only.", 123456)


@pytest.mark.parametrize(
    "text",
    ["TS-HYD-0042", "APP-LND-00042", "case 2026/0042", "Sec 42A", "v42", "x-42"],
)
def test_identifier_digits_never_match(text: str) -> None:
    assert not _matches(text, 42)
    assert find_numbers(text) == []


def test_crore_and_indic_multiplier_words() -> None:
    assert normalize_number("Rs 2.5 crore") == 25_000_000
    assert normalize_number("2 करोड़ रुपये") == 20_000_000
    assert normalize_number("3 లక్షలు") == 300_000
    assert normalize_number("15 thousand") == 15_000
    assert normalize_number("no figure here") is None


def test_integer_lakh_is_exact_decimal_lakh_is_rounded() -> None:
    assert not _matches("3 lakh", 312_000)
    assert _matches("3.12 lakh", 312_000)
    # "1.2 lakh" states 1,15,000 .. 1,25,000
    assert _matches("1.2 lakh", 123_456)
    assert not _matches("1.2 lakh", 126_000)


def test_tolerance() -> None:
    assert _matches("about 1,005 cases", 1000, tolerance=5)
    assert not _matches("about 1,006 cases", 1000, tolerance=5)
    assert not _matches("1,001", 1000)


def test_percentages_and_decimals() -> None:
    assert _matches("an increase of 12.5%", 12.5)
    assert _matches("రేటు 7.25 శాతం", 7.25)
    assert not _matches("12.5%", 125)


def test_dates_in_all_supported_forms() -> None:
    for text in [
        "2026-03-31",
        "31-03-2026",
        "31/03/2026",
        "31.03.2026",
        "31st March 2026",
        "March 31, 2026",
        "31 Mar 2026",
        "౩౧ మార్చి ౨౦౨౬",
        "31 मार्च 2026",
    ]:
        assert _matches(f"Last date: {text}.", "2026-03-31", unit="date"), text
    assert not _matches("Last date: 30-03-2026", "2026-03-31", unit="date")


def test_date_digits_are_not_figures() -> None:
    assert find_numbers("on 31-03-2026") == []
    assert find_dates("31-02-2026") == []  # invalid calendar date ignored


def test_one_result_per_figure() -> None:
    figures = [ExpectedFigure(value=500), ExpectedFigure(value=700)]
    assert match_expected_figures("Fee Rs 500 per application", figures) == [
        True,
        False,
    ]
    assert match_expected_figures("anything", []) == []


def test_comma_separated_rows() -> None:
    # Extracted CSV/XLSX rows: a figure right after a text cell still counts.
    assert _matches("LND-WGL-01234,Warangal,Sale Deed,1250,Approved", 1250)
    assert not _matches("LND-WGL-01234,Warangal", 1234)
