"""Pydantic schemas for the admin query-history API (clean-room rewrite)."""

import datetime
from uuid import UUID

from pydantic import BaseModel

from om.configs.constants import MessageType
from om.configs.constants import QAFeedbackType
from om.configs.constants import SessionType


class ChatSessionSummary(BaseModel):
    """A single row in the query-history list."""

    id: UUID
    user_email: str | None
    name: str | None
    first_user_message: str
    first_ai_message: str
    agent_id: int | None
    agent_name: str | None
    time_created: datetime.datetime
    # Overall feedback polarity for the session (all-positive/all-negative/mixed).
    feedback: QAFeedbackType | None
    flow_type: SessionType
    message_count: int


class QueryHistoryMessage(BaseModel):
    """One message inside a session detail view."""

    id: int
    message_type: MessageType
    message: str
    time_created: datetime.datetime
    feedback: QAFeedbackType | None
    feedback_text: str | None


class ChatSessionDetail(BaseModel):
    """Full session view (ordered messages)."""

    id: UUID
    user_email: str | None
    name: str | None
    agent_id: int | None
    agent_name: str | None
    time_created: datetime.datetime
    flow_type: SessionType
    messages: list[QueryHistoryMessage]


class PaginatedSessions(BaseModel):
    """A page of session summaries plus the total filtered count."""

    items: list[ChatSessionSummary]
    total_items: int
