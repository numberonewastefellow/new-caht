"""Tenant-scoped query-history service (clean-room rewrite).

Lists / inspects past chat sessions for admins and streams a CSV export. Operates
purely on the injected tenant-bound session, so all reads are confined to the
current tenant's Postgres schema. CSV export is synchronous streaming (paged
internally) — no Celery / file-store round-trip.
"""

import csv
import datetime
import io
from collections.abc import Generator
from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from sqlalchemy.orm import Session

from om.auth.users import get_display_email
from om.configs.constants import MessageType
from om.configs.constants import QAFeedbackType
from om.configs.constants import SessionType
from om.db.engine.sql_engine import get_session_with_tenant
from om.db.models import ChatMessage
from om.db.models import ChatMessageFeedback
from om.db.models import ChatSession
from om.server.query_history.schemas import ChatSessionDetail
from om.server.query_history.schemas import ChatSessionSummary
from om.server.query_history.schemas import PaginatedSessions
from om.server.query_history.schemas import QueryHistoryMessage

_CSV_HEADER = [
    "session_id",
    "message_pair",
    "user_message",
    "ai_response",
    "feedback",
    "feedback_text",
    "agent_name",
    "user_email",
    "flow_type",
    "time_created",
]

_EXPORT_PAGE_SIZE = 100


class QueryHistoryService:
    def __init__(self, db_session: Session) -> None:
        self._db = db_session

    # ------------------------------------------------------------------ #
    # Listing / detail
    # ------------------------------------------------------------------ #
    def list_sessions(
        self,
        page_num: int,
        page_size: int,
        feedback: QAFeedbackType | None,
        start: datetime.datetime | None,
        end: datetime.datetime | None,
    ) -> PaginatedSessions:
        conditions = self._filter_conditions(start, end, feedback)

        total = (
            self._db.scalar(
                select(func.count())
                .select_from(ChatSession)
                .where(*conditions)
            )
            or 0
        )

        id_subq = (
            select(ChatSession.id)
            .where(*conditions)
            .order_by(ChatSession.time_created.desc(), ChatSession.id)
            .limit(page_size)
            .offset(page_num * page_size)
            .subquery()
        )
        stmt = (
            select(ChatSession)
            .join(id_subq, ChatSession.id == id_subq.c.id)
            .options(
                joinedload(ChatSession.user),
                joinedload(ChatSession.agent),
                joinedload(ChatSession.messages).joinedload(
                    ChatMessage.chat_message_feedbacks
                ),
            )
            .order_by(ChatSession.time_created.desc(), ChatSession.id)
        )
        sessions = self._db.execute(stmt).unique().scalars().all()
        return PaginatedSessions(
            items=[self._to_summary(s) for s in sessions],
            total_items=int(total),
        )

    def get_detail(self, session_id: UUID) -> ChatSessionDetail | None:
        stmt = (
            select(ChatSession)
            .where(ChatSession.id == session_id)
            .options(
                joinedload(ChatSession.user),
                joinedload(ChatSession.agent),
                joinedload(ChatSession.messages).joinedload(
                    ChatMessage.chat_message_feedbacks
                ),
            )
        )
        session = self._db.execute(stmt).unique().scalar_one_or_none()
        if session is None:
            return None

        messages = [
            self._to_message(m)
            for m in sorted(session.messages, key=lambda m: m.id)
            if m.message_type != MessageType.SYSTEM
        ]
        return ChatSessionDetail(
            id=session.id,
            user_email=get_display_email(
                session.user.email if session.user else None
            ),
            name=session.description,
            agent_id=session.agent_id,
            agent_name=session.agent.name if session.agent else None,
            time_created=session.time_created,
            flow_type=(
                SessionType.SLACK if session.onyxbot_flow else SessionType.CHAT
            ),
            messages=messages,
        )

    # ------------------------------------------------------------------ #
    # CSV export (synchronous streaming)
    # ------------------------------------------------------------------ #
    def iter_csv(
        self, start: datetime.datetime | None, end: datetime.datetime | None
    ) -> Generator[str, None, None]:
        """Yield CSV lines of question/answer pairs across the time range."""
        yield self._csv_line(_CSV_HEADER)

        conditions = self._filter_conditions(start, end, None)
        page = 0
        while True:
            id_subq = (
                select(ChatSession.id)
                .where(*conditions)
                .order_by(ChatSession.time_created.asc(), ChatSession.id)
                .limit(_EXPORT_PAGE_SIZE)
                .offset(page * _EXPORT_PAGE_SIZE)
                .subquery()
            )
            stmt = (
                select(ChatSession)
                .join(id_subq, ChatSession.id == id_subq.c.id)
                .options(
                    joinedload(ChatSession.user),
                    joinedload(ChatSession.agent),
                    joinedload(ChatSession.messages).joinedload(
                        ChatMessage.chat_message_feedbacks
                    ),
                )
                .order_by(ChatSession.time_created.asc(), ChatSession.id)
            )
            sessions = self._db.execute(stmt).unique().scalars().all()
            if not sessions:
                break

            for session in sessions:
                for row in self._session_to_csv_rows(session):
                    yield self._csv_line(row)

            if len(sessions) < _EXPORT_PAGE_SIZE:
                break
            page += 1

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _filter_conditions(
        self,
        start: datetime.datetime | None,
        end: datetime.datetime | None,
        feedback: QAFeedbackType | None,
    ) -> list[Any]:
        conditions: list[Any] = []
        if start is not None:
            conditions.append(ChatSession.time_created >= start)
        if end is not None:
            conditions.append(ChatSession.time_created <= end)

        if feedback is not None:
            positive_sessions = (
                select(ChatMessage.chat_session_id)
                .join(
                    ChatMessageFeedback,
                    ChatMessageFeedback.chat_message_id == ChatMessage.id,
                )
                .where(ChatMessageFeedback.is_positive.is_(True))
            )
            negative_sessions = (
                select(ChatMessage.chat_session_id)
                .join(
                    ChatMessageFeedback,
                    ChatMessageFeedback.chat_message_id == ChatMessage.id,
                )
                .where(ChatMessageFeedback.is_positive.is_(False))
            )
            if feedback == QAFeedbackType.LIKE:
                conditions.append(ChatSession.id.in_(positive_sessions))
                conditions.append(~ChatSession.id.in_(negative_sessions))
            elif feedback == QAFeedbackType.DISLIKE:
                conditions.append(ChatSession.id.in_(negative_sessions))
                conditions.append(~ChatSession.id.in_(positive_sessions))
            elif feedback == QAFeedbackType.MIXED:
                conditions.append(ChatSession.id.in_(positive_sessions))
                conditions.append(ChatSession.id.in_(negative_sessions))

        return conditions

    def _to_summary(self, session: ChatSession) -> ChatSessionSummary:
        messages = sorted(session.messages, key=lambda m: m.id)
        first_user = next(
            (m.message for m in messages if m.message_type == MessageType.USER), ""
        )
        first_ai = next(
            (m.message for m in messages if m.message_type == MessageType.ASSISTANT),
            "",
        )
        return ChatSessionSummary(
            id=session.id,
            user_email=get_display_email(
                session.user.email if session.user else None
            ),
            name=session.description,
            first_user_message=first_user,
            first_ai_message=first_ai,
            agent_id=session.agent_id,
            agent_name=session.agent.name if session.agent else None,
            time_created=session.time_created,
            feedback=self._session_feedback(messages),
            flow_type=(
                SessionType.SLACK if session.onyxbot_flow else SessionType.CHAT
            ),
            message_count=len(
                [m for m in messages if m.message_type != MessageType.SYSTEM]
            ),
        )

    @staticmethod
    def _session_feedback(
        messages: Sequence[ChatMessage],
    ) -> QAFeedbackType | None:
        polarities = [
            fb.is_positive
            for m in messages
            for fb in m.chat_message_feedbacks
            if fb.is_positive is not None
        ]
        if not polarities:
            return None
        if all(polarities):
            return QAFeedbackType.LIKE
        if not any(polarities):
            return QAFeedbackType.DISLIKE
        return QAFeedbackType.MIXED

    @staticmethod
    def _to_message(message: ChatMessage) -> QueryHistoryMessage:
        latest = (
            message.chat_message_feedbacks[-1]
            if message.chat_message_feedbacks
            else None
        )
        feedback: QAFeedbackType | None = None
        if latest is not None and latest.is_positive is not None:
            feedback = (
                QAFeedbackType.LIKE if latest.is_positive else QAFeedbackType.DISLIKE
            )
        return QueryHistoryMessage(
            id=message.id,
            message_type=message.message_type,
            message=message.message,
            time_created=message.time_sent,
            feedback=feedback,
            feedback_text=latest.feedback_text if latest else None,
        )

    def _session_to_csv_rows(self, session: ChatSession) -> list[list[Any]]:
        messages = [
            m
            for m in sorted(session.messages, key=lambda m: m.id)
            if m.message_type != MessageType.SYSTEM
        ]
        user_email = get_display_email(
            session.user.email if session.user else None
        )
        agent_name = session.agent.name if session.agent else ""
        flow_type = (
            SessionType.SLACK.value
            if session.onyxbot_flow
            else SessionType.CHAT.value
        )

        rows: list[list[Any]] = []
        for pair_num, idx in enumerate(range(1, len(messages), 2), start=1):
            user_msg = messages[idx - 1]
            ai_msg = messages[idx]
            latest = (
                ai_msg.chat_message_feedbacks[-1]
                if ai_msg.chat_message_feedbacks
                else None
            )
            feedback = ""
            if latest is not None and latest.is_positive is not None:
                feedback = "like" if latest.is_positive else "dislike"
            rows.append(
                [
                    str(session.id),
                    pair_num,
                    user_msg.message,
                    ai_msg.message,
                    feedback,
                    latest.feedback_text if latest else "",
                    agent_name,
                    user_email,
                    flow_type,
                    session.time_created.isoformat(),
                ]
            )
        return rows

    @staticmethod
    def _csv_line(fields: Sequence[Any]) -> str:
        buffer = io.StringIO()
        csv.writer(buffer).writerow(fields)
        return buffer.getvalue()


def stream_query_history_csv(
    tenant_id: str,
    start: datetime.datetime | None,
    end: datetime.datetime | None,
) -> Generator[str, None, None]:
    """Stream the query-history CSV using a dedicated tenant-bound session.

    A ``StreamingResponse`` is consumed *after* the request handler returns, so the
    body generator must not depend on the request-scoped session staying open. We
    open our own session bound to the tenant id captured in the handler and keep it
    open for the lifetime of the generator (the ``with`` block spans the stream).
    """
    with get_session_with_tenant(tenant_id=tenant_id) as db_session:
        yield from QueryHistoryService(db_session).iter_csv(start, end)
