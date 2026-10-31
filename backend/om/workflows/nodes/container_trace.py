"""The trace node of a container step (parallel, loop): best effort, like all tracing."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from om.utils.logger import setup_logger

if TYPE_CHECKING:
    from om.workflows.graph import WorkflowNode
    from om.workflows.state import RunContext

logger = setup_logger()


def trace_container_start(
    node: WorkflowNode, ctx: RunContext, input_text: str
) -> str | None:
    try:
        trace_id = ctx.trace.start_step(
            step_id=node.step_id,
            name=node.name,
            node_type=node.node_type,
            input_text=input_text,
        )
        ctx.persist_trace()
        return trace_id
    except Exception:
        logger.debug("[Trace] %s start failed", node.node_type, exc_info=True)
        return None


def trace_container_finish(
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
        logger.debug("[Trace] container finish failed", exc_info=True)
