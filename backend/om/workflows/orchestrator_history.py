"""The orchestrator's conversation in ``llm_decision`` mode.

The orchestrator decides what to do next from what its agents returned, so each
delegation is stored the way the LLM API expects: an assistant message carrying the
tool call, followed by a tool response with the same id. ``construct_message_history``
drops tool responses that aren't linked to a call, so an unlinked result never reaches
the LLM.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from om.chat.models import ChatMessageSimple
from om.chat.models import ToolCallSimple
from om.configs.constants import MessageType
from om.utils.logger import setup_logger

logger = setup_logger()

TokenCounter = Callable[[str], int]


def agent_call(
    tool_call_id: str,
    tool_name: str,
    arguments: dict[str, Any],
    token_counter: TokenCounter,
) -> ChatMessageSimple:
    """The orchestrator delegating to an agent."""
    token_count = token_counter(json.dumps(arguments))
    return ChatMessageSimple(
        message="",
        token_count=token_count,
        message_type=MessageType.ASSISTANT,
        tool_calls=[
            ToolCallSimple(
                tool_call_id=tool_call_id,
                tool_name=tool_name,
                tool_arguments=arguments,
                token_count=token_count,
            )
        ],
    )


def agent_result(
    tool_call_id: str, text: str, token_counter: TokenCounter
) -> ChatMessageSimple:
    """What an agent returned for the call with ``tool_call_id``."""
    return ChatMessageSimple(
        message=text,
        token_count=token_counter(text),
        message_type=MessageType.TOOL_CALL_RESPONSE,
        tool_call_id=tool_call_id,
    )


def serialize_history(history: list[ChatMessageSimple]) -> list[dict[str, Any]]:
    """The history as stored in a checkpoint."""
    return [
        message.model_dump(
            mode="json",
            include={
                "message",
                "token_count",
                "message_type",
                "tool_call_id",
                "tool_calls",
            },
            exclude_none=True,
        )
        for message in history
    ]


def restore_history(entries: list[dict[str, Any]]) -> list[ChatMessageSimple]:
    """Rebuild the history from a checkpoint.

    Checkpoints from before calls were linked to results are upgraded on read. A
    call still waiting for its result is removed: it belongs to the agent that paused
    for the user, and resuming records that agent's call again with the user's answer.
    Corrupted entries are skipped rather than failing the resume.
    """
    history: list[ChatMessageSimple] = []
    pending_call_id: str | None = None
    for entry in entries:
        try:
            message = _upgrade_call(ChatMessageSimple.model_validate(entry))
        except ValueError as e:
            logger.warning("Skipping corrupted history entry: %s (%s)", entry, e)
            continue
        if message.tool_calls:
            pending_call_id = message.tool_calls[-1].tool_call_id
        elif message.message_type == MessageType.TOOL_CALL_RESPONSE:
            message = _link_result(message, pending_call_id)
            pending_call_id = None
        history.append(message)
    return _without_unanswered_calls(history)


def _upgrade_call(message: ChatMessageSimple) -> ChatMessageSimple:
    """Older checkpoints stored a call as JSON text in an assistant message."""
    if message.message_type != MessageType.ASSISTANT or message.tool_calls:
        return message
    try:
        data = json.loads(message.message)
    except json.JSONDecodeError:
        return message
    if not isinstance(data, dict) or "tool_call_id" not in data or "name" not in data:
        return message
    return message.model_copy(
        update={
            "message": "",
            "tool_calls": [
                ToolCallSimple(
                    tool_call_id=data["tool_call_id"],
                    tool_name=data["name"],
                    tool_arguments=data.get("arguments") or {},
                    token_count=message.token_count,
                )
            ],
        }
    )


def _link_result(
    message: ChatMessageSimple, pending_call_id: str | None
) -> ChatMessageSimple:
    if message.tool_call_id:
        return message
    if pending_call_id:
        return message.model_copy(update={"tool_call_id": pending_call_id})
    # Older checkpoints stored the user's reply as a tool response with no call.
    return message.model_copy(update={"message_type": MessageType.USER})


def _without_unanswered_calls(
    history: list[ChatMessageSimple],
) -> list[ChatMessageSimple]:
    answered = {m.tool_call_id for m in history if m.tool_call_id}
    return [
        m
        for m in history
        if not m.tool_calls or all(c.tool_call_id in answered for c in m.tool_calls)
    ]
