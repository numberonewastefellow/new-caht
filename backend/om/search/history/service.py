"""Search-history service.

``SearchHistoryService`` doubles as the orchestrator's ``HistoryRecorder``: its
``record`` is invoked from inside the streaming generator (after the request
session has closed), so it opens its own fresh tenant session. Persistence is
best-effort — a history failure never breaks the search.
"""

from uuid import UUID

from sqlalchemy.orm import Session

from om.db.models import SearchQuery
from om.search.history.repository import SearchQueryRepository
from om.search.log_events import ACTION_CREATE
from om.search.log_events import ACTION_READ
from om.search.log_events import emit_search_event
from om.search.log_events import STATUS_SUCCESS
from om.tenancy.context import get_current_tenant_session
from om.utils.logger import setup_logger

logger = setup_logger()


class SearchHistoryService:
    def __init__(self, user_id: UUID) -> None:
        self._user_id = user_id

    def record(self, *, query: str, expansions: list[str]) -> str | None:
        """Persist one search. Opens its own tenant session; never raises."""
        try:
            with get_current_tenant_session() as session:
                row = SearchQueryRepository(session).create(
                    self._user_id, query, expansions or None
                )
                emit_search_event(
                    event="search.history_saved",
                    action=ACTION_CREATE,
                    status=STATUS_SUCCESS,
                    entity_id=row.id,
                    actor_user_id=self._user_id,
                    num_expansions=len(expansions or []),
                )
                return str(row.id)
        except Exception as exc:
            logger.warning("failed to persist search history: %s", exc)
            return None


def list_search_history(
    session: Session,
    user_id: UUID,
    limit: int = 100,
    filter_days: int | None = None,
) -> list[SearchQuery]:
    """Read a user's search history (tenant-scoped via the bound session)."""
    rows = SearchQueryRepository(session).list_for_user(user_id, limit, filter_days)
    emit_search_event(
        event="search.history_read",
        action=ACTION_READ,
        status=STATUS_SUCCESS,
        actor_user_id=user_id,
        num_rows=len(rows),
    )
    return rows
