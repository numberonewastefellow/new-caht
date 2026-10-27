"""Unit tests for Pulse input modes (om.pulse.inputs) and {{item}} rendering."""

import datetime as dt

import pytest

from om.pulse.inputs import DEFAULT_LIST_MESSAGE
from om.pulse.inputs import DEFAULT_WINDOW_MESSAGE
from om.pulse.inputs import default_ask_prompt
from om.pulse.inputs import InputValidationError
from om.pulse.inputs import item_for_index
from om.pulse.inputs import normalize_inputs
from om.pulse.timing import render_input_message

UTC = dt.timezone.utc


def norm(**kw: object) -> tuple:
    base: dict = {"mode": "fixed", "message": None, "prompt": None, "items": None}
    base.update(kw)
    return normalize_inputs(**base)


def test_fixed_requires_a_message() -> None:
    with pytest.raises(InputValidationError, match="request"):
        norm(mode="fixed", message="   ")
    assert norm(mode="fixed", message=" what is the use of paracetamol? ") == (
        "fixed",
        "what is the use of paracetamol?",
        None,
        None,
    )


def test_window_defaults_and_override() -> None:
    assert norm(mode="window")[1] == DEFAULT_WINDOW_MESSAGE
    assert norm(mode="window", message="Digest since {{window_start}}")[1] == (
        "Digest since {{window_start}}"
    )


def test_ask_keeps_optional_prompt() -> None:
    mode, message, prompt, items = norm(mode="ask", prompt="Paste today's notes")
    assert (mode, prompt, items) == ("ask", "Paste today's notes", None)
    assert message  # placeholder stored, never sent
    assert norm(mode="ask")[2] is None
    assert "Weekly report" in default_ask_prompt("Weekly report")


def test_list_validation_and_defaults() -> None:
    with pytest.raises(InputValidationError, match="at least one item"):
        norm(mode="list", items=["", "  "])
    with pytest.raises(InputValidationError, match=r"\{\{item\}\}"):
        norm(mode="list", items=["a"], message="no placeholder")
    mode, message, _, items = norm(mode="list", items=[" asthma ", "", "diabetes"])
    assert (mode, message, items) == ("list", DEFAULT_LIST_MESSAGE, ["asthma", "diabetes"])
    assert norm(mode="list", items=["x"], message="Guidance on {{ item }}")[1] == (
        "Guidance on {{ item }}"
    )


def test_unknown_mode_rejected() -> None:
    with pytest.raises(InputValidationError):
        norm(mode="sometimes")


def test_item_for_index_cycles() -> None:
    items = ["a", "b", "c"]
    assert [item_for_index(items, i) for i in range(5)] == ["a", "b", "c", "a", "b"]
    assert item_for_index([], 0) is None
    assert item_for_index(None, 3) is None


def test_render_item_variable() -> None:
    out = render_input_message(
        "Summarise the latest guidance on {{item}} for {{date}}",
        timezone="UTC",
        scheduled_for=dt.datetime(2026, 10, 27, 9, tzinfo=UTC),
        now=dt.datetime(2026, 10, 27, 9, tzinfo=UTC),
        last_success_scheduled_for=None,
        period_seconds=86400,
        item="asthma {{date}}",  # item text is inserted verbatim, not re-rendered
    )
    assert out == "Summarise the latest guidance on asthma {{date}} for 2026-10-27"


def test_item_placeholder_left_alone_outside_list_mode() -> None:
    out = render_input_message(
        "{{item}}",
        timezone="UTC",
        scheduled_for=dt.datetime(2026, 10, 27, tzinfo=UTC),
        now=dt.datetime(2026, 10, 27, tzinfo=UTC),
        last_success_scheduled_for=None,
        period_seconds=None,
    )
    assert out == "{{item}}"
