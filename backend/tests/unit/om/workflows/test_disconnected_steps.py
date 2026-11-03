"""A disconnected (disabled) step is kept in the workflow but doesn't run."""

from types import SimpleNamespace
from typing import Any

import pytest

from om.db.workflow import runnable_workflow_steps
from om.workflows.graph import graph_from_definition
from om.workflows.graph import WorkflowGraph
from om.workflows.graph import WorkflowNode
from om.workflows.models import WorkflowStepCreate
from om.workflows.reference_check import runnable_steps
from om.workflows.reference_check import skipped_keys
from om.workflows.reference_check import skipped_step_problem
from om.workflows.saving import _check_references
from om.workflows.saving import WorkflowSaveError


def _node(key: str, order: int, *, disabled: bool = False, parent: str | None = None) -> WorkflowNode:
    return WorkflowNode(
        node_key=key,
        node_type="agent",
        type_version=1,
        step_order=order,
        name=key,
        output_key=key,
        disabled=disabled,
        parent_key=parent,
        branch_index=0 if parent else None,
    )


def _graph(*nodes: WorkflowNode) -> WorkflowGraph:
    return WorkflowGraph(
        workflow_id=1, name="wf", orchestration_mode="sequential", nodes=list(nodes)
    )


def _step(
    key: str,
    order: int,
    *,
    disabled: bool = False,
    reads: str | None = None,
    parent: str | None = None,
    step_type: str = "agent",
    config: dict[str, Any] | None = None,
    condition: Any = None,
) -> Any:
    return SimpleNamespace(
        node_key=key,
        step_type=step_type,
        step_name=key,
        step_order=order,
        output_key=key,
        parent_key=parent,
        branch_index=0 if parent else None,
        input_mapping={"task": reads} if reads else None,
        config=config,
        condition=condition,
        disabled=disabled,
    )


class TestRunnableGraph:
    def test_a_graph_with_nothing_disabled_is_returned_as_is(self) -> None:
        graph = _graph(_node("a", 0), _node("b", 1))
        assert graph.runnable() is graph

    def test_disabled_steps_and_everything_inside_them_are_left_out(self) -> None:
        graph = _graph(
            _node("a", 0),
            _node("box", 1, disabled=True),
            _node("inner", 2, parent="box"),
            _node("deeper", 3, parent="inner"),
            _node("c", 4, disabled=True),
        )
        runnable = graph.runnable()
        assert [n.node_key for n in runnable.nodes] == ["a"]
        assert runnable.node_for_key("box") is None
        # The full graph keeps them, for the version history
        assert len(graph.nodes) == 5

    def test_lookups_are_not_carried_over_from_the_full_graph(self) -> None:
        graph = _graph(_node("a", 0), _node("b", 1, disabled=True))
        assert graph.node_for_key("b") is not None  # fills the full graph's cache
        assert graph.runnable().node_for_key("b") is None


class TestDefinition:
    def test_the_flag_is_written_only_when_set(self) -> None:
        nodes = _graph(_node("a", 0), _node("b", 1, disabled=True)).to_definition()["nodes"]
        assert "disabled" not in nodes[0]
        assert nodes[1]["disabled"] is True

    def test_a_definition_without_the_flag_hashes_as_before(self) -> None:
        graph = _graph(_node("a", 0))
        before = graph.model_dump(mode="json")
        for node in before["nodes"]:
            node.pop("disabled")
        assert graph.to_definition() == before

    def test_a_restored_version_keeps_disconnected_steps(self) -> None:
        graph = _graph(_node("a", 0), _node("b", 1, disabled=True))
        restored = graph_from_definition(graph.to_definition())
        assert restored == graph
        assert [n.node_key for n in restored.runnable().nodes] == ["a"]


class TestSkippedSteps:
    def test_children_of_a_disabled_container_are_skipped(self) -> None:
        steps = [
            _step("a", 0),
            _step("box", 1, disabled=True),
            _step("inner", 2, parent="box"),
        ]
        assert skipped_keys(steps) == {"box", "inner"}
        assert [s.node_key for s in runnable_steps(steps)] == ["a"]

    def test_steps_saved_before_the_flag_existed_all_run(self) -> None:
        old = SimpleNamespace(node_key="a", step_order=0, parent_key=None)
        assert skipped_keys([old]) == set()

    def test_reading_a_disconnected_step_is_refused(self) -> None:
        steps = [_step("a", 0), _step("b", 1, disabled=True), _step("c", 2, reads="$b")]
        problem = skipped_step_problem(steps)
        assert problem is not None
        assert '"c" reads $b' in problem and '"b" is disconnected' in problem

    def test_a_disconnected_step_may_read_anything(self) -> None:
        steps = [_step("a", 0, disabled=True), _step("b", 1, disabled=True, reads="$a")]
        assert skipped_step_problem(steps) is None

    def test_reading_only_running_steps_is_fine(self) -> None:
        steps = [_step("a", 0), _step("b", 1, reads="$a"), _step("c", 2, disabled=True)]
        assert skipped_step_problem(steps) is None

    def test_a_condition_leading_to_a_disconnected_step_is_refused(self) -> None:
        router = _step(
            "r", 0, step_type="conditional_router", config={"true_node_keys": ["b"]}
        )
        problem = skipped_step_problem([router, _step("b", 1, disabled=True)])
        assert problem is not None and '"r" leads to "b"' in problem

    def test_a_version_1_condition_is_checked_by_step_order(self) -> None:
        router = _step(
            "r", 0, step_type="conditional_router", condition={"true_steps": [1]}
        )
        problem = skipped_step_problem([router, _step("b", 1, disabled=True)])
        assert problem is not None and '"b"' in problem


def _create(key: str, order: int, **fields: Any) -> WorkflowStepCreate:
    return WorkflowStepCreate(
        node_key=key, step_type="code", step_order=order, step_name=key, output_key=key, **fields
    )


class TestSaveChecks:
    def test_every_step_disconnected_is_refused(self) -> None:
        steps = [_create("a", 0, disabled=True), _create("b", 1, disabled=True)]
        with pytest.raises(WorkflowSaveError, match="nothing to run"):
            _check_references(steps, 2, "sequential")

    def test_llm_decision_also_needs_one_step_to_run(self) -> None:
        with pytest.raises(WorkflowSaveError, match="nothing to run"):
            _check_references([_create("a", 0, disabled=True)], 2, "llm_decision")

    def test_reading_a_disconnected_step_is_refused_on_save(self) -> None:
        steps = [
            _create("a", 0, disabled=True),
            _create("b", 1, input_mapping={"task": "$a"}),
        ]
        with pytest.raises(WorkflowSaveError, match="disconnected"):
            _check_references(steps, 2, "sequential")

    def test_disconnected_steps_after_the_running_ones_save(self) -> None:
        steps = [
            _create("a", 0),
            _create("b", 1, input_mapping={"task": "$a"}, disabled=True),
        ]
        _check_references(steps, 2, "sequential")

    def test_an_old_format_workflow_checks_only_running_steps(self) -> None:
        steps = [_create("a", 0), _create("b", 1, disabled=True)]
        _check_references(steps, 1, "sequential")


def _row(step_id: int, order: int, *, disabled: bool = False, parent: int | None = None) -> Any:
    return SimpleNamespace(
        id=step_id, step_order=order, disabled=disabled, parent_step_id=parent
    )


def test_engines_reading_step_rows_skip_disconnected_ones() -> None:
    workflow = SimpleNamespace(
        steps=[
            _row(3, 2, disabled=True),
            _row(1, 0),
            _row(4, 3, parent=3),
            _row(2, 1),
        ]
    )
    assert [s.id for s in runnable_workflow_steps(workflow)] == [1, 2]
