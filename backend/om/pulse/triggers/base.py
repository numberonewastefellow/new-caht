"""The two things a trigger's input step can tell the runner to do."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SendMessage:
    """Run the workflow with this message."""

    text: str


@dataclass(frozen=True)
class FinishRun:
    """Don't run the workflow; finish the run with this result."""

    status: str
    error: str | None = None
    output_preview: str | None = None


RunInput = SendMessage | FinishRun
