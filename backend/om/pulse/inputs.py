"""What each scheduled run receives ("input modes"). Pure helpers, no DB.

fixed   the same request every run (input_message)
window  new information since the last run (template using {{window_start}} …)
ask     the run opens the workflow chat and waits for the user to send the input
list    the next item of input_items each run, inserted via {{item}}
"""

from typing import Literal

InputMode = Literal["fixed", "window", "ask", "list"]
INPUT_MODES: tuple[str, ...] = ("fixed", "window", "ask", "list")

DEFAULT_WINDOW_MESSAGE = (
    "Run for {{date}}. Only include what changed since {{window_start}}."
)
DEFAULT_LIST_MESSAGE = "{{item}}"
MAX_LIST_ITEMS = 500
MAX_ITEM_CHARS = 2000


class InputValidationError(ValueError):
    """Invalid input configuration; message is user-facing."""


def default_ask_prompt(workflow_name: str) -> str:
    return (
        f"Your scheduled run of “{workflow_name}” is ready. "
        "Send the input for this run below to start it."
    )


def normalize_inputs(
    *,
    mode: str,
    message: str | None,
    prompt: str | None,
    items: list[str] | None,
) -> tuple[str, str, str | None, list[str] | None]:
    """Validate a schedule's input settings and fill per-mode defaults.

    Returns (mode, input_message, input_prompt, input_items) ready to store.
    """
    if mode not in INPUT_MODES:
        raise InputValidationError(
            f"input_mode must be one of {', '.join(INPUT_MODES)}"
        )
    message = (message or "").strip()

    if mode == "fixed":
        if not message:
            raise InputValidationError(
                "Write the request the workflow should receive on every run"
            )
        return mode, message, None, None

    if mode == "window":
        return mode, message or DEFAULT_WINDOW_MESSAGE, None, None

    if mode == "ask":
        # input_message is not sent in ask mode; keep a readable placeholder
        prompt = (prompt or "").strip() or None
        return mode, message or "(asked each run)", prompt, None

    # list
    cleaned = [i.strip() for i in (items or []) if i and i.strip()]
    if not cleaned:
        raise InputValidationError("Add at least one item (one per line)")
    if len(cleaned) > MAX_LIST_ITEMS:
        raise InputValidationError(f"At most {MAX_LIST_ITEMS} items")
    if any(len(i) > MAX_ITEM_CHARS for i in cleaned):
        raise InputValidationError(f"Each item can be at most {MAX_ITEM_CHARS} characters")
    message = message or DEFAULT_LIST_MESSAGE
    if "{{item}}" not in message.replace(" ", ""):
        raise InputValidationError(
            "The message for a list must contain {{item}} where each item goes"
        )
    return mode, message, None, cleaned


def item_for_index(items: list[str] | None, index: int) -> str | None:
    if not items:
        return None
    return items[index % len(items)]
