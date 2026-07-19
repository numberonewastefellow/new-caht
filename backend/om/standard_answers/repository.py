"""Data-access layer for standard answers (repositories).

Pure persistence: each repository wraps a tenant-scoped :class:`Session` (the
session is already bound to the caller's Postgres schema per Contract 3, so no
tenant filtering is needed here) and exposes atomic operations. Business rules,
validation, and logging live in :mod:`om.standard_answers.service`.

Repositories never commit — the caller owns the transaction boundary.
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import delete as sql_delete
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm import selectinload

from om.db.models import SlackChannelConfig__StandardAnswerCategory
from om.db.models import StandardAnswer
from om.db.models import StandardAnswer__StandardAnswerCategory
from om.db.models import StandardAnswerCategory

# The seeded catch-all category (see service.ensure_default_category).
DEFAULT_CATEGORY_ID = 0
DEFAULT_CATEGORY_NAME = "General"


class CategoryNotFoundError(ValueError):
    """Raised when one or more referenced category ids do not exist."""


class StandardAnswerCategoryRepository:
    def __init__(self, db_session: Session) -> None:
        self._db = db_session

    def get(self, category_id: int) -> StandardAnswerCategory | None:
        return self._db.get(StandardAnswerCategory, category_id)

    def get_many(self, category_ids: Sequence[int]) -> list[StandardAnswerCategory]:
        if not category_ids:
            return []
        rows = self._db.scalars(
            select(StandardAnswerCategory).where(
                StandardAnswerCategory.id.in_(list(category_ids))
            )
        ).all()
        return list(rows)

    def get_by_names(self, names: Sequence[str]) -> list[StandardAnswerCategory]:
        if not names:
            return []
        rows = self._db.scalars(
            select(StandardAnswerCategory).where(
                StandardAnswerCategory.name.in_(list(names))
            )
        ).all()
        return list(rows)

    def list_all(self) -> list[StandardAnswerCategory]:
        rows = self._db.scalars(
            select(StandardAnswerCategory).order_by(StandardAnswerCategory.name)
        ).all()
        return list(rows)

    def resolve_all_or_raise(
        self, category_ids: Sequence[int]
    ) -> list[StandardAnswerCategory]:
        """Fetch every id, raising :class:`CategoryNotFoundError` if any is missing."""

        unique_ids = list(dict.fromkeys(category_ids))
        found = self.get_many(unique_ids)
        if len(found) != len(unique_ids):
            missing = set(unique_ids) - {c.id for c in found}
            raise CategoryNotFoundError(
                f"Unknown standard-answer category id(s): {sorted(missing)}"
            )
        return found

    def create(self, name: str) -> StandardAnswerCategory:
        category = StandardAnswerCategory(name=name)
        self._db.add(category)
        self._db.flush()
        return category

    def update(self, category_id: int, name: str) -> StandardAnswerCategory | None:
        category = self.get(category_id)
        if category is None:
            return None
        category.name = name
        self._db.flush()
        return category

    def delete(self, category: StandardAnswerCategory) -> None:
        # Core DELETE (not session.delete) so we don't load the m2m collections just
        # to tear them down. Safe because the service checks reference_counts first,
        # and the association FKs are the DB-level backstop against a race.
        self._db.execute(
            sql_delete(StandardAnswerCategory).where(
                StandardAnswerCategory.id == category.id
            )
        )
        self._db.flush()

    def reference_counts(
        self, category: StandardAnswerCategory
    ) -> tuple[int, int]:
        """(#answers, #slack-channels) still referencing this category.

        Counts directly on the association tables so it neither loads the related
        objects nor depends on the ``slack_channel_config`` table being reachable.
        """

        answer_count = (
            self._db.scalar(
                select(func.count()).where(
                    StandardAnswer__StandardAnswerCategory.standard_answer_category_id
                    == category.id
                )
            )
            or 0
        )
        channel_count = (
            self._db.scalar(
                select(func.count()).where(
                    SlackChannelConfig__StandardAnswerCategory.standard_answer_category_id
                    == category.id
                )
            )
            or 0
        )
        return (answer_count, channel_count)

    def ensure_default(self) -> None:
        """Idempotently seed the id=0 catch-all category used by the query API."""

        if self.get(DEFAULT_CATEGORY_ID) is not None:
            return
        self._db.add(
            StandardAnswerCategory(id=DEFAULT_CATEGORY_ID, name=DEFAULT_CATEGORY_NAME)
        )
        self._db.flush()


class StandardAnswerRepository:
    def __init__(self, db_session: Session) -> None:
        self._db = db_session

    def get(self, answer_id: int) -> StandardAnswer | None:
        return self._db.get(StandardAnswer, answer_id)

    def list_active(self) -> list[StandardAnswer]:
        rows = self._db.scalars(
            select(StandardAnswer)
            .where(StandardAnswer.active.is_(True))
            .options(selectinload(StandardAnswer.categories))
            .order_by(StandardAnswer.id)
        ).all()
        return list(rows)

    def list_active_in_categories(
        self, category_ids: Sequence[int]
    ) -> list[StandardAnswer]:
        """Active answers tagged with at least one of ``category_ids`` (deduped)."""

        if not category_ids:
            return []
        rows = self._db.scalars(
            select(StandardAnswer)
            .join(
                StandardAnswer__StandardAnswerCategory,
                StandardAnswer__StandardAnswerCategory.standard_answer_id
                == StandardAnswer.id,
            )
            .where(
                StandardAnswer.active.is_(True),
                StandardAnswer__StandardAnswerCategory.standard_answer_category_id.in_(
                    list(category_ids)
                ),
            )
            .options(selectinload(StandardAnswer.categories))
            .order_by(StandardAnswer.id)
            .distinct()
        ).all()
        return list(rows)

    def create(
        self,
        *,
        keyword: str,
        answer: str,
        categories: list[StandardAnswerCategory],
        match_regex: bool,
        match_any_keywords: bool,
    ) -> StandardAnswer:
        row = StandardAnswer(
            keyword=keyword,
            answer=answer,
            categories=categories,
            active=True,
            match_regex=match_regex,
            match_any_keywords=match_any_keywords,
        )
        self._db.add(row)
        self._db.flush()
        return row

    def update(
        self,
        answer_id: int,
        *,
        keyword: str,
        answer: str,
        categories: list[StandardAnswerCategory],
        match_regex: bool,
        match_any_keywords: bool,
    ) -> StandardAnswer | None:
        row = self.get(answer_id)
        if row is None:
            return None
        row.keyword = keyword
        row.answer = answer
        row.categories = categories
        row.match_regex = match_regex
        row.match_any_keywords = match_any_keywords
        self._db.flush()
        return row

    def deactivate(self, answer_id: int) -> StandardAnswer | None:
        """Soft delete — flips ``active`` off so the row is preserved for audit and
        so its historical thread links remain valid."""

        row = self.get(answer_id)
        if row is None:
            return None
        row.active = False
        self._db.flush()
        return row


def fetch_standard_answer_categories_by_ids(
    standard_answer_category_ids: list[int], db_session: Session
) -> list[StandardAnswerCategory]:
    """Compatibility helper for ``om.db.slack_channel_config`` (replaces the deleted
    ``om.db.standard_answer.fetch_standard_answer_categories_by_ids``). Returns the
    categories for the given ids, in the tenant-scoped session."""

    return StandardAnswerCategoryRepository(db_session).get_many(
        standard_answer_category_ids
    )
