"""Slack incoming-message handler for standard answers (clean-room).

Wired into the Slack message path (before the regular LLM answer): on an inbound
message it matches active answers in the channel's categories, skips any already
posted in the thread, posts the new ones as blocks with a "Generate Full Answer"
button, records a synthetic chat session/messages (so the thread has history and
future de-dup works), and clears the processing reaction.

``handle_standard_answers`` keeps the exact signature the listener already calls, so
integration is a one-line import repoint. ``oneoff_standard_answers`` is the
stateless variant behind the query endpoint.
"""

from __future__ import annotations

from collections.abc import Sequence

from slack_sdk import WebClient
from sqlalchemy.orm import Session

from om.configs.constants import MessageType
from om.configs.onyxbot_configs import OM_BOT_REACT_EMOJI
from om.db.chat import create_chat_session
from om.db.chat import create_new_chat_message
from om.db.chat import get_chat_messages_by_sessions
from om.db.chat import get_chat_sessions_by_slack_thread_id
from om.db.chat import get_or_create_root_message
from om.db.models import SlackChannelConfig
from om.db.models import StandardAnswer
from om.onyxbot.slack.models import SlackMessageInfo
from om.onyxbot.slack.utils import respond_in_thread_or_channel
from om.onyxbot.slack.utils import update_emote_react
from om.standard_answers.blocks import build_answer_blocks
from om.standard_answers.config import load_config
from om.standard_answers.schemas import StandardAnswer as StandardAnswerDTO
from om.standard_answers.service import StandardAnswerService
from om.utils.logger import OmLoggingAdapter


def _message_text(message_info: SlackMessageInfo) -> str:
    if not message_info.thread_messages:
        return ""
    return (message_info.thread_messages[-1].message or "").strip()


def _already_used_answer_ids(
    slack_thread_id: str, db_session: Session
) -> set[int]:
    """Ids of answers already posted anywhere in this Slack thread (for de-dup)."""

    sessions = get_chat_sessions_by_slack_thread_id(slack_thread_id, None, db_session)
    if not sessions:
        return set()
    messages = get_chat_messages_by_sessions(
        [s.id for s in sessions], None, db_session, skip_permission_check=True
    )
    used: set[int] = set()
    for message in messages:
        used.update(answer.id for answer in message.standard_answers)
    return used


def _record_synthetic_chat(
    message_info: SlackMessageInfo,
    slack_channel_config: SlackChannelConfig,
    message_text: str,
    answers: Sequence[StandardAnswer],
    db_session: Session,
) -> None:
    """Persist a user→assistant chat pair for the thread and link the posted answers.

    Reuses the thread's existing onyxbot chat session when present so a thread maps
    to a single session; the assistant message's ``standard_answers`` link is what a
    later message in the same thread reads to skip already-served answers.
    """

    slack_thread_id = message_info.thread_to_respond or message_info.msg_to_respond
    sessions = (
        get_chat_sessions_by_slack_thread_id(slack_thread_id, None, db_session)
        if slack_thread_id
        else []
    )
    if sessions:
        chat_session = sessions[-1]
    else:
        chat_session = create_chat_session(
            db_session=db_session,
            description=None,
            user_id=None,
            agent_id=slack_channel_config.agent_id,
            onyxbot_flow=True,
            slack_thread_id=slack_thread_id,
        )

    root_message = get_or_create_root_message(chat_session.id, db_session)
    user_message = create_new_chat_message(
        chat_session_id=chat_session.id,
        parent_message=root_message,
        message=message_text,
        token_count=0,
        message_type=MessageType.USER,
        db_session=db_session,
        commit=False,
    )
    assistant_message = create_new_chat_message(
        chat_session_id=chat_session.id,
        parent_message=user_message,
        message="\n\n".join(answer.answer for answer in answers),
        token_count=0,
        message_type=MessageType.ASSISTANT,
        db_session=db_session,
        commit=False,
    )
    assistant_message.standard_answers = list(answers)
    db_session.commit()


def handle_standard_answers(
    message_info: SlackMessageInfo,
    receiver_ids: list[str] | None,
    slack_channel_config: SlackChannelConfig,
    logger: OmLoggingAdapter,
    client: WebClient,
    db_session: Session,
) -> bool:
    """Post matching standard answer(s) if any apply; return whether one was posted.

    Returning True suppresses the regular LLM answer for this message.
    """

    config = load_config(db_session)
    if not config.enabled:
        return False

    message_text = _message_text(message_info)
    if not message_text:
        return False

    category_ids = [c.id for c in slack_channel_config.standard_answer_categories]
    if not category_ids:
        return False

    service = StandardAnswerService(db_session)
    # Truncate before matching — defence-in-depth against pathological input length.
    candidate_text = message_text[: config.match_input_char_limit]
    matches = service.match_by_category_ids(candidate_text, category_ids)
    if not matches:
        return False

    slack_thread_id = message_info.thread_to_respond or message_info.msg_to_respond
    used_ids = (
        _already_used_answer_ids(slack_thread_id, db_session)
        if slack_thread_id
        else set()
    )
    new_answers = [answer for answer in matches if answer.id not in used_ids]
    if not new_answers:
        # Everything that matched was already posted in this thread — let the regular
        # answer flow decide what to do with the repeat.
        return False

    new_answers = new_answers[: max(0, config.max_matches_per_message)]
    if not new_answers:
        # Guard against a misconfigured (<=0) cap so we never post an empty message.
        return False

    try:
        respond_in_thread_or_channel(
            client=client,
            channel=message_info.channel_to_respond,
            thread_ts=message_info.msg_to_respond,
            blocks=build_answer_blocks(new_answers),
            receiver_ids=receiver_ids,
        )
    except Exception:
        logger.exception("Failed to post standard answer(s) to Slack")
        return False

    # Posted successfully — record history and clear the reaction best-effort; a
    # failure here must not cause a second (regular) answer, so we still return True.
    try:
        _record_synthetic_chat(
            message_info, slack_channel_config, message_text, new_answers, db_session
        )
    except Exception:
        logger.exception("Failed to record standard-answer chat session")
        db_session.rollback()

    if not message_info.is_slash_command:
        try:
            update_emote_react(
                emoji=OM_BOT_REACT_EMOJI,
                channel=message_info.channel_to_respond,
                message_ts=message_info.msg_to_respond,
                remove=True,
                client=client,
            )
        except Exception:
            logger.exception("Failed to clear standard-answer reaction")

    return True


def oneoff_standard_answers(
    message: str,
    slack_bot_categories: list[str],
    db_session: Session,
) -> list[StandardAnswerDTO]:
    """Stateless match by category name — powers ``GET /query/standard-answer``.

    No Slack side effects and no chat records.
    """

    service = StandardAnswerService(db_session)
    matches = service.match_by_category_names(message, slack_bot_categories)
    return [StandardAnswerDTO.from_model(answer) for answer in matches]
