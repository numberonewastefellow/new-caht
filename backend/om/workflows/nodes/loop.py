"""Built-in node type ``loop`` v1: repeat a body of steps.

A loop step is a container whose child steps (branch 0) form the body.

Modes:
    for_each: run the body once per item of a list (a JSON array, or one item
        per line of text) taken from a ``$reference``.
    while: run the body while a condition holds (checked before every
        iteration, against the latest iteration's outputs).

``max_iterations`` is mandatory (default 5, at most 50). Inside the body,
``$loop.item``, ``$loop.index`` (0-based) and ``$loop.previous`` (the previous
iteration's result) are available: as typed values to code steps, and as text
to agent input mappings.

Each iteration runs with a fresh copy of the workflow context, so iterations
only see each other through ``$loop.previous``. The loop's output is a JSON
array of every iteration's result (``collect: list``) or the last result
(``collect: last``); after the loop, the body steps' outputs are those of the
last iteration.
"""

from __future__ import annotations

import json
import time
from collections.abc import Generator
from typing import Any
from typing import Literal
from typing import TYPE_CHECKING

from pydantic import Field
from pydantic import model_validator
from pydantic import ValidationError

from om.server.query_and_chat.placement import Placement
from om.server.query_and_chat.streaming_models import Packet
from om.server.query_and_chat.streaming_models import SectionEnd
from om.server.query_and_chat.streaming_models import WorkflowStepDelta
from om.server.query_and_chat.streaming_models import WorkflowStepEnd
from om.server.query_and_chat.streaming_models import WorkflowStepStart
from om.utils.logger import setup_logger
from om.workflows.blocks import run_block
from om.workflows.branches import ScopedRunContext
from om.workflows.inputs import as_text
from om.workflows.inputs import UnresolvedReferenceError
from om.workflows.models import CONDITION_OPERATORS
from om.workflows.nodes.base import SaveContext
from om.workflows.nodes.container_trace import trace_container_finish
from om.workflows.nodes.container_trace import trace_container_start
from om.workflows.nodes.base import StepOutcome
from om.workflows.nodes.base import StepSaveError
from om.workflows.nodes.base import StepStatus
from om.workflows.nodes.router import ConditionFields
from om.workflows.state import RunState
from om.workflows.step_runners.conditional_router import evaluate_condition

if TYPE_CHECKING:
    from om.workflows.graph import WorkflowNode
    from om.workflows.models import WorkflowStepCreate
    from om.workflows.state import RunContext

logger = setup_logger()

LOOP_NODE_TYPE = "loop"
LOOP_VARIABLE = "loop"
STOPPED = "Stopped before it finished"
MAX_ITERATIONS = 50


class LoopConfigV1(ConditionFields):
    """Settings of a ``loop`` v1 step (the condition fields apply to ``while``)."""

    mode: Literal["for_each", "while"] = "for_each"
    items: str = Field(
        default="",
        description="for_each: a $reference to a JSON list or to text with one item "
        "per line (e.g. $research.output.items)",
    )
    max_iterations: int = Field(default=5, ge=1, le=MAX_ITERATIONS)
    collect: Literal["list", "last"] = "list"

    @model_validator(mode="after")
    def _mode_needs_its_settings(self) -> LoopConfigV1:
        if self.mode == "for_each" and not self.items.strip():
            raise ValueError("for_each loops need 'items' (a $reference to a list)")
        if self.mode == "while" and not self.condition_field.strip():
            raise ValueError("while loops need a condition ('condition_field')")
        return self


# ── Save-time validation ──────────────────────────────────────────────────


def prepare_loop_step_v1(step: WorkflowStepCreate, ctx: SaveContext) -> WorkflowStepCreate:
    try:
        config = LoopConfigV1.model_validate(step.config or {})
    except ValidationError as e:
        raise StepSaveError(
            f"Loop step '{step.step_name}': {e.errors()[0]['msg']}"
        ) from e
    if config.operator not in CONDITION_OPERATORS:
        # An unknown operator evaluates to False: the loop would silently never run.
        raise StepSaveError(
            f"Loop step '{step.step_name}': unknown operator '{config.operator}'"
        )
    key = step.node_key or ""
    body = [s for s in ctx.steps.values() if s.parent_key == key]
    if not body:
        raise StepSaveError(f"Loop step '{step.step_name}' has no steps to repeat")
    if any(s.branch_index != 0 for s in body):
        raise StepSaveError(
            f"Loop step '{step.step_name}': its steps must all be in branch 0"
        )
    return step.model_copy(update={"config": config.model_dump(mode="json")})


# ── Runner ────────────────────────────────────────────────────────────────


class LoopRunnerV1:
    """Runs a ``loop`` v1 node's body on the coordinator thread, iteration by iteration."""

    def run(self, node: WorkflowNode, ctx: RunContext) -> Generator[Packet, None, StepOutcome]:
        config = LoopConfigV1.model_validate(node.config)
        body = ctx.graph.branches(node.node_key)[0]
        state = ctx.state
        started = time.monotonic()

        placement = Placement(turn_index=state.turn.value)
        yield Packet(
            placement=placement,
            obj=WorkflowStepStart(
                step_name=node.name, agent_name=None,
                step_order=node.step_order, step_type=LOOP_NODE_TYPE,
            ),
        )
        try:
            items = self._items(config, ctx) if config.mode == "for_each" else None
        except UnresolvedReferenceError as e:
            message = f"Loop step '{node.name}': {e}"
            yield Packet(placement=placement, obj=WorkflowStepDelta(content=message))
            yield from _close(node, placement)
            state.turn.advance()
            return StepOutcome(status=StepStatus.FAILED, error=message)

        yield Packet(placement=placement, obj=WorkflowStepDelta(content=_describe(config, items)))
        yield from _close(node, placement)
        state.turn.advance()
        trace_id = trace_container_start(node, ctx, _describe(config, items))

        results: list[Any] = []
        last_scope: RunState | None = None
        # A while condition reads what the last iteration produced.
        condition_ctx = ctx
        limit = config.max_iterations if items is None else min(len(items), config.max_iterations)
        for index in range(limit):
            if ctx.stop_requested():
                trace_container_finish(ctx, trace_id, STOPPED, "failed", started)
                return StepOutcome(status=StepStatus.CANCELLED)
            item = items[index] if items is not None else None
            previous = results[-1] if results else None
            try:
                if config.mode == "while" and not _condition_holds(
                    config, condition_ctx, _loop_vars(item, index, previous)
                ):
                    break
            except UnresolvedReferenceError as e:
                message = f"Loop step '{node.name}': {e}"
                trace_container_finish(ctx, trace_id, message, "failed", started)
                return StepOutcome(status=StepStatus.FAILED, error=message)

            scope = _iteration_state(state, item, index, previous)
            scope_ctx = _scoped(ctx, scope)
            yield from _iteration_marker(node, ctx, index, limit, item)
            block_status = yield from run_block(body, scope_ctx)

            state.steps_executed.extend(scope.steps_executed)
            state.total_tokens += scope.total_tokens
            if block_status == StepStatus.CANCELLED:
                trace_container_finish(ctx, trace_id, STOPPED, "failed", started)
                return StepOutcome(status=StepStatus.CANCELLED)
            if scope.timed_out:
                state.timed_out = True
            results.append(_iteration_result(body, scope))
            last_scope = scope
            condition_ctx = scope_ctx
            if state.timed_out:
                break

        if last_scope is not None:
            _merge_last_iteration(ctx, body, last_scope)
        output = (
            json.dumps(results, ensure_ascii=False)
            if config.collect == "list"
            else as_text(results[-1] if results else "")
        )
        ctx.complete_node(node, output)
        state.steps_executed.append({
            "step_id": node.step_id,
            "agent_id": None,
            "step_name": node.name,
            "input_text": _describe(config, items)[:500],
            "output_text": output[:2000],
            "duration_ms": int((time.monotonic() - started) * 1000),
            "tokens_used": 0,
        })
        trace_container_finish(ctx, trace_id, output, "completed", started)
        return StepOutcome(status=StepStatus.COMPLETED, output=output)

    @staticmethod
    def _items(config: LoopConfigV1, ctx: RunContext) -> list[Any]:
        value = ctx.read_reference(config.items)
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, list):
                return parsed
            return [line.strip() for line in value.splitlines() if line.strip()]
        raise UnresolvedReferenceError(
            f"{config.items} is not a list (got {type(value).__name__})"
        )


# ── Iterations ────────────────────────────────────────────────────────────


def _loop_vars(item: Any, index: int, previous: Any) -> dict[str, Any]:
    return {"item": item, "index": index, "previous": previous}


def _iteration_state(state: RunState, item: Any, index: int, previous: Any) -> RunState:
    """A fresh scope for one iteration: a copy of the run's context + loop variables."""
    context = state.context.model_copy(deep=True)
    loop_vars = _loop_vars(item, index, previous)
    # Agent input mappings substitute text: expose $loop.item etc. as outputs.
    for name, value in loop_vars.items():
        context.step_outputs[f"{LOOP_VARIABLE}.{name}"] = as_text(value)
    return RunState(
        context=context,
        turn=state.turn,  # same thread: iterations share the run's cursor
        started_at=state.started_at,
        variables={**state.variables, LOOP_VARIABLE: loop_vars},
    )


def _scoped(ctx: RunContext, scope: RunState) -> ScopedRunContext:
    return ScopedRunContext(
        graph=ctx.graph,
        registry=ctx.registry,
        state=scope,
        db_session=ctx.db_session,
        user=ctx.user,
        emitter=ctx.emitter,
        execution=ctx.execution,
        trace=ctx.trace,
        agent_tools=ctx.agent_tools,
        # Stops with the block around it, such as a branch that lost a first_success.
        is_connected=lambda: not ctx.stop_requested(),
        chat_files=ctx.chat_files,
        sandbox_session_id=ctx.sandbox_session_id,
    )


def _condition_holds(
    config: LoopConfigV1, ctx: RunContext, loop_vars: dict[str, Any]
) -> bool:
    holds, explanation = evaluate_condition(
        config.condition_dict(),
        ctx.state.context,
        resolve=lambda ref: as_text(ctx.read_reference(ref, {LOOP_VARIABLE: loop_vars})),
    )
    logger.info("[Loop] %s", explanation)
    return holds


def _iteration_result(body: list[WorkflowNode], scope: RunState) -> Any:
    """The iteration's result: the output of its last completed step."""
    for node in reversed(body):
        if node.node_key in scope.completed_keys:
            output = scope.context.step_outputs.get(node.output_key, "")
            try:
                return json.loads(output)
            except (json.JSONDecodeError, TypeError):
                return output
    return None


def _merge_last_iteration(ctx: RunContext, body: list[WorkflowNode], scope: RunState) -> None:
    for node in body:
        if node.node_key in scope.completed_keys:
            ctx.state.record_output(node.output_key, scope.context.step_outputs[node.output_key])
            ctx.state.completed_keys.add(node.node_key)
    files = scope.context.shared_data.get("step_files", {})
    body_keys = {node.output_key for node in body}
    for key, info in files.items():
        if key in body_keys:
            ctx.state.context.shared_data.setdefault("step_files", {})[key] = info


def _iteration_marker(
    node: WorkflowNode, ctx: RunContext, index: int, total: int, item: Any
) -> Generator[Packet, None, None]:
    """A small timeline row per iteration, so runs show where each one starts."""
    placement = Placement(turn_index=ctx.state.turn.value)
    label = f"{node.name} · {index + 1}/{total}"
    yield Packet(
        placement=placement,
        obj=WorkflowStepStart(
            step_name=label, agent_name=None,
            step_order=node.step_order, step_type="loop_iteration",
        ),
    )
    if item is not None:
        preview = as_text(item)
        yield Packet(
            placement=placement,
            obj=WorkflowStepDelta(content=preview[:300] + ("…" if len(preview) > 300 else "")),
        )
    yield Packet(placement=placement, obj=WorkflowStepEnd(step_name=label, output_key=node.output_key))
    yield Packet(placement=placement, obj=SectionEnd())
    ctx.state.turn.advance()


def _describe(config: LoopConfigV1, items: list[Any] | None) -> str:
    if items is not None:
        note = (
            f" (only the first {config.max_iterations} of {len(items)})"
            if len(items) > config.max_iterations
            else ""
        )
        return f"Repeating for each of {len(items)} items{note}"
    return (
        f"Repeating while {config.condition_field} {config.operator} "
        f"'{config.match_value}' (at most {config.max_iterations} times)"
    )


def _close(node: WorkflowNode, placement: Placement) -> Generator[Packet, None, None]:
    yield Packet(
        placement=placement,
        obj=WorkflowStepEnd(step_name=node.name, output_key=node.output_key),
    )
    yield Packet(placement=placement, obj=SectionEnd())
