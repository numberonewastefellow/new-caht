"""Unit tests for the ``loop`` container."""

import json
from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel

from om.server.query_and_chat.placement import Placement
from om.server.query_and_chat.streaming_models import Packet
from om.server.query_and_chat.streaming_models import WorkflowStepStart
from om.workflows.blocks import WorkflowNodeError
from om.workflows.graph import WorkflowGraph
from om.workflows.graph import WorkflowNode
from om.workflows.inputs import apply_input_mapping
from om.workflows.models import WorkflowContext
from om.workflows.models import WorkflowStepCreate
from om.workflows.nodes.base import NodeTypeSpec
from om.workflows.nodes.base import SaveContext
from om.workflows.nodes.base import StepOutcome
from om.workflows.nodes.base import StepSaveError
from om.workflows.nodes.base import StepStatus
from om.workflows.nodes.base import StepSummary
from om.workflows.nodes.builtin import get_node_registry
from om.workflows.nodes.loop import LoopRunnerV1
from om.workflows.nodes.loop import prepare_loop_step_v1
from om.workflows.nodes.registry import NodeTypeRegistry
from om.workflows.state import RunContext
from om.workflows.state import RunState


class _EchoConfig(BaseModel):
    fail_on: Any = None
    done_at: int | None = None


seen: list[dict[str, Any]] = []


class _EchoRunner:
    """Body step: records what it can see and returns 'item@index'."""

    def run(self, node: WorkflowNode, ctx: Any) -> Generator[Packet, None, StepOutcome]:
        config = _EchoConfig.model_validate(node.config)
        loop = ctx.state.variables["loop"]
        seen.append({
            "item": loop["item"], "index": loop["index"], "previous": loop["previous"],
            "outputs": sorted(k for k in ctx.state.context.step_outputs if not k.startswith("loop.")),
        })
        yield Packet(
            placement=Placement(turn_index=ctx.state.turn.value),
            obj=WorkflowStepStart(step_name=node.name, step_order=node.step_order),
        )
        if config.fail_on is not None and loop["item"] == config.fail_on:
            return StepOutcome(status=StepStatus.FAILED, error="bad item")
        value = "DONE" if config.done_at == loop["index"] else f"{loop['item']}@{loop['index']}"
        ctx.complete_node(node, value)
        ctx.state.steps_executed.append({"step_name": node.name})
        ctx.state.turn.advance()
        return StepOutcome(status=StepStatus.COMPLETED, output=value)


def _setup(loop_config: dict[str, Any], step_outputs: dict[str, str] | None = None,
           **body_config: Any) -> tuple[RunContext, WorkflowNode]:
    seen.clear()
    registry = NodeTypeRegistry()
    registry.register(get_node_registry().latest("loop"))
    registry.register(NodeTypeSpec(
        node_type="echo", version=1, label="Echo", description="t", category="t",
        config_model=_EchoConfig, runner=_EchoRunner(),
    ))
    loop = WorkflowNode(
        node_key="lp", node_type="loop", type_version=1, step_order=0, name="Each city",
        output_key="cities", config=loop_config,
    )
    body = WorkflowNode(
        node_key="echo", node_type="echo", type_version=1, step_order=1, name="Echo",
        output_key="echo", parent_key="lp", branch_index=0, config=body_config,
    )
    ctx = RunContext(
        graph=WorkflowGraph(workflow_id=1, name="wf", orchestration_mode="sequential", nodes=[loop, body]),
        registry=registry,
        state=RunState(context=WorkflowContext(user_input="go", step_outputs=step_outputs or {})),
        db_session=MagicMock(), user=MagicMock(), emitter=MagicMock(),
        execution=MagicMock(id=1), trace=MagicMock(), agent_tools=MagicMock(),
    )
    ctx.save_checkpoint = MagicMock()  # type: ignore[method-assign]
    return ctx, loop


def _drive(ctx: RunContext, node: WorkflowNode) -> tuple[list[Packet], StepOutcome]:
    gen = LoopRunnerV1().run(node, ctx)
    packets: list[Packet] = []
    while True:
        try:
            packets.append(next(gen))
        except StopIteration as stop:
            return packets, stop.value


CITIES = {"plan": json.dumps({"cities": ["Goa", "Pune", "Agra"]})}


class TestForEach:
    def test_runs_body_once_per_item(self) -> None:
        ctx, loop = _setup({"mode": "for_each", "items": "$plan.output.cities"}, CITIES)
        packets, outcome = _drive(ctx, loop)

        assert outcome.status == StepStatus.COMPLETED
        assert [s["item"] for s in seen] == ["Goa", "Pune", "Agra"]
        assert [s["index"] for s in seen] == [0, 1, 2]
        assert [s["previous"] for s in seen] == [None, "Goa@0", "Pune@1"]
        assert json.loads(outcome.output or "") == ["Goa@0", "Pune@1", "Agra@2"]
        # After the loop: the body's output is the last iteration's
        assert ctx.state.context.step_outputs["echo"] == "Agra@2"
        assert {"lp", "echo"} <= ctx.state.completed_keys
        markers = [p.obj.step_name for p in packets if p.obj.type == "workflow_step_start"  # type: ignore[union-attr]
                   and p.obj.step_type == "loop_iteration"]  # type: ignore[union-attr]
        assert markers == ["Each city · 1/3", "Each city · 2/3", "Each city · 3/3"]
        ctx.save_checkpoint.assert_called_once()  # type: ignore[attr-defined]

    def test_iterations_are_isolated(self) -> None:
        ctx, loop = _setup({"mode": "for_each", "items": "$plan.output.cities"}, CITIES)
        _drive(ctx, loop)
        # Each iteration sees the run's outputs, never another iteration's echo
        assert all(s["outputs"] == ["plan"] for s in seen)

    def test_items_from_lines_of_text(self) -> None:
        ctx, loop = _setup({"mode": "for_each", "items": "$notes"}, {"notes": "alpha\n\n beta \n"})
        _, outcome = _drive(ctx, loop)
        assert json.loads(outcome.output or "") == ["alpha@0", "beta@1"]

    def test_max_iterations_caps_the_list(self) -> None:
        ctx, loop = _setup({"mode": "for_each", "items": "$plan.output.cities", "max_iterations": 2}, CITIES)
        packets, outcome = _drive(ctx, loop)
        assert len(json.loads(outcome.output or "")) == 2
        header = next(p.obj.content for p in packets if p.obj.type == "workflow_step_delta")  # type: ignore[union-attr]
        assert "only the first 2 of 3" in header

    def test_collect_last(self) -> None:
        ctx, loop = _setup({"mode": "for_each", "items": "$plan.output.cities", "collect": "last"}, CITIES)
        _, outcome = _drive(ctx, loop)
        assert outcome.output == "Agra@2"

    def test_missing_items_reference_fails_the_step(self) -> None:
        ctx, loop = _setup({"mode": "for_each", "items": "$nothing.output.x"})
        _, outcome = _drive(ctx, loop)
        assert outcome.status == StepStatus.FAILED
        assert seen == []

    def test_body_failure_propagates(self) -> None:
        ctx, loop = _setup({"mode": "for_each", "items": "$plan.output.cities"}, CITIES, fail_on="Pune")
        with pytest.raises(WorkflowNodeError, match="bad item"):
            _drive(ctx, loop)

    def test_stop_request_cancels(self) -> None:
        ctx, loop = _setup({"mode": "for_each", "items": "$plan.output.cities"}, CITIES)
        ctx.is_connected = lambda: False
        _, outcome = _drive(ctx, loop)
        assert outcome.status == StepStatus.CANCELLED


class TestWhile:
    def test_condition_on_the_upcoming_index(self) -> None:
        ctx, loop = _setup({
            "mode": "while", "condition_field": "$loop.index",
            "operator": "less_than", "match_value": "3", "max_iterations": 10,
        })
        _, outcome = _drive(ctx, loop)
        assert [s["index"] for s in seen] == [0, 1, 2]
        assert [s["item"] for s in seen] == [None, None, None]  # while loops have no item
        assert json.loads(outcome.output or "") == ["None@0", "None@1", "None@2"]

    def test_condition_on_the_previous_result(self) -> None:
        ctx, loop = _setup(
            {"mode": "while", "condition_field": "$loop.previous", "operator": "not_contains",
             "match_value": "DONE", "max_iterations": 10},
            done_at=1,
        )
        _, outcome = _drive(ctx, loop)
        assert [s["index"] for s in seen] == [0, 1]  # iteration 1 said DONE

    def test_max_iterations_is_a_hard_cap(self) -> None:
        ctx, loop = _setup({
            "mode": "while", "condition_field": "$user_input", "operator": "is_not_empty",
            "max_iterations": 4,
        })
        _drive(ctx, loop)
        assert len(seen) == 4


def test_agent_mappings_can_use_loop_variables() -> None:
    context = WorkflowContext(user_input="go", step_outputs={"loop.item": "Goa", "loop.index": "0"})
    text = apply_input_mapping({"task": "Plan a day in $loop.item (#$loop.index)"}, context)
    assert text == "task: Plan a day in Goa (#0)"


class TestPrepare:
    def _ctx(self, steps: dict[str, StepSummary]) -> SaveContext:
        return SaveContext(
            db_session=MagicMock(), orchestration_mode="sequential",
            step_order_to_node_key={s.step_order: k for k, s in steps.items()}, steps=steps,
        )

    def _step(self, **config: Any) -> WorkflowStepCreate:
        return WorkflowStepCreate(
            node_key="lp", step_type="loop", step_order=0, step_name="Each", config=config,
        )

    def test_valid(self) -> None:
        ctx = self._ctx({"lp": StepSummary("loop", 0), "a": StepSummary("agent", 1, "lp", 0)})
        prepared = prepare_loop_step_v1(self._step(items="$x.output.list"), ctx)
        assert prepared.config is not None and prepared.config["max_iterations"] == 5

    @pytest.mark.parametrize(
        ("config", "steps", "message"),
        [
            ({"items": ""}, {"a": StepSummary("agent", 1, "lp", 0)}, "need 'items'"),
            ({"mode": "while"}, {"a": StepSummary("agent", 1, "lp", 0)}, "need a condition"),
            ({"items": "$x", "max_iterations": 99}, {"a": StepSummary("agent", 1, "lp", 0)}, "less than or equal"),
            ({"items": "$x"}, {}, "no steps to repeat"),
            ({"items": "$x"}, {"a": StepSummary("agent", 1, "lp", 1)}, "branch 0"),
            (
                {"mode": "while", "condition_field": "$a", "operator": "nonsense"},
                {"a": StepSummary("agent", 1, "lp", 0)},
                "unknown operator",
            ),
        ],
    )
    def test_rejects(self, config: dict[str, Any], steps: dict[str, StepSummary], message: str) -> None:
        ctx = self._ctx({"lp": StepSummary("loop", 0), **steps})
        with pytest.raises(StepSaveError, match=message):
            prepare_loop_step_v1(self._step(**config), ctx)
