"""Sticky notes on the workflow canvas.

Notes are documentation for the people building a workflow. Runs never read them, so they
live apart from the workflow definition: saving one doesn't create a workflow version.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

NoteColor = Literal["yellow", "blue", "green", "pink", "purple", "gray"]

NOTE_TEXT_MAX_CHARS = 20000
# Far beyond any real canvas, but keeps a bad client from storing nonsense
_COORDINATE_LIMIT = 100_000
_MIN_WIDTH, _MAX_WIDTH = 120, 1600
_MIN_HEIGHT, _MAX_HEIGHT = 60, 1600
_NODE_KEY_MAX_CHARS = 64


class WorkflowNoteCreate(BaseModel):
    text: str = Field(default="", max_length=NOTE_TEXT_MAX_CHARS)
    color: NoteColor = "yellow"
    # A step's node_key. When set, x and y are relative to that step.
    step_node_key: str | None = Field(default=None, max_length=_NODE_KEY_MAX_CHARS)
    x: int = Field(ge=-_COORDINATE_LIMIT, le=_COORDINATE_LIMIT)
    y: int = Field(ge=-_COORDINATE_LIMIT, le=_COORDINATE_LIMIT)
    width: int = Field(default=260, ge=_MIN_WIDTH, le=_MAX_WIDTH)
    height: int = Field(default=180, ge=_MIN_HEIGHT, le=_MAX_HEIGHT)


class WorkflowNoteUpdate(BaseModel):
    """Only the fields sent are changed. Sending step_node_key as null removes the link."""

    # The version the editor loaded, so a stale edit is refused rather than overwriting
    expected_version: int
    text: str | None = Field(default=None, max_length=NOTE_TEXT_MAX_CHARS)
    color: NoteColor | None = None
    step_node_key: str | None = Field(default=None, max_length=_NODE_KEY_MAX_CHARS)
    x: int | None = Field(default=None, ge=-_COORDINATE_LIMIT, le=_COORDINATE_LIMIT)
    y: int | None = Field(default=None, ge=-_COORDINATE_LIMIT, le=_COORDINATE_LIMIT)
    width: int | None = Field(default=None, ge=_MIN_WIDTH, le=_MAX_WIDTH)
    height: int | None = Field(default=None, ge=_MIN_HEIGHT, le=_MAX_HEIGHT)


class WorkflowNoteResponse(BaseModel):
    # Built straight from an AgentWorkflowNote row
    model_config = ConfigDict(from_attributes=True)

    id: int
    workflow_id: int
    text: str
    color: NoteColor
    step_node_key: str | None
    x: int
    y: int
    width: int
    height: int
    version: int
    created_at: datetime
    updated_at: datetime
