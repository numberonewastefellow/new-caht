"""Unit tests for the ReDoS-resistant regex layer."""

import pytest

from om.standard_answers.safe_regex import MAX_MATCH_INPUT_CHARS
from om.standard_answers.safe_regex import SafeRegex
from om.standard_answers.safe_regex import UnsafeRegexError
from om.standard_answers.safe_regex import validate_pattern


class TestValidatePattern:
    def test_accepts_ordinary_pattern(self) -> None:
        validate_pattern(r"reset\s+password")
        validate_pattern(r"^error code \d{3,4}$")
        validate_pattern(r"(cat|dog|bird)")  # bounded alternation, no outer quantifier

    @pytest.mark.parametrize(
        "pattern",
        [
            r"(a+)+",
            r"(a*)*",
            r"(a+)*",
            r"(\w+)+",
            r"(.*)+",
            r"(\d+)+$",
        ],
    )
    def test_rejects_nested_quantifiers(self, pattern: str) -> None:
        with pytest.raises(UnsafeRegexError):
            validate_pattern(pattern)

    @pytest.mark.parametrize("pattern", [r"(a|a)*", r"(x|xy)+"])
    def test_rejects_overlapping_alternation_under_quantifier(
        self, pattern: str
    ) -> None:
        with pytest.raises(UnsafeRegexError):
            validate_pattern(pattern)

    def test_rejects_invalid_syntax(self) -> None:
        with pytest.raises(UnsafeRegexError):
            validate_pattern(r"(unclosed")

    def test_rejects_empty(self) -> None:
        with pytest.raises(UnsafeRegexError):
            validate_pattern("")
        with pytest.raises(UnsafeRegexError):
            validate_pattern("   ")

    def test_rejects_overlong_pattern(self) -> None:
        with pytest.raises(UnsafeRegexError):
            validate_pattern("a" * 2000)


class TestSafeRegex:
    def test_compile_and_search_case_insensitive(self) -> None:
        rx = SafeRegex.compile(r"reset\s+password")
        assert rx.search("Please RESET   PASSWORD now") is True
        assert rx.search("nothing here") is False

    def test_case_sensitive_option(self) -> None:
        rx = SafeRegex.compile(r"Error", case_insensitive=False)
        assert rx.search("Error found") is True
        assert rx.search("error found") is False

    def test_empty_text_never_matches(self) -> None:
        rx = SafeRegex.compile(r".*")
        assert rx.search("") is False

    def test_input_is_length_capped(self) -> None:
        # A benign pattern over a huge input must still return quickly and correctly.
        rx = SafeRegex.compile(r"needle")
        haystack = ("x" * (MAX_MATCH_INPUT_CHARS + 5000)) + "needle"
        # The needle sits beyond the cap, so it should NOT be found.
        assert rx.search(haystack) is False
        assert rx.search("needle" + "x" * 100000) is True

    def test_compile_rejects_unsafe(self) -> None:
        with pytest.raises(UnsafeRegexError):
            SafeRegex.compile(r"(a+)+")
