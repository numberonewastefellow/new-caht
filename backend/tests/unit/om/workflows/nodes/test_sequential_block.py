"""Unit tests for the coordinator's block loop (dispatch via the registry)."""

from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel

from om.server.query_and_chat.streaming_models import Packet
from om.workflows.graph import WorkflowGraph
from om.workflows.graph import WorkflowNode
from om.workflows.models import WorkflowContext
from om.workflows.nodes.base import NodeTypeSpec
from om.workflows.nodes.base import StepOutcome
from om.workflows.nodes.base import StepStatus
from om.workflows.nodes.registry import NodeTypeRegistry
from om.workflows.blocks import run_block
from om.workflows.blocks import WorkflowNodeError
from om.workflows.state import RunContext
from om.workflows.state import RunState


class _Empty(BaseModel):
    pass


class _ScriptedRunner:
    """Returns a scripted status per node key and records the call order."""

    def __init__(self, statuses: dict[str, StepStatus]) -> None:
        self.statuses = statuses
        self.calls: list[str] = []

    def run(self, node: WorkflowNode, ctx: Any) -> Generator[Packet, None, StepOutcome]:
        self.calls.append(node.node_key)
        status = self.statuses.get(node.node_key, StepStatus.COMPLETED)
        return StepOutcome(status=status, error="boom" if status == StepStatus.FAILED else None)
        yield  # pragma: no cover


def _setup(
    keys: list[str], statuses: dict[str, StepStatus] | None = None, timeout: int = 1800
) -> tuple[RunContext, _ScriptedRunner]:
    runner = _ScriptedRunner(statuses or {})
    registry = NodeTypeRegistry()
    registry.register(
        NodeTypeSpec(
            node_type="scripted",
            version=1,
            label="S",
            description="S",
            category="test",
            config_model=_Empty,
            runner=runner,
        )
    )
    nodes = [
        WorkflowNode(
            node_key=k, node_type="scripted", type_version=1, step_order=i, name=k
        )
        for i, k in enumerate(keys)
    ]
    ctx = RunContext(
        graph=WorkflowGraph(
            workflow_id=1,
            name="wf",
            orchestration_mode="sequential",
            timeout_seconds=timeout,
            nodes=nodes,
        ),
        registry=registry,
        state=RunState(context=WorkflowContext(user_input="x")),
        db_session=MagicMock(),
        user=MagicMock(),
        emitter=MagicMock(),
        execution=MagicMock(id=1),
        trace=MagicMock(),
        agent_tools=MagicMock(),
    )
    return ctx, runner


def _status(ctx: RunContext) -> StepStatus:
    gen = run_block(ctx.graph.nodes, ctx)
    while True:
        try:
            next(gen)
        except StopIteration as stop:
            return stop.value


def test_runs_every_node_in_order() -> None:
    ctx, runner = _setup(["a", "b", "c"])
    assert _status(ctx) == StepStatus.COMPLETED
    assert runner.calls == ["a", "b", "c"]


def test_completed_and_skipped_nodes_are_not_run() -> None:
    ctx, runner = _setup(["a", "b", "c"])
    ctx.state.completed_keys = {"a"}
    ctx.state.skipped_keys = {"b"}
    _status(ctx)
    assert runner.calls == ["c"]


def test_skipped_outcome_continues() -> None:
    ctx, runner = _setup(["a", "b"], {"a": StepStatus.SKIPPED})
    assert _status(ctx) == StepStatus.COMPLETED
    assert runner.calls == ["a", "b"]


def test_terminal_stops_the_block() -> None:
    ctx, runner = _setup(["a", "b"], {"a": StepStatus.TERMINAL})
    assert _status(ctx) == StepStatus.COMPLETED
    assert runner.calls == ["a"]


def test_pause_stops_the_block() -> None:
    ctx, runner = _setup(["a", "b"], {"a": StepStatus.PAUSED})
    assert _status(ctx) == StepStatus.PAUSED
    assert runner.calls == ["a"]


def test_cancel_from_runner_marks_state() -> None:
    ctx, runner = _setup(["a", "b"], {"a": StepStatus.CANCELLED})
    assert _status(ctx) == StepStatus.CANCELLED
    assert ctx.state.cancelled is True
    assert runner.calls == ["a"]


def test_stop_request_before_a_node() -> None:
    ctx, runner = _setup(["a", "b"])
    ctx.is_connected = lambda: False
    assert _status(ctx) == StepStatus.CANCELLED
    assert runner.calls == []


def test_timeout_stops_and_is_flagged() -> None:
    ctx, runner = _setup(["a", "b"], timeout=0)
    ctx.state.started_at -= 5  # 5 seconds already elapsed
    assert _status(ctx) == StepStatus.COMPLETED
    assert ctx.state.timed_out is True
    assert runner.calls == ["a"]


def test_failed_outcome_raises() -> None:
    ctx, _ = _setup(["a"], {"a": StepStatus.FAILED})
    with pytest.raises(WorkflowNodeError, match="boom"):
        _status(ctx)
