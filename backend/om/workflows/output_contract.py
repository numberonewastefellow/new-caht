"""What an agent step must return, when other steps depend on its shape.

An agent's reply is free text, so a format asked for in a prompt isn't guaranteed:
the same agent and prompt can return JSON on one request and plain lines on the next.
A step can declare a JSON schema (``output_schema``), which is enforced in layers:

1. The provider constrains the reply, where the model supports it (``response_format``).
2. Small mistakes are repaired, then the result is validated (``read_output``). Repair
   can't turn prose into data, and it accepts a reply that was cut off, so validation
   decides.
3. The runner asks once more, sending the problem back, then fails the step clearly.

Later steps read the cleaned JSON. A step without a schema isn't touched.
"""

from __future__ import annotations

import json
from typing import Any
from typing import TYPE_CHECKING

import json_repair
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from om.utils.logger import setup_logger

if TYPE_CHECKING:
    from om.llm.interfaces import LLM

logger = setup_logger()

RESPONSE_FORMAT_NAME = "step_output"
MAX_REPLY_IN_RETRY = 4000


class OutputContractError(ValueError):
    """A reply doesn't match the step's schema. The message says why."""


def check_schema(schema: Any) -> None:
    """Check a schema when a step is saved.

    The top level must be an object: strict providers require it, and later steps
    read its fields by name (``$step.output.days``).

    Raises:
        ValueError: The schema can't be used.
    """
    if not isinstance(schema, dict):
        raise ValueError("the output schema must be a JSON object")
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as e:
        raise ValueError(f"the output schema isn't valid: {e.message}") from e
    if schema.get("type") != "object" or not schema.get("properties"):
        raise ValueError(
            'the output schema must be an object with properties, like '
            '{"type": "object", "properties": {"days": {"type": "array"}}}'
        )


def declared_fields(schema: dict[str, Any]) -> set[str]:
    """The top-level fields later steps can read."""
    return set(schema.get("properties") or {})


def _strict(schema: dict[str, Any]) -> dict[str, Any]:
    """The form strict providers need: every object closed, every field required."""
    strict = dict(schema)
    if isinstance(strict.get("properties"), dict):
        strict["properties"] = {
            name: _strict(value) if isinstance(value, dict) else value
            for name, value in strict["properties"].items()
        }
        strict["required"] = list(strict["properties"])
        strict["additionalProperties"] = False
    if isinstance(strict.get("items"), dict):
        strict["items"] = _strict(strict["items"])
    return strict


def response_format(schema: dict[str, Any]) -> dict[str, Any]:
    """``schema`` as the LLM's ``response_format``."""
    return {
        "type": "json_schema",
        "json_schema": {
            "name": RESPONSE_FORMAT_NAME,
            "strict": True,
            "schema": _strict(schema),
        },
    }


def supports_response_format(llm: LLM) -> bool:
    """Whether the provider can enforce a schema for this model."""
    import litellm

    try:
        return bool(
            litellm.supports_response_schema(
                model=llm.config.model_name,
                custom_llm_provider=llm.config.model_provider,
            )
        )
    except Exception:
        logger.warning(
            "[Output] Couldn't tell if %s supports response schemas; assuming not",
            llm.config.model_name,
            exc_info=True,
        )
        return False


def read_output(reply: str, schema: dict[str, Any]) -> str:
    """The reply as compact JSON, repaired if needed and validated against ``schema``.

    Raises:
        OutputContractError: The reply can't be read as data of that shape.
    """
    try:
        value = json.loads(reply)
    except json.JSONDecodeError:
        value = json_repair.loads(reply)
    if not isinstance(value, dict):
        raise OutputContractError("the reply isn't a JSON object")

    problems = sorted(
        Draft202012Validator(schema).iter_errors(value),
        key=lambda e: list(map(str, e.absolute_path)),
    )
    if problems:
        first = problems[0]
        where = ".".join(map(str, first.absolute_path)) or "the reply"
        raise OutputContractError(f"{where}: {first.message}")
    return json.dumps(value, ensure_ascii=False)


def format_instruction(schema: dict[str, Any]) -> str:
    """For a model that can't enforce the schema: what to return, stated in the task."""
    return (
        "Reply with only one JSON object that matches this JSON schema, with no "
        f"commentary or code fences:\n{json.dumps(schema, ensure_ascii=False)}"
    )


def retry_task(task: str, reply: str, problem: str, schema: dict[str, Any]) -> str:
    """The task again, with what was wrong. The same input alone repeats the same reply."""
    return (
        f"{task}\n\nYour previous reply can't be used: {problem}\n"
        f"Previous reply:\n{reply[:MAX_REPLY_IN_RETRY]}\n\n"
        "Keep the content, and fix the format. "
        f"{format_instruction(schema)}"
    )
