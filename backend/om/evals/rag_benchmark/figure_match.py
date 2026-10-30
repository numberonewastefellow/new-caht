"""Deterministic figure matching for answers in English, Telugu and Hindi.

Handles Indian digit grouping (1,23,456), lakh/crore (and their Telugu/Hindi
words), currency prefixes (Rs, Rs., INR, the rupee sign), Telugu and
Devanagari digits, percentages and dates. Digits glued to identifiers such
as ``TS-HYD-0042`` or ``Sec 22A`` are never read as figures.
"""

import re
from dataclasses import dataclass
from datetime import date

from om.evals.rag_benchmark.models import ExpectedFigure

_FLOAT_EPS = 1e-6

# Telugu U+0C66..U+0C6F and Devanagari U+0966..U+096F digits -> ASCII.
_DIGIT_TABLE = {0x0C66 + i: ord("0") + i for i in range(10)}
_DIGIT_TABLE.update({0x0966 + i: ord("0") + i for i in range(10)})

_MULTIPLIERS: dict[str, float] = {
    "thousand": 1e3,
    "lakhs": 1e5,
    "lakh": 1e5,
    "lacs": 1e5,
    "lac": 1e5,
    "crores": 1e7,
    "crore": 1e7,
    "cr": 1e7,
    "million": 1e6,
    # Telugu
    "వేలు": 1e3,
    "వేల": 1e3,
    "లక్షలు": 1e5,
    "లక్షల": 1e5,
    "లక్ష": 1e5,
    "కోట్లు": 1e7,
    "కోట్ల": 1e7,
    "కోటి": 1e7,
    # Hindi
    "हज़ार": 1e3,
    "हजार": 1e3,
    "लाख": 1e5,
    "करोड़": 1e7,
    "करोड": 1e7,
}
_UNIT_SCALES = {"lakh": 1e5, "crore": 1e7}
# Longest first so "lakhs" wins over "lakh" and "crore" over "cr".
_MULT_ALT = "|".join(re.escape(m) for m in sorted(_MULTIPLIERS, key=len, reverse=True))
_CURRENCY = r"(?:₹|Rs\.?|INR|రూ\.?|रु\.?|रुपये)"

_NUMBER_RE = re.compile(
    # Not glued to an identifier, and not the tail of a grouped number "1,234".
    r"(?<![A-Za-z0-9_\-/.])(?<!\d,)"
    rf"(?:{_CURRENCY}\s*)?"
    r"(?P<num>(?:\d{1,3}(?:,\d{2,3})+|\d+)(?:\.(?P<dec>\d+))?)"
    r"(?:st|nd|rd|th)?"  # ordinals: "15th of every month"
    rf"(?:\s*(?P<mult>{_MULT_ALT}))?"
    r"(?![A-Za-z0-9\-/]|,\d)",
    flags=re.IGNORECASE,
)

_MONTHS: dict[str, int] = {}
for _idx, _names in enumerate(
    [
        ("january", "jan", "జనవరి", "जनवरी"),
        ("february", "feb", "ఫిబ్రవరి", "फ़रवरी", "फरवरी"),
        ("march", "mar", "మార్చి", "मार्च"),
        ("april", "apr", "ఏప్రిల్", "अप्रैल"),
        ("may", "మే", "मई"),
        ("june", "jun", "జూన్", "जून"),
        ("july", "jul", "జూలై", "जुलाई"),
        ("august", "aug", "ఆగస్టు", "अगस्त"),
        ("september", "sep", "sept", "సెప్టెంబర్", "सितंबर", "सितम्बर"),
        ("october", "oct", "అక్టోబర్", "अक्टूबर"),
        ("november", "nov", "నవంబర్", "नवंबर", "नवम्बर"),
        ("december", "dec", "డిసెంబర్", "दिसंबर", "दिसम्बर"),
    ],
    start=1,
):
    for _name in _names:
        _MONTHS[_name] = _idx
_MONTH_ALT = "|".join(re.escape(m) for m in sorted(_MONTHS, key=len, reverse=True))

_DATE_ISO_RE = re.compile(r"(?<!\d)(\d{4})-(\d{1,2})-(\d{1,2})(?!\d)")
_DATE_DMY_RE = re.compile(r"(?<!\d)(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})(?!\d)")
_DATE_D_MON_Y_RE = re.compile(
    rf"(?<!\d)(\d{{1,2}})(?:st|nd|rd|th)?\s+({_MONTH_ALT})\.?,?\s+(\d{{4}})(?!\d)",
    flags=re.IGNORECASE,
)
_DATE_MON_D_Y_RE = re.compile(
    rf"({_MONTH_ALT})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s+(\d{{4}})(?!\d)",
    flags=re.IGNORECASE,
)


@dataclass(frozen=True)
class FoundNumber:
    value: float
    # Half of the smallest unit a decimal lakh/crore form states,
    # e.g. "1.23 lakh" -> 500. 0 for plain numbers.
    rounding: float
    text: str


def normalize_digits(text: str) -> str:
    return text.translate(_DIGIT_TABLE)


def _parse_match(match: re.Match[str]) -> FoundNumber:
    raw = match.group("num").replace(",", "")
    value = float(raw)
    mult_word = match.group("mult")
    rounding = 0.0
    if mult_word:
        mult = _MULTIPLIERS[mult_word.lower()]
        value *= mult
        decimals = len(match.group("dec") or "")
        # "1.23 lakh" is a rounded statement of 1,23,xxx; "3 lakh" is exact.
        if decimals:
            rounding = 0.5 * (10**-decimals) * mult
    return FoundNumber(value=value, rounding=rounding, text=match.group(0))


def find_numbers(text: str) -> list[FoundNumber]:
    """All standalone figures in ``text`` (identifier digits and dates skipped)."""
    return [_parse_match(m) for m in _NUMBER_RE.finditer(normalize_digits(text))]


def normalize_number(text: str) -> float | None:
    """Value of the first figure in ``text`` (e.g. "Rs 1.5 crore" -> 15000000.0)."""
    found = find_numbers(text)
    return found[0].value if found else None


def _safe_date(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def find_dates(text: str) -> list[date]:
    text = normalize_digits(text)
    found: list[date | None] = []
    for m in _DATE_ISO_RE.finditer(text):
        found.append(_safe_date(int(m.group(1)), int(m.group(2)), int(m.group(3))))
    for m in _DATE_DMY_RE.finditer(text):
        found.append(_safe_date(int(m.group(3)), int(m.group(2)), int(m.group(1))))
    for m in _DATE_D_MON_Y_RE.finditer(text):
        found.append(
            _safe_date(int(m.group(3)), _MONTHS[m.group(2).lower()], int(m.group(1)))
        )
    for m in _DATE_MON_D_Y_RE.finditer(text):
        found.append(
            _safe_date(int(m.group(3)), _MONTHS[m.group(1).lower()], int(m.group(2)))
        )
    return [d for d in found if d is not None]


def _figure_in(
    figure: ExpectedFigure, numbers: list[FoundNumber], dates: list[date]
) -> bool:
    if figure.unit == "date":
        target = date.fromisoformat(str(figure.value))
        return target in dates
    value = float(figure.value)
    # unit "lakh"/"crore": the value is stated in that unit (e.g. a table column
    # "Allocation (Rs lakh)"), so both "16.8" and "16,80,000" / "16.8 lakh" count.
    scale = _UNIT_SCALES.get((figure.unit or "").lower())
    targets = [value] if scale is None else [value, value * scale]
    for number in numbers:
        allowed = max(figure.tolerance, number.rounding) + _FLOAT_EPS
        if any(abs(number.value - target) <= allowed for target in targets):
            return True
    return False


def match_expected_figures(text: str, figures: list[ExpectedFigure]) -> list[bool]:
    """One bool per expected figure: does ``text`` state it (within tolerance)?"""
    if not figures:
        return []
    numbers = find_numbers(text)
    dates = find_dates(text) if any(f.unit == "date" for f in figures) else []
    return [_figure_in(f, numbers, dates) for f in figures]
