"""A webhook's runs can only use the tools its owner chose, in every way a step gets tools."""

from typing import Any
from unittest.mock import MagicMock

import pytest

from om.tools.tool_implementations.agent_tool import AgentTool
from om.workflows import workflow_engine
from om.workflows.nodes import agent_tools as agent_tools_module
from om.workflows.nodes.agent_tools import AgentToolCache


def _agent_tool(override: list[int] | None, allowlist: list[int] | None) -> AgentTool:
    tool = AgentTool.__new__(AgentTool)
    tool._agent = MagicMock(tools=[MagicMock(id=1), MagicMock(id=2), MagicMock(id=3)])
    tool._tool_ids_override = override
    tool._tool_allowlist = allowlist
    return tool


@pytest.mark.parametrize(
    "override,allowlist,expected",
    [
        # No limit: exactly today's behaviour
        (None, None, None),
        ([1], None, [1]),
        # A limit cuts down whatever the step would have had
        (None, [2], [2]),
        ([1, 2], [2, 3], [2]),
        # A tool the step doesn't have can't be added by the limit
        ([1], [3], []),
        (None, [99], []),
        # An empty limit means no tools, not "no limit"
        (None, [], []),
        ([1, 2], [], []),
    ],
)
def test_allowed_tools(
    override: list[int] | None, allowlist: list[int] | None, expected: list[int] | None
) -> None:
    assert _agent_tool(override, allowlist)._allowed_tool_ids() == expected


def test_sequential_steps_get_the_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}
    monkeypatch.setattr(
        agent_tools_module, "AgentTool", lambda **kwargs: captured.update(kwargs) or MagicMock()
    )
    monkeypatch.setattr(agent_tools_module, "load_step_agent", lambda *_: MagicMock(tools=[]))
    cache = AgentToolCache(
        db_session=MagicMock(), user=MagicMock(), emitter=MagicMock(), tool_allowlist=[7]
    )
    monkeypatch.setattr(cache, "_llm_for", lambda *_: MagicMock())
    cache.get(
        MagicMock(node_key="a"),
        MagicMock(output_schema=None, tool_ids_override=None),
    )
    assert captured["tool_allowlist"] == [7]


def test_llm_decision_steps_get_the_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}
    monkeypatch.setattr(
        workflow_engine, "AgentTool", lambda **kwargs: captured.update(kwargs) or MagicMock()
    )
    monkeypatch.setattr(workflow_engine, "get_llm_for_agent", lambda *_, **__: MagicMock())
    monkeypatch.setattr(
        workflow_engine,
        "load_step_agent",
        lambda *_: MagicMock(tools=[], llm_model_provider_override=None, llm_model_version_override=None),
    )
    step = MagicMock(
        step_type="agent",
        agent=MagicMock(tools=[], deleted=False),
        llm_provider_override=None,
        llm_model_override=None,
    )
    workflow_engine._build_agent_tools(
        [step], MagicMock(), MagicMock(), user=MagicMock(), tool_allowlist=[7]
    )
    assert captured["tool_allowlist"] == [7]


def test_parallel_branches_inherit_the_limit() -> None:
    cache = AgentToolCache(
        db_session=MagicMock(), user=MagicMock(), emitter=MagicMock(), tool_allowlist=[7]
    )
    branch = cache.for_branch(db_session=MagicMock(), user=MagicMock(), emitter=MagicMock())
    assert branch._tool_allowlist == [7]
    assert branch._sandbox_session_id is None
