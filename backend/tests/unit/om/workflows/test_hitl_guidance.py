"""A step that may pause is told how to ask, so the option works on its own."""

from typing import Any
from unittest.mock import MagicMock

import pytest

from om.server.query_and_chat.placement import Placement
from om.tools.tool_implementations.agent_tool import AgentTool
from om.workflows.hitl import agent_requests_input
from om.workflows.hitl import INPUT_REQUEST_GUIDANCE
from om.workflows.hitl import NEEDS_INPUT_PREFIX
from om.workflows.hitl import with_input_guidance
from om.workflows.nodes import agent_tools as agent_tools_module
from om.workflows.nodes.agent_tools import AgentToolCache

PROMPT = "You review FIRs."


class _PromptBuilt(Exception):
    """Stops the agent once its prompt is built: no LLM is needed past that point."""


def _prompt_sent(monkeypatch: pytest.MonkeyPatch, **agent_tool_args: Any) -> str:
    """The system prompt a real AgentTool would send to the LLM."""
    captured: dict[str, str] = {}

    def capture(*, system_prompt: Any, **_: Any) -> None:
        captured["prompt"] = system_prompt.message
        raise _PromptBuilt

    monkeypatch.setattr("om.chat.llm_loop.construct_message_history", capture)
    monkeypatch.setattr("om.llm.factory.get_llm_token_counter", lambda _: lambda text: len(text))
    agent = MagicMock(system_prompt=PROMPT, task_prompt="", tools=[], description="")
    agent.name = "FIR Correction Helper"
    tool = AgentTool(
        agent=agent,
        emitter=MagicMock(),
        db_session=MagicMock(),
        user=MagicMock(),
        llm=MagicMock(),
        has_tools=False,
        **agent_tool_args,
    )
    with pytest.raises(_PromptBuilt):
        tool._run_agent(Placement(turn_index=0), task="review this")
    return captured["prompt"]


class TestWithInputGuidance:
    def test_a_prompt_without_the_marker_gets_the_guidance(self) -> None:
        assert with_input_guidance(PROMPT) == PROMPT + INPUT_REQUEST_GUIDANCE

    @pytest.mark.parametrize("marker", [NEEDS_INPUT_PREFIX, NEEDS_INPUT_PREFIX.lower()])
    def test_a_prompt_that_covers_it_is_left_alone(self, marker: str) -> None:
        prompt = f"If anything is missing, start with {marker}."
        assert with_input_guidance(prompt) == prompt

    def test_the_guidance_names_the_marker_the_engine_looks_for(self) -> None:
        assert NEEDS_INPUT_PREFIX in INPUT_REQUEST_GUIDANCE

    def test_a_reply_following_the_guidance_pauses_the_run(self) -> None:
        assert agent_requests_input(f"{NEEDS_INPUT_PREFIX}\nPlease provide the FIR text.")

    def test_the_guidance_does_not_ask_for_text_users_would_see(self) -> None:
        """Nothing removes this from replies, so it mustn't be requested."""
        assert "STATUS: COMPLETE" not in INPUT_REQUEST_GUIDANCE


class TestPromptSentToTheLlm:
    def test_a_step_that_can_pause_is_told_how(self, monkeypatch: pytest.MonkeyPatch) -> None:
        sent = _prompt_sent(monkeypatch, can_request_input=True)
        assert sent == PROMPT + INPUT_REQUEST_GUIDANCE

    def test_other_steps_are_unchanged(self, monkeypatch: pytest.MonkeyPatch) -> None:
        assert _prompt_sent(monkeypatch) == PROMPT

    def test_a_step_prompt_override_is_covered(self, monkeypatch: pytest.MonkeyPatch) -> None:
        sent = _prompt_sent(monkeypatch, can_request_input=True, system_prompt_override="Override.")
        assert sent == "Override." + INPUT_REQUEST_GUIDANCE


@pytest.mark.parametrize("can_pause", [True, False])
def test_the_cache_passes_the_step_setting_to_the_agent(
    monkeypatch: pytest.MonkeyPatch, can_pause: bool
) -> None:
    captured: dict[str, Any] = {}
    monkeypatch.setattr(
        agent_tools_module, "AgentTool", lambda **kwargs: captured.update(kwargs) or MagicMock()
    )
    monkeypatch.setattr(agent_tools_module, "load_step_agent", lambda *_: MagicMock(tools=[]))
    cache = AgentToolCache(db_session=MagicMock(), user=MagicMock(), emitter=MagicMock())
    monkeypatch.setattr(cache, "_llm_for", lambda *_: MagicMock())

    cache.get(
        MagicMock(node_key="a", can_request_input=can_pause),
        MagicMock(output_schema=None, tool_ids_override=None),
    )
    assert captured["can_request_input"] is can_pause
