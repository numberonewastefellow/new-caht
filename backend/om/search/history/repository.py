"""Repository for per-user search history (the ``search_query`` table).

The session is tenant-bound (Contract 3), so every query is naturally scoped to
the caller's schema; user scoping is enforced with an explicit ``user_id`` filter.
"""

import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from om.db.models import SearchQuery


class SearchQueryRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self, user_id: UUID, query: str, expansions: list[str] | None
    ) -> SearchQuery:
        row = SearchQuery(
            user_id=user_id,
            query=query,
            query_expansions=expansions or None,
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return row

    def list_for_user(
        self,
        user_id: UUID,
        limit: int = 100,
        filter_days: int | None = None,
    ) -> list[SearchQuery]:
        stmt = select(SearchQuery).where(SearchQuery.user_id == user_id)
        if filter_days is not None and filter_days > 0:
            cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
                days=filter_days
            )
            stmt = stmt.where(SearchQuery.created_at >= cutoff)
        stmt = stmt.order_by(SearchQuery.created_at.desc()).limit(max(1, limit))
        return list(self._session.scalars(stmt).all())
