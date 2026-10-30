"""Unit tests for typed reference resolution (resolve_reference)."""

import json

import pytest

from om.workflows.inputs import resolve_reference
from om.workflows.inputs import UnresolvedReferenceError
from om.workflows.models import WorkflowContext

CONTEXT = WorkflowContext(
    user_input="plan a trip",
    step_outputs={
        "research": "plain text",
        "research_notes": "notes",
        "data": json.dumps({"items": [{"title": "A"}, {"title": "B"}], "count": 2}),
    },
)


@pytest.mark.parametrize(
    ("ref", "expected"),
    [
        ("hello", "hello"),
        ("$user_input", "plan a trip"),
        ("$research", "plain text"),
        ("$research.output", "plain text"),
        ("$research_notes", "notes"),  # no substring confusion with $research
        ("$data.output.count", 2),
        ("$data.output.items[1].title", "B"),
        ("$data.output.items", [{"title": "A"}, {"title": "B"}]),
    ],
)
def test_resolves(ref: str, expected: object) -> None:
    assert resolve_reference(ref, CONTEXT) == expected


def test_variables_take_precedence() -> None:
    assert resolve_reference("$item", CONTEXT, {"item": {"x": 1}}) == {"x": 1}
    assert resolve_reference("$item.output.x", CONTEXT, {"item": {"x": 1}}) == 1


@pytest.mark.parametrize(
    ("ref", "message"),
    [
        ("$missing", "no step output"),
        ("$research.output.title", "not JSON"),
        ("$data.output.items[5]", "path not found"),
        ("$data.output.nope", "path not found"),
        ("$bad name", "Invalid reference"),
    ],
)
def test_errors(ref: str, message: str) -> None:
    with pytest.raises(UnresolvedReferenceError, match=message):
        resolve_reference(ref, CONTEXT)
