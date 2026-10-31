"""Per-run state of the sequential workflow coordinator.

``RunState`` is the mutable state of one workflow run (outputs, completed and
skipped nodes, placement cursor, accounting). ``RunContext`` bundles it with the
read-only inputs every node runner needs (graph, DB session, user, emitter...).

Checkpoints are written only from here (``RunContext.save_checkpoint``) so the
on-disk format has a single owner. See ``WorkflowCheckpoint`` for the versions.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import TYPE_CHECKING

from om.db.models import AgentWorkflowStep
from om.db.workflow import save_checkpoint as db_save_checkpoint
from om.db.workflow import update_workflow_execution
from om.workflows.graph import WorkflowGraph
from om.workflows.graph import WorkflowNode
from om.workflows.hitl import build_clarification_task
from om.workflows.inputs import resolve_reference
from om.workflows.models import WorkflowCheckpoint
from om.workflows.models import WorkflowContext
from om.workflows.trace_models import persist_workflow_trace

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from om.chat.emitter import Emitter
    from om.db.models import User
    from om.db.models import WorkflowExecution
    from om.tools.models import ChatFile
    from om.workflows.nodes.agent_tools import AgentToolCache
    from om.workflows.nodes.registry import NodeTypeRegistry
    from om.workflows.trace_models import WorkflowTraceBuilder

CHECKPOINT_VERSION = 2

# Key under which the first user message is kept in shared_data, so resumed
# runs still know the original request.
ORIGINAL_USER_INPUT_KEY = "_original_user_input"


class TurnCursor:
    """The next free ``Placement.turn_index`` for packets emitted by the run.

    Sub-agents emit their own packets with higher turn indices; ``observe`` moves
    the cursor past them so the next node never collides with them.
    """

    def __init__(self, start: int = 0) -> None:
        self.value = start

    def observe(self, highest_seen: int) -> None:
        self.value = max(self.value, highest_seen)

    def advance(self, steps: int = 1) -> int:
        self.value += steps
        return self.value


@dataclass
class ResumePoint:
    """How to continue a run that paused for human input.

    Attributes:
        node_key: The node that paused; it runs again with ``task_override``.
        task_override: Conversation-aware task for that node (None for legacy
            checkpoints without a clarification conversation).
        conversation: Accumulated agent/user clarification dialog, including
            the user's latest reply.
        original_task: The task the paused node was first given.
    """

    node_key: str | None
    task_override: str | None = None
    conversation: list[dict[str, str]] | None = None
    original_task: str = ""


@dataclass
class RunState:
    """Mutable state of one workflow run."""

    context: WorkflowContext
    turn: TurnCursor = field(default_factory=TurnCursor)
    completed_keys: set[str] = field(default_factory=set)
    skipped_keys: set[str] = field(default_factory=set)
    # Output keys in completion order (see WorkflowCheckpoint.output_order).
    output_order: list[str] = field(default_factory=list)
    steps_executed: list[dict[str, Any]] = field(default_factory=list)
    total_tokens: int = 0
    started_at: float = field(default_factory=time.monotonic)
    cancelled: bool = False
    timed_out: bool = False
    resume: ResumePoint | None = None
    # Named values available to $references besides step outputs (e.g. the
    # "loop" variables inside a loop body).
    variables: dict[str, Any] = field(default_factory=dict)

    def record_output(self, output_key: str, output: str) -> None:
        """Store a node's output and mark it as the most recent one."""
        self.context.step_outputs[output_key] = output
        if output_key in self.output_order:
            self.output_order.remove(output_key)
        self.output_order.append(output_key)

    def last_output(self) -> str | None:
        """The most recently recorded output, or None when nothing ran."""
        for key in reversed(self.output_order):
            if key in self.context.step_outputs:
                return self.context.step_outputs[key]
        # Outputs restored from a legacy checkpoint carry no order information.
        if self.context.step_outputs:
            return list(self.context.step_outputs.values())[-1]
        return None

    def elapsed_seconds(self) -> float:
        return time.monotonic() - self.started_at

    def elapsed_ms(self) -> int:
        return int(self.elapsed_seconds() * 1000)


class ResumeIncompatibleError(Exception):
    """The checkpoint references steps that no longer exist in the workflow.

    Raised for legacy (v1) checkpoints of runs paused before workflow versions
    existed, when the workflow was edited while the run was paused. The caller
    fails the old run and starts a fresh one instead of resuming wrong steps.
    """


def restore_run_state(
    checkpoint: WorkflowCheckpoint,
    graph: WorkflowGraph,
    user_message: str,
    paused_at_step_id: int | None,
) -> RunState:
    """Rebuild the run state of a paused run, with the user's reply applied.

    Raises:
        ResumeIncompatibleError: A v1 checkpoint does not match ``graph``.
    """
    shared_data = checkpoint.shared_data
    original_input = shared_data.get(ORIGINAL_USER_INPUT_KEY, user_message)

    if checkpoint.clarification_conversation and checkpoint.paused_agent_original_task:
        # Conversation-aware resume: the paused node re-runs with the dialog.
        conversation = [
            *checkpoint.clarification_conversation,
            {"role": "user", "content": user_message},
        ]
        context = WorkflowContext(
            user_input=original_input,
            step_outputs=checkpoint.step_outputs,
            shared_data=shared_data,
        )
        task_override: str | None = build_clarification_task(
            checkpoint.paused_agent_original_task, conversation
        )
    else:
        # Older checkpoints without a conversation: everything the user said
        # becomes the new user input.
        user_input, clarifications = everything_user_said(checkpoint, user_message)
        context = WorkflowContext(
            user_input=user_input,
            step_outputs=checkpoint.step_outputs,
            shared_data={**shared_data, "_clarifications": clarifications},
        )
        conversation = None
        task_override = None

    if checkpoint.checkpoint_version >= 2:
        completed = set(checkpoint.completed_node_keys)
        unknown = sorted(k for k in completed if not graph.has_node(k))
        if unknown:
            # Only possible when the run is not pinned to the definition it
            # started on; never resume against a different set of nodes.
            raise ResumeIncompatibleError(
                f"The workflow changed since this run paused (nodes {unknown} "
                f"no longer exist)"
            )
        skipped = set(checkpoint.skipped_node_keys)
        output_order = list(checkpoint.output_order)
        paused_key = checkpoint.paused_node_key
    else:
        completed = _node_keys_for_step_ids(graph, checkpoint.completed_step_ids)
        skipped = set()
        output_order = []
        paused_node = (
            graph.node_for_step_id(paused_at_step_id)
            if paused_at_step_id is not None
            else None
        )
        paused_key = paused_node.node_key if paused_node else None

    return RunState(
        context=context,
        turn=TurnCursor(checkpoint.turn_index),
        completed_keys=completed,
        skipped_keys=skipped,
        output_order=output_order,
        resume=ResumePoint(
            node_key=paused_key,
            task_override=task_override,
            conversation=conversation,
            original_task=checkpoint.paused_agent_original_task,
        ),
    )


def everything_user_said(
    checkpoint: WorkflowCheckpoint, user_message: str
) -> tuple[str, list[str]]:
    """The original request plus every clarification, as one user input.

    Returns ``(user_input, clarifications)`` where ``clarifications`` includes
    ``user_message``. Used to resume legacy checkpoints without a conversation,
    and to restart a run that can no longer be resumed without losing what the
    user already said.
    """
    shared_data = checkpoint.shared_data
    original_input = shared_data.get(ORIGINAL_USER_INPUT_KEY, user_message)
    clarifications = [*shared_data.get("_clarifications", []), user_message]
    said = "\n".join(f"- {text}" for text in [original_input, *clarifications])
    return f"Everything the user has said:\n{said}", clarifications


def _node_keys_for_step_ids(graph: WorkflowGraph, step_ids: list[int]) -> set[str]:
    keys: set[str] = set()
    missing: list[int] = []
    for step_id in step_ids:
        node = graph.node_for_step_id(step_id)
        if node is None:
            missing.append(step_id)
        else:
            keys.add(node.node_key)
    if missing:
        raise ResumeIncompatibleError(
            f"The workflow changed since this run paused (steps {missing} no "
            f"longer exist)"
        )
    return keys


@dataclass
class RunContext:
    """Everything a node runner needs for one workflow run."""

    graph: WorkflowGraph
    registry: NodeTypeRegistry
    state: RunState
    db_session: Session
    user: User
    emitter: Emitter
    execution: WorkflowExecution
    trace: WorkflowTraceBuilder
    agent_tools: AgentToolCache
    is_connected: Callable[[], bool] | None = None
    chat_files: list[ChatFile] | None = None
    sandbox_session_id: str | None = None

    @property
    def trace_file_names(self) -> list[str]:
        return [f.filename for f in (self.chat_files or [])]

    def stop_requested(self) -> bool:
        return self.is_connected is not None and not self.is_connected()

    def reference_variables(self) -> dict[str, Any]:
        """What references can read besides step outputs.

        Loop variables, and every step that has no output: a router skipped it, its
        branch lost or failed, or its loop never ran. Reading such a step gives empty
        text. The save check has already refused references to steps not yet run.
        """
        outputs = self.state.context.step_outputs
        no_output = {
            node.output_key: "" for node in self.graph.nodes if node.output_key not in outputs
        }
        return {**no_output, **self.state.variables}

    def read_reference(self, value: str, extra: dict[str, Any] | None = None) -> Any:
        """The value of a literal or ``$reference`` in this step's scope."""
        return resolve_reference(
            value, self.state.context, {**self.reference_variables(), **(extra or {})}
        )

    def complete_node(
        self,
        node: WorkflowNode,
        output: str,
        *,
        skip_node_keys: set[str] | frozenset[str] = frozenset(),
    ) -> None:
        """Record a node's output and completion, then checkpoint.

        Branch skips from routers are applied in the same checkpoint, so a run
        resumed after this point keeps the losing branch skipped.
        """
        self.state.record_output(node.output_key, output)
        self.state.completed_keys.add(node.node_key)
        self.state.skipped_keys.update(skip_node_keys)
        self.save_checkpoint()

    def persist_trace(self, include_message_key: bool = False) -> None:
        """Persist the trace graph (callers wrap this in best-effort handling)."""
        persist_workflow_trace(self.trace.trace, include_message_key=include_message_key)

    def persist_progress(
        self, *, status: str | None = None, error_message: str | None = None
    ) -> None:
        """Write the run's accounting (and optionally its final status) to the DB."""
        fields: dict[str, Any] = {
            "steps_executed": self.state.steps_executed,
            "total_tokens": self.state.total_tokens,
            "total_duration_ms": self.state.elapsed_ms(),
        }
        if status is not None:
            fields["status"] = status
        if error_message is not None:
            fields["error_message"] = error_message
        update_workflow_execution(self.db_session, self.execution.id, **fields)

    def save_checkpoint(
        self,
        *,
        paused_node: WorkflowNode | None = None,
        paused_agent_original_task: str = "",
        clarification_conversation: list[dict[str, str]] | None = None,
    ) -> None:
        """Persist the run state (after a node completes, or when pausing)."""
        state = self.state
        checkpoint = WorkflowCheckpoint(
            checkpoint_version=CHECKPOINT_VERSION,
            step_outputs=dict(state.context.step_outputs),
            shared_data={
                **state.context.shared_data,
                ORIGINAL_USER_INPUT_KEY: state.context.shared_data.get(
                    ORIGINAL_USER_INPUT_KEY, state.context.user_input
                ),
            },
            # Written for servers that only understand version 1 checkpoints.
            completed_step_ids=[
                node.step_id
                for node in self.graph.nodes
                if node.node_key in state.completed_keys and node.step_id is not None
            ],
            turn_index=state.turn.value,
            paused_agent_original_task=paused_agent_original_task,
            clarification_conversation=clarification_conversation or [],
            completed_node_keys=sorted(state.completed_keys),
            skipped_node_keys=sorted(state.skipped_keys),
            output_order=list(state.output_order),
            paused_node_key=paused_node.node_key if paused_node else None,
        )
        db_save_checkpoint(
            self.db_session,
            self.execution.id,
            checkpoint,
            paused_at_step_id=self._existing_step_id(paused_node),
            paused=paused_node is not None,
        )

    def _existing_step_id(self, node: WorkflowNode | None) -> int | None:
        """The node's step row id, if that row still exists.

        A run pinned to an older definition may reference a step that was
        deleted since; the FK then has to stay NULL.
        """
        if node is None or node.step_id is None:
            return None
        exists = self.db_session.get(AgentWorkflowStep, node.step_id) is not None
        return node.step_id if exists else None
