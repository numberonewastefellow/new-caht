"""Handler orchestration tests: config gate, matching, thread de-dup, post, react,
and synthetic chat recording. The Slack client and chat-recording DB helpers are
stubbed (monkeypatched) so we can drive the real matching service on SQLite without
the full chat schema or a live Slack workspace.
"""

import uuid
from collections.abc import Iterator
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import om.standard_answers.slack_handler as handler_mod
from om.configs.constants import MessageType
from om.db.models import ChatMessage__StandardAnswer
from om.db.models import SlackChannelConfig__StandardAnswerCategory
from om.db.models import StandardAnswer__StandardAnswerCategory
from om.db.models import StandardAnswerCategory
from om.db.models import StandardAnswer as StandardAnswerModel
from om.db.models import StandardAnswerConfig
from om.onyxbot.slack.models import SlackMessageInfo
from om.onyxbot.slack.models import ThreadMessage
from om.standard_answers.service import StandardAnswerService


@pytest.fixture
def db_session() -> Iterator[Session]:
    engine = create_engine("sqlite://")
    for table in (
        StandardAnswerCategory.__table__,
        StandardAnswerModel.__table__,
        StandardAnswer__StandardAnswerCategory.__table__,
        SlackChannelConfig__StandardAnswerCategory.__table__,
        ChatMessage__StandardAnswer.__table__,
        StandardAnswerConfig.__table__,
    ):
        table.create(bind=engine, checkfirst=True)
    with Session(engine) as session:
        yield session


@pytest.fixture
def seeded(db_session: Session) -> tuple[Session, int]:
    service = StandardAnswerService(db_session)
    cat = service.create_category("Support")
    service.create_answer(
        keyword="vpn",
        answer="Reconnect your VPN from the tray icon.",
        category_ids=[cat.id],
        match_regex=False,
        match_any_keywords=True,
    )
    return db_session, cat.id


def _message_info(text: str, *, thread: str | None = "1700000000.0001") -> SlackMessageInfo:
    return SlackMessageInfo(
        thread_messages=[ThreadMessage(message=text, sender=None, role=MessageType.USER)],
        channel_to_respond="C123",
        msg_to_respond="1700000000.0001",
        thread_to_respond=thread,
        sender_id="U123",
        email=None,
        bypass_filters=False,
        is_slash_command=False,
        is_bot_dm=False,
    )


def _channel_config(category_id: int) -> SimpleNamespace:
    category = SimpleNamespace(id=category_id, name="Support")
    return SimpleNamespace(standard_answer_categories=[category], agent_id=None)


def _install_stubs(
    monkeypatch: pytest.MonkeyPatch,
    *,
    prior_used_answers: list[int] | None = None,
) -> dict[str, MagicMock]:
    """Stub Slack + chat-recording I/O; return the mocks for assertions."""

    posted = MagicMock(name="respond_in_thread_or_channel", return_value=["ts1"])
    reacted = MagicMock(name="update_emote_react")
    monkeypatch.setattr(handler_mod, "respond_in_thread_or_channel", posted)
    monkeypatch.setattr(handler_mod, "update_emote_react", reacted)

    # Thread history: a prior session whose messages already linked some answers.
    if prior_used_answers:
        prior_session = SimpleNamespace(id=uuid.uuid4())
        prior_messages = [
            SimpleNamespace(
                standard_answers=[SimpleNamespace(id=aid) for aid in prior_used_answers]
            )
        ]
        monkeypatch.setattr(
            handler_mod,
            "get_chat_sessions_by_slack_thread_id",
            MagicMock(return_value=[prior_session]),
        )
        monkeypatch.setattr(
            handler_mod,
            "get_chat_messages_by_sessions",
            MagicMock(return_value=prior_messages),
        )
    else:
        monkeypatch.setattr(
            handler_mod,
            "get_chat_sessions_by_slack_thread_id",
            MagicMock(return_value=[]),
        )
        monkeypatch.setattr(
            handler_mod,
            "get_chat_messages_by_sessions",
            MagicMock(return_value=[]),
        )

    created_session = SimpleNamespace(id=uuid.uuid4())
    root = SimpleNamespace(id=1)
    recorded_msg = SimpleNamespace(standard_answers=None)
    monkeypatch.setattr(
        handler_mod, "create_chat_session", MagicMock(return_value=created_session)
    )
    monkeypatch.setattr(
        handler_mod, "get_or_create_root_message", MagicMock(return_value=root)
    )
    monkeypatch.setattr(
        handler_mod, "create_new_chat_message", MagicMock(return_value=recorded_msg)
    )
    return {"posted": posted, "reacted": reacted, "recorded_msg": recorded_msg}


def _call(session: Session, message_info: SlackMessageInfo, category_id: int) -> bool:
    return handler_mod.handle_standard_answers(
        message_info=message_info,
        receiver_ids=None,
        slack_channel_config=_channel_config(category_id),
        logger=MagicMock(),
        client=MagicMock(),
        db_session=session,
    )


class TestHandlerHappyPath:
    def test_posts_records_and_reacts(
        self, seeded: tuple[Session, int], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        session, category_id = seeded
        mocks = _install_stubs(monkeypatch)

        result = _call(session, _message_info("my vpn is down"), category_id)

        assert result is True
        # posted with blocks to the right channel/thread
        assert mocks["posted"].call_count == 1
        _, kwargs = mocks["posted"].call_args
        assert kwargs["channel"] == "C123"
        assert kwargs["thread_ts"] == "1700000000.0001"
        assert kwargs["blocks"]  # non-empty block list
        # synthetic chat recorded: the assistant message got the answers linked
        assert mocks["recorded_msg"].standard_answers is not None
        assert len(mocks["recorded_msg"].standard_answers) == 1
        # processing reaction cleared
        assert mocks["reacted"].call_count == 1
        assert mocks["reacted"].call_args.kwargs["remove"] is True


class TestNoMatch:
    def test_no_keyword_match_returns_false(
        self, seeded: tuple[Session, int], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        session, category_id = seeded
        mocks = _install_stubs(monkeypatch)
        result = _call(session, _message_info("everything is fine"), category_id)
        assert result is False
        mocks["posted"].assert_not_called()

    def test_disabled_config_short_circuits(
        self, seeded: tuple[Session, int], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        session, category_id = seeded
        StandardAnswerService(session).update_config(enabled=False)
        mocks = _install_stubs(monkeypatch)
        result = _call(session, _message_info("my vpn is down"), category_id)
        assert result is False
        mocks["posted"].assert_not_called()


class TestThreadDedup:
    def test_skips_answer_already_used_in_thread(
        self, seeded: tuple[Session, int], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        session, category_id = seeded
        # The only matching answer has id=1; mark it already-used in the thread.
        mocks = _install_stubs(monkeypatch, prior_used_answers=[1])
        result = _call(session, _message_info("my vpn is down"), category_id)
        # Nothing new to post → handler declines so the regular flow can decide.
        assert result is False
        mocks["posted"].assert_not_called()
