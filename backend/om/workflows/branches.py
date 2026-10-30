"""Run a container's branches concurrently: coordinator + branch workers.

Design (docs/flow-nodes/DESIGN.md "Containers"; pattern from Dify's graphon
dispatcher, with LangGraph's ordered merge):

- The calling (generator) thread is the only coordinator. It yields packets,
  and it alone touches the run's DB session, checkpoint and trace.
- Each branch runs ``run_block`` in a worker thread with a ``ScopedRunContext``:
  a deep copy of the workflow context (branches can't see each other's
  writes), its own run state and turn range, its own DB session, emitter and
  agent tools. Checkpoint/progress/trace persistence are no-ops there; trace
  calls are buffered and replayed on the run's trace at the join.
- Workers send ``(branch, packet)`` events through one queue; the coordinator
  forwards them as they arrive and watches for stop requests.
- Results are merged into the run **in declared branch order**, so the outcome
  does not depend on which branch finished first.
"""

from __future__ import annotations

import contextvars
import threading
from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from dataclasses import field
from queue import Empty
from queue import Queue
from typing import Any

from om.chat.emitter import get_default_emitter
from om.db.engine.sql_engine import get_session_with_current_tenant
from om.db.models import User
from om.server.query_and_chat.streaming_models import Packet
from om.utils.logger import setup_logger
from om.workflows.blocks import run_block
from om.workflows.graph import WorkflowNode
from om.workflows.nodes.agent_tools import AgentToolCache
from om.workflows.nodes.base import StepStatus
from om.workflows.state import RunContext
from om.workflows.state import RunState
from om.workflows.state import TurnCursor

logger = setup_logger()

# Each branch gets its own range of Placement.turn_index values, so its steps
# and its sub-agents' tool groups never collide with another branch's.
BRANCH_TURN_STRIDE = 1000

_POLL_SECONDS = 0.05
_DONE = object()


class BufferedTrace:
    """Records the trace calls a branch makes; replayed on the run's trace later.

    Returns stand-in node ids so runners can pair ``start_*`` with
    ``finish_agent`` exactly as they do on the real trace builder.
    """

    def __init__(self, prefix: str) -> None:
        self._prefix = prefix
        self._count = 0
        self._calls: list[tuple[str, str | None, tuple[Any, ...], dict[str, Any]]] = []

    def _record(self, method: str, args: tuple[Any, ...], kwargs: dict[str, Any]) -> str:
        self._count += 1
        ref = f"{self._prefix}{self._count}"
        self._calls.append((method, ref, args, kwargs))
        return ref

    def start_agent(self, *args: Any, **kwargs: Any) -> str:
        return self._record("start_agent", args, kwargs)

    def start_step(self, *args: Any, **kwargs: Any) -> str:
        return self._record("start_step", args, kwargs)

    def add_router(self, *args: Any, **kwargs: Any) -> str:
        return self._record("add_router", args, kwargs)

    def finish_agent(self, node_ref: str | None, *args: Any, **kwargs: Any) -> None:
        self._calls.append(("finish_agent", node_ref, args, kwargs))

    def replay(self, builder: Any) -> None:
        """Apply the recorded calls to a real ``WorkflowTraceBuilder``."""
        real_ids: dict[str, str | None] = {}
        for method, ref, args, kwargs in self._calls:
            if method == "finish_agent":
                builder.finish_agent(real_ids.get(ref or ""), *args, **kwargs)
            else:
                real_ids[ref or ""] = getattr(builder, method)(*args, **kwargs)


@dataclass
class ScopedRunContext(RunContext):
    """A child scope of the run (a parallel branch or a loop iteration).

    It has its own state but never persists anything itself: the container
    that owns the scope checkpoints and records results when it completes.
    """

    cancel_event: threading.Event = field(default_factory=threading.Event)

    def stop_requested(self) -> bool:
        return self.cancel_event.is_set() or super().stop_requested()

    def save_checkpoint(self, **_: Any) -> None:
        """Branches never checkpoint; the container checkpoints when it completes."""

    def persist_progress(self, **_: Any) -> None:
        """Branch accounting is merged into the run at the join."""

    def persist_trace(self, include_message_key: bool = False) -> None:
        """Branch trace calls are buffered and replayed at the join."""


@dataclass
class BranchResult:
    """How one branch ended, with everything needed to merge it."""

    index: int
    status: StepStatus
    state: RunState
    trace: BufferedTrace
    error: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.status == StepStatus.COMPLETED and self.error is None


def run_branches(
    container: WorkflowNode,
    branches: list[list[WorkflowNode]],
    ctx: RunContext,
    *,
    max_concurrency: int,
    first_success: bool = False,
) -> Generator[Packet, None, list[BranchResult | None]]:
    """Run ``branches`` concurrently and forward their packets as they arrive.

    Returns one result per branch, in branch order; ``None`` for branches that
    never finished (cancelled, or stopped early by ``first_success``).
    """
    base_turn = ctx.state.turn.value
    events: Queue[tuple[int, Any]] = Queue()
    cancel = threading.Event()
    results: list[BranchResult | None] = [None] * len(branches)
    user_id = ctx.user.id

    def work(index: int, nodes: list[WorkflowNode]) -> None:
        state = RunState(
            context=ctx.state.context.model_copy(deep=True),
            turn=TurnCursor(base_turn + index * BRANCH_TURN_STRIDE),
            # The workflow timeout counts from the start of the run.
            started_at=ctx.state.started_at,
            variables=dict(ctx.state.variables),
        )
        trace = BufferedTrace(prefix=f"{container.node_key}/{index}/")
        try:
            with get_session_with_current_tenant() as db_session:
                # ORM objects are not shared across threads: reload in this session.
                user = db_session.get(User, user_id)
                emitter = get_default_emitter()
                branch_ctx = ScopedRunContext(
                    graph=ctx.graph,
                    registry=ctx.registry,
                    state=state,
                    db_session=db_session,
                    user=user,  # type: ignore[arg-type]
                    emitter=emitter,
                    execution=ctx.execution,
                    trace=trace,  # type: ignore[arg-type]
                    agent_tools=AgentToolCache(
                        db_session=db_session,
                        user=user,  # type: ignore[arg-type]
                        emitter=emitter,
                        chat_files=ctx.chat_files,
                        # A sandbox session is stateful; branches must not share it.
                        sandbox_session_id=None,
                    ),
                    is_connected=ctx.is_connected,
                    chat_files=ctx.chat_files,
                    cancel_event=cancel,
                )
                status = yield_to_queue(run_block(nodes, branch_ctx), index, events)
            results[index] = BranchResult(index, status, state, trace)
        except Exception as e:
            logger.exception(
                "[Parallel] Branch %d of '%s' failed", index, container.name
            )
            results[index] = BranchResult(index, StepStatus.FAILED, state, trace, str(e))
        finally:
            events.put((index, _DONE))

    workers = max(1, min(max_concurrency, len(branches)))
    pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="wf-branch")
    for index, nodes in enumerate(branches):
        pool.submit(contextvars.copy_context().run, work, index, nodes)

    remaining = len(branches)
    try:
        while remaining:
            event = _next_event(events)
            if event is None:
                if ctx.stop_requested():
                    logger.info("[Parallel] Stop requested in '%s'", container.name)
                    break
                continue
            index, item = event
            if item is _DONE:
                remaining -= 1
                result = results[index]
                if first_success and result is not None and result.succeeded:
                    break
                continue
            yield item
    finally:
        # Stops branches between nodes; running agents finish on their own
        # (threads can't be killed) and their late packets are discarded.
        cancel.set()
        pool.shutdown(wait=False, cancel_futures=True)

    if remaining:
        # Only results of branches that finished before we stopped count.
        return [r if r is not None and r.status != StepStatus.CANCELLED else None for r in results]
    return results


def _next_event(events: Queue[tuple[int, Any]]) -> tuple[int, Any] | None:
    """The next branch event, or None when none arrived within the poll interval."""
    try:
        return events.get(timeout=_POLL_SECONDS)
    except Empty:
        return None


def yield_to_queue(
    gen: Generator[Packet, None, StepStatus], index: int, events: Queue[tuple[int, Any]]
) -> StepStatus:
    """Drive a branch's block, sending each packet to the coordinator."""
    while True:
        try:
            events.put((index, next(gen)))
        except StopIteration as stop:
            return stop.value


def merge_branch(ctx: RunContext, nodes: list[WorkflowNode], result: BranchResult) -> None:
    """Fold a finished branch into the run (outputs, files, accounting, trace)."""
    branch = result.state
    for node in nodes:
        if node.node_key in branch.completed_keys:
            ctx.state.record_output(
                node.output_key, branch.context.step_outputs[node.output_key]
            )
            ctx.state.completed_keys.add(node.node_key)

    branch_output_keys = {node.output_key for node in nodes}
    branch_files = branch.context.shared_data.get("step_files", {})
    for key, files in branch_files.items():
        if key in branch_output_keys:
            ctx.state.context.shared_data.setdefault("step_files", {})[key] = files

    ctx.state.steps_executed.extend(branch.steps_executed)
    ctx.state.total_tokens += branch.total_tokens
    result.trace.replay(ctx.trace)
    ctx.state.turn.observe(branch.turn.value)


def last_output(nodes: list[WorkflowNode], result: BranchResult) -> str | None:
    """The output of the last node that completed in a branch."""
    for node in reversed(nodes):
        if node.node_key in result.state.completed_keys:
            return result.state.context.step_outputs.get(node.output_key)
    return None
