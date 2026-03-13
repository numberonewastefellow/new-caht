"""Deterministic condition evaluator for conditional router steps.

Evaluates conditions against workflow context without any LLM call.
Used in sequential mode only — in llm_decision mode the orchestrator
handles routing naturally.
"""

import re
from typing import Any

from onyx.utils.logger import setup_logger
from onyx.workflows.models import WorkflowContext

logger = setup_logger()

# Supported comparison operators (exported for frontend sync)
OPERATORS = {
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

# Safety limits for regex patterns
MAX_REGEX_PATTERN_LENGTH = 500


def _resolve_reference(field_ref: str, context: WorkflowContext) -> str:
    """Resolve a variable reference like $step_name.output to its actual value.

    Returns the resolved value as a string. Logs a warning if the reference
    cannot be resolved (returns empty string).
    """
    if not field_ref.startswith("$"):
        return field_ref

    ref = field_ref[1:]  # strip leading $

    # Try $key.output form first — use removesuffix to avoid greedy replacement
    if ref.endswith(".output"):
        key = ref.removesuffix(".output")
        value = context.step_outputs.get(key)
        if value is None:
            logger.warning(
                "Conditional router: reference '%s' not found in step_outputs "
                "(available keys: %s)",
                field_ref,
                list(context.step_outputs.keys()),
            )
            return ""
        return str(value)

    # Try bare $key
    if ref in context.step_outputs:
        return str(context.step_outputs[ref])

    # Try $user_input
    if ref == "user_input":
        return str(context.user_input)

    logger.warning(
        "Conditional router: unresolved reference '%s' "
        "(available step outputs: %s)",
        field_ref,
        list(context.step_outputs.keys()),
    )
    return ""


def _apply_operator(
    actual: str,
    operator: str,
    expected: str,
    case_sensitive: bool,
) -> bool:
    """Apply a comparison operator to actual vs expected values."""
    a = actual if case_sensitive else actual.lower()
    e = expected if case_sensitive else expected.lower()

    if operator == "equals":
        return a == e
    elif operator == "not_equals":
        return a != e
    elif operator == "contains":
        return e in a
    elif operator == "not_contains":
        return e not in a
    elif operator == "starts_with":
        return a.startswith(e)
    elif operator == "ends_with":
        return a.endswith(e)
    elif operator == "regex_match":
        if len(expected) > MAX_REGEX_PATTERN_LENGTH:
            logger.warning(
                "Regex pattern too long (%d chars, max %d): truncating",
                len(expected),
                MAX_REGEX_PATTERN_LENGTH,
            )
            return False
        try:
            flags = 0 if case_sensitive else re.IGNORECASE
            # Use re.search with a compiled pattern for safety
            pattern = re.compile(expected, flags)
            return bool(pattern.search(actual))
        except re.error as exc:
            logger.warning("Invalid regex pattern '%s': %s", expected, exc)
            return False
    elif operator == "is_empty":
        return len(actual.strip()) == 0
    elif operator == "is_not_empty":
        return len(actual.strip()) > 0
    elif operator in (
        "greater_than",
        "greater_than_or_equal",
        "less_than",
        "less_than_or_equal",
    ):
        try:
            num_a = float(actual)
            num_e = float(expected)
        except (ValueError, TypeError):
            logger.warning(
                "Numeric comparison failed: cannot convert '%s' or '%s' to float "
                "(operator: %s)",
                actual[:80],
                expected[:80],
                operator,
            )
            return False
        if operator == "greater_than":
            return num_a > num_e
        elif operator == "greater_than_or_equal":
            return num_a >= num_e
        elif operator == "less_than":
            return num_a < num_e
        elif operator == "less_than_or_equal":
            return num_a <= num_e

    logger.warning("Unknown operator: %s", operator)
    return False


def evaluate_condition(
    condition_config: dict[str, Any],
    context: WorkflowContext,
) -> tuple[bool, str]:
    """Evaluate a condition against the workflow context.

    Args:
        condition_config: The condition JSONB from the step, e.g.:
            {
                "condition_field": "$research.output",
                "operator": "contains",
                "match_value": "error",
                "case_sensitive": false,
                "true_steps": [3, 4],
                "false_steps": [5, 6]
            }
        context: Current workflow runtime context.

    Returns:
        (result, explanation) — boolean result and a human-readable explanation.
    """
    field_ref = condition_config.get("condition_field", "")
    operator = condition_config.get("operator", "contains")
    match_value = condition_config.get("match_value", "")
    case_sensitive = condition_config.get("case_sensitive", False)

    if operator not in OPERATORS:
        explanation = f"Unknown operator '{operator}' — defaulting to False"
        logger.warning(explanation)
        return False, explanation

    actual_value = _resolve_reference(field_ref, context)
    result = _apply_operator(actual_value, operator, match_value, case_sensitive)

    # Truncate displayed values for readability
    display_actual = (
        actual_value[:80] + "..." if len(actual_value) > 80 else actual_value
    )
    explanation = (
        f"Condition: {field_ref} {operator} '{match_value}' → "
        f"{'TRUE' if result else 'FALSE'} "
        f"(actual: '{display_actual}')"
    )
    logger.info("[ConditionalRouter] %s", explanation)

    return result, explanation
