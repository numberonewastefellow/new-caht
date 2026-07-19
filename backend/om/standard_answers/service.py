"""Business logic for standard answers — the CRUD + matching service.

Orchestrates the repositories, enforces validation (non-empty keyword/answer,
ReDoS-safe regex, category existence + name length), owns the transaction
boundary, and emits the structured OpenSearch events (Standard 9). Transport-
agnostic: it takes primitives, not HTTP DTOs, so the Slack handler and the FastAPI
routers share one implementation.
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.orm import Session

from om.db.models import StandardAnswer
from om.db.models import StandardAnswerCategory
from om.standard_answers.config import StandardAnswerConfigView
from om.standard_answers.config import SINGLETON_ID
from om.standard_answers.config import get_or_create_config
from om.standard_answers.config import load_config
from om.standard_answers.events import logged_operation
from om.standard_answers.events import SAAction
from om.standard_answers.events import SAEntity
from om.standard_answers.events import SAEvent
from om.standard_answers.events import SAStatus
from om.standard_answers.events import emit_event
from om.standard_answers.matching import AnswerRule
from om.standard_answers.matching import StandardAnswerMatcher
from om.standard_answers.repository import DEFAULT_CATEGORY_ID
from om.standard_answers.repository import StandardAnswerCategoryRepository
from om.standard_answers.repository import StandardAnswerRepository
from om.standard_answers.safe_regex import UnsafeRegexError
from om.standard_answers.safe_regex import validate_pattern

MAX_CATEGORY_NAME_LENGTH = 255


class StandardAnswerNotFoundError(Exception):
    """Raised when a referenced standard answer / category does not exist (→ 404)."""


class InvalidStandardAnswerError(ValueError):
    """Raised on validation failure (→ 400)."""


class StandardAnswerService:
    def __init__(self, db_session: Session) -> None:
        self._db = db_session
        self._answers = StandardAnswerRepository(db_session)
        self._categories = StandardAnswerCategoryRepository(db_session)

    # -- categories --------------------------------------------------------------

    def list_categories(self) -> list[StandardAnswerCategory]:
        return self._categories.list_all()

    def ensure_default_category(self) -> None:
        """Idempotent startup seed (id=0 'General'); commits its own work."""

        self._categories.ensure_default()
        self._db.commit()

    def create_category(
        self, name: str, *, actor_user_id: str | None = None
    ) -> StandardAnswerCategory:
        self._validate_category_name(name)
        with logged_operation(
            event=SAEvent.CATEGORY_CREATED,
            entity=SAEntity.CATEGORY,
            action=SAAction.CREATE,
            actor_user_id=actor_user_id,
        ) as ctx:
            category = self._categories.create(name.strip())
            ctx["entity_id"] = category.id
            self._db.commit()
        return category

    def update_category(
        self, category_id: int, name: str, *, actor_user_id: str | None = None
    ) -> StandardAnswerCategory:
        self._validate_category_name(name)
        with logged_operation(
            event=SAEvent.CATEGORY_UPDATED,
            entity=SAEntity.CATEGORY,
            action=SAAction.UPDATE,
            entity_id=category_id,
            actor_user_id=actor_user_id,
        ):
            category = self._categories.update(category_id, name.strip())
            if category is None:
                raise StandardAnswerNotFoundError(
                    f"Standard answer category {category_id} not found."
                )
            self._db.commit()
        return category

    def delete_category(
        self, category_id: int, *, actor_user_id: str | None = None
    ) -> None:
        if category_id == DEFAULT_CATEGORY_ID:
            raise InvalidStandardAnswerError(
                "The default category cannot be deleted."
            )
        with logged_operation(
            event=SAEvent.CATEGORY_DELETED,
            entity=SAEntity.CATEGORY,
            action=SAAction.DELETE,
            entity_id=category_id,
            actor_user_id=actor_user_id,
        ):
            category = self._categories.get(category_id)
            if category is None:
                raise StandardAnswerNotFoundError(
                    f"Standard answer category {category_id} not found."
                )
            answer_count, channel_count = self._categories.reference_counts(category)
            if answer_count or channel_count:
                raise InvalidStandardAnswerError(
                    f"Category is in use by {answer_count} answer(s) and "
                    f"{channel_count} Slack channel(s); reassign or remove those first."
                )
            self._categories.delete(category)
            self._db.commit()

    # -- answers -----------------------------------------------------------------

    def list_answers(self) -> list[StandardAnswer]:
        return self._answers.list_active()

    def create_answer(
        self,
        *,
        keyword: str,
        answer: str,
        category_ids: Sequence[int],
        match_regex: bool,
        match_any_keywords: bool,
        actor_user_id: str | None = None,
    ) -> StandardAnswer:
        self._validate_answer_fields(keyword, answer, match_regex)
        categories = self._resolve_categories(category_ids)
        with logged_operation(
            event=SAEvent.CREATED,
            entity=SAEntity.STANDARD_ANSWER,
            action=SAAction.CREATE,
            actor_user_id=actor_user_id,
        ) as ctx:
            row = self._answers.create(
                keyword=keyword.strip(),
                answer=answer,
                categories=categories,
                match_regex=match_regex,
                match_any_keywords=match_any_keywords,
            )
            ctx["entity_id"] = row.id
            self._db.commit()
        return row

    def update_answer(
        self,
        answer_id: int,
        *,
        keyword: str,
        answer: str,
        category_ids: Sequence[int],
        match_regex: bool,
        match_any_keywords: bool,
        actor_user_id: str | None = None,
    ) -> StandardAnswer:
        self._validate_answer_fields(keyword, answer, match_regex)
        categories = self._resolve_categories(category_ids)
        with logged_operation(
            event=SAEvent.UPDATED,
            entity=SAEntity.STANDARD_ANSWER,
            action=SAAction.UPDATE,
            entity_id=answer_id,
            actor_user_id=actor_user_id,
        ):
            row = self._answers.update(
                answer_id,
                keyword=keyword.strip(),
                answer=answer,
                categories=categories,
                match_regex=match_regex,
                match_any_keywords=match_any_keywords,
            )
            if row is None:
                raise StandardAnswerNotFoundError(
                    f"Standard answer {answer_id} not found."
                )
            self._db.commit()
        return row

    def delete_answer(
        self, answer_id: int, *, actor_user_id: str | None = None
    ) -> None:
        with logged_operation(
            event=SAEvent.DELETED,
            entity=SAEntity.STANDARD_ANSWER,
            action=SAAction.DELETE,
            entity_id=answer_id,
            actor_user_id=actor_user_id,
        ):
            row = self._answers.deactivate(answer_id)
            if row is None:
                raise StandardAnswerNotFoundError(
                    f"Standard answer {answer_id} not found."
                )
            self._db.commit()

    # -- per-tenant config -------------------------------------------------------

    def get_config(self) -> StandardAnswerConfigView:
        return load_config(self._db)

    def update_config(
        self,
        *,
        enabled: bool | None = None,
        max_matches_per_message: int | None = None,
        match_input_char_limit: int | None = None,
        actor_user_id: str | None = None,
    ) -> StandardAnswerConfigView:
        with logged_operation(
            event=SAEvent.CONFIG_UPDATED,
            entity=SAEntity.CONFIG,
            action=SAAction.UPDATE,
            entity_id=SINGLETON_ID,
            actor_user_id=actor_user_id,
        ):
            row = get_or_create_config(self._db)
            if enabled is not None:
                row.enabled = enabled
            if max_matches_per_message is not None:
                row.max_matches_per_message = max_matches_per_message
            if match_input_char_limit is not None:
                row.match_input_char_limit = match_input_char_limit
            self._db.commit()
            view = StandardAnswerConfigView.from_model(row)
        return view

    # -- matching (Slack handler + query endpoint) -------------------------------

    def match_by_category_ids(
        self, message: str, category_ids: Sequence[int]
    ) -> list[StandardAnswer]:
        candidates = self._answers.list_active_in_categories(list(category_ids))
        return self._run_matcher(message, candidates)

    def match_by_category_names(
        self, message: str, category_names: Sequence[str]
    ) -> list[StandardAnswer]:
        categories = self._categories.get_by_names(list(category_names))
        return self.match_by_category_ids(message, [c.id for c in categories])

    def _run_matcher(
        self, message: str, candidates: list[StandardAnswer]
    ) -> list[StandardAnswer]:
        if not candidates:
            return []
        matcher = StandardAnswerMatcher()
        by_id = {a.id: a for a in candidates}
        rules = [self._to_rule(a) for a in candidates]
        matched = matcher.find_matches(rules, message)
        for rule in matched:
            emit_event(
                event=SAEvent.MATCHED,
                entity=SAEntity.STANDARD_ANSWER,
                action=SAAction.MATCH,
                status=SAStatus.SUCCESS,
                entity_id=rule.id,
            )
        return [by_id[rule.id] for rule in matched]

    # -- helpers -----------------------------------------------------------------

    @staticmethod
    def _to_rule(model: StandardAnswer) -> AnswerRule:
        return AnswerRule(
            id=model.id,
            keyword=model.keyword,
            answer=model.answer,
            match_regex=model.match_regex,
            match_any_keywords=model.match_any_keywords,
            category_ids=frozenset(c.id for c in model.categories),
        )

    def _resolve_categories(
        self, category_ids: Sequence[int]
    ) -> list[StandardAnswerCategory]:
        try:
            return self._categories.resolve_all_or_raise(category_ids)
        except ValueError as exc:
            raise InvalidStandardAnswerError(str(exc)) from exc

    @staticmethod
    def _validate_category_name(name: str) -> None:
        cleaned = (name or "").strip()
        if not cleaned:
            raise InvalidStandardAnswerError("Category name must not be empty.")
        if len(cleaned) > MAX_CATEGORY_NAME_LENGTH:
            raise InvalidStandardAnswerError(
                f"Category name must be at most {MAX_CATEGORY_NAME_LENGTH} characters."
            )

    @staticmethod
    def _validate_answer_fields(keyword: str, answer: str, match_regex: bool) -> None:
        if not keyword or not keyword.strip():
            raise InvalidStandardAnswerError("Keyword/trigger must not be empty.")
        if not answer or not answer.strip():
            raise InvalidStandardAnswerError("Answer text must not be empty.")
        if match_regex:
            try:
                validate_pattern(keyword.strip())
            except UnsafeRegexError as exc:
                raise InvalidStandardAnswerError(str(exc)) from exc
