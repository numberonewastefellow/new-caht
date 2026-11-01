"""Workflow LLM calls run inside a trace, so they're recorded and don't log errors."""

from types import SimpleNamespace
from typing import Any

from om.server.query_and_chat.placement import Placement
from om.tools.tool_implementations.agent_tool import AgentTool
from om.tracing.framework.create import ensure_trace
from om.tracing.framework.create import get_current_trace


def _tool() -> AgentTool:
    tool = AgentTool.__new__(AgentTool)
    tool._agent = SimpleNamespace(name="Writer")  # type: ignore[assignment]
    tool._step_name = "Draft"
    return tool


def test_an_agents_llm_loop_runs_inside_a_trace() -> None:
    tool = _tool()
    seen: dict[str, Any] = {}

    def run_agent(placement: Placement, **kwargs: Any) -> str:
        seen["trace"] = get_current_trace()
        seen["task"] = kwargs["task"]
        return "reply"

    tool._run_agent = run_agent  # type: ignore[method-assign,assignment]

    assert tool.run(Placement(turn_index=0), task="write") == "reply"
    assert seen["trace"] is not None
    assert seen["task"] == "write"
    assert get_current_trace() is None


def test_a_trace_already_open_is_reused() -> None:
    tool = _tool()
    seen: dict[str, Any] = {}

    def run_agent(placement: Placement, **kwargs: Any) -> str:
        seen["trace"] = get_current_trace()
        return "reply"

    tool._run_agent = run_agent  # type: ignore[method-assign,assignment]

    with ensure_trace("outer") as outer:
        tool.run(Placement(turn_index=0), task="write")
    assert seen["trace"] is outer


def test_the_trace_closes_when_the_agent_fails() -> None:
    tool = _tool()

    def run_agent(placement: Placement, **kwargs: Any) -> str:
        raise RuntimeError("boom")

    tool._run_agent = run_agent  # type: ignore[method-assign,assignment]

    try:
        tool.run(Placement(turn_index=0), task="write")
    except RuntimeError:
        pass
    assert get_current_trace() is None
