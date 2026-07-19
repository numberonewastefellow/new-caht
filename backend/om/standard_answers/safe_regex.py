"""ReDoS-resistant regular-expression handling for standard answers.

Admin-authored patterns are only *semi*-trusted, and matching runs on every
inbound Slack message, so a catastrophic-backtracking ("evil") pattern against a
long message could pin a worker. Defence in depth (see module README, "Research"):

1. **Validate at write time** (`validate_pattern`): compile for syntax and reject
   obvious evil shapes (nested / overlapping quantifiers). Surfaces a clear error
   to the admin instead of failing silently at match time.
2. **Cap the input length** (`MAX_MATCH_INPUT_CHARS`) before matching — bounds the
   work regardless of pattern.
3. **Prefer a linear-time engine**: use Google RE2 (``google-re2``) when importable
   (immune to backtracking); otherwise fall back to the stdlib ``re`` on the already
   validated + length-capped input, always inside ``try/except``.

This module is pure/stateless and has no dependency on the ORM or tenancy layer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from typing import Final
from typing import Protocol

# Hard ceiling on how much message text any single pattern is run against. A Slack
# message body is normally well under this; capping bounds worst-case matcher work.
MAX_MATCH_INPUT_CHARS: Final[int] = 8_000

# Reject patterns longer than this at validation time — long admin patterns are
# almost always a mistake and enlarge the compile/search surface.
MAX_PATTERN_CHARS: Final[int] = 1_000


class UnsafeRegexError(ValueError):
    """Raised when a pattern is invalid or matches a catastrophic-backtracking shape."""


class _CompiledMatcher(Protocol):
    """Minimal surface shared by ``re.Pattern`` and ``re2`` compiled patterns.

    ``text`` is positional-only (``/``) so ``re.Pattern.search`` (whose parameter is
    named ``string``) structurally conforms under strict mypy.
    """

    def search(self, text: str, /) -> object | None: ...


# --- optional linear-time engine ------------------------------------------------


def _load_re2() -> Any:
    """Import Google RE2 if available, else return None. Typed ``Any`` so the
    (stub-less) module's attributes are usable without per-line type-ignores."""

    try:  # pragma: no cover - availability is environment-dependent
        import re2  # type: ignore

        return re2
    except Exception:  # noqa: BLE001 - any import failure means "not available"
        return None


_re2: Any = _load_re2()
_HAS_RE2: bool = _re2 is not None


def linear_time_engine_available() -> bool:
    """True when Google RE2 is importable (guarantees linear-time matching)."""

    return _HAS_RE2


# --- evil-shape heuristic -------------------------------------------------------

# Heuristics for the classic ReDoS shapes: a quantifier applied to a group that is
# itself quantified, e.g. ``(a+)+``, ``(a*)*``, ``(.*)+``, ``(\w+)*``, or overlapping
# alternation under a quantifier like ``(a|a)*``. These are conservative — they may
# reject an unusual-but-safe pattern, which for admin-authored triggers is the right
# trade (a keyword rule is almost always the better tool anyway).
_NESTED_QUANTIFIER: Final[re.Pattern[str]] = re.compile(
    r"""
    \(                      # opening group
        (?![?]:)?           # ordinary or non-capturing group
        [^()]*              # group body (no nested parens)
        [+*]                # ... containing an inner quantifier
        [^()]*
    \)
    [?]?                    # optional group
    \s*
    (?:[+*]|\{\d+,?\d*\})   # ... with an outer quantifier applied to the group
    """,
    re.VERBOSE,
)

_OVERLAPPING_ALTERNATION: Final[re.Pattern[str]] = re.compile(
    r"\((?![?]:)[^()|]+\|[^()]*\)[+*]"  # (x|...)+  — alternation directly under +/*
)


def _looks_catastrophic(pattern: str) -> bool:
    return bool(
        _NESTED_QUANTIFIER.search(pattern)
        or _OVERLAPPING_ALTERNATION.search(pattern)
    )


def validate_pattern(pattern: str) -> None:
    """Validate an admin-supplied regex; raise :class:`UnsafeRegexError` if unusable.

    Checks, in order: non-empty, length bound, compiles as a regex, and does not
    match the evil-shape heuristic. Call this on every create/update of a
    regex-mode standard answer so the admin gets immediate feedback.
    """

    if not pattern or not pattern.strip():
        raise UnsafeRegexError("Regex pattern must not be empty.")
    if len(pattern) > MAX_PATTERN_CHARS:
        raise UnsafeRegexError(
            f"Regex pattern is too long (>{MAX_PATTERN_CHARS} characters)."
        )
    try:
        re.compile(pattern)
    except re.error as exc:
        raise UnsafeRegexError(f"Invalid regular expression: {exc}") from exc
    if _looks_catastrophic(pattern):
        raise UnsafeRegexError(
            "Regex uses nested or overlapping quantifiers that risk catastrophic "
            "backtracking (ReDoS). Simplify the pattern or use a keyword rule."
        )


@dataclass(frozen=True, slots=True)
class SafeRegex:
    """A validated, compiled pattern that searches within a bounded input.

    Construct via :meth:`compile`, which validates first. ``search`` is total: any
    engine-level error is swallowed and reported as "no match" so a single bad
    pattern can never take down message handling.
    """

    pattern: str
    _matcher: _CompiledMatcher

    @classmethod
    def compile(cls, pattern: str, *, case_insensitive: bool = True) -> "SafeRegex":
        validate_pattern(pattern)
        if _HAS_RE2:
            # google-re2 is a drop-in for `re`: compile(pattern, flags). It mirrors the
            # `re` flag constants, so pass IGNORECASE via flags rather than the Options
            # object (whose `compile` position differs across versions).
            flags = _re2.IGNORECASE if case_insensitive else 0
            matcher: _CompiledMatcher = _re2.compile(pattern, flags)
            return cls(pattern=pattern, _matcher=matcher)
        re_flags = re.IGNORECASE if case_insensitive else 0
        return cls(pattern=pattern, _matcher=re.compile(pattern, re_flags))

    def search(self, text: str) -> bool:
        """Return True if the pattern is found within the (length-capped) text."""

        if not text:
            return False
        capped = text[:MAX_MATCH_INPUT_CHARS]
        try:
            return self._matcher.search(capped) is not None
        except Exception:  # noqa: BLE001 - never let a pattern break matching
            return False
