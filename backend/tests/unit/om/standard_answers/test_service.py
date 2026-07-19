"""Service + repository CRUD/matching tests against an in-memory SQLite session.

This exercises the real ORM models, repositories, and service (validation, soft
delete, matching, config) without a Postgres server. The partial-unique index is
Postgres-specific (``postgresql_where``) and is simply inert under SQLite, which is
fine for these behavioural checks. Full multi-tenant/Postgres integration is the
integrator's gate.
"""

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from om.db.models import ChatMessage__StandardAnswer
from om.db.models import SlackChannelConfig__StandardAnswerCategory
from om.db.models import StandardAnswer__StandardAnswerCategory
from om.db.models import StandardAnswerCategory
from om.db.models import StandardAnswer as StandardAnswerModel
from om.db.models import StandardAnswerConfig
from om.standard_answers.service import InvalidStandardAnswerError
from om.standard_answers.service import StandardAnswerNotFoundError
from om.standard_answers.service import StandardAnswerService


@pytest.fixture
def db_session() -> Iterator[Session]:
    engine = create_engine("sqlite://")
    tables = [
        StandardAnswerCategory.__table__,
        StandardAnswerModel.__table__,
        StandardAnswer__StandardAnswerCategory.__table__,
        SlackChannelConfig__StandardAnswerCategory.__table__,
        ChatMessage__StandardAnswer.__table__,
        StandardAnswerConfig.__table__,
    ]
    for table in tables:
        table.create(bind=engine, checkfirst=True)
    with Session(engine) as session:
        yield session


@pytest.fixture
def service(db_session: Session) -> StandardAnswerService:
    return StandardAnswerService(db_session)


def _make_category(service: StandardAnswerService, name: str = "General") -> int:
    return service.create_category(name).id


class TestCategoryCrud:
    def test_create_and_list(self, service: StandardAnswerService) -> None:
        service.create_category("Billing")
        service.create_category("Onboarding")
        names = {c.name for c in service.list_categories()}
        assert names == {"Billing", "Onboarding"}

    def test_rejects_empty_name(self, service: StandardAnswerService) -> None:
        with pytest.raises(InvalidStandardAnswerError):
            service.create_category("   ")

    def test_update_missing_raises(self, service: StandardAnswerService) -> None:
        with pytest.raises(StandardAnswerNotFoundError):
            service.update_category(999, "Nope")

    def test_delete_unused_category(self, service: StandardAnswerService) -> None:
        cat = service.create_category("Temp")
        service.delete_category(cat.id)
        assert service.list_categories() == []

    def test_delete_missing_category_raises(
        self, service: StandardAnswerService
    ) -> None:
        with pytest.raises(StandardAnswerNotFoundError):
            service.delete_category(999)

    def test_delete_default_category_blocked(
        self, service: StandardAnswerService
    ) -> None:
        service._categories.ensure_default()  # seeds id=0
        with pytest.raises(InvalidStandardAnswerError):
            service.delete_category(0)

    def test_delete_in_use_category_blocked(
        self, service: StandardAnswerService
    ) -> None:
        cat = service.create_category("Billing")
        service.create_answer(
            keyword="refund",
            answer="…",
            category_ids=[cat.id],
            match_regex=False,
            match_any_keywords=True,
        )
        with pytest.raises(InvalidStandardAnswerError):
            service.delete_category(cat.id)


class TestAnswerCrud:
    def test_create_requires_valid_category(
        self, service: StandardAnswerService
    ) -> None:
        with pytest.raises(InvalidStandardAnswerError):
            service.create_answer(
                keyword="vpn",
                answer="Reset it here.",
                category_ids=[123],  # does not exist
                match_regex=False,
                match_any_keywords=True,
            )

    def test_create_rejects_unsafe_regex(
        self, service: StandardAnswerService
    ) -> None:
        cat = _make_category(service)
        with pytest.raises(InvalidStandardAnswerError):
            service.create_answer(
                keyword=r"(a+)+",
                answer="x",
                category_ids=[cat],
                match_regex=True,
                match_any_keywords=False,
            )

    def test_create_list_update_softdelete(
        self, service: StandardAnswerService
    ) -> None:
        cat = _make_category(service)
        created = service.create_answer(
            keyword="vpn wifi",
            answer="Try reconnecting.",
            category_ids=[cat],
            match_regex=False,
            match_any_keywords=True,
        )
        assert created.active is True
        assert [a.id for a in service.list_answers()] == [created.id]

        updated = service.update_answer(
            created.id,
            keyword="vpn",
            answer="Updated text.",
            category_ids=[cat],
            match_regex=False,
            match_any_keywords=True,
        )
        assert updated.answer == "Updated text."

        service.delete_answer(created.id)
        # Soft delete → no longer listed (list_active only).
        assert service.list_answers() == []

    def test_delete_missing_raises(self, service: StandardAnswerService) -> None:
        with pytest.raises(StandardAnswerNotFoundError):
            service.delete_answer(999)


class TestMatching:
    def test_match_by_category_ids(self, service: StandardAnswerService) -> None:
        billing = _make_category(service, "Billing")
        other = _make_category(service, "Other")
        service.create_answer(
            keyword="refund",
            answer="Refunds take 5 days.",
            category_ids=[billing],
            match_regex=False,
            match_any_keywords=True,
        )
        service.create_answer(
            keyword="password",
            answer="Reset via the portal.",
            category_ids=[other],
            match_regex=False,
            match_any_keywords=True,
        )

        # Only the Billing category is in scope → only the refund answer can match.
        matched = service.match_by_category_ids("I need a refund", [billing])
        assert [a.answer for a in matched] == ["Refunds take 5 days."]

        # Message mentions password but that answer is out of scope for Billing.
        assert service.match_by_category_ids("reset my password", [billing]) == []

    def test_match_by_category_names(self, service: StandardAnswerService) -> None:
        cat = _make_category(service, "Support")
        service.create_answer(
            keyword=r"error code \d{3}",
            answer="Check the status page.",
            category_ids=[cat],
            match_regex=True,
            match_any_keywords=False,
        )
        matched = service.match_by_category_names("got error code 500", ["Support"])
        assert len(matched) == 1
        assert service.match_by_category_names("all good", ["Support"]) == []

    def test_no_categories_no_match(self, service: StandardAnswerService) -> None:
        assert service.match_by_category_ids("anything", []) == []


class TestConfig:
    def test_defaults_when_unset(self, service: StandardAnswerService) -> None:
        cfg = service.get_config()
        assert cfg.enabled is True
        assert cfg.max_matches_per_message == 3

    def test_update_persists(self, service: StandardAnswerService) -> None:
        updated = service.update_config(enabled=False, max_matches_per_message=1)
        assert updated.enabled is False
        assert updated.max_matches_per_message == 1
        # Re-read confirms persistence.
        assert service.get_config().enabled is False
