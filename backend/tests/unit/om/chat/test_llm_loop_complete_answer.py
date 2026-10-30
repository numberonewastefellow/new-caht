"""run_llm_loop (public chat entry) with a mock LLM step: the complete-answer
texts appear only once a search tool ran (or the turn cites workspace files),
and replace-prompt agents get the reminder but not the system-prompt guidance.

This is the path used by web chat, Slack/ombot, Pulse and the eval harness
(all go through stream_chat_message -> run_llm_loop)."""

from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from om.chat.llm_loop import run_llm_loop
from om.chat.models import ChatMessageSimple
from om.chat.models import ExtractedWorkspaceFiles
from om.chat.models import LlmStepResult
from om.configs.constants import MessageType
from om.prompts.chat_prompts import CITATION_REMINDER
from om.prompts.chat_prompts import COMPLETE_ANSWER_REMINDER
from om.prompts.chat_prompts import DEFAULT_SYSTEM_PROMPT
from om.prompts.chat_prompts import MULTI_PART_ANSWER_GUIDANCE
from om.prompts.chat_prompts import REQUIRE_CITATION_GUIDANCE
from om.server.query_and_chat.placement import Placement
from om.tools.models import ParallelToolCallResponse
from om.tools.models import ToolCallKickoff
from om.tools.models import ToolResponse
from om.tools.tool_implementations.search.search_tool import SearchTool

_LOOP = "om.chat.llm_loop"
_FLAG = "om.prompts.prompt_utils.ENABLE_COMPLETE_ANSWER_PROMPTS"


def _workspace_files(num_files: int = 0) -> ExtractedWorkspaceFiles:
    return ExtractedWorkspaceFiles(
        workspace_file_texts=[f"file {i}" for i in range(num_files)],
        workspace_image_files=[],
        workspace_as_filter=False,
        total_token_count=10 * num_files,
        workspace_file_metadata=[],
        workspace_uncapped_token_count=10 * num_files,
    )


def _search_tool() -> MagicMock:
    tool = MagicMock(spec=SearchTool)
    tool.name = SearchTool.NAME
    tool.id = 1
    tool.tool_definition.return_value = {"type": "function"}
    return tool


def _search_call() -> ToolCallKickoff:
    return ToolCallKickoff(
        tool_call_id="call_1",
        tool_name=SearchTool.NAME,
        tool_args={"queries": ["q"]},
        placement=Placement(turn_index=0),
    )


class _Captured:
    def __init__(self) -> None:
        self.system: list[str | None] = []
        self.reminders: list[str | None] = []

    def construct_message_history(self, **kwargs: Any) -> list[ChatMessageSimple]:
        sp = kwargs["system_prompt"]
        rm = kwargs["reminder_message"]
        self.system.append(sp.message if sp else None)
        self.reminders.append(rm.message if rm else None)
        return list(kwargs["simple_chat_history"])


def _run(
    *,
    agent: Any = None,
    search_first: bool,
    workspace_files: ExtractedWorkspaceFiles | None = None,
) -> _Captured:
    captured = _Captured()
    steps = []
    if search_first:
        steps.append(
            LlmStepResult(reasoning=None, answer=None, tool_calls=[_search_call()])
        )
    steps.append(LlmStepResult(reasoning=None, answer="final", tool_calls=None))
    step_iter = iter(steps)

    def fake_run_tool_calls(**kwargs: Any) -> ParallelToolCallResponse:
        calls = kwargs["tool_calls"]
        return ParallelToolCallResponse(
            tool_responses=[
                ToolResponse(
                    rich_response="docs",
                    llm_facing_response='{"results": []}',
                    tool_call=c,
                )
                for c in calls
            ],
            updated_citation_mapping={},
        )

    llm = MagicMock()
    llm.config = SimpleNamespace(max_input_tokens=100_000, model_provider="openai")
    history = [
        ChatMessageSimple(
            message="What is X and how much does it cost?",
            token_count=10,
            message_type=MessageType.USER,
        )
    ]
    with (
        patch(
            f"{_LOOP}.get_default_base_system_prompt",
            return_value=DEFAULT_SYSTEM_PROMPT,
        ),
        patch("om.chat.prompt_utils.get_company_context", return_value=None),
        patch(
            f"{_LOOP}.construct_message_history",
            side_effect=captured.construct_message_history,
        ),
        patch(
            f"{_LOOP}.run_llm_step",
            side_effect=lambda **_: (next(step_iter), False),
        ),
        patch(f"{_LOOP}.run_tool_calls", side_effect=fake_run_tool_calls),
        patch(f"{_LOOP}.update_citation_processor_from_tool_response"),
        patch("om.llm.litellm_singleton.config.initialize_litellm"),
    ):
        run_llm_loop(
            emitter=MagicMock(),
            state_container=MagicMock(),
            simple_chat_history=history,
            tools=[_search_tool()],
            custom_agent_prompt=None,
            workspace_files=workspace_files or _workspace_files(),
            agent=agent,
            user_memory_context=None,
            llm=llm,
            token_counter=lambda s: len(s) // 4,
            db_session=MagicMock(),
        )
    return captured


@pytest.fixture
def flag_on() -> Iterator[None]:
    with patch(_FLAG, True):
        yield


def _agent(
    *, replace: bool, system_prompt: str = "", task_prompt: str | None = None
) -> SimpleNamespace:
    return SimpleNamespace(
        replace_base_system_prompt=replace,
        system_prompt=system_prompt,
        task_prompt=task_prompt,
        datetime_aware=True,
        max_output_tokens=None,
    )


@pytest.mark.usefixtures("flag_on")
def test_first_turn_without_search_has_no_texts() -> None:
    cap = _run(search_first=False)
    assert len(cap.system) == 1
    assert MULTI_PART_ANSWER_GUIDANCE not in (cap.system[0] or "")
    assert cap.reminders[0] is None


@pytest.mark.parametrize(
    "agent",
    [None, _agent(replace=False), _agent(replace=False, task_prompt="Be brief.")],
    ids=["no-agent", "default-prompt-agent", "task-prompt-agent"],
)
@pytest.mark.usefixtures("flag_on")
def test_after_search_both_texts_present(agent: Any) -> None:
    cap = _run(agent=agent, search_first=True)
    assert len(cap.system) == 2
    # cycle 1: before any search
    assert MULTI_PART_ANSWER_GUIDANCE not in (cap.system[0] or "")
    assert COMPLETE_ANSWER_REMINDER not in (cap.reminders[0] or "")
    # cycle 2: answering after a search
    system, reminder = cap.system[1] or "", cap.reminders[1] or ""
    assert REQUIRE_CITATION_GUIDANCE + MULTI_PART_ANSWER_GUIDANCE in system
    assert reminder.index(CITATION_REMINDER) < reminder.index(COMPLETE_ANSWER_REMINDER)
    if agent is not None and agent.task_prompt:
        assert reminder.startswith(agent.task_prompt)


@pytest.mark.usefixtures("flag_on")
def test_replace_prompt_agent_gets_reminder_only() -> None:
    agent = _agent(replace=True, system_prompt="Own prompt, fully owned by admin.")
    cap = _run(agent=agent, search_first=True)
    assert cap.system[1] == "Own prompt, fully owned by admin."
    assert COMPLETE_ANSWER_REMINDER in (cap.reminders[1] or "")


@pytest.mark.usefixtures("flag_on")
def test_workspace_turn_cites_without_search() -> None:
    cap = _run(search_first=False, workspace_files=_workspace_files(num_files=2))
    assert MULTI_PART_ANSWER_GUIDANCE in (cap.system[0] or "")
    assert COMPLETE_ANSWER_REMINDER in (cap.reminders[0] or "")


def test_flag_off_matches_previous_behaviour() -> None:
    with patch(_FLAG, False):
        cap = _run(search_first=True)
    assert MULTI_PART_ANSWER_GUIDANCE not in (cap.system[1] or "")
    assert REQUIRE_CITATION_GUIDANCE in (cap.system[1] or "")
    assert cap.reminders[1] == CITATION_REMINDER
