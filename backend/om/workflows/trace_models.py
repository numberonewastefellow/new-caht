"""
Workflow execution TRACE GRAPH — models, incremental builder, and persistence.

Captures a multi-agent workflow run as an explainable graph:
  - nodes  = the user input (start), each orchestrator decision, each agent
             invocation, and the final answer (finish)
  - edges  = handoffs (delegation orchestrator->agent, return agent->orchestrator)

Each node carries full input / output / why / timing / tokens / files so the UI
can show exactly what every agent received and produced.

The assembled trace is serialized to JSON and stored in the blob store (MinIO)
under a DETERMINISTIC file id ``wftrace_{execution_id}`` (re-saved on each
update, no orphans), identified by ``FileOrigin.WORKFLOW_TRACE`` + metadata.
No DB migration is needed.

All persistence is best-effort: tracing must NEVER break a workflow run, so
callers should wrap builder/persist calls defensively (this module also guards
its own IO).
"""

from __future__ import annotations

import json
from datetime import datetime
from datetime import timezone
from io import BytesIO
from typing import Literal

from pydantic import BaseModel
from pydantic import Field

from om.configs.constants import FileOrigin
from om.file_store.file_store import get_default_file_store
from om.utils.logger import setup_logger

logger = setup_logger()

NodeType = Literal["start", "orchestrator", "agent", "pause", "finish", "router"]
EdgeType = Literal["delegation", "return", "sequence"]
NodeStatus = Literal["running", "completed", "paused", "failed"]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _edge_label(reason: str | None, limit: int = 120) -> str | None:
    """Short, single-line summary for an on-graph edge label.

    The full rationale is kept on the node (``reason`` / ``output``) for the
    inspector; this just keeps the canvas readable.
    """
    if not reason:
        return None
    first_line = reason.strip().splitlines()[0].strip()
    if len(first_line) <= limit:
        return first_line
    return first_line[: limit - 1].rstrip() + "…"


def _trace_file_id(execution_id: int) -> str:
    return f"wftrace_{execution_id}"


def _trace_msg_file_id(message_id: int) -> str:
    return f"wftrace_msg_{message_id}"


class TraceNode(BaseModel):
    id: str
    type: NodeType
    name: str
    status: NodeStatus = "completed"
    # The task/prompt this node received (full text), and what it produced.
    input: str = ""
    output: str = ""
    # Why this node was reached (orchestrator's routing rationale).
    reason: str | None = None
    step_id: int | None = None
    agent_id: int | None = None
    call_index: int | None = None  # e.g. 2 for the 2nd call to the same agent
    duration_ms: int | None = None
    tokens: int | None = None
    file_ids: list[str] = Field(default_factory=list)
    file_names: list[str] = Field(default_factory=list)
    started_at: str | None = None
    ended_at: str | None = None


class TraceEdge(BaseModel):
    from_id: str
    to_id: str
    type: EdgeType = "delegation"
    label: str | None = None  # short reason / handoff summary


class WorkflowTrace(BaseModel):
    execution_id: int
    workflow_id: int
    workflow_name: str
    chat_session_id: str | None = None
    message_id: int | None = None
    mode: str = "llm_decision"
    status: str = "running"
    started_at: str | None = None
    completed_at: str | None = None
    total_tokens: int = 0
    total_duration_ms: int = 0
    nodes: list[TraceNode] = Field(default_factory=list)
    edges: list[TraceEdge] = Field(default_factory=list)


class WorkflowTraceBuilder:
    """Accumulates trace nodes/edges as the engine runs.

    Every method is defensive (never raises) so a tracing bug can't break a
    workflow run.
    """

    def __init__(
        self,
        execution_id: int,
        workflow_id: int,
        workflow_name: str,
        chat_session_id: str | None,
        mode: str = "llm_decision",
        message_id: int | None = None,
    ) -> None:
        self.trace = WorkflowTrace(
            execution_id=execution_id,
            workflow_id=workflow_id,
            workflow_name=workflow_name,
            chat_session_id=chat_session_id,
            message_id=message_id,
            mode=mode,
            started_at=_now_iso(),
        )
        self._prev_id: str | None = None       # last node in the main flow
        self._last_orch_id: str | None = None   # most recent orchestrator node
        self._pending_reason: str | None = None  # orchestrator rationale for next delegation
        self._agent_count = 0
        self._orch_count = 0

    def restore(self, prior: "WorkflowTrace") -> None:
        """Continue an existing trace (used on HITL resume so earlier nodes
        aren't lost when the same execution_id is re-persisted)."""
        try:
            self.trace.nodes = list(prior.nodes)
            self.trace.edges = list(prior.edges)
            self.trace.started_at = prior.started_at or self.trace.started_at
            self._agent_count = sum(1 for n in prior.nodes if n.type == "agent")
            self._orch_count = sum(1 for n in prior.nodes if n.type == "orchestrator")
            self._prev_id = prior.nodes[-1].id if prior.nodes else None
            orch_ids = [n.id for n in prior.nodes if n.type == "orchestrator"]
            self._last_orch_id = orch_ids[-1] if orch_ids else None
            self.trace.status = "running"
        except Exception:
            logger.debug("[Trace] restore failed", exc_info=True)

    # -- construction -------------------------------------------------------

    def set_start(self, user_message: str, file_names: list[str] | None = None) -> None:
        try:
            node = TraceNode(
                id="start",
                type="start",
                name="Claim submitted" if file_names else "User request",
                input=user_message or "",
                file_names=file_names or [],
                started_at=_now_iso(),
            )
            self.trace.nodes.append(node)
            self._prev_id = "start"
        except Exception:
            logger.debug("[Trace] set_start failed", exc_info=True)

    def add_orchestrator(self, cycle: int, reason: str | None) -> None:
        try:
            self._orch_count += 1
            node_id = f"orch_{cycle}_{self._orch_count}"
            node = TraceNode(
                id=node_id,
                type="orchestrator",
                name="Orchestrator",
                output=reason or "",
                reason=reason,
                started_at=_now_iso(),
            )
            self.trace.nodes.append(node)
            if self._prev_id:
                self.trace.edges.append(
                    TraceEdge(from_id=self._prev_id, to_id=node_id, type="return")
                )
            self._last_orch_id = node_id
            self._prev_id = node_id
            self._pending_reason = reason
        except Exception:
            logger.debug("[Trace] add_orchestrator failed", exc_info=True)

    def add_agent(
        self,
        step_id: int | None,
        name: str,
        agent_id: int | None,
        input_text: str,
        output_text: str,
        status: NodeStatus = "completed",
        duration_ms: int | None = None,
        tokens: int | None = None,
        file_ids: list[str] | None = None,
        file_names: list[str] | None = None,
        call_index: int | None = None,
    ) -> str | None:
        try:
            self._agent_count += 1
            node_id = f"agent_{self._agent_count}"
            node = TraceNode(
                id=node_id,
                type="agent",
                name=name,
                status=status,
                input=input_text or "",
                output=output_text or "",
                reason=self._pending_reason,
                step_id=step_id,
                agent_id=agent_id,
                call_index=call_index,
                duration_ms=duration_ms,
                tokens=tokens,
                file_ids=file_ids or [],
                file_names=file_names or [],
                started_at=_now_iso(),
                ended_at=_now_iso(),
            )
            self.trace.nodes.append(node)
            src = self._last_orch_id or self._prev_id
            if src:
                self.trace.edges.append(
                    TraceEdge(
                        from_id=src,
                        to_id=node_id,
                        type="delegation",
                        label=_edge_label(self._pending_reason),
                    )
                )
            self._prev_id = node_id
            return node_id
        except Exception:
            logger.debug("[Trace] add_agent failed", exc_info=True)
            return None

    def start_agent(
        self,
        step_id: int | None,
        name: str,
        agent_id: int | None,
        input_text: str,
        file_names: list[str] | None = None,
        call_index: int | None = None,
    ) -> str | None:
        """Append an agent node in the ``running`` state and return its id.

        Pair with ``finish_agent`` once the agent completes / pauses so the
        live graph can show an in-progress node before its output exists.
        """
        try:
            self._agent_count += 1
            node_id = f"agent_{self._agent_count}"
            node = TraceNode(
                id=node_id,
                type="agent",
                name=name,
                status="running",
                input=input_text or "",
                output="",
                reason=self._pending_reason,
                step_id=step_id,
                agent_id=agent_id,
                call_index=call_index,
                file_names=file_names or [],
                started_at=_now_iso(),
            )
            self.trace.nodes.append(node)
            src = self._last_orch_id or self._prev_id
            if src:
                self.trace.edges.append(
                    TraceEdge(
                        from_id=src,
                        to_id=node_id,
                        type="delegation",
                        label=_edge_label(self._pending_reason),
                    )
                )
            self._prev_id = node_id
            return node_id
        except Exception:
            logger.debug("[Trace] start_agent failed", exc_info=True)
            return None

    def finish_agent(
        self,
        node_id: str | None,
        output_text: str,
        status: NodeStatus = "completed",
        duration_ms: int | None = None,
        tokens: int | None = None,
        file_ids: list[str] | None = None,
        file_names: list[str] | None = None,
    ) -> None:
        """Update a node previously created by ``start_agent``.

        Falls back to ``add_agent`` if the node can't be found (defensive)."""
        try:
            for node in self.trace.nodes:
                if node.id == node_id:
                    node.output = output_text or node.output
                    node.status = status
                    if duration_ms is not None:
                        node.duration_ms = duration_ms
                    if tokens is not None:
                        node.tokens = tokens
                    if file_ids:
                        node.file_ids = file_ids
                    if file_names:
                        node.file_names = file_names
                    node.ended_at = _now_iso()
                    return
            # Node not found — create it fresh so nothing is lost.
            self.add_agent(
                step_id=None,
                name="Agent",
                agent_id=None,
                input_text="",
                output_text=output_text,
                status=status,
                duration_ms=duration_ms,
                tokens=tokens,
                file_ids=file_ids,
                file_names=file_names,
            )
        except Exception:
            logger.debug("[Trace] finish_agent failed", exc_info=True)

    def add_router(
        self, name: str, explanation: str | None, branch_taken: str
    ) -> str | None:
        """Append a conditional-router decision node (sequential mode)."""
        try:
            node_id = f"router_{len(self.trace.nodes)}"
            node = TraceNode(
                id=node_id,
                type="router",
                name=name,
                status="completed",
                output=f"branch: {branch_taken}",
                reason=explanation,
                started_at=_now_iso(),
                ended_at=_now_iso(),
            )
            self.trace.nodes.append(node)
            if self._prev_id:
                self.trace.edges.append(
                    TraceEdge(
                        from_id=self._prev_id, to_id=node_id, type="sequence"
                    )
                )
            self._prev_id = node_id
            return node_id
        except Exception:
            logger.debug("[Trace] add_router failed", exc_info=True)
            return None

    def mark_paused(self, node_id: str | None, questions: str) -> None:
        try:
            for node in self.trace.nodes:
                if node.id == node_id:
                    node.status = "paused"
                    node.output = questions or node.output
                    break
            self.trace.status = "paused"
        except Exception:
            logger.debug("[Trace] mark_paused failed", exc_info=True)

    def add_finish(self, answer: str) -> None:
        try:
            node = TraceNode(
                id="finish",
                type="finish",
                name="Final answer",
                output=answer or "",
                started_at=_now_iso(),
            )
            self.trace.nodes.append(node)
            if self._prev_id:
                self.trace.edges.append(
                    TraceEdge(from_id=self._prev_id, to_id="finish", type="return")
                )
        except Exception:
            logger.debug("[Trace] add_finish failed", exc_info=True)

    def finalize(self, status: str, total_tokens: int, total_duration_ms: int) -> None:
        self.trace.status = status
        self.trace.completed_at = _now_iso()
        self.trace.total_tokens = total_tokens
        self.trace.total_duration_ms = total_duration_ms


# -- persistence ------------------------------------------------------------


def persist_workflow_trace(
    trace: WorkflowTrace, include_message_key: bool = False
) -> str | None:
    """Save the trace JSON to the blob store under deterministic id(s).

    Always writes the execution-keyed blob ``wftrace_{execution_id}`` (used for
    pause/resume continuity and crash resilience). When ``include_message_key``
    and a ``message_id`` is set, ALSO writes ``wftrace_msg_{message_id}`` so the
    UI can fetch the trace for a specific assistant message (a session may have
    multiple runs / a run may span multiple turns).

    Best-effort: returns the execution file id, or None on failure (never raises).
    """
    try:
        payload = json.dumps(trace.model_dump(), ensure_ascii=False).encode("utf-8")
        metadata = {
            "execution_id": trace.execution_id,
            "workflow_id": trace.workflow_id,
            "chat_session_id": trace.chat_session_id,
            "message_id": trace.message_id,
        }
        store = get_default_file_store()
        file_id = _trace_file_id(trace.execution_id)
        store.save_file(
            content=BytesIO(payload),
            display_name=f"workflow_trace_{trace.execution_id}.json",
            file_origin=FileOrigin.WORKFLOW_TRACE,
            file_type="application/json",
            file_metadata=metadata,
            file_id=file_id,
        )
        if include_message_key and trace.message_id is not None:
            store.save_file(
                content=BytesIO(payload),
                display_name=f"workflow_trace_msg_{trace.message_id}.json",
                file_origin=FileOrigin.WORKFLOW_TRACE,
                file_type="application/json",
                file_metadata=metadata,
                file_id=_trace_msg_file_id(trace.message_id),
            )
        logger.info(
            "[Trace] persisted execution_id=%d message_id=%s nodes=%d edges=%d "
            "file_id=%s msg_key=%s",
            trace.execution_id,
            trace.message_id,
            len(trace.nodes),
            len(trace.edges),
            file_id,
            include_message_key and trace.message_id is not None,
        )
        return file_id
    except Exception:
        logger.exception("[Trace] persist failed for execution_id=%s", trace.execution_id)
        return None


def load_workflow_trace(execution_id: int) -> WorkflowTrace | None:
    """Load a persisted trace by execution id; None if absent/unreadable."""
    return _load_trace(_trace_file_id(execution_id), f"execution_id={execution_id}")


def load_workflow_trace_by_message(message_id: int) -> WorkflowTrace | None:
    """Load a persisted trace by assistant message id; None if absent."""
    return _load_trace(_trace_msg_file_id(message_id), f"message_id={message_id}")


def _load_trace(file_id: str, label: str) -> WorkflowTrace | None:
    try:
        raw = get_default_file_store().read_file(file_id, mode="b")
        data = json.loads(raw.read())
        return WorkflowTrace.model_validate(data)
    except Exception:
        logger.debug("[Trace] no trace for %s", label, exc_info=True)
        return None
