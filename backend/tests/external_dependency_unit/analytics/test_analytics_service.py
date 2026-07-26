"""Real-DB tests for :class:`om.server.analytics.service.AnalyticsService` (WS-H).

These run against the live Postgres used by the ``external_dependency_unit`` tier
(the ``db_session`` fixture from ``tests/external_dependency_unit/conftest.py``).
We seed ``ChatSession`` / ``ChatMessage`` / ``ChatMessageFeedback`` rows directly
through the ORM and assert the aggregation queries return exactly the expected
daily series and window totals.

Isolation strategy
------------------
The daily-usage / summary / top-agents queries aggregate over *all* rows in the
time window, so to avoid colliding with any real chat data (or with a previous
run of this test) we seed into a fixed, far-past window in the year 1990 and
delete every row we create in fixture teardown.
"""

import datetime
from collections.abc import Generator
from dataclasses import dataclass
from dataclasses import field
from uuid import uuid4

import pytest
from fastapi_users.password import PasswordHelper
from sqlalchemy.orm import Session

from om.configs.constants import MessageType
from om.db.models import Agent
from om.db.models import ChatMessage
from om.db.models import ChatMessageFeedback
from om.db.models import ChatSession
from om.db.models import RecencyBiasSetting
from om.db.models import User
from om.db.models import UserRole
from om.server.analytics.service import AnalyticsService
from om.server.analytics.service import user_can_view_assistant_stats


# Fixed, collision-free aggregation window (no real chat data lives in 1990).
WINDOW_START = datetime.datetime(1990, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
WINDOW_END = datetime.datetime(1990, 1, 31, 23, 59, 59, tzinfo=datetime.timezone.utc)
DAY_1 = datetime.date(1990, 1, 10)
DAY_2 = datetime.date(1990, 1, 11)


def _dt(day: datetime.date, hour: int) -> datetime.datetime:
    return datetime.datetime(
        day.year, day.month, day.day, hour, 0, 0, tzinfo=datetime.timezone.utc
    )


@dataclass
class SeededAnalytics:
    admin: User
    user1: User
    user2: User
    agent_a: Agent
    agent_b: Agent
    # bookkeeping for teardown
    user_ids: list = field(default_factory=list)
    agent_ids: list = field(default_factory=list)
    session_ids: list = field(default_factory=list)
    message_ids: list = field(default_factory=list)
    feedback_ids: list = field(default_factory=list)


def _make_user(db_session: Session, prefix: str, role: UserRole) -> User:
    helper = PasswordHelper()
    user = User(
        id=uuid4(),
        email=f"{prefix}_{uuid4().hex[:8]}@analytics.test",
        hashed_password=helper.hash(helper.generate()),
        is_active=True,
        is_superuser=False,
        is_verified=True,
        role=role,
    )
    db_session.add(user)
    db_session.flush()
    return user


def _make_agent(db_session: Session, name: str, owner: User) -> Agent:
    agent = Agent(
        user_id=owner.id,
        name=name,
        description="analytics test agent",
        num_chunks=10,
        chunks_above=0,
        chunks_below=0,
        llm_relevance_filter=False,
        llm_filter_extraction=False,
        recency_bias=RecencyBiasSetting.AUTO,
    )
    db_session.add(agent)
    db_session.flush()
    return agent


def _make_session(db_session: Session, user: User, agent: Agent) -> ChatSession:
    session = ChatSession(
        id=uuid4(),
        user_id=user.id,
        agent_id=agent.id,
        description="analytics test session",
    )
    db_session.add(session)
    db_session.flush()
    return session


def _make_msg(
    db_session: Session,
    session: ChatSession,
    when: datetime.datetime,
    message_type: MessageType,
    latency: float | None,
) -> ChatMessage:
    msg = ChatMessage(
        chat_session_id=session.id,
        message="hello" if message_type == MessageType.USER else "hi there",
        token_count=3,
        message_type=message_type,
        time_sent=when,
        processing_duration_seconds=latency,
    )
    db_session.add(msg)
    db_session.flush()
    return msg


def _make_feedback(
    db_session: Session, msg: ChatMessage, is_positive: bool
) -> ChatMessageFeedback:
    fb = ChatMessageFeedback(chat_message_id=msg.id, is_positive=is_positive)
    db_session.add(fb)
    db_session.flush()
    return fb


@pytest.fixture(scope="function")
def seeded(db_session: Session) -> Generator[SeededAnalytics, None, None]:
    """Seed a deterministic set of assistant messages + feedback and clean up.

    Layout (all assistant messages unless noted):

      Agent A (owner=user1):
        D1: m1 (user1, latency 1.0s)  -> like
            m2 (user1, latency 3.0s)  -> dislike
            m3 (user2, latency 2.0s)  -> like
        D2: m4 (user1, latency 5.0s)  -> like
      Agent B (owner=user2):
        D1: m5 (user2, latency 10.0s) -> (no feedback)

      Plus one USER-type message on D1 that MUST be ignored by every query.
    """
    admin = _make_user(db_session, "admin", UserRole.ADMIN)
    user1 = _make_user(db_session, "u1", UserRole.BASIC)
    user2 = _make_user(db_session, "u2", UserRole.BASIC)

    agent_a = _make_agent(db_session, f"AgentA_{uuid4().hex[:6]}", owner=user1)
    agent_b = _make_agent(db_session, f"AgentB_{uuid4().hex[:6]}", owner=user2)

    s1 = _make_session(db_session, user1, agent_a)
    s2 = _make_session(db_session, user2, agent_a)
    s3 = _make_session(db_session, user1, agent_a)
    s4 = _make_session(db_session, user2, agent_b)

    # USER-type message: must be excluded from all assistant aggregations.
    _make_msg(db_session, s1, _dt(DAY_1, 8), MessageType.USER, None)

    m1 = _make_msg(db_session, s1, _dt(DAY_1, 10), MessageType.ASSISTANT, 1.0)
    m2 = _make_msg(db_session, s1, _dt(DAY_1, 11), MessageType.ASSISTANT, 3.0)
    m3 = _make_msg(db_session, s2, _dt(DAY_1, 12), MessageType.ASSISTANT, 2.0)
    m4 = _make_msg(db_session, s3, _dt(DAY_2, 10), MessageType.ASSISTANT, 5.0)
    m5 = _make_msg(db_session, s4, _dt(DAY_1, 9), MessageType.ASSISTANT, 10.0)

    f1 = _make_feedback(db_session, m1, True)
    f2 = _make_feedback(db_session, m2, False)
    f3 = _make_feedback(db_session, m3, True)
    f4 = _make_feedback(db_session, m4, True)

    db_session.commit()

    data = SeededAnalytics(
        admin=admin,
        user1=user1,
        user2=user2,
        agent_a=agent_a,
        agent_b=agent_b,
        user_ids=[admin.id, user1.id, user2.id],
        agent_ids=[agent_a.id, agent_b.id],
        session_ids=[s1.id, s2.id, s3.id, s4.id],
        message_ids=[m1.id, m2.id, m3.id, m4.id, m5.id],
        feedback_ids=[f1.id, f2.id, f3.id, f4.id],
    )
    try:
        yield data
    finally:
        # Teardown in FK-safe order: feedback -> messages -> sessions -> agents -> users.
        db_session.rollback()
        db_session.query(ChatMessageFeedback).filter(
            ChatMessageFeedback.id.in_(data.feedback_ids)
        ).delete(synchronize_session=False)
        db_session.query(ChatMessage).filter(
            ChatMessage.chat_session_id.in_(data.session_ids)
        ).delete(synchronize_session=False)
        db_session.query(ChatSession).filter(
            ChatSession.id.in_(data.session_ids)
        ).delete(synchronize_session=False)
        db_session.query(Agent).filter(
            Agent.id.in_(data.agent_ids)
        ).delete(synchronize_session=False)
        db_session.query(User).filter(
            User.id.in_(data.user_ids)
        ).delete(synchronize_session=False)
        db_session.commit()


def test_get_daily_usage(db_session: Session, seeded: SeededAnalytics) -> None:
    svc = AnalyticsService(db_session)
    points = svc.get_daily_usage(WINDOW_START, WINDOW_END)
    by_day = {p.date: p for p in points}

    assert set(by_day) == {DAY_1, DAY_2}

    d1 = by_day[DAY_1]
    assert d1.total_queries == 4  # m1,m2,m3,m5
    assert d1.active_users == 2  # user1, user2
    assert d1.likes == 2  # m1, m3
    assert d1.dislikes == 1  # m2
    assert d1.avg_latency_ms == 4000.0  # (1+3+2+10)/4 = 4.0s

    d2 = by_day[DAY_2]
    assert d2.total_queries == 1  # m4
    assert d2.active_users == 1  # user1
    assert d2.likes == 1  # m4
    assert d2.dislikes == 0
    assert d2.avg_latency_ms == 5000.0

    # Days are returned in ascending order.
    assert [p.date for p in points] == sorted(p.date for p in points)


def test_get_summary(db_session: Session, seeded: SeededAnalytics) -> None:
    svc = AnalyticsService(db_session)
    summary = svc.get_summary(WINDOW_START, WINDOW_END)

    assert summary.total_queries == 5  # m1..m5 assistant messages
    assert summary.total_active_users == 2  # user1, user2
    assert summary.total_likes == 3  # m1, m3, m4
    assert summary.total_dislikes == 1  # m2
    # (1+3+2+5+10)/5 = 4.2s -> 4200 ms
    assert summary.avg_latency_ms == 4200.0


def test_get_top_agents(db_session: Session, seeded: SeededAnalytics) -> None:
    svc = AnalyticsService(db_session)
    top = svc.get_top_agents(WINDOW_START, WINDOW_END, limit=10)
    by_name = {p.agent_name: p.total_messages for p in top}

    assert by_name[seeded.agent_a.name] == 4  # m1,m2,m3,m4
    assert by_name[seeded.agent_b.name] == 1  # m5

    # Agent A (4 messages) must rank strictly before Agent B (1 message).
    names_in_order = [p.agent_name for p in top]
    assert names_in_order.index(seeded.agent_a.name) < names_in_order.index(
        seeded.agent_b.name
    )

    # limit is honored: only the single busiest agent comes back.
    top1 = svc.get_top_agents(WINDOW_START, WINDOW_END, limit=1)
    assert len(top1) == 1
    assert top1[0].agent_name == seeded.agent_a.name
    assert top1[0].total_messages == 4


def test_get_assistant_stats(db_session: Session, seeded: SeededAnalytics) -> None:
    svc = AnalyticsService(db_session)
    stats = svc.get_assistant_stats(seeded.agent_a.id, WINDOW_START, WINDOW_END)

    by_day = {p.date: p for p in stats.daily_stats}
    assert set(by_day) == {DAY_1, DAY_2}

    assert by_day[DAY_1].total_messages == 3  # m1,m2,m3
    assert by_day[DAY_1].total_unique_users == 2  # user1, user2
    assert by_day[DAY_2].total_messages == 1  # m4
    assert by_day[DAY_2].total_unique_users == 1  # user1

    # Window totals are computed independently of the per-day rows.
    assert stats.total_messages == 4  # m1..m4
    assert stats.total_unique_users == 2  # user1, user2

    # Daily rows are ordered by day ascending.
    assert [p.date for p in stats.daily_stats] == sorted(
        p.date for p in stats.daily_stats
    )

    # Agent B: only m5 on D1 by user2.
    stats_b = svc.get_assistant_stats(seeded.agent_b.id, WINDOW_START, WINDOW_END)
    assert stats_b.total_messages == 1
    assert stats_b.total_unique_users == 1


def test_user_can_view_assistant_stats(
    db_session: Session, seeded: SeededAnalytics
) -> None:
    # Admin may view any assistant's stats.
    assert user_can_view_assistant_stats(
        db_session, seeded.admin, seeded.agent_a.id
    )
    assert user_can_view_assistant_stats(
        db_session, seeded.admin, seeded.agent_b.id
    )

    # Owner may view their own assistant's stats.
    assert user_can_view_assistant_stats(
        db_session, seeded.user1, seeded.agent_a.id
    )
    assert user_can_view_assistant_stats(
        db_session, seeded.user2, seeded.agent_b.id
    )

    # A non-owner, non-admin user may NOT view someone else's assistant stats.
    assert not user_can_view_assistant_stats(
        db_session, seeded.user2, seeded.agent_a.id
    )
    assert not user_can_view_assistant_stats(
        db_session, seeded.user1, seeded.agent_b.id
    )
