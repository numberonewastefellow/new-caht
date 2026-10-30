"""Unit tests for the per-run workflow state."""

from typing import Any
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from om.workflows.graph import WorkflowGraph
from om.workflows.graph import WorkflowNode
from om.workflows.models import WorkflowCheckpoint
from om.workflows.models import WorkflowContext
from om.workflows.state import CHECKPOINT_VERSION
from om.workflows.state import everything_user_said
from om.workflows.state import restore_run_state
from om.workflows.state import ResumeIncompatibleError
from om.workflows.state import RunContext
from om.workflows.state import RunState
from om.workflows.state import TurnCursor


def _node(key: str, order: int, step_id: int | None) -> WorkflowNode:
    return WorkflowNode(
        node_key=key,
        step_id=step_id,
        node_type="agent",
        type_version=1,
        step_order=order,
        name=key,
        output_key=f"out_{key}",
    )


def _context(state: RunState, db_session: Any) -> RunContext:
    graph = WorkflowGraph(
        workflow_id=1,
        name="wf",
        orchestration_mode="sequential",
        nodes=[_node("a", 0, 10), _node("b", 1, 11), _node("c", 2, None)],
    )
    return RunContext(
        graph=graph,
        registry=MagicMock(),
        state=state,
        db_session=db_session,
        user=MagicMock(),
        emitter=MagicMock(),
        execution=MagicMock(id=99),
        trace=MagicMock(),
        agent_tools=MagicMock(),
    )


class TestRestoreRunState:
    def _graph(self) -> WorkflowGraph:
        return WorkflowGraph(
            workflow_id=1,
            name="wf",
            orchestration_mode="sequential",
            nodes=[_node("a", 0, 10), _node("b", 1, 11)],
        )

    def test_conversation_aware_resume(self) -> None:
        checkpoint = WorkflowCheckpoint(
            checkpoint_version=2,
            step_outputs={"out_a": "A"},
            shared_data={"_original_user_input": "plan a trip"},
            turn_index=5,
            paused_agent_original_task="Find flights",
            clarification_conversation=[{"role": "agent", "content": "Dates?"}],
            completed_node_keys=["a"],
            skipped_node_keys=["x"],
            output_order=["out_a"],
            paused_node_key="b",
        )
        state = restore_run_state(checkpoint, self._graph(), "May 3-7", None)

        assert state.context.user_input == "plan a trip"
        assert state.completed_keys == {"a"}
        assert state.skipped_keys == {"x"}
        assert state.output_order == ["out_a"]
        assert state.turn.value == 5
        assert state.resume is not None
        assert state.resume.node_key == "b"
        assert state.resume.original_task == "Find flights"
        assert state.resume.conversation == [
            {"role": "agent", "content": "Dates?"},
            {"role": "user", "content": "May 3-7"},
        ]
        assert state.resume.task_override is not None
        assert "Find flights" in state.resume.task_override
        assert "May 3-7" in state.resume.task_override

    def test_legacy_checkpoint_without_conversation(self) -> None:
        checkpoint = WorkflowCheckpoint(
            shared_data={"_original_user_input": "hi", "_clarifications": ["one"]},
            completed_step_ids=[10],
        )
        state = restore_run_state(checkpoint, self._graph(), "two", 11)

        assert state.context.user_input == (
            "Everything the user has said:\n- hi\n- one\n- two"
        )
        assert state.context.shared_data["_clarifications"] == ["one", "two"]
        assert state.completed_keys == {"a"}
        assert state.resume is not None
        assert state.resume.node_key == "b"
        assert state.resume.task_override is None

    def test_legacy_checkpoint_paused_step_deleted(self) -> None:
        checkpoint = WorkflowCheckpoint(completed_step_ids=[10])
        state = restore_run_state(checkpoint, self._graph(), "reply", None)
        assert state.resume is not None
        assert state.resume.node_key is None

    def test_v2_checkpoint_with_unknown_nodes_is_rejected(self) -> None:
        checkpoint = WorkflowCheckpoint(
            checkpoint_version=2, completed_node_keys=["a", "gone"]
        )
        with pytest.raises(ResumeIncompatibleError, match="gone"):
            restore_run_state(checkpoint, self._graph(), "reply", None)

    def test_everything_user_said_keeps_the_original_request(self) -> None:
        checkpoint = WorkflowCheckpoint(
            shared_data={"_original_user_input": "plan a trip"}
        )
        text, clarifications = everything_user_said(checkpoint, "May 3-7")
        assert text == "Everything the user has said:\n- plan a trip\n- May 3-7"
        assert clarifications == ["May 3-7"]

    def test_legacy_checkpoint_for_edited_workflow_is_rejected(self) -> None:
        checkpoint = WorkflowCheckpoint(completed_step_ids=[10, 77])
        with pytest.raises(ResumeIncompatibleError, match="changed"):
            restore_run_state(checkpoint, self._graph(), "reply", 11)


class TestTurnCursor:
    def test_observe_only_moves_forward(self) -> None:
        cursor = TurnCursor(3)
        cursor.observe(1)
        assert cursor.value == 3
        cursor.observe(7)
        assert cursor.value == 7

    def test_advance(self) -> None:
        cursor = TurnCursor()
        assert cursor.advance() == 1
        assert cursor.advance(2) == 3


class TestRunState:
    def test_output_order_tracks_latest_write(self) -> None:
        state = RunState(context=WorkflowContext(user_input="hi"))
        state.record_output("a", "1")
        state.record_output("b", "2")
        state.record_output("a", "3")
        assert state.output_order == ["b", "a"]
        assert state.last_output() == "3"

    def test_last_output_falls_back_for_legacy_restores(self) -> None:
        context = WorkflowContext(user_input="hi", step_outputs={"x": "1", "y": "2"})
        state = RunState(context=context)
        assert state.last_output() == "2"

    def test_last_output_none_when_nothing_ran(self) -> None:
        assert RunState(context=WorkflowContext(user_input="hi")).last_output() is None


class TestSaveCheckpoint:
    def test_completed_checkpoint_is_v2_and_v1_compatible(self) -> None:
        state = RunState(context=WorkflowContext(user_input="plan a trip"))
        state.record_output("out_a", "A")
        state.completed_keys = {"a", "c"}
        state.skipped_keys = {"b"}
        state.turn.value = 4
        ctx = _context(state, MagicMock())

        with patch("om.workflows.state.db_save_checkpoint") as save:
            ctx.save_checkpoint()

        _session, execution_id, checkpoint = save.call_args.args
        assert execution_id == 99
        assert isinstance(checkpoint, WorkflowCheckpoint)
        assert checkpoint.checkpoint_version == CHECKPOINT_VERSION
        assert checkpoint.completed_node_keys == ["a", "c"]
        assert checkpoint.skipped_node_keys == ["b"]
        assert checkpoint.output_order == ["out_a"]
        # v1 field: only nodes that have a step row
        assert checkpoint.completed_step_ids == [10]
        assert checkpoint.turn_index == 4
        assert checkpoint.shared_data["_original_user_input"] == "plan a trip"
        assert save.call_args.kwargs == {"paused_at_step_id": None, "paused": False}

    def test_original_user_input_is_preserved_across_resumes(self) -> None:
        context = WorkflowContext(
            user_input="Everything the user has said: ...",
            shared_data={"_original_user_input": "first message"},
        )
        ctx = _context(RunState(context=context), MagicMock())
        with patch("om.workflows.state.db_save_checkpoint") as save:
            ctx.save_checkpoint()
        checkpoint = save.call_args.args[2]
        assert checkpoint.shared_data["_original_user_input"] == "first message"

    def test_pause_records_node_and_conversation(self) -> None:
        state = RunState(context=WorkflowContext(user_input="hi"))
        session = MagicMock()
        ctx = _context(state, session)
        paused = ctx.graph.node("b")

        with patch("om.workflows.state.db_save_checkpoint") as save:
            ctx.save_checkpoint(
                paused_node=paused,
                paused_agent_original_task="the task",
                clarification_conversation=[{"role": "agent", "content": "Q?"}],
            )

        checkpoint = save.call_args.args[2]
        assert checkpoint.paused_node_key == "b"
        assert checkpoint.paused_agent_original_task == "the task"
        assert checkpoint.clarification_conversation == [
            {"role": "agent", "content": "Q?"}
        ]
        assert save.call_args.kwargs == {"paused_at_step_id": 11, "paused": True}

    def test_pause_at_deleted_step_keeps_fk_null_but_still_pauses(self) -> None:
        state = RunState(context=WorkflowContext(user_input="hi"))
        session = MagicMock()
        session.get.return_value = None  # step row was deleted after pinning
        ctx = _context(state, session)

        with patch("om.workflows.state.db_save_checkpoint") as save:
            ctx.save_checkpoint(paused_node=ctx.graph.node("b"))

        assert save.call_args.kwargs == {"paused_at_step_id": None, "paused": True}
        assert save.call_args.args[2].paused_node_key == "b"
