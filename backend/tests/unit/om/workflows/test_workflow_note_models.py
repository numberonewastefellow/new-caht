"""What a sticky note on the workflow canvas may contain."""

import pytest
from pydantic import ValidationError

from om.workflows.note_models import NOTE_TEXT_MAX_CHARS
from om.workflows.note_models import WorkflowNoteCreate
from om.workflows.note_models import WorkflowNoteUpdate


def test_a_new_note_has_sensible_defaults() -> None:
    note = WorkflowNoteCreate(x=10, y=20)
    assert (note.text, note.color, note.step_node_key) == ("", "yellow", None)
    assert note.width > 0 and note.height > 0


@pytest.mark.parametrize("color", ["yellow", "blue", "green", "pink", "purple", "gray"])
def test_every_palette_colour_is_accepted(color: str) -> None:
    assert WorkflowNoteCreate(x=0, y=0, color=color).color == color


@pytest.mark.parametrize("color", ["red", "#ffcc00", "", "Yellow"])
def test_anything_outside_the_palette_is_refused(color: str) -> None:
    with pytest.raises(ValidationError):
        WorkflowNoteCreate(x=0, y=0, color=color)


def test_text_has_a_limit() -> None:
    WorkflowNoteCreate(x=0, y=0, text="x" * NOTE_TEXT_MAX_CHARS)
    with pytest.raises(ValidationError):
        WorkflowNoteCreate(x=0, y=0, text="x" * (NOTE_TEXT_MAX_CHARS + 1))


@pytest.mark.parametrize("field,value", [("width", 10), ("height", 5000), ("x", 10**9), ("y", -(10**9))])
def test_sizes_and_positions_stay_in_range(field: str, value: int) -> None:
    with pytest.raises(ValidationError):
        WorkflowNoteCreate(**{"x": 0, "y": 0, field: value})


def test_an_update_must_say_which_version_it_edits() -> None:
    with pytest.raises(ValidationError):
        WorkflowNoteUpdate(text="hello")  # type: ignore[call-arg]


def test_an_update_can_remove_the_link_explicitly() -> None:
    update = WorkflowNoteUpdate(expected_version=1, step_node_key=None)
    assert "step_node_key" in update.model_fields_set
    assert "step_node_key" not in WorkflowNoteUpdate(expected_version=1).model_fields_set
