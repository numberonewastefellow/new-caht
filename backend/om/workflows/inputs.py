"""Build a step's task input from the workflow context, and collect its files.

Shared by the sequential and llm_decision orchestration modes.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any

from om.workflows.models import WorkflowContext


def apply_input_mapping(
    mapping: dict[str, Any] | None,
    context: WorkflowContext,
) -> str:
    """Apply input mapping to resolve context references into a task string.

    Legacy semantics (workflow ``schema_version`` 1): references are replaced
    by plain substring substitution, so ``$research`` also matches the start
    of ``$research_notes``. Kept as-is so existing workflows behave the same.
    """
    if not mapping:
        # Default: pass user input + all previous outputs
        parts = [f"User request: {context.user_input}"]
        for key, output in context.step_outputs.items():
            parts.append(f"\nOutput from '{key}':\n{output}")

        # Inject structured file metadata from previous steps so downstream
        # agents know exact filenames and paths without relying on text parsing.
        step_files = context.shared_data.get("step_files", {})
        if step_files:
            file_lines: list[str] = []
            for step_key, file_info in step_files.items():
                for f in file_info.get("files", []):
                    file_lines.append(
                        f"- {f['filename']} "
                        f"(path: {f['file_path']}, from step '{step_key}')"
                    )
            if file_lines:
                parts.append(
                    "\nFiles created by previous steps:\n"
                    + "\n".join(file_lines)
                )

        return "\n".join(parts)

    result_parts = []
    for key, template in mapping.items():
        if isinstance(template, str):
            # Replace $user_input with actual user input
            resolved = template.replace("$user_input", context.user_input)
            # Replace step output references — support both $key.output and $key
            # Do longer pattern first to avoid partial matches
            for output_key, output in context.step_outputs.items():
                resolved = resolved.replace(f"${output_key}.output", output)
            for output_key, output in context.step_outputs.items():
                resolved = resolved.replace(f"${output_key}", output)
            result_parts.append(f"{key}: {resolved}")
        else:
            result_parts.append(f"{key}: {template}")
    return "\n".join(result_parts)


class UnresolvedReferenceError(LookupError):
    """A ``$reference`` names an output (or JSON path) that does not exist."""


# $name, $name.output, $name.output.<path> or $name.<path> where <path> is
# dotted keys and [index] segments, e.g. $research.output.items[0].title or
# $loop.item.title
_REFERENCE = re.compile(
    r"^\$(?P<name>[A-Za-z_][A-Za-z0-9_]*)"
    r"(?:\.output)?(?P<path>(?:\.[A-Za-z_][A-Za-z0-9_]*|\[\d+\])*)$"
)
_PATH_SEGMENT = re.compile(r"\.([A-Za-z_][A-Za-z0-9_]*)|\[(\d+)\]")


def resolve_reference(
    value: str,
    context: WorkflowContext,
    variables: Mapping[str, Any] | None = None,
) -> Any:
    """Resolve a typed input value for nodes that take structured inputs.

    - Not starting with ``$``: returned as-is (a literal).
    - ``$user_input``: the user's request.
    - ``$name`` / ``$name.output``: the raw output text of step ``name``.
    - ``$name.output.a.b[0]`` (or ``$name.a.b[0]``): parse that output as
      JSON and follow the path.
    - ``variables`` provides extra names (e.g. ``loop`` for loop variables:
      ``$loop.item``, ``$loop.index``) and takes precedence over step outputs.

    Raises:
        UnresolvedReferenceError: The output or path does not exist, or the
            output is not valid JSON when a path is given.
    """
    if not value.startswith("$"):
        return value
    match = _REFERENCE.match(value)
    if match is None:
        raise UnresolvedReferenceError(f"Invalid reference {value!r}")
    name, path = match.group("name"), match.group("path")

    if variables is not None and name in variables:
        base: Any = variables[name]
    elif name == "user_input":
        base = context.user_input
    elif name in context.step_outputs:
        base = context.step_outputs[name]
    else:
        raise UnresolvedReferenceError(
            f"{value}: no step output named {name!r} "
            f"(available: {sorted(context.step_outputs)})"
        )
    if not path:
        return base
    return _follow_json_path(value, base, path)


def _follow_json_path(reference: str, base: Any, path: str) -> Any:
    current = base
    if isinstance(current, str):
        try:
            current = json.loads(current)
        except json.JSONDecodeError as e:
            raise UnresolvedReferenceError(
                f"{reference}: the output is not JSON, so it has no fields"
            ) from e
    for key, index in _PATH_SEGMENT.findall(path):
        try:
            current = current[int(index)] if index else current[key]
        except (KeyError, IndexError, TypeError) as e:
            raise UnresolvedReferenceError(f"{reference}: path not found") from e
    return current


def collect_workflow_files(
    step_files: dict[str, Any],
) -> tuple[list[str], list[str]]:
    """Aggregate deliverable files across steps, de-duplicated by filename.

    Each agent step captures and re-saves any office file it touches under a
    fresh file_id (see collect_pending_files), with no cross-step de-dup. When
    several steps touch the same document (e.g. a builder creates it and a
    reviewer edits it), the same filename ends up saved multiple times. Here we
    keep only the most recently saved version per filename (last writer wins).

    step_files is dict-ordered by execution order, and within each step
    file_ids[i] corresponds to files[i] (built in lockstep by
    collect_pending_files), so iterating + overwriting yields the latest id.

    Returns (file_ids, file_names) aligned by index.
    """
    latest_by_name: dict[str, str] = {}
    for _step_key, file_info in step_files.items():
        file_ids = file_info.get("file_ids", [])
        files = file_info.get("files", [])
        for fid, f in zip(file_ids, files):
            latest_by_name[f["filename"]] = fid
    return list(latest_by_name.values()), list(latest_by_name.keys())
