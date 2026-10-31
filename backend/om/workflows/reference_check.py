"""Save-time check of the ``$references`` in a workflow (``schema_version`` 2).

A step can read the user's input, its loop's variables, and the output of steps that
have run by then: earlier steps in its own block or in the blocks around it, plus the
direct children of an earlier container, which are merged when the container ends. A
parallel branch can't read a sibling branch, which runs at the same time. A while loop's
condition also reads its own variables and what its body produced.

Text settings can mention references anywhere (``render_template``). Other settings are
one value, a literal or a single reference (``resolve_reference``).
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from collections.abc import Sequence
from typing import Any
from typing import Protocol

from om.workflows.inputs import find_references
from om.workflows.inputs import is_reference
from om.workflows.inputs import reference_name

USER_INPUT = "user_input"
LOOP_VARIABLES = "loop"
LOOP_NODE_TYPE = "loop"
LOOP_FIELDS = ("item", "index", "previous")
_LOOP_FIELD = re.compile(r"^\$loop\.([A-Za-z_][A-Za-z0-9_]*)")


class _Step(Protocol):
    node_key: str | None
    step_type: str
    step_name: str
    step_order: int
    output_key: str
    parent_key: str | None
    branch_index: int | None
    input_mapping: dict[str, Any] | None
    config: dict[str, Any] | None
    condition: Any


def _templates_of(step: _Step) -> Iterable[str]:
    for value in (step.input_mapping or {}).values():
        if isinstance(value, str):
            yield value


def _router_field(step: _Step) -> Any:
    condition = step.condition
    return (
        condition.get("condition_field")
        if isinstance(condition, dict)
        else getattr(condition, "condition_field", None)
    )


def _values_of(step: _Step) -> Iterable[Any]:
    """The settings read as one value before the step runs."""
    config = step.config or {}
    yield from (config.get("inputs") or {}).values()
    yield config.get("items")
    yield _router_field(step)
    if step.step_type != LOOP_NODE_TYPE:
        yield config.get("condition_field")


def _loop_condition(step: _Step) -> Any:
    config = step.config or {}
    if step.step_type == LOOP_NODE_TYPE and config.get("mode") == "while":
        return config.get("condition_field")
    return None


def _visible_names(step: _Step, steps: Sequence[_Step]) -> set[str]:
    by_key = {s.node_key: s for s in steps}
    children: dict[str | None, list[_Step]] = {}
    for candidate in steps:
        children.setdefault(candidate.parent_key, []).append(candidate)

    names = {USER_INPUT}
    scope: _Step | None = step
    while scope is not None:
        for earlier in children.get(scope.parent_key, []):
            if (
                earlier.branch_index == scope.branch_index
                and earlier.step_order < scope.step_order
            ):
                names.add(earlier.output_key)
                names |= {c.output_key for c in children.get(earlier.node_key, [])}
        parent = by_key.get(scope.parent_key) if scope.parent_key else None
        if parent is not None and parent.step_type == LOOP_NODE_TYPE:
            names.add(LOOP_VARIABLES)
        scope = parent
    return names


def _unavailable(step: _Step, references: Iterable[str], names: set[str]) -> str | None:
    for reference in references:
        if reference_name(reference) not in names:
            return (
                f'"{step.step_name}" reads {reference}, which isn\'t available there. '
                f"It can read: {', '.join(f'${n}' for n in sorted(names))}"
            )
        field = _LOOP_FIELD.match(reference)
        if field and field.group(1) not in LOOP_FIELDS:
            return (
                f'"{step.step_name}" reads {reference}: a loop has '
                f"{', '.join(f'$loop.{f}' for f in LOOP_FIELDS)}"
            )
    return None


def _value_problem(step: _Step, value: Any, names: set[str]) -> str | None:
    if not isinstance(value, str) or not value.startswith("$"):
        return None
    if not is_reference(value):
        return (
            f'"{step.step_name}" has {value}: a value starting with $ must be a single '
            "reference, like $step.output.field"
        )
    return _unavailable(step, [value], names)


def reference_problem(steps: Sequence[_Step]) -> str | None:
    """The first reference that can't resolve when its step runs, if any."""
    for step in sorted(steps, key=lambda s: s.step_order):
        visible = _visible_names(step, steps)
        problems = [
            *(_unavailable(step, find_references(t), visible) for t in _templates_of(step)),
            *(_value_problem(step, v, visible) for v in _values_of(step)),
        ]
        body = {s.output_key for s in steps if s.parent_key == step.node_key}
        problems.append(
            _value_problem(step, _loop_condition(step), visible | body | {LOOP_VARIABLES})
        )
        problem = next((p for p in problems if p), None)
        if problem:
            return problem
    return None
