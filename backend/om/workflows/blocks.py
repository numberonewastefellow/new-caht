"""Run a block of workflow nodes in order (the top level, or a container branch).

Each node is executed by the runner registered for its ``(type, version)``;
this loop only decides what runs next: it honours stop requests, skips
completed and router-deactivated nodes, and stops on pause, cancel, a
terminal node, or the workflow timeout.
"""

from __future__ import annotations

from collections.abc import Generator
from typing import TYPE_CHECKING

from om.server.query_and_chat.streaming_models import WorkflowStepStart
from om.utils.logger import setup_logger
from om.workflows.nodes.base import StepStatus

if TYPE_CHECKING:
    from om.server.query_and_chat.streaming_models import Packet
    from om.workflows.nodes.base import StepOutcome
    from om.workflows.graph import WorkflowNode
    from om.workflows.state import RunContext

logger = setup_logger()


class WorkflowNodeError(RuntimeError):
    """A node runner reported a failure."""


def _scope_of(node: WorkflowNode, ctx: RunContext) -> tuple[str | None, int | None]:
    """Where a node runs, for the timeline and trace; None at the top level."""
    if node.parent_key is None:
        return None, None
    parent = ctx.graph.node_for_key(node.parent_key)
    if parent is None:
        return None, None

    depth = 0
    ancestor: WorkflowNode | None = parent
    while ancestor is not None:
        depth += 1
        ancestor = (
            ctx.graph.node_for_key(ancestor.parent_key) if ancestor.parent_key else None
        )

    loop = ctx.state.variables.get("loop")
    if parent.node_type == "loop" and isinstance(loop, dict):
        return f"{parent.name} · {loop.get('index', 0) + 1}", depth
    branches = (parent.config or {}).get("branches") or []
    index = node.branch_index or 0
    if index < len(branches):
        return f"{parent.name} · {branches[index].get('label')}", depth
    return parent.name, depth


def _in_scope(
    packets: Generator[Packet, None, StepOutcome], scope: str | None, depth: int | None
) -> Generator[Packet, None, StepOutcome]:
    """Tag the steps a node starts; nested steps already carry their own scope."""
    if scope is None:
        return (yield from packets)
    while True:
        try:
            packet = next(packets)
        except StopIteration as stop:
            return stop.value
        if isinstance(packet.obj, WorkflowStepStart) and packet.obj.scope is None:
            packet = packet.model_copy(
                update={"obj": packet.obj.model_copy(update={"scope": scope, "depth": depth})}
            )
        yield packet


def run_block(
    nodes: list[WorkflowNode], ctx: RunContext
) -> Generator[Packet, None, StepStatus]:
    """Run ``nodes`` in order and report how the block ended.

    Returns COMPLETED (ran to the end, a terminal node, or a timeout), PAUSED
    or CANCELLED.

    Raises:
        WorkflowNodeError: a node failed.
    """
    state = ctx.state
    for node in nodes:
        if ctx.stop_requested():
            logger.info("Workflow cancelled by user before step %s", node.name)
            state.cancelled = True
            return StepStatus.CANCELLED

        if node.node_key in state.completed_keys:
            logger.debug(
                "[Sequential] Skipping completed step '%s' (key=%s)",
                node.name, node.node_key,
            )
            continue
        if node.node_key in state.skipped_keys:
            logger.info(
                "[Sequential] Skipping step '%s' (order=%d) — "
                "inactive conditional branch",
                node.name, node.step_order,
            )
            continue

        runner = ctx.registry.get(node.node_type, node.type_version).runner
        scope, depth = _scope_of(node, ctx)
        ctx.trace.set_scope(scope, depth)
        outcome = yield from _in_scope(runner.run(node, ctx), scope, depth)

        if outcome.status == StepStatus.SKIPPED:
            continue
        if outcome.status == StepStatus.PAUSED:
            return StepStatus.PAUSED
        if outcome.status == StepStatus.CANCELLED:
            state.cancelled = True
            return StepStatus.CANCELLED
        if outcome.status == StepStatus.FAILED:
            raise WorkflowNodeError(outcome.error or f"Step '{node.name}' failed")

        if state.elapsed_seconds() > ctx.graph.timeout_seconds:
            logger.warning(f"Workflow timeout after {state.elapsed_seconds():.1f}s")
            state.timed_out = True
            return StepStatus.COMPLETED
        if outcome.status == StepStatus.TERMINAL:
            return StepStatus.COMPLETED
    return StepStatus.COMPLETED
