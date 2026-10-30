"""Unit tests for WorkflowGraph and its builders."""

from collections.abc import Generator
from typing import Any

import pytest
from pydantic import ValidationError

from om.db.models import AgentWorkflow
from om.db.models import AgentWorkflowStep
from om.workflows.graph import DEFINITION_FORMAT
from om.workflows.graph import graph_from_definition
from om.workflows.graph import graph_from_workflow
from om.workflows.graph import WorkflowGraph
from om.workflows.graph import WorkflowNode
from om.workflows.nodes.agent import AGENT_NODE_TYPE
from om.workflows.nodes.agent import AgentStepConfigV1
from om.workflows.nodes.agent import load_agent_config_v1
from om.workflows.nodes.base import NodeTypeSpec
from om.workflows.nodes.base import StepOutcome
from om.workflows.nodes.base import StepStatus
from om.workflows.nodes.registry import NodeTypeRegistry
from om.workflows.nodes.registry import UnknownNodeTypeError
from om.workflows.nodes.router import load_router_config_v1
from om.workflows.nodes.router import ROUTER_NODE_TYPE
from om.workflows.nodes.router import RouterConfigV1


class _NoopRunner:
    def run(self, node: Any, ctx: Any) -> Generator[Any, None, StepOutcome]:
        return StepOutcome(status=StepStatus.COMPLETED)
        yield  # pragma: no cover


@pytest.fixture
def registry() -> NodeTypeRegistry:
    reg = NodeTypeRegistry()
    reg.register(
        NodeTypeSpec(
            node_type=AGENT_NODE_TYPE,
            version=1,
            label="Agent",
            description="Runs an agent.",
            category="core",
            config_model=AgentStepConfigV1,
            runner=_NoopRunner(),
            load_legacy_config=load_agent_config_v1,
        )
    )
    reg.register(
        NodeTypeSpec(
            node_type=ROUTER_NODE_TYPE,
            version=1,
            label="Condition",
            description="Branches on a condition.",
            category="logic",
            config_model=RouterConfigV1,
            runner=_NoopRunner(),
            load_legacy_config=load_router_config_v1,
        )
    )
    return reg


def _workflow(steps: list[AgentWorkflowStep]) -> AgentWorkflow:
    return AgentWorkflow(
        id=7,
        name="Demo",
        orchestration_mode="sequential",
        timeout_seconds=600,
        steps=steps,
    )


def _agent_step(step_id: int, order: int, **kwargs: Any) -> AgentWorkflowStep:
    fields: dict[str, Any] = {
        "id": step_id,
        "workflow_id": 7,
        "step_type": "agent",
        "agent_id": 100 + step_id,
        "step_order": order,
        "step_name": f"Step {order}",
        "output_key": f"out_{order}",
    }
    return AgentWorkflowStep(**{**fields, **kwargs})


class TestGraphFromWorkflow:
    def test_legacy_rows_load_with_backfill_compatible_keys(
        self, registry: NodeTypeRegistry
    ) -> None:
        # Unflushed legacy-style rows: no node_key / type_version set.
        graph = graph_from_workflow(
            _workflow([_agent_step(12, 1), _agent_step(11, 0)]), registry
        )
        assert [n.node_key for n in graph.nodes] == ["s11", "s12"]
        assert [n.step_order for n in graph.nodes] == [0, 1]
        assert graph.nodes[0].type_version == 1
        assert graph.schema_version == 1
        assert graph.timeout_seconds == 600

    def test_agent_config_read_from_legacy_columns(
        self, registry: NodeTypeRegistry
    ) -> None:
        step = _agent_step(
            1,
            0,
            node_key="n_aaaa",
            type_version=1,
            llm_model_override="gpt-4.1",
            tool_ids_override=[3, 4],
        )
        (node,) = graph_from_workflow(_workflow([step]), registry).nodes
        assert node.node_key == "n_aaaa"
        assert node.config["agent_id"] == 101
        assert node.config["llm_model_override"] == "gpt-4.1"
        assert node.config["tool_ids_override"] == [3, 4]

    def test_router_config_read_leniently(self, registry: NodeTypeRegistry) -> None:
        router = AgentWorkflowStep(
            id=5,
            workflow_id=7,
            step_type="conditional_router",
            step_order=0,
            step_name="Route",
            output_key="route",
            condition={"condition_field": "$a", "true_steps": ["2"], "goto": "x"},
        )
        (node,) = graph_from_workflow(_workflow([router]), registry).nodes
        assert node.config["true_steps"] == [2]  # legacy string orders coerced
        assert node.config["operator"] == "contains"  # legacy default
        assert "goto" not in node.config  # unknown legacy keys dropped

    def test_unknown_type_is_a_hard_error(self, registry: NodeTypeRegistry) -> None:
        step = _agent_step(1, 0, step_type="teleport")
        with pytest.raises(UnknownNodeTypeError):
            graph_from_workflow(_workflow([step]), registry)

    def test_unknown_version_is_a_hard_error(self, registry: NodeTypeRegistry) -> None:
        step = _agent_step(1, 0, type_version=9)
        with pytest.raises(UnknownNodeTypeError):
            graph_from_workflow(_workflow([step]), registry)


class TestGraphInvariants:
    def _node(self, key: str, order: int) -> WorkflowNode:
        return WorkflowNode(
            node_key=key, node_type="agent", type_version=1, step_order=order, name=key
        )

    def test_duplicate_keys_rejected(self) -> None:
        with pytest.raises(ValidationError, match="unique node keys"):
            WorkflowGraph(
                workflow_id=1,
                name="x",
                orchestration_mode="sequential",
                nodes=[self._node("a", 0), self._node("a", 1)],
            )

    def test_duplicate_orders_rejected(self) -> None:
        with pytest.raises(ValidationError, match="unique step orders"):
            WorkflowGraph(
                workflow_id=1,
                name="x",
                orchestration_mode="sequential",
                nodes=[self._node("a", 0), self._node("b", 0)],
            )

    def test_unsorted_nodes_rejected(self) -> None:
        with pytest.raises(ValidationError, match="sorted"):
            WorkflowGraph(
                workflow_id=1,
                name="x",
                orchestration_mode="sequential",
                nodes=[self._node("a", 1), self._node("b", 0)],
            )

    def test_lookups(self) -> None:
        graph = WorkflowGraph(
            workflow_id=1,
            name="x",
            orchestration_mode="sequential",
            nodes=[
                self._node("a", 0).model_copy(update={"step_id": 10}),
                self._node("b", 3),
            ],
        )
        assert graph.node("b").step_order == 3
        assert graph.node_for_step_id(10).node_key == "a"  # type: ignore[union-attr]
        assert graph.node_for_step_id(99) is None
        assert graph.step_order_to_node_key() == {0: "a", 3: "b"}


class TestContainers:
    def _n(self, key: str, order: int, parent: str | None = None, branch: int | None = None) -> WorkflowNode:
        return WorkflowNode(
            node_key=key, node_type="agent", type_version=1, step_order=order,
            name=key, parent_key=parent, branch_index=branch,
        )

    def _graph(self, nodes: list[WorkflowNode]) -> WorkflowGraph:
        return WorkflowGraph(
            workflow_id=1, name="x", orchestration_mode="sequential", nodes=nodes
        )

    def test_top_level_and_branches(self) -> None:
        graph = self._graph([
            self._n("intake", 0),
            self._n("par", 1),
            self._n("hotel", 2, "par", 1),
            self._n("flight", 3, "par", 0),
            self._n("flight_check", 4, "par", 0),
            self._n("summary", 5),
        ])
        assert [n.node_key for n in graph.top_level()] == ["intake", "par", "summary"]
        assert [[n.node_key for n in b] for b in graph.branches("par")] == [
            ["flight", "flight_check"],
            ["hotel"],
        ]
        assert graph.depth("flight") == 1 and graph.depth("par") == 0

    def test_unknown_container_rejected(self) -> None:
        with pytest.raises(ValidationError, match="unknown container"):
            self._graph([self._n("a", 0, "ghost", 0)])

    def test_child_must_come_after_container(self) -> None:
        with pytest.raises(ValidationError, match="must come after"):
            self._graph([self._n("a", 0, "par", 0), self._n("par", 1)])

    def test_child_needs_branch_index(self) -> None:
        with pytest.raises(ValidationError, match="branch index"):
            self._graph([self._n("par", 0), self._n("a", 1, "par", None)])

    def test_parent_links_load_from_rows(self, registry: NodeTypeRegistry) -> None:
        parent = _agent_step(10, 0, node_key="n_par")
        child = _agent_step(11, 1, node_key="n_child", parent_step_id=10, branch_index=2)
        graph = graph_from_workflow(_workflow([parent, child]), registry)
        assert graph.node("n_child").parent_key == "n_par"
        assert graph.node("n_child").branch_index == 2


class TestDefinitionRoundTrip:
    def test_round_trip_and_stable_hash(self, registry: NodeTypeRegistry) -> None:
        graph = graph_from_workflow(
            _workflow([_agent_step(1, 0), _agent_step(2, 1)]), registry
        )
        definition = graph.to_definition()
        assert definition["definition_format"] == DEFINITION_FORMAT
        restored = graph_from_definition(definition)
        assert restored == graph
        assert restored.content_hash() == graph.content_hash()

    def test_hash_changes_with_content(self, registry: NodeTypeRegistry) -> None:
        a = graph_from_workflow(_workflow([_agent_step(1, 0)]), registry)
        b = graph_from_workflow(
            _workflow([_agent_step(1, 0, llm_model_override="x")]), registry
        )
        assert a.content_hash() != b.content_hash()

    def test_newer_definition_format_rejected(self) -> None:
        with pytest.raises(ValueError, match="newer than this server"):
            graph_from_definition(
                {
                    "definition_format": DEFINITION_FORMAT + 1,
                    "workflow_id": 1,
                    "name": "x",
                    "orchestration_mode": "sequential",
                }
            )
