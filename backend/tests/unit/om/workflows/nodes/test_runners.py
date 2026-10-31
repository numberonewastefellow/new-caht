"""Unit tests for the built-in node runners (agent, conditional_router)."""

import json
from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from om.server.query_and_chat.placement import Placement
from om.server.query_and_chat.streaming_models import Packet
from om.workflows.graph import WorkflowGraph
from om.workflows.graph import WorkflowNode
from om.workflows.models import WorkflowContext
from om.workflows.nodes.agent import AgentRunnerV1
from om.workflows.nodes.agent import UnusableStepAgentError
from om.workflows.nodes.base import StepOutcome
from om.workflows.nodes.base import StepStatus
from om.workflows.nodes.base import UpgradeContext
from om.workflows.nodes.builtin import get_node_registry
from om.workflows.nodes.router import RouterRunnerV1
from om.workflows.nodes.router import RouterRunnerV2
from om.workflows.nodes.router import upgrade_router_v1_to_v2
from om.workflows.state import ResumePoint
from om.workflows.state import RunContext
from om.workflows.state import RunState


def _node(key: str, order: int, node_type: str = "agent", **kwargs: Any) -> WorkflowNode:
    defaults: dict[str, Any] = {
        "node_key": key,
        "step_id": 100 + order,
        "node_type": node_type,
        "type_version": 1,
        "step_order": order,
        "name": f"Step {key}",
        "output_key": f"out_{key}",
        "config": {"agent_id": 7} if node_type == "agent" else {},
    }
    return WorkflowNode(**{**defaults, **kwargs})


def _ctx(nodes: list[WorkflowNode], state: RunState | None = None) -> RunContext:
    agent_tool = MagicMock()
    agent_tool._agent.name = "Writer"
    agent_tools = MagicMock()
    agent_tools.get.return_value = agent_tool
    ctx = RunContext(
        graph=WorkflowGraph(
            workflow_id=1, name="wf", orchestration_mode="sequential", nodes=nodes
        ),
        registry=get_node_registry(),
        state=state or RunState(context=WorkflowContext(user_input="hello")),
        db_session=MagicMock(),
        user=MagicMock(),
        emitter=MagicMock(),
        execution=MagicMock(id=5),
        trace=MagicMock(),
        agent_tools=agent_tools,
    )
    ctx.save_checkpoint = MagicMock()  # type: ignore[method-assign]
    ctx.persist_progress = MagicMock()  # type: ignore[method-assign]
    return ctx


def _drive(gen: Generator[Packet, None, StepOutcome]) -> tuple[list[Packet], StepOutcome]:
    packets: list[Packet] = []
    while True:
        try:
            packets.append(next(gen))
        except StopIteration as stop:
            return packets, stop.value


def _fake_stream(output: str, *, cancelled: bool = False, max_turn: int | None = None):
    """Replacement for stream_agent_packets that 'runs' the agent instantly."""

    def fake(agent_tool: Any, placement: Placement, emitter: Any, result: Any, **kw: Any):
        result.response = MagicMock(llm_facing_response=json.dumps({"agent_output": output}))
        result.cancelled = cancelled
        if max_turn is not None:
            result.max_turn_index = max_turn
        fake.task = kw.get("task")
        return iter(())

    return fake


def _types(packets: list[Packet]) -> list[tuple[str, int]]:
    return [(p.obj.type, p.placement.turn_index) for p in packets]


class TestAgentRunner:
    def test_completes_records_output_and_advances_cursor(self) -> None:
        node = _node("a", 0)
        ctx = _ctx([node])
        with patch("om.workflows.nodes.agent.stream_agent_packets", _fake_stream("Done!")):
            packets, outcome = _drive(AgentRunnerV1().run(node, ctx))

        assert outcome == StepOutcome(status=StepStatus.COMPLETED, output="Done!")
        assert [t for t, _ in _types(packets)] == [
            "workflow_step_start",
            "workflow_step_delta",
            "workflow_step_end",
            "section_end",
        ]
        assert ctx.state.context.step_outputs == {"out_a": "Done!"}
        assert ctx.state.completed_keys == {"a"}
        assert ctx.state.turn.value == 1
        ctx.save_checkpoint.assert_called_once_with()  # type: ignore[attr-defined]
        assert ctx.state.steps_executed[0]["agent_id"] == 7

    def test_sub_agent_turns_move_the_cursor(self) -> None:
        node = _node("a", 0)
        ctx = _ctx([node])
        with patch(
            "om.workflows.nodes.agent.stream_agent_packets",
            _fake_stream("x", max_turn=4),
        ):
            _drive(AgentRunnerV1().run(node, ctx))
        assert ctx.state.turn.value == 5

    def test_promoted_output_is_emitted_as_message(self) -> None:
        node = _node("a", 0, promote_output=True)
        ctx = _ctx([node])
        with patch("om.workflows.nodes.agent.stream_agent_packets", _fake_stream("Final")):
            packets, _ = _drive(AgentRunnerV1().run(node, ctx))
        assert _types(packets)[-3:] == [
            ("message_start", 1),
            ("message_delta", 1),
            ("section_end", 1),
        ]
        assert ctx.state.turn.value == 2

    def test_terminal_node_reports_terminal(self) -> None:
        node = _node("a", 0, is_terminal=True)
        ctx = _ctx([node])
        with patch("om.workflows.nodes.agent.stream_agent_packets", _fake_stream("x")):
            _, outcome = _drive(AgentRunnerV1().run(node, ctx))
        assert outcome.status == StepStatus.TERMINAL

    def test_unusable_agent_fails_the_step_without_packets(self) -> None:
        node = _node("a", 0)
        ctx = _ctx([node])
        ctx.agent_tools.get.side_effect = UnusableStepAgentError(  # type: ignore[attr-defined]
            "uses the default Assistant; choose a dedicated agent"
        )
        packets, outcome = _drive(AgentRunnerV1().run(node, ctx))
        assert packets == []
        assert outcome.status == StepStatus.FAILED
        assert outcome.error == (
            '"Step a" uses the default Assistant; choose a dedicated agent'
        )
        assert ctx.state.completed_keys == set()

    def test_a_bad_reference_fails_the_step_before_it_starts(self) -> None:
        node = _node("a", 0, input_mapping={"task": "$nope.output"})
        ctx = _ctx([node])
        ctx.graph = ctx.graph.model_copy(update={"schema_version": 2})
        packets, outcome = _drive(AgentRunnerV1().run(node, ctx))
        assert packets == []
        assert outcome.status == StepStatus.FAILED
        assert outcome.error is not None and "nope" in outcome.error

    def test_a_skipped_step_reads_as_empty_on_schema_2(self) -> None:
        skipped = _node("b", 0)
        node = _node("a", 1, input_mapping={"task": "[$out_b]"})
        ctx = _ctx([skipped, node])
        ctx.graph = ctx.graph.model_copy(update={"schema_version": 2})
        ctx.state.skipped_keys.add("b")
        assert AgentRunnerV1._task_input(node, ctx) == "task: []"

    def test_schema_1_keeps_legacy_substitution(self) -> None:
        node = _node("a", 0, input_mapping={"task": "[$nope]"})
        ctx = _ctx([node])
        assert AgentRunnerV1._task_input(node, ctx) == "task: [$nope]"

    def test_cancel_closes_the_step(self) -> None:
        node = _node("a", 0)
        ctx = _ctx([node])
        with patch(
            "om.workflows.nodes.agent.stream_agent_packets",
            _fake_stream("", cancelled=True, max_turn=2),
        ):
            packets, outcome = _drive(AgentRunnerV1().run(node, ctx))
        assert outcome.status == StepStatus.CANCELLED
        assert [t for t, _ in _types(packets)][-2:] == ["workflow_step_end", "section_end"]
        assert ctx.state.turn.value == 3
        assert ctx.state.completed_keys == set()

    def test_pause_asks_questions_and_checkpoints(self) -> None:
        node = _node("a", 0, can_request_input=True)
        ctx = _ctx([node])
        with patch(
            "om.workflows.nodes.agent.stream_agent_packets",
            _fake_stream("[NEEDS_INPUT] Which dates?"),
        ):
            packets, outcome = _drive(AgentRunnerV1().run(node, ctx))

        assert outcome.status == StepStatus.PAUSED
        assert _types(packets)[-7:] == [
            ("workflow_step_end", 0),
            ("section_end", 0),
            ("workflow_pause_for_input", 1),
            ("section_end", 1),
            ("message_start", 2),
            ("message_delta", 2),
            ("section_end", 2),
        ]
        assert packets[-2].obj.content == "Which dates?"  # type: ignore[union-attr]
        assert ctx.state.turn.value == 3  # coordinator emits the stop at turn 3
        kwargs = ctx.save_checkpoint.call_args.kwargs  # type: ignore[attr-defined]
        assert kwargs["paused_node"] == node
        assert kwargs["clarification_conversation"] == [
            {"role": "agent", "content": "Which dates?"}
        ]
        assert ctx.state.completed_keys == set()

    def test_resumed_node_uses_clarification_task(self) -> None:
        node = _node("a", 0)
        state = RunState(context=WorkflowContext(user_input="hello"))
        state.resume = ResumePoint(node_key="a", task_override="TASK + answers")
        ctx = _ctx([node], state)
        fake = _fake_stream("ok")
        with patch("om.workflows.nodes.agent.stream_agent_packets", fake):
            _drive(AgentRunnerV1().run(node, ctx))
        assert fake.task == "TASK + answers"  # type: ignore[attr-defined]


def _router(order: int, version: int, config: dict[str, Any]) -> WorkflowNode:
    return _node(
        "r", order, node_type="conditional_router", type_version=version, config=config
    )


class TestRouterRunner:
    @pytest.mark.parametrize(
        ("value", "expected_skip"), [("an error happened", {"b"}), ("all good", {"a"})]
    )
    def test_v1_skips_losing_branch_by_step_order(
        self, value: str, expected_skip: set[str]
    ) -> None:
        router = _router(
            0,
            1,
            {
                "condition_field": "$user_input",
                "operator": "contains",
                "match_value": "error",
                "true_steps": [1],
                "false_steps": [2, 99],  # 99 matches no step
            },
        )
        nodes = [router, _node("a", 1), _node("b", 2)]
        ctx = _ctx(nodes, RunState(context=WorkflowContext(user_input=value)))

        packets, outcome = _drive(RouterRunnerV1().run(router, ctx))

        assert outcome.status == StepStatus.COMPLETED
        assert ctx.state.skipped_keys == expected_skip
        assert ctx.state.completed_keys == {"r"}
        assert [t for t, _ in _types(packets)] == [
            "workflow_step_start",
            "workflow_step_delta",
            "workflow_step_end",
            "section_end",
        ]
        assert ctx.state.turn.value == 1
        ctx.save_checkpoint.assert_called_once_with()  # type: ignore[attr-defined]

    def test_v2_skips_by_node_key(self) -> None:
        router = _router(
            0,
            2,
            {
                "condition_field": "$user_input",
                "operator": "equals",
                "match_value": "yes",
                "true_node_keys": ["a"],
                "false_node_keys": ["b"],
            },
        )
        ctx = _ctx(
            [router, _node("a", 1), _node("b", 2)],
            RunState(context=WorkflowContext(user_input="no")),
        )
        _, outcome = _drive(RouterRunnerV2().run(router, ctx))
        assert outcome.output == "false"
        assert ctx.state.skipped_keys == {"a"}
        assert ctx.state.context.step_outputs["out_r"] == "false"


class TestRouterUpgrade:
    def test_v1_orders_become_node_keys(self) -> None:
        result = get_node_registry().upgrade_config(
            "conditional_router",
            1,
            {
                "condition_field": "$x",
                "operator": "equals",
                "true_steps": [2],
                "false_steps": [3, 42],
            },
            context=UpgradeContext(step_order_to_node_key={2: "n_two", 3: "n_three"}),
        )
        assert result.to_version == 2
        assert result.config["true_node_keys"] == ["n_two"]
        assert result.config["false_node_keys"] == ["n_three"]
        assert result.config["condition_field"] == "$x"

    def test_upgrade_function_is_pure(self) -> None:
        config = {"condition_field": "$x", "true_steps": [1]}
        ctx = UpgradeContext(step_order_to_node_key={1: "k"})
        assert upgrade_router_v1_to_v2(config, ctx) == upgrade_router_v1_to_v2(config, ctx)
        assert config == {"condition_field": "$x", "true_steps": [1]}


class TestBuiltinRegistry:
    def test_builtin_types_and_versions(self) -> None:
        registry = get_node_registry()
        assert registry.types() == ["agent", "code", "conditional_router", "loop", "parallel"]
        assert registry.versions("conditional_router") == [1, 2]
        assert registry.get("conditional_router", 1).deprecated is True
        assert registry.latest("agent").capabilities.can_pause is True


class TestRouterReferences:
    """A safe-references workflow reads a condition like every other setting."""

    def _route(self, field: str, outputs: dict[str, str], schema_version: int = 2) -> Any:
        router = _router(
            0,
            1,
            {
                "condition_field": field,
                "operator": "contains",
                "match_value": "yes",
                "true_steps": [1],
                "false_steps": [2],
            },
        )
        state = RunState(context=WorkflowContext(user_input="go", step_outputs=outputs))
        ctx = _ctx([router, _node("a", 1), _node("b", 2)], state)
        ctx.graph = ctx.graph.model_copy(update={"schema_version": schema_version})
        _, outcome = _drive(RouterRunnerV1().run(router, ctx))
        return outcome, ctx.state.skipped_keys

    def test_it_follows_a_path(self) -> None:
        outcome, skipped = self._route("$check.output.ok", {"check": '{"ok": "yes"}'})
        assert outcome.status == StepStatus.COMPLETED
        assert skipped == {"b"}

    def test_a_step_that_did_not_run_reads_as_empty(self) -> None:
        outcome, skipped = self._route("$out_a.output", {})
        assert outcome.status == StepStatus.COMPLETED
        assert skipped == {"a"}

    def test_a_wrong_path_fails_clearly(self) -> None:
        outcome, _ = self._route("$check.output.ok", {"check": "not json"})
        assert outcome.status == StepStatus.FAILED
        assert "not JSON" in (outcome.error or "")

    def test_an_old_workflow_keeps_its_lookup(self) -> None:
        outcome, skipped = self._route(
            "$check.output.ok", {"check": '{"ok": "yes"}'}, schema_version=1
        )
        assert outcome.status == StepStatus.COMPLETED
        assert skipped == {"a"}
