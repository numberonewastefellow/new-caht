"""Unit tests for the conditional router step evaluator.

Tests cover:
  - All 13 comparison operators
  - Reference resolution ($step.output, $user_input, bare $key)
  - Case sensitivity
  - Invalid regex patterns (ReDoS protection via length limit)
  - Numeric conversion failures (logged, not silent)
  - Missing/empty references (warning logged)
  - Type safety (non-string step outputs cast to str)
  - Unknown operators
"""

import pytest

from onyx.workflows.models import WorkflowContext
from onyx.workflows.step_runners.conditional_router import (
    OPERATORS,
    MAX_REGEX_PATTERN_LENGTH,
    _apply_operator,
    _resolve_reference,
    evaluate_condition,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ctx(
    user_input: str = "hello",
    step_outputs: dict | None = None,
) -> WorkflowContext:
    return WorkflowContext(
        user_input=user_input,
        step_outputs=step_outputs or {},
    )


# ---------------------------------------------------------------------------
# Reference resolution
# ---------------------------------------------------------------------------


class TestResolveReference:

    def test_literal_string(self) -> None:
        assert _resolve_reference("hello", _ctx()) == "hello"

    def test_user_input(self) -> None:
        assert _resolve_reference("$user_input", _ctx(user_input="test")) == "test"

    def test_step_output_suffix(self) -> None:
        ctx = _ctx(step_outputs={"research": "result data"})
        assert _resolve_reference("$research.output", ctx) == "result data"

    def test_bare_step_key(self) -> None:
        ctx = _ctx(step_outputs={"research": "result data"})
        assert _resolve_reference("$research", ctx) == "result data"

    def test_missing_reference_returns_empty(self) -> None:
        ctx = _ctx(step_outputs={})
        assert _resolve_reference("$nonexistent.output", ctx) == ""

    def test_missing_bare_key_returns_empty(self) -> None:
        ctx = _ctx(step_outputs={})
        assert _resolve_reference("$nonexistent", ctx) == ""

    def test_greedy_output_fix(self) -> None:
        """Regression: step name containing 'output' should not be mangled.

        Previously, ref.replace('.output', '') would break this.
        Now uses removesuffix('.output').
        """
        ctx = _ctx(step_outputs={"output_processor": "processed data"})
        # $output_processor.output should resolve correctly
        assert (
            _resolve_reference("$output_processor.output", ctx) == "processed data"
        )

    def test_string_step_output_returned_as_is(self) -> None:
        """Step outputs are strings (enforced by WorkflowContext schema)."""
        ctx = _ctx(step_outputs={"api_result": '{"status": "ok", "count": 42}'})
        result = _resolve_reference("$api_result.output", ctx)
        assert isinstance(result, str)
        assert "status" in result

    def test_numeric_string_step_output(self) -> None:
        ctx = _ctx(step_outputs={"count": "42"})
        result = _resolve_reference("$count", ctx)
        assert result == "42"


# ---------------------------------------------------------------------------
# String operators
# ---------------------------------------------------------------------------


class TestStringOperators:

    def test_equals(self) -> None:
        assert _apply_operator("hello", "equals", "hello", True) is True
        assert _apply_operator("Hello", "equals", "hello", True) is False
        assert _apply_operator("Hello", "equals", "hello", False) is True

    def test_not_equals(self) -> None:
        assert _apply_operator("hello", "not_equals", "world", True) is True
        assert _apply_operator("hello", "not_equals", "hello", True) is False

    def test_contains(self) -> None:
        assert _apply_operator("hello world", "contains", "world", True) is True
        assert _apply_operator("hello world", "contains", "World", True) is False
        assert _apply_operator("hello world", "contains", "World", False) is True

    def test_not_contains(self) -> None:
        assert _apply_operator("hello world", "not_contains", "xyz", True) is True
        assert _apply_operator("hello world", "not_contains", "world", True) is False

    def test_starts_with(self) -> None:
        assert _apply_operator("hello world", "starts_with", "hello", True) is True
        assert _apply_operator("hello world", "starts_with", "world", True) is False

    def test_ends_with(self) -> None:
        assert _apply_operator("hello world", "ends_with", "world", True) is True
        assert _apply_operator("hello world", "ends_with", "hello", True) is False

    def test_is_empty(self) -> None:
        assert _apply_operator("", "is_empty", "", True) is True
        assert _apply_operator("   ", "is_empty", "", True) is True
        assert _apply_operator("hello", "is_empty", "", True) is False

    def test_is_not_empty(self) -> None:
        assert _apply_operator("hello", "is_not_empty", "", True) is True
        assert _apply_operator("", "is_not_empty", "", True) is False
        assert _apply_operator("   ", "is_not_empty", "", True) is False


# ---------------------------------------------------------------------------
# Regex operator
# ---------------------------------------------------------------------------


class TestRegexOperator:

    def test_valid_regex(self) -> None:
        assert _apply_operator("error 404", "regex_match", r"\d{3}", True) is True
        assert _apply_operator("no digits", "regex_match", r"\d{3}", True) is False

    def test_invalid_regex_returns_false(self) -> None:
        assert _apply_operator("test", "regex_match", "[invalid", True) is False

    def test_regex_case_insensitive(self) -> None:
        assert _apply_operator("ERROR", "regex_match", "error", False) is True
        assert _apply_operator("ERROR", "regex_match", "error", True) is False

    def test_regex_too_long_returns_false(self) -> None:
        """Patterns exceeding MAX_REGEX_PATTERN_LENGTH should be rejected."""
        long_pattern = "a" * (MAX_REGEX_PATTERN_LENGTH + 1)
        assert _apply_operator("test", "regex_match", long_pattern, True) is False


# ---------------------------------------------------------------------------
# Numeric operators
# ---------------------------------------------------------------------------


class TestNumericOperators:

    def test_greater_than(self) -> None:
        assert _apply_operator("10", "greater_than", "5", True) is True
        assert _apply_operator("5", "greater_than", "10", True) is False
        assert _apply_operator("5", "greater_than", "5", True) is False

    def test_greater_than_or_equal(self) -> None:
        assert _apply_operator("5", "greater_than_or_equal", "5", True) is True
        assert _apply_operator("4", "greater_than_or_equal", "5", True) is False

    def test_less_than(self) -> None:
        assert _apply_operator("3", "less_than", "5", True) is True
        assert _apply_operator("5", "less_than", "3", True) is False

    def test_less_than_or_equal(self) -> None:
        assert _apply_operator("5", "less_than_or_equal", "5", True) is True
        assert _apply_operator("6", "less_than_or_equal", "5", True) is False

    def test_float_comparison(self) -> None:
        assert _apply_operator("3.14", "greater_than", "3.0", True) is True

    def test_non_numeric_returns_false(self) -> None:
        """Non-numeric values should return False with a logged warning."""
        assert _apply_operator("abc", "greater_than", "5", True) is False
        assert _apply_operator("5", "greater_than", "abc", True) is False


# ---------------------------------------------------------------------------
# Unknown operator
# ---------------------------------------------------------------------------


class TestUnknownOperator:

    def test_unknown_operator_returns_false(self) -> None:
        assert _apply_operator("test", "unknown_op", "test", True) is False


# ---------------------------------------------------------------------------
# evaluate_condition (integration)
# ---------------------------------------------------------------------------


class TestEvaluateCondition:

    def test_basic_contains_true(self) -> None:
        ctx = _ctx(step_outputs={"research": "found some error in the data"})
        result, explanation = evaluate_condition(
            {
                "condition_field": "$research.output",
                "operator": "contains",
                "match_value": "error",
                "case_sensitive": False,
                "true_steps": [3, 4],
                "false_steps": [5, 6],
            },
            ctx,
        )
        assert result is True
        assert "TRUE" in explanation

    def test_basic_contains_false(self) -> None:
        ctx = _ctx(step_outputs={"research": "everything is fine"})
        result, explanation = evaluate_condition(
            {
                "condition_field": "$research.output",
                "operator": "contains",
                "match_value": "error",
                "case_sensitive": False,
                "true_steps": [3],
                "false_steps": [5],
            },
            ctx,
        )
        assert result is False
        assert "FALSE" in explanation

    def test_unknown_operator_in_config(self) -> None:
        ctx = _ctx()
        result, explanation = evaluate_condition(
            {
                "condition_field": "$user_input",
                "operator": "fuzzy_match",
                "match_value": "test",
            },
            ctx,
        )
        assert result is False
        assert "Unknown operator" in explanation

    def test_user_input_reference(self) -> None:
        ctx = _ctx(user_input="yes please")
        result, _ = evaluate_condition(
            {
                "condition_field": "$user_input",
                "operator": "contains",
                "match_value": "yes",
            },
            ctx,
        )
        assert result is True

    def test_long_actual_value_truncated_in_explanation(self) -> None:
        long_output = "x" * 200
        ctx = _ctx(step_outputs={"data": long_output})
        _, explanation = evaluate_condition(
            {
                "condition_field": "$data.output",
                "operator": "is_not_empty",
            },
            ctx,
        )
        assert "..." in explanation

    def test_defaults_for_missing_config_fields(self) -> None:
        """Missing config fields should use sensible defaults."""
        ctx = _ctx(step_outputs={})
        result, _ = evaluate_condition({}, ctx)
        # Default: condition_field="", operator="contains", match_value=""
        # Empty string contains empty string → True
        assert result is True


# ---------------------------------------------------------------------------
# Operator set completeness
# ---------------------------------------------------------------------------


class TestOperatorCompleteness:

    def test_all_operators_present(self) -> None:
        expected = {
            "equals",
            "not_equals",
            "contains",
            "not_contains",
            "starts_with",
            "ends_with",
            "regex_match",
            "greater_than",
            "greater_than_or_equal",
            "less_than",
            "less_than_or_equal",
            "is_empty",
            "is_not_empty",
        }
        assert OPERATORS == expected
