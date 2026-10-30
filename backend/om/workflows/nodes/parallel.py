"""Built-in node type ``parallel`` v1: run branches of steps at the same time.

A parallel step is a container: its child steps carry ``parent_key`` (this
step) and a ``branch_index``. Each branch runs its steps in order; branches run
concurrently (see om/workflows/branches.py). The container's output is JSON
``{branch label: that branch's last output}``, and every child's own output is
also available to later steps under its output key.
"""

from __future__ import annotations

import json
import time
from collections.abc import Generator
from typing import Literal
from typing import TYPE_CHECKING

from pydantic import BaseModel
from pydantic import Field
from pydantic import ValidationError

from om.server.query_and_chat.placement import Placement
from om.server.query_and_chat.streaming_models import Packet
from om.server.query_and_chat.streaming_models import SectionEnd
from om.server.query_and_chat.streaming_models import WorkflowStepDelta
from om.server.query_and_chat.streaming_models import WorkflowStepEnd
from om.server.query_and_chat.streaming_models import WorkflowStepStart
from om.utils.logger import setup_logger
from om.workflows.branches import last_output
from om.workflows.branches import merge_branch
from om.workflows.branches import run_branches
from om.workflows.nodes.base import SaveContext
from om.workflows.nodes.base import StepOutcome
from om.workflows.nodes.base import StepSaveError
from om.workflows.nodes.base import StepStatus

if TYPE_CHECKING:
    from om.workflows.graph import WorkflowNode
    from om.workflows.models import WorkflowStepCreate
    from om.workflows.state import RunContext

logger = setup_logger()

PARALLEL_NODE_TYPE = "parallel"
MAX_BRANCHES = 8


class BranchSpec(BaseModel):
    label: str = Field(min_length=1, max_length=80)


class ParallelConfigV1(BaseModel):
    """Settings of a ``parallel`` v1 step."""

    branches: list[BranchSpec] = Field(
        default_factory=lambda: [BranchSpec(label="Branch 1"), BranchSpec(label="Branch 2")],
        min_length=2,
        max_length=MAX_BRANCHES,
    )
    join: Literal["wait_all", "first_success"] = Field(
        default="wait_all",
        description="wait_all: continue when every branch finished; "
        "first_success: continue as soon as one branch succeeds",
    )
    on_branch_error: Literal["fail", "continue"] = Field(
        default="fail",
        description="fail: the workflow fails if any branch fails; "
        "continue: record the error and keep the other branches' results",
    )
    max_concurrency: int = Field(default=4, ge=1, le=MAX_BRANCHES)


# ── Save-time validation ──────────────────────────────────────────────────


def prepare_parallel_step_v1(
    step: WorkflowStepCreate, ctx: SaveContext
) -> WorkflowStepCreate:
    try:
        config = ParallelConfigV1.model_validate(step.config or {})
    except ValidationError as e:
        error = e.errors()[0]
        location = ".".join(str(p) for p in error["loc"])
        raise StepSaveError(
            f"Parallel step '{step.step_name}': {location}: {error['msg']}"
        ) from e

    key = step.node_key or ""
    if any(ctx.steps[a].node_type == PARALLEL_NODE_TYPE for a in ctx.ancestors(key)):
        raise StepSaveError(
            f"Parallel step '{step.step_name}' can't be inside another parallel step"
        )

    used = {s.branch_index for s in ctx.steps.values() if s.parent_key == key}
    out_of_range = sorted(i for i in used if i is not None and i >= len(config.branches))
    if out_of_range:
        raise StepSaveError(
            f"Parallel step '{step.step_name}' has steps in branches {out_of_range}, "
            f"but only {len(config.branches)} branches are defined"
        )
    empty = [b.label for i, b in enumerate(config.branches) if i not in used]
    if empty:
        raise StepSaveError(
            f"Parallel step '{step.step_name}': branches without steps: {', '.join(empty)}"
        )
    return step.model_copy(update={"config": config.model_dump(mode="json")})


# ── Runner ────────────────────────────────────────────────────────────────


class ParallelRunnerV1:
    """Runs a ``parallel`` v1 node's branches concurrently and joins them."""

    def run(
        self, node: WorkflowNode, ctx: RunContext
    ) -> Generator[Packet, None, StepOutcome]:
        config = ParallelConfigV1.model_validate(node.config)
        branches = ctx.graph.branches(node.node_key)
        labels = [
            config.branches[i].label if i < len(config.branches) else f"Branch {i + 1}"
            for i in range(len(branches))
        ]
        state = ctx.state
        started = time.monotonic()

        # Header step for the container, closed before the branches stream.
        placement = Placement(turn_index=state.turn.value)
        yield Packet(
            placement=placement,
            obj=WorkflowStepStart(
                step_name=node.name,
                agent_name=None,
                step_order=node.step_order,
                step_type=PARALLEL_NODE_TYPE,
            ),
        )
        yield Packet(
            placement=placement,
            obj=WorkflowStepDelta(
                content=f"Running {len(branches)} branches in parallel: {', '.join(labels)}"
            ),
        )
        yield from _close(node, placement)
        state.turn.advance()
        trace_id = self._trace_start(node, ctx, labels)

        results = yield from run_branches(
            node,
            branches,
            ctx,
            max_concurrency=config.max_concurrency,
            first_success=config.join == "first_success",
        )

        for nodes, result in zip(branches, results):
            if result is not None:
                merge_branch(ctx, nodes, result)
        state.turn.advance()

        if ctx.stop_requested():
            return StepOutcome(status=StepStatus.CANCELLED)

        failures = [r for r in results if r is not None and not r.succeeded]
        if failures and config.on_branch_error == "fail":
            first = failures[0]
            message = (
                f"Parallel step '{node.name}': branch '{labels[first.index]}' failed: "
                f"{first.error or first.status.value}"
            )
            self._trace_finish(ctx, trace_id, message, "failed", started)
            return StepOutcome(status=StepStatus.FAILED, error=message)

        combined: dict[str, object] = {}
        for nodes, result, label in zip(branches, results, labels):
            if result is None:
                continue
            combined[label] = (
                last_output(nodes, result)
                if result.succeeded
                else {"error": result.error or result.status.value}
            )
        output = json.dumps(combined, ensure_ascii=False)
        ctx.complete_node(node, output)
        state.steps_executed.append({
            "step_id": node.step_id,
            "agent_id": None,
            "step_name": node.name,
            "input_text": f"{len(branches)} branches: {', '.join(labels)}",
            "output_text": output[:2000],
            "duration_ms": int((time.monotonic() - started) * 1000),
            "tokens_used": 0,
        })
        self._trace_finish(ctx, trace_id, output, "completed", started)
        return StepOutcome(status=StepStatus.COMPLETED, output=output)

    @staticmethod
    def _trace_start(node: WorkflowNode, ctx: RunContext, labels: list[str]) -> str | None:
        try:
            trace_id = ctx.trace.start_step(
                step_id=node.step_id,
                name=node.name,
                node_type=PARALLEL_NODE_TYPE,
                input_text=", ".join(labels),
            )
            ctx.persist_trace()
            return trace_id
        except Exception:
            logger.debug("[Trace] parallel start failed", exc_info=True)
            return None

    @staticmethod
    def _trace_finish(
        ctx: RunContext, trace_id: str | None, output: str, status: str, started: float
    ) -> None:
        try:
            ctx.trace.finish_agent(
                trace_id,
                output,
                status=status,  # type: ignore[arg-type]
                duration_ms=int((time.monotonic() - started) * 1000),
            )
            ctx.persist_trace()
        except Exception:
            logger.debug("[Trace] parallel finish failed", exc_info=True)


def _close(node: WorkflowNode, placement: Placement) -> Generator[Packet, None, None]:
    yield Packet(
        placement=placement,
        obj=WorkflowStepEnd(step_name=node.name, output_key=node.output_key),
    )
    yield Packet(placement=placement, obj=SectionEnd())
