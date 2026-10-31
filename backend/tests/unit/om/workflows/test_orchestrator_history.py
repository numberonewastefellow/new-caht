"""The orchestrator must see what its agents returned (``llm_decision`` mode)."""

import json
from types import SimpleNamespace
from typing import Any

from om.chat.llm_loop import construct_message_history
from om.chat.llm_step import translate_history_to_llm_format
from om.chat.models import ChatMessageSimple
from om.configs.constants import MessageType
from om.workflows.orchestrator_history import agent_call
from om.workflows.orchestrator_history import agent_result
from om.workflows.orchestrator_history import restore_history
from om.workflows.orchestrator_history import serialize_history


def _count(text: str) -> int:
    return len(text.split())


def _user(text: str = "I was charged twice") -> ChatMessageSimple:
    return ChatMessageSimple(message=text, token_count=3, message_type=MessageType.USER)


def _sent_to_llm(history: list[ChatMessageSimple]) -> list[Any]:
    """The messages the orchestrator's LLM really receives."""
    constructed = construct_message_history(
        system_prompt=ChatMessageSimple(
            message="You are an orchestrator",
            token_count=4,
            message_type=MessageType.SYSTEM,
        ),
        custom_agent_prompt=None,
        simple_chat_history=history,
        reminder_message=None,
        workspace_files=None,
        available_tokens=10_000,
    )
    config = SimpleNamespace(model_provider="openai", model_name="gpt-4o-mini")
    return list(translate_history_to_llm_format(constructed, config))  # type: ignore[arg-type]


def _delegation(call_id: str = "call_1", output: str = "Refund takes 5 days") -> list[ChatMessageSimple]:
    return [
        agent_call(call_id, "delegate_to_billing", {"task": "refund"}, _count),
        agent_result(call_id, output, _count),
    ]


class TestTheOrchestratorSeesAgentResults:
    def test_agent_output_reaches_the_llm(self) -> None:
        messages = _sent_to_llm([_user(), *_delegation()])
        assert [m.role for m in messages] == ["system", "user", "assistant", "tool"]
        assert messages[-1].content == "Refund takes 5 days"
        assert messages[-1].tool_call_id == "call_1"

    def test_the_call_is_a_real_tool_call_not_text_to_imitate(self) -> None:
        call = _sent_to_llm([_user(), *_delegation()])[2]
        assert call.tool_calls[0].id == "call_1"
        assert call.tool_calls[0].function.name == "delegate_to_billing"
        assert json.loads(call.tool_calls[0].function.arguments) == {"task": "refund"}
        assert "tool_call_id" not in (call.content or "")

    def test_several_agents_stay_in_order(self) -> None:
        history = [
            _user(),
            *_delegation("call_1", "Billing answer"),
            *_delegation("call_2", "FAQ answer"),
        ]
        contents = [m.content for m in _sent_to_llm(history) if m.role == "tool"]
        assert contents == ["Billing answer", "FAQ answer"]


class TestCheckpointRoundTrip:
    def test_restores_what_was_saved(self) -> None:
        history = [_user(), *_delegation()]
        assert restore_history(serialize_history(history)) == history

    def test_saved_form_is_json(self) -> None:
        json.dumps(serialize_history([_user(), *_delegation()]))

    def test_a_restored_history_still_reaches_the_llm(self) -> None:
        restored = restore_history(serialize_history([_user(), *_delegation()]))
        assert _sent_to_llm(restored)[-1].content == "Refund takes 5 days"


class TestPausedAgents:
    def test_a_call_waiting_for_the_user_is_removed_on_resume(self) -> None:
        paused = [
            _user(),
            *_delegation("call_1", "Done"),
            agent_call("call_2", "delegate_to_intake", {"task": "ask"}, _count),
        ]
        restored = restore_history(serialize_history(paused))
        assert restored == [_user(), *_delegation("call_1", "Done")]

    def test_resuming_records_the_agent_again_with_its_answer(self) -> None:
        restored = restore_history(
            serialize_history(
                [_user(), agent_call("call_1", "delegate_to_intake", {"task": "ask"}, _count)]
            )
        )
        restored += _delegation("resume_9_1", "Now I have what I need")
        messages = _sent_to_llm(restored)
        assert [m.role for m in messages] == ["system", "user", "assistant", "tool"]
        assert messages[-1].content == "Now I have what I need"


class TestCheckpointsFromBeforeCallsWereLinked:
    @staticmethod
    def _old_call(call_id: str = "call_1", name: str = "delegate_to_billing") -> dict[str, Any]:
        return {
            "message": json.dumps(
                {"tool_call_id": call_id, "name": name, "arguments": {"task": "refund"}}
            ),
            "token_count": 50,
            "message_type": "assistant",
        }

    @staticmethod
    def _old_result(text: str = "Old answer") -> dict[str, Any]:
        return {"message": text, "token_count": 2, "message_type": "tool_call_response"}

    def test_an_old_paused_run_reaches_the_llm_correctly(self) -> None:
        restored = restore_history(
            [
                {"message": "Hello", "token_count": 1, "message_type": "user"},
                self._old_call("call_1"),
                self._old_result("First answer"),
                self._old_call("call_2", "delegate_to_faq"),
                self._old_result("Second answer"),
            ]
        )
        messages = _sent_to_llm(restored)
        assert [m.role for m in messages] == [
            "system", "user", "assistant", "tool", "assistant", "tool",
        ]
        assert messages[3].tool_call_id == "call_1"
        assert messages[5].tool_call_id == "call_2"
        assert messages[5].content == "Second answer"

    def test_an_old_paused_call_is_removed(self) -> None:
        restored = restore_history(
            [
                {"message": "Hello", "token_count": 1, "message_type": "user"},
                self._old_call(),
            ]
        )
        assert [m.message_type for m in restored] == [MessageType.USER]

    def test_an_old_user_reply_stored_as_a_tool_response_becomes_a_user_message(self) -> None:
        restored = restore_history(
            [
                {"message": "Hello", "token_count": 1, "message_type": "user"},
                self._old_result("The user responded: yes"),
            ]
        )
        assert restored[-1].message_type == MessageType.USER
        assert restored[-1].message == "The user responded: yes"

    def test_ordinary_assistant_text_is_left_alone(self) -> None:
        text = '{"answer": "not a tool call"}'
        restored = restore_history(
            [{"message": text, "token_count": 1, "message_type": "assistant"}]
        )
        assert restored[0].message == text
        assert restored[0].tool_calls is None

    def test_corrupted_entries_are_skipped(self) -> None:
        restored = restore_history(
            [
                {"message": "Hello", "token_count": 1, "message_type": "user"},
                {"token_count": 1},
                {"message": "x", "token_count": 1, "message_type": "nonsense"},
            ]
        )
        assert [m.message for m in restored] == ["Hello"]
