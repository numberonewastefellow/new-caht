"""resolve_evidence_selection_llm: env-configured cheaper model for the search
tool's evidence selection, always falling back to the chat model."""

from collections.abc import Iterator
from contextlib import contextmanager
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from om.secondary_llm_flows import evidence_selection_llm as mod
from om.secondary_llm_flows.evidence_selection_llm import (
    resolve_evidence_selection_llm,
)

_CFG = "om.configs.app_configs"


@contextmanager
def _env(provider: str | None, name: str | None) -> Iterator[None]:
    with (
        patch(f"{_CFG}.EVIDENCE_SELECTION_LLM_PROVIDER", provider),
        patch(f"{_CFG}.EVIDENCE_SELECTION_LLM_NAME", name),
    ):
        yield


@pytest.fixture
def db() -> Iterator[MagicMock]:
    """Patch the DB session + provider lookup + LLM builder."""
    with (
        patch.object(mod, "get_session_with_current_tenant") as session,
        patch.object(mod, "fetch_llm_provider_view") as fetch,
        patch.object(mod, "llm_from_provider") as build,
    ):
        session.return_value.__enter__.return_value = MagicMock()
        m = MagicMock()
        m.session, m.fetch, m.build = session, fetch, build
        yield m


@pytest.fixture
def warnings() -> Iterator[MagicMock]:
    with patch.object(mod, "logger") as logger:
        yield logger.warning


def test_unset_returns_chat_llm_without_db(db: MagicMock) -> None:
    chat = MagicMock()
    with _env(None, None):
        assert resolve_evidence_selection_llm(chat) is chat
    db.session.assert_not_called()
    db.fetch.assert_not_called()
    db.build.assert_not_called()


def test_both_set_returns_resolved_llm(db: MagicMock) -> None:
    chat, cheap, view = MagicMock(), MagicMock(), MagicMock()
    db.fetch.return_value = view
    db.build.return_value = cheap
    with _env("CheapProvider", "gpt-4o-mini"):
        assert resolve_evidence_selection_llm(chat) is cheap
    assert db.fetch.call_args.args[1] == "CheapProvider"
    db.build.assert_called_once_with(model_name="gpt-4o-mini", llm_provider=view)


@pytest.mark.parametrize(
    "provider,name", [("CheapProvider", None), (None, "gpt-4o-mini")]
)
def test_only_one_set_warns_and_falls_back(
    db: MagicMock,
    warnings: MagicMock,
    provider: str | None,
    name: str | None,
) -> None:
    chat = MagicMock()
    with _env(provider, name):
        assert resolve_evidence_selection_llm(chat) is chat
    db.fetch.assert_not_called()
    assert warnings.call_count == 1


def test_unknown_provider_warns_and_falls_back(
    db: MagicMock, warnings: MagicMock
) -> None:
    chat = MagicMock()
    db.fetch.return_value = None
    with _env("Missing", "gpt-4o-mini"):
        assert resolve_evidence_selection_llm(chat) is chat
    db.build.assert_not_called()
    assert warnings.call_count == 1


def test_builder_exception_warns_and_falls_back(
    db: MagicMock, warnings: MagicMock
) -> None:
    chat = MagicMock()
    db.build.side_effect = RuntimeError("bad key")
    with _env("CheapProvider", "gpt-4o-mini"):
        assert resolve_evidence_selection_llm(chat) is chat
    assert warnings.call_count == 1


def test_db_exception_falls_back(db: MagicMock) -> None:
    chat = MagicMock()
    db.session.side_effect = RuntimeError("db down")
    with _env("CheapProvider", "gpt-4o-mini"):
        assert resolve_evidence_selection_llm(chat) is chat


# ---- selection-call timeout (document_filter) ------------------------------


def test_selection_calls_are_bounded_by_timeout() -> None:
    from om.secondary_llm_flows import document_filter

    llm = MagicMock()
    llm.invoke.return_value.choice.message.content = "[0]"
    section = MagicMock()
    section.center_chunk.metadata = {}
    section.center_chunk.semantic_identifier = "doc"
    section.center_chunk.source_type = "file"
    section.center_chunk.updated_at = None
    section.center_chunk.primary_owners = None
    section.center_chunk.secondary_owners = None
    section.combined_content = "text"
    with patch.object(document_filter, "EVIDENCE_SELECTION_LLM_TIMEOUT_S", 7):
        document_filter.select_sections_for_expansion(
            sections=[section], user_query="q", llm=llm, max_chunks_per_section=None
        )
        document_filter.classify_section_relevance(
            document_title="t",
            section_text="s",
            user_query="q",
            llm=llm,
            section_above_text=None,
            section_below_text=None,
        )
    timeouts = [c.kwargs["timeout_override"] for c in llm.invoke.call_args_list]
    assert timeouts == [7, 7]
