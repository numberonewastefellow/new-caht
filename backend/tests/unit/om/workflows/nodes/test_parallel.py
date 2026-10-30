"""Unit tests for the ``parallel`` container: concurrency, join, merge, errors."""

import contextlib
import json
import threading
import time
from collections.abc import Generator
from collections.abc import Iterator
from typing import Any
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from pydantic import BaseModel

from om.server.query_and_chat.placement import Placement
from om.server.query_and_chat.streaming_models import Packet
from om.server.query_and_chat.streaming_models import WorkflowStepStart
from om.workflows.branches import BRANCH_TURN_STRIDE
from om.workflows.graph import WorkflowGraph
from om.workflows.graph import WorkflowNode
from om.workflows.models import WorkflowContext
from om.workflows.models import WorkflowStepCreate
from om.workflows.nodes.base import NodeCapabilities
from om.workflows.nodes.base import NodeTypeSpec
from om.workflows.nodes.base import SaveContext
from om.workflows.nodes.base import StepOutcome
from om.workflows.nodes.base import StepSaveError
from om.workflows.nodes.base import StepStatus
from om.workflows.nodes.base import StepSummary
from om.workflows.nodes.builtin import get_node_registry
from om.workflows.nodes.parallel import ParallelRunnerV1
from om.workflows.nodes.parallel import prepare_parallel_step_v1
from om.workflows.nodes.registry import NodeTypeRegistry
from om.workflows.state import RunContext
from om.workflows.state import RunState

# ── A scripted node type that runs inside branch threads ──────────────────


class _SleepConfig(BaseModel):
    seconds: float = 0.0
    value: str = ""
    fail: bool = False


_timeline: list[tuple[str, str, float]] = []
_timeline_lock = threading.Lock()


class _SleepRunner:
    def run(self, node: WorkflowNode, ctx: Any) -> Generator[Packet, None, StepOutcome]:
        config = _SleepConfig.model_validate(node.config)
        with _timeline_lock:
            _timeline.append((node.node_key, "start", time.monotonic()))
        yield Packet(
            placement=Placement(turn_index=ctx.state.turn.value),
            obj=WorkflowStepStart(step_name=node.name, step_order=node.step_order),
        )
        time.sleep(config.seconds)
        with _timeline_lock:
            _timeline.append((node.node_key, "end", time.monotonic()))
        if config.fail:
            return StepOutcome(status=StepStatus.FAILED, error=f"{node.name} broke")
        ctx.trace.start_step(step_id=None, name=node.name, node_type="sleep", input_text="")
        ctx.complete_node(node, config.value)
        ctx.state.steps_executed.append({"step_name": node.name})
        ctx.state.turn.advance()
        return StepOutcome(status=StepStatus.COMPLETED, output=config.value)


def _registry() -> NodeTypeRegistry:
    registry = NodeTypeRegistry()
    builtin = get_node_registry()
    registry.register(builtin.latest("parallel"))
    registry.register(
        NodeTypeSpec(
            node_type="sleep", version=1, label="Sleep", description="test",
            category="test", config_model=_SleepConfig, runner=_SleepRunner(),
            capabilities=NodeCapabilities(),
        )
    )
    return registry


@contextlib.contextmanager
def _fake_session() -> Iterator[MagicMock]:
    yield MagicMock()


@pytest.fixture(autouse=True)
def _no_db() -> Iterator[None]:
    _timeline.clear()
    with patch("om.workflows.branches.get_session_with_current_tenant", _fake_session):
        yield


def _sleep(key: str, order: int, branch: int, seconds: float, value: str, **kw: Any) -> WorkflowNode:
    return WorkflowNode(
        node_key=key, node_type="sleep", type_version=1, step_order=order, name=key,
        output_key=key, parent_key="par", branch_index=branch,
        config={"seconds": seconds, "value": value, **kw},
    )


def _setup(children: list[WorkflowNode], **config: Any) -> tuple[RunContext, WorkflowNode]:
    labels = sorted({c.branch_index for c in children if c.branch_index is not None})
    container = WorkflowNode(
        node_key="par", node_type="parallel", type_version=1, step_order=0,
        name="Fan out", output_key="fan",
        config={"branches": [{"label": f"B{i}"} for i in labels], **config},
    )
    ctx = RunContext(
        graph=WorkflowGraph(
            workflow_id=1, name="wf", orchestration_mode="sequential",
            nodes=[container, *children],
        ),
        registry=_registry(),
        state=RunState(context=WorkflowContext(user_input="go")),
        db_session=MagicMock(),
        user=MagicMock(id="u1"),
        emitter=MagicMock(),
        execution=MagicMock(id=1),
        trace=MagicMock(),
        agent_tools=MagicMock(),
    )
    ctx.save_checkpoint = MagicMock()  # type: ignore[method-assign]
    return ctx, container


def _drive(ctx: RunContext, container: WorkflowNode) -> tuple[list[Packet], StepOutcome, float]:
    started = time.monotonic()
    gen = ParallelRunnerV1().run(container, ctx)
    packets: list[Packet] = []
    while True:
        try:
            packets.append(next(gen))
        except StopIteration as stop:
            return packets, stop.value, time.monotonic() - started


class TestParallelRun:
    def test_branches_run_concurrently_and_merge_in_branch_order(self) -> None:
        ctx, container = _setup([
            _sleep("slow", 1, 0, 0.6, "first"),
            _sleep("mid", 2, 1, 0.3, "second"),
            _sleep("fast", 3, 2, 0.05, "third"),
        ])
        _, outcome, elapsed = _drive(ctx, container)

        assert outcome.status == StepStatus.COMPLETED
        assert elapsed < 1.0  # 0.6 + 0.3 + 0.05 if it were sequential
        # Merge order is the declared branch order, not completion order
        assert ctx.state.output_order[:3] == ["slow", "mid", "fast"]
        assert json.loads(outcome.output or "") == {"B0": "first", "B1": "second", "B2": "third"}
        assert ctx.state.context.step_outputs["fan"] == outcome.output
        assert {"slow", "mid", "fast", "par"} <= ctx.state.completed_keys
        assert [s["step_name"] for s in ctx.state.steps_executed][:3] == ["slow", "mid", "fast"]
        ctx.save_checkpoint.assert_called_once()  # type: ignore[attr-defined]

    def test_concurrency_limit(self) -> None:
        ctx, container = _setup(
            [_sleep("a", 1, 0, 0.2, "a"), _sleep("b", 2, 1, 0.2, "b"), _sleep("c", 3, 2, 0.2, "c")],
            max_concurrency=1,
        )
        _, _, elapsed = _drive(ctx, container)
        assert elapsed >= 0.6
        # never two running at once
        running = 0
        for _key, kind, _t in sorted(_timeline, key=lambda e: e[2]):
            running += 1 if kind == "start" else -1
            assert running <= 1

    def test_steps_in_a_branch_run_in_order(self) -> None:
        ctx, container = _setup([
            _sleep("a1", 1, 0, 0.05, "x"),
            _sleep("a2", 2, 0, 0.05, "y"),
            _sleep("b1", 3, 1, 0.01, "z"),
        ])
        _, outcome, _ = _drive(ctx, container)
        a_events = [(k, kind) for k, kind, _ in _timeline if k.startswith("a")]
        assert a_events == [("a1", "start"), ("a1", "end"), ("a2", "start"), ("a2", "end")]
        assert json.loads(outcome.output or "") == {"B0": "y", "B1": "z"}

    def test_each_branch_uses_its_own_turn_range(self) -> None:
        ctx, container = _setup([_sleep("a", 1, 0, 0.01, "a"), _sleep("b", 2, 1, 0.01, "b")])
        packets, _, _ = _drive(ctx, container)
        branch_turns = sorted(
            p.placement.turn_index for p in packets
            if p.obj.type == "workflow_step_start" and p.obj.step_type == "agent"  # type: ignore[union-attr]
        )
        assert branch_turns == [1, 1 + BRANCH_TURN_STRIDE]
        assert ctx.state.turn.value > 1 + BRANCH_TURN_STRIDE

    def test_failure_fails_the_step_by_default(self) -> None:
        ctx, container = _setup([_sleep("ok", 1, 0, 0.01, "fine"), _sleep("bad", 2, 1, 0.01, "", fail=True)])
        _, outcome, _ = _drive(ctx, container)
        assert outcome.status == StepStatus.FAILED
        assert "bad broke" in (outcome.error or "")

    def test_failure_can_be_tolerated(self) -> None:
        ctx, container = _setup(
            [_sleep("ok", 1, 0, 0.01, "fine"), _sleep("bad", 2, 1, 0.01, "", fail=True)],
            on_branch_error="continue",
        )
        _, outcome, _ = _drive(ctx, container)
        assert outcome.status == StepStatus.COMPLETED
        combined = json.loads(outcome.output or "")
        assert combined["B0"] == "fine"
        assert "bad broke" in combined["B1"]["error"]

    def test_first_success_does_not_wait_for_slow_branches(self) -> None:
        ctx, container = _setup(
            [_sleep("fast", 1, 0, 0.05, "quick"), _sleep("slow", 2, 1, 1.5, "late")],
            join="first_success",
        )
        _, outcome, elapsed = _drive(ctx, container)
        assert elapsed < 1.0
        assert json.loads(outcome.output or "") == {"B0": "quick"}

    def test_stop_request_cancels(self) -> None:
        ctx, container = _setup([_sleep("a", 1, 0, 0.5, "a"), _sleep("b", 2, 1, 0.5, "b")])
        ctx.is_connected = lambda: False
        _, outcome, _ = _drive(ctx, container)
        assert outcome.status == StepStatus.CANCELLED

    def test_branch_trace_calls_are_replayed_on_the_run_trace(self) -> None:
        ctx, container = _setup([_sleep("a", 1, 0, 0.01, "a"), _sleep("b", 2, 1, 0.01, "b")])
        _drive(ctx, container)
        names = [c.kwargs.get("name") for c in ctx.trace.start_step.call_args_list]  # type: ignore[attr-defined]
        assert names == ["Fan out", "a", "b"]

    def test_branches_cannot_see_each_others_outputs(self) -> None:
        seen: dict[str, list[str]] = {}

        class _Peek(_SleepRunner):
            def run(self, node: WorkflowNode, ctx: Any) -> Generator[Packet, None, StepOutcome]:
                ctx.complete_node(node, node.node_key)
                # "a" writes early; "b" looks late, after "a" has written.
                time.sleep(0.05 if node.node_key == "a" else 0.2)
                seen[node.node_key] = sorted(ctx.state.context.step_outputs)
                return StepOutcome(status=StepStatus.COMPLETED, output=node.node_key)
                yield  # pragma: no cover

        ctx, container = _setup([_sleep("a", 1, 0, 0, "a"), _sleep("b", 2, 1, 0, "b")])
        ctx.registry = NodeTypeRegistry()
        ctx.registry.register(get_node_registry().latest("parallel"))
        ctx.registry.register(
            NodeTypeSpec(
                node_type="sleep", version=1, label="S", description="t", category="t",
                config_model=_SleepConfig, runner=_Peek(),
            )
        )
        _drive(ctx, container)
        assert seen == {"a": ["a"], "b": ["b"]}


def _summary(node_type: str, order: int, parent: str | None = None, branch: int | None = None) -> StepSummary:
    return StepSummary(node_type=node_type, step_order=order, parent_key=parent, branch_index=branch)


class TestPrepare:
    def _ctx(self, steps: dict[str, StepSummary]) -> SaveContext:
        return SaveContext(
            db_session=MagicMock(), orchestration_mode="sequential",
            step_order_to_node_key={s.step_order: k for k, s in steps.items()}, steps=steps,
        )

    def _step(self, key: str = "par", **config: Any) -> WorkflowStepCreate:
        return WorkflowStepCreate(
            node_key=key, step_type="parallel", step_order=0, step_name="Fan out",
            config=config or None,
        )

    def test_valid(self) -> None:
        ctx = self._ctx({
            "par": _summary("parallel", 0),
            "a": _summary("agent", 1, "par", 0),
            "b": _summary("agent", 2, "par", 1),
        })
        prepared = prepare_parallel_step_v1(self._step(), ctx)
        assert prepared.config is not None
        assert prepared.config["join"] == "wait_all"

    def test_empty_branch_rejected(self) -> None:
        ctx = self._ctx({"par": _summary("parallel", 0), "a": _summary("agent", 1, "par", 0)})
        with pytest.raises(StepSaveError, match="branches without steps: Branch 2"):
            prepare_parallel_step_v1(self._step(), ctx)

    def test_out_of_range_branch_rejected(self) -> None:
        ctx = self._ctx({
            "par": _summary("parallel", 0),
            "a": _summary("agent", 1, "par", 0),
            "b": _summary("agent", 2, "par", 1),
            "c": _summary("agent", 3, "par", 5),
        })
        with pytest.raises(StepSaveError, match=r"branches \[5\]"):
            prepare_parallel_step_v1(self._step(), ctx)

    def test_nested_parallel_rejected(self) -> None:
        ctx = self._ctx({
            "outer": _summary("parallel", 0),
            "par": _summary("parallel", 1, "outer", 0),
            "a": _summary("agent", 2, "par", 0),
            "b": _summary("agent", 3, "par", 1),
        })
        with pytest.raises(StepSaveError, match="inside another parallel"):
            prepare_parallel_step_v1(self._step(), ctx)

    def test_one_branch_rejected(self) -> None:
        ctx = self._ctx({"par": _summary("parallel", 0), "a": _summary("agent", 1, "par", 0)})
        with pytest.raises(StepSaveError, match="branches"):
            prepare_parallel_step_v1(self._step(branches=[{"label": "only"}]), ctx)
