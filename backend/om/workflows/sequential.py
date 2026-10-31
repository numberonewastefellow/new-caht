"""Sequential workflow coordinator (engine v2).

Runs a workflow's nodes in order. The coordinator owns the run lifecycle
(fresh start or resume, trace, final summary, final status); each node is
executed by the runner registered for its ``(type, version)`` in the node type
registry, so adding a node type never touches this module.

This is the only place that decides *what runs next*. Runners decide *how a
node runs* and record their results through ``RunContext``.

Behaviour matches the legacy ``run_workflow_sequential`` (guarded by the golden
harness), plus these intentional fixes:
- a timed-out run ends with status "timeout" instead of "completed";
- router branch skips and output order survive pause/resume;
- step-level LLM and tool overrides are honoured;
- a legacy checkpoint whose steps no longer exist starts a fresh run instead of
  silently re-running the wrong steps.
"""

from __future__ import annotations

import datetime
from collections.abc import Callable
from collections.abc import Generator
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from om.chat.emitter import Emitter
from om.db.models import AgentWorkflow
from om.db.models import User
from om.db.models import WorkflowExecution
from om.db.workflow import create_workflow_execution
from om.db.workflow import get_workflow_for_update
from om.db.workflow import load_checkpoint
from om.server.query_and_chat.placement import Placement
from om.server.query_and_chat.streaming_models import AgentResponseDelta
from om.server.query_and_chat.streaming_models import AgentResponseStart
from om.server.query_and_chat.streaming_models import OverallStop
from om.server.query_and_chat.streaming_models import Packet
from om.server.query_and_chat.streaming_models import SectionEnd
from om.tools.models import ChatFile
from om.utils.logger import setup_logger
from om.workflows.blocks import run_block
from om.workflows.graph import graph_from_workflow
from om.workflows.graph import WorkflowGraph
from om.workflows.inputs import collect_workflow_files
from om.workflows.models import WorkflowContext
from om.workflows.nodes.agent_tools import AgentToolCache
from om.workflows.nodes.base import StepStatus
from om.workflows.nodes.builtin import get_node_registry
from om.workflows.nodes.registry import NodeTypeRegistry
from om.workflows.state import everything_user_said
from om.workflows.state import restore_run_state
from om.workflows.state import ResumeIncompatibleError
from om.workflows.state import RunContext
from om.workflows.state import RunState
from om.workflows.trace_models import load_workflow_trace
from om.workflows.trace_models import WorkflowTraceBuilder
from om.workflows.versioning import graph_for_execution
from om.workflows.versioning import pin_workflow_version

logger = setup_logger()


def run_workflow_sequential_v2(
    workflow: AgentWorkflow,
    user_message: str,
    emitter: Emitter,
    db_session: Session,
    user: User,
    is_connected: Callable[[], bool] | None = None,
    chat_session_id: UUID | None = None,
    paused_execution: WorkflowExecution | None = None,
    chat_files: list[ChatFile] | None = None,
    sandbox_session_id: str | None = None,
    assistant_message_id: int | None = None,
) -> Generator[Packet, None, None]:
    """Run a workflow in sequential mode — fixed order, no LLM routing.

    Each node's output becomes available to the following nodes. Supports
    pause/resume via checkpoints (human-in-the-loop).
    """
    registry = get_node_registry()
    logger.info(
        "[Sequential] Starting with %d steps, resume=%s",
        len(workflow.steps),
        paused_execution is not None,
    )

    execution, state, graph = _start_or_resume(
        registry, workflow, user_message, db_session, user, chat_session_id,
        paused_execution,
    )
    trace = _init_trace(
        execution, workflow, chat_session_id, assistant_message_id,
        user_message, chat_files, resumed=paused_execution is not None,
    )
    ctx = RunContext(
        graph=graph,
        registry=registry,
        state=state,
        db_session=db_session,
        user=user,
        emitter=emitter,
        execution=execution,
        trace=trace,
        agent_tools=AgentToolCache(
            db_session=db_session,
            user=user,
            emitter=emitter,
            chat_files=chat_files,
            sandbox_session_id=sandbox_session_id,
        ),
        is_connected=is_connected,
        chat_files=chat_files,
        sandbox_session_id=sandbox_session_id,
    )

    try:
        status = yield from run_block(graph.top_level(), ctx)
        if status == StepStatus.PAUSED:
            # The pausing runner saved the checkpoint and emitted the questions.
            yield _overall_stop(ctx)
            return
        yield from _emit_final_summary(ctx)
        _finish(ctx)
    except Exception as e:
        logger.exception("[Sequential] Workflow execution failed")
        ctx.persist_progress(status="failed", error_message=str(e))
        try:
            trace.finalize("failed", state.total_tokens, state.elapsed_ms())
            ctx.persist_trace(include_message_key=True)
        except Exception:
            logger.debug("[Trace] sequential failed persist failed", exc_info=True)
        raise

    yield _overall_stop(ctx)


# ── Run lifecycle ─────────────────────────────────────────────────────────


def _start_or_resume(
    registry: NodeTypeRegistry,
    workflow: AgentWorkflow,
    user_message: str,
    db_session: Session,
    user: User,
    chat_session_id: UUID | None,
    paused_execution: WorkflowExecution | None,
) -> tuple[WorkflowExecution, RunState, WorkflowGraph]:
    """Resume ``paused_execution`` if possible, otherwise start a fresh run.

    A resumed run continues with the definition it was pinned to; a fresh run
    pins the workflow's current definition.
    """
    fresh_input = user_message
    if paused_execution is not None:
        graph = graph_for_execution(db_session, paused_execution, workflow, registry)
        checkpoint = load_checkpoint(paused_execution)
        if checkpoint is None:
            _abandon(db_session, paused_execution, "Checkpoint data corrupted")
            logger.warning(
                "[Sequential] Checkpoint corrupted for execution_id=%d, "
                "starting fresh",
                paused_execution.id,
            )
        else:
            try:
                state = restore_run_state(
                    checkpoint, graph, user_message,
                    paused_execution.paused_at_step_id,
                )
            except ResumeIncompatibleError as e:
                _abandon(db_session, paused_execution, str(e))
                # Keep what the user already said: the original request and
                # their answers become the new run's input.
                fresh_input, _ = everything_user_said(checkpoint, user_message)
                logger.warning(
                    "[Sequential] Cannot resume execution_id=%d (%s), "
                    "starting fresh",
                    paused_execution.id, e,
                )
            else:
                paused_execution.status = "running"
                paused_execution.paused_at_step_id = None
                db_session.commit()
                state.steps_executed = list(paused_execution.steps_executed or [])
                logger.info(
                    "[Sequential] Resumed execution_id=%d, completed=%s, "
                    "step_outputs_keys=%s direct_resume=%s",
                    paused_execution.id,
                    sorted(state.completed_keys),
                    list(state.context.step_outputs),
                    bool(state.resume and state.resume.task_override),
                )
                return paused_execution, state, graph

    # A save may have landed since this object was read; it can't while this holds.
    workflow = get_workflow_for_update(db_session, workflow.id) or workflow
    graph = graph_from_workflow(workflow, registry)
    version = pin_workflow_version(db_session, workflow, graph, user.id)
    execution = create_workflow_execution(
        db_session, workflow.id, user.id, chat_session_id,
        workflow_version_id=version.id,
    )
    return execution, RunState(context=WorkflowContext(user_input=fresh_input)), graph


def _abandon(db_session: Session, execution: WorkflowExecution, reason: str) -> None:
    """Mark a paused run that cannot be resumed as failed."""
    execution.status = "failed"
    execution.error_message = reason
    execution.completed_at = datetime.datetime.now(datetime.timezone.utc)
    db_session.commit()


def _init_trace(
    execution: WorkflowExecution,
    workflow: AgentWorkflow,
    chat_session_id: UUID | None,
    assistant_message_id: int | None,
    user_message: str,
    chat_files: list[ChatFile] | None,
    *,
    resumed: bool,
) -> WorkflowTraceBuilder:
    """Trace graph builder (best-effort; never breaks a run)."""
    trace = WorkflowTraceBuilder(
        execution.id,
        workflow.id,
        workflow.name,
        str(chat_session_id) if chat_session_id else None,
        mode="sequential",
        message_id=assistant_message_id,
    )
    try:
        if resumed:
            prior = load_workflow_trace(execution.id)
            if prior:
                trace.restore(prior)
        else:
            trace.set_start(user_message, [f.filename for f in (chat_files or [])])
    except Exception:
        logger.debug("[Trace] sequential init failed", exc_info=True)
    return trace


def _emit_final_summary(ctx: RunContext) -> Generator[Packet, None, None]:
    """Show the final answer (and deliverable files) as the main message."""
    state = ctx.state
    outputs = state.context.step_outputs
    if state.cancelled or not outputs:
        return

    any_promoted = any(
        node.promote_output for node in ctx.graph.nodes if node.output_key in outputs
    )
    # De-duplicated by filename (last writer wins), in completion order.
    file_ids, file_names = collect_workflow_files(
        _in_completion_order(state.context.shared_data.get("step_files", {}), state)
    )

    if not any_promoted:
        content = _final_answer(ctx) or ""
    elif file_ids:
        # A step promoted its output; still show the files' download links.
        content = ""
    else:
        return

    placement = Placement(turn_index=state.turn.value)
    yield Packet(placement=placement, obj=AgentResponseStart())
    yield Packet(
        placement=placement,
        obj=AgentResponseDelta(
            content=content,
            file_ids=file_ids or None,
            file_names=file_names or None,
        ),
    )
    yield Packet(placement=placement, obj=SectionEnd())
    state.turn.advance()


def _final_answer(ctx: RunContext) -> str | None:
    """The last output, shown the way its node type presents a final answer."""
    state = ctx.state
    output = state.last_output()
    if output is None or not state.output_order:
        return output
    last_key = state.output_order[-1]
    producer = next(
        (n for n in reversed(ctx.graph.nodes) if n.output_key == last_key), None
    )
    if producer is None:
        return output
    spec = ctx.registry.get(producer.node_type, producer.type_version)
    return spec.present_output(output) if spec.present_output else output


def _in_completion_order(step_files: dict[str, Any], state: RunState) -> dict[str, Any]:
    """Order step files like their outputs completed (JSONB loses dict order)."""
    rank = {key: i for i, key in enumerate(state.output_order)}
    ordered = sorted(step_files, key=lambda key: rank.get(key, -1))
    return {key: step_files[key] for key in ordered}


def _finish(ctx: RunContext) -> None:
    """Record the final status, then complete the trace graph."""
    state = ctx.state
    if state.cancelled:
        status, error = "cancelled", None
    elif state.timed_out:
        status = "timeout"
        error = f"Workflow timed out after {ctx.graph.timeout_seconds}s"
    else:
        status, error = "completed", None

    logger.info(
        "[Sequential] COMPLETE execution_id=%d status=%s "
        "steps_ran=%d total_tokens=%d total_time=%dms per_step_times=[%s]",
        ctx.execution.id,
        status,
        len(state.steps_executed),
        state.total_tokens,
        state.elapsed_ms(),
        ", ".join(
            f"{s['step_name']}={s['duration_ms']}ms" for s in state.steps_executed
        ),
    )
    ctx.persist_progress(status=status, error_message=error)

    try:
        final_answer = _final_answer(ctx)
        if not state.cancelled and final_answer is not None:
            ctx.trace.add_finish(final_answer)
        ctx.trace.finalize(status, state.total_tokens, state.elapsed_ms())
        ctx.persist_trace(include_message_key=True)
    except Exception:
        logger.debug("[Trace] sequential complete persist failed", exc_info=True)


def _overall_stop(ctx: RunContext) -> Packet:
    return Packet(
        placement=Placement(turn_index=ctx.state.turn.value),
        obj=OverallStop(
            type="stop",
            stop_reason="user_cancelled" if ctx.state.cancelled else None,
        ),
    )
