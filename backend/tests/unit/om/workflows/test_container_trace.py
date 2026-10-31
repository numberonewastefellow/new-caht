"""The trace shows containers as they ran: forks, joins, scopes and real times."""

from typing import Any

from om.workflows.branches import BufferedTrace
from om.workflows.graph import WorkflowGraph
from om.workflows.graph import WorkflowNode
from om.workflows.trace_models import WorkflowTraceBuilder


def _builder() -> WorkflowTraceBuilder:
    return WorkflowTraceBuilder(
        execution_id=1,
        workflow_id=1,
        workflow_name="wf",
        chat_session_id=None,
        mode="sequential",
    )


def _edges(builder: WorkflowTraceBuilder) -> set[tuple[str, str]]:
    names = {n.id: n.name for n in builder.trace.nodes}
    return {
        (names.get(e.from_id, e.from_id), names.get(e.to_id, e.to_id))
        for e in builder.trace.edges
    }


def _step(builder: Any, name: str) -> Any:
    return builder.start_step(step_id=None, name=name, node_type="code", input_text="")


class TestForkAndJoin:
    def _parallel(self) -> WorkflowTraceBuilder:
        builder = _builder()
        _step(builder, "before")
        parallel = _step(builder, "parallel")
        for name in ("a", "b"):
            branch = BufferedTrace(prefix=f"{name}/")
            ref = _step(branch, name)
            branch.finish_agent(ref, "output", status="completed")
            builder.begin_branch(parallel)
            branch.replay(builder)
            builder.end_branch()
        builder.join_branches()
        _step(builder, "after")
        return builder

    def test_every_branch_starts_from_the_container(self) -> None:
        edges = _edges(self._parallel())
        assert ("parallel", "a") in edges
        assert ("parallel", "b") in edges

    def test_branches_are_not_chained_to_each_other(self) -> None:
        assert ("a", "b") not in _edges(self._parallel())

    def test_the_next_step_follows_every_branch(self) -> None:
        edges = _edges(self._parallel())
        assert ("a", "after") in edges
        assert ("b", "after") in edges

    def test_steps_after_the_join_chain_normally(self) -> None:
        builder = self._parallel()
        _step(builder, "later")
        edges = _edges(builder)
        assert ("after", "later") in edges
        assert ("a", "later") not in edges

    def test_the_final_answer_can_follow_a_join(self) -> None:
        builder = _builder()
        parallel = _step(builder, "parallel")
        branch = BufferedTrace(prefix="a/")
        _step(branch, "a")
        builder.begin_branch(parallel)
        branch.replay(builder)
        builder.end_branch()
        builder.join_branches()
        builder.add_finish("done")
        assert any(e.to_id == "finish" for e in builder.trace.edges)


class TestBranchTimes:
    def test_branch_nodes_keep_the_time_they_really_ran(self) -> None:
        builder = _builder()
        branch = BufferedTrace(prefix="a/")
        ref = _step(branch, "a")
        branch.finish_agent(ref, "done", status="completed")
        started_when_recorded = branch._calls[0][4]
        ended_when_recorded = branch._calls[1][4]
        branch.replay(builder)
        node = next(n for n in builder.trace.nodes if n.name == "a")
        assert node.started_at == started_when_recorded
        assert node.ended_at == ended_when_recorded
        assert node.status == "completed"


class TestScope:
    def test_nodes_carry_the_scope_they_ran_in(self) -> None:
        builder = _builder()
        builder.set_scope("Plan each day · 2", 1)
        _step(builder, "inside")
        builder.set_scope(None, None)
        _step(builder, "outside")
        by_name = {n.name: n for n in builder.trace.nodes}
        assert by_name["inside"].scope == "Plan each day · 2"
        assert by_name["inside"].depth == 1
        assert by_name["outside"].scope is None

    def test_buffered_branches_keep_their_scope(self) -> None:
        builder = _builder()
        branch = BufferedTrace(prefix="a/")
        branch.set_scope("Research · Flights", 1)
        _step(branch, "a")
        branch.replay(builder)
        assert builder.trace.nodes[-1].scope == "Research · Flights"

    def test_saved_traces_leave_out_empty_scope(self) -> None:
        builder = _builder()
        _step(builder, "top")
        saved = builder.trace.nodes[-1].model_dump()
        assert "scope" not in saved and "depth" not in saved
        builder.set_scope("x", 1)
        _step(builder, "in")
        assert builder.trace.nodes[-1].model_dump()["scope"] == "x"


class TestScopeOf:
    @staticmethod
    def _graph() -> WorkflowGraph:
        def node(key: str, order: int, node_type: str = "agent", **extra: Any) -> WorkflowNode:
            return WorkflowNode(
                node_key=key, step_id=order, node_type=node_type, type_version=1,
                step_order=order, name=key, output_key=key, config=extra.pop("config", {}), **extra,
            )

        return WorkflowGraph(
            workflow_id=1, name="wf", orchestration_mode="sequential",
            nodes=[
                node("top", 0),
                node("par", 1, "parallel", config={"branches": [{"label": "Flights"}, {"label": "Hotels"}]}),
                node("hotel", 2, parent_key="par", branch_index=1),
                node("each", 3, "loop", parent_key="par", branch_index=0),
                node("day", 4, parent_key="each", branch_index=0),
            ],
        )

    def _scope(self, key: str, variables: dict[str, Any] | None = None) -> tuple[str | None, int | None]:
        from types import SimpleNamespace

        from om.workflows.blocks import _scope_of

        graph = self._graph()
        ctx: Any = SimpleNamespace(graph=graph, state=SimpleNamespace(variables=variables or {}))
        node = graph.node_for_key(key)
        assert node is not None
        return _scope_of(node, ctx)

    def test_top_level_has_no_scope(self) -> None:
        assert self._scope("top") == (None, None)

    def test_a_branch_uses_its_label(self) -> None:
        assert self._scope("hotel") == ("par · Hotels", 1)

    def test_a_loop_uses_the_iteration_counted_from_one(self) -> None:
        assert self._scope("day", {"loop": {"index": 1}}) == ("each · 2", 2)
