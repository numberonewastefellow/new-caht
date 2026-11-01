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


_EXAMPLE = (
    '{"type": "object", "properties": {"days": {"type": "array", "items": {"type": "string"}}}}'
)
_NOT_SUPPORTED_BY_STRICT = (
    "oneOf",
    "allOf",
    "not",
    "if",
    "then",
    "else",
    "dependentRequired",
    "dependentSchemas",
    "patternProperties",
)


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
        raise ValueError(f"the output schema must be an object with properties, like {_EXAMPLE}")
    _check_strict(schema, "the output schema")


def _check_strict(schema: Any, where: str) -> None:
    """Refuse at save what strict providers would reject on every run."""
    if not isinstance(schema, dict):
        raise ValueError(f"{where} must be a JSON object, like {_EXAMPLE}")
    for keyword in _NOT_SUPPORTED_BY_STRICT:
        if keyword in schema:
            raise ValueError(f"{where} uses {keyword}, which models can't be held to")
    for name, definition in schema.get("$defs", {}).items():
        _check_strict(definition, f'definition "{name}"')
    if "$ref" in schema:
        return
    for branch in schema.get("anyOf", []):
        _check_strict(branch, where)

    types = schema.get("type")
    if types is None and "anyOf" in schema:
        return
    types = types if isinstance(types, list) else [types]
    if types == [None]:
        raise ValueError(f"{where} needs a type, like {_EXAMPLE}")
    if "object" in types:
        properties = schema.get("properties")
        if not properties:
            raise ValueError(f"{where} is an object, so it must list its properties")
        for name, value in properties.items():
            _check_strict(value, f'field "{name}"')
    if "array" in types:
        items = schema.get("items")
        if not isinstance(items, dict):
            raise ValueError(f'{where} is an array, so it must say what its "items" are')
        _check_strict(items, where)


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
    if isinstance(strict.get("anyOf"), list):
        strict["anyOf"] = [_strict(branch) for branch in strict["anyOf"]]
    if isinstance(strict.get("$defs"), dict):
        strict["$defs"] = {name: _strict(value) for name, value in strict["$defs"].items()}
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


def _stops_mid_structure(text: str) -> bool:
    """Whether the first JSON object in ``text`` is still open where the text ends."""
    start = text.find("{")
    if start < 0:
        return False
    depth = 0
    in_string = False
    escaped = False
    for char in text[start:]:
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
        elif char == '"':
            in_string = True
        elif char in "{[":
            depth += 1
        elif char in "}]":
            depth -= 1
            if depth == 0:
                return False
    return True


def read_output(reply: str, schema: dict[str, Any]) -> str:
    """The reply as compact JSON, repaired if needed and validated against ``schema``.

    Raises:
        OutputContractError: The reply can't be read as data of that shape.
    """
    try:
        value = json.loads(reply)
    except json.JSONDecodeError:
        # Repair fixes syntax. Closing a reply that stopped partway would pass off part of
        # the data as all of it, and not every provider says when it hit a limit.
        if _stops_mid_structure(reply):
            raise OutputContractError("the reply stops before its JSON is complete") from None
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
