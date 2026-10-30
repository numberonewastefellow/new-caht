"""SearchTool routes evidence selection (section selection + per-section
relevance classification) to `evidence_selection_llm`, keeps query expansion
on the chat model, and guards the selection model's context window."""

from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from om.server.query_and_chat.placement import Placement
from om.tools.models import SearchToolOverrideKwargs
from om.tools.tool_implementations.search import search_tool as st
from om.tools.tool_implementations.search.search_tool import SearchTool
from shared_configs.configs import DOC_EMBEDDING_CONTEXT_SIZE

_ST = "om.tools.tool_implementations.search.search_tool"


def _llm(name: str, max_input_tokens: int = 128_000) -> MagicMock:
    llm = MagicMock(name=name)
    llm.config = SimpleNamespace(model_name=name, max_input_tokens=max_input_tokens)
    return llm


def _section(doc_id: str) -> MagicMock:
    sec = MagicMock()
    sec.center_chunk.document_id = doc_id
    sec.center_chunk.chunk_id = 0
    return sec


def _make_tool(chat_llm: MagicMock) -> SearchTool:
    db_session = MagicMock()
    return SearchTool(
        tool_id=1,
        db_session=db_session,
        emitter=MagicMock(),
        user=MagicMock(),
        agent=MagicMock(),
        llm=chat_llm,
        document_index=MagicMock(),
        user_selected_filters=None,
        workspace_id=None,
        enable_slack_search=False,
    )


class _Calls:
    def __init__(self) -> None:
        self.expansion_llms: list[Any] = []
        self.selection_llm: Any = None
        self.classify_llms: list[Any] = []
        self.trim_budget: int | None = None
        self.sections: list[Any] = []


@pytest.fixture
def calls() -> Iterator[_Calls]:
    c = _Calls()
    c.sections = [_section("d1"), _section("d2")]

    def rephrase(_history: Any, llm: Any, *_: Any) -> str:
        c.expansion_llms.append(llm)
        return "semantic q"

    def keywords(_history: Any, llm: Any, *_: Any) -> list[str]:
        c.expansion_llms.append(llm)
        return []

    def trim(**kwargs: Any) -> list:
        c.trim_budget = kwargs["max_tokens"]
        return kwargs["sections"]

    def select(**kwargs: Any) -> tuple[list, None]:
        c.selection_llm = kwargs["llm"]
        return kwargs["sections"], None

    def expand(**kwargs: Any) -> Any:
        c.classify_llms.append(kwargs["llm"])
        return kwargs["section"]

    with (
        patch(f"{_ST}.semantic_query_rephrase", side_effect=rephrase),
        patch(f"{_ST}.keyword_query_expansion", side_effect=keywords),
        patch.object(SearchTool, "_run_search_for_query", return_value=[]),
        patch.object(SearchTool, "_get_thread_safe_session", return_value=MagicMock()),
        patch(f"{_ST}.weighted_reciprocal_rank_fusion", return_value=[]),
        patch(f"{_ST}.rerank_chunks_with_status", return_value=([], False)),
        patch(f"{_ST}.merge_individual_chunks", side_effect=lambda _: c.sections),
        patch(f"{_ST}.convert_inference_sections_to_search_docs", return_value=[]),
        patch(f"{_ST}.get_llm_token_counter", return_value=lambda s: len(s)),
        patch(f"{_ST}._trim_sections_by_tokens", side_effect=trim),
        patch(f"{_ST}.select_sections_for_expansion", side_effect=select),
        patch(f"{_ST}.expand_section_with_context", side_effect=expand),
        patch(f"{_ST}.merge_overlapping_sections", side_effect=lambda s: s),
        patch(
            f"{_ST}.convert_inference_sections_to_llm_string",
            return_value=("docs", {}),
        ),
    ):
        yield c


def _run(tool: SearchTool) -> None:
    tool.run(
        placement=Placement(turn_index=0),
        override_kwargs=SearchToolOverrideKwargs(
            starting_citation_num=1, original_query="what is X"
        ),
        queries=["X"],
    )


def test_empty_search_never_resolves_selection_model(calls: _Calls) -> None:
    calls.sections = []
    tool = _make_tool(_llm("chat"))
    with patch(
        f"{_ST}.resolve_evidence_selection_llm",
        side_effect=AssertionError("must not resolve"),
    ) as resolver:
        _run(tool)
    resolver.assert_not_called()


def test_resolver_failure_keeps_search_on_chat_model(calls: _Calls) -> None:
    # The resolver itself swallows errors; through the real resolver a failing
    # provider lookup must still leave both selection steps on the chat model.
    chat = _llm("chat")
    tool = _make_tool(chat)
    with (
        patch("om.configs.app_configs.EVIDENCE_SELECTION_LLM_PROVIDER", "Missing"),
        patch("om.configs.app_configs.EVIDENCE_SELECTION_LLM_NAME", "gpt-4o-mini"),
        patch(
            "om.secondary_llm_flows.evidence_selection_llm."
            "get_session_with_current_tenant",
            side_effect=RuntimeError("db down"),
        ),
    ):
        _run(tool)
    assert calls.selection_llm is chat
    assert calls.classify_llms == [chat, chat]


def _base_budget() -> int:
    return SearchToolOverrideKwargs(starting_citation_num=1).max_llm_chunks * (  # type: ignore[operator]
        DOC_EMBEDDING_CONTEXT_SIZE
    )


def test_unconfigured_uses_chat_llm_everywhere(calls: _Calls) -> None:
    chat = _llm("chat")
    tool = _make_tool(chat)
    with patch(f"{_ST}.resolve_evidence_selection_llm", side_effect=lambda llm: llm):
        _run(tool)
    assert calls.expansion_llms == [chat, chat]
    assert calls.selection_llm is chat
    assert calls.classify_llms == [chat, chat]


def test_configured_routes_selection_and_classification(calls: _Calls) -> None:
    chat, cheap = _llm("chat"), _llm("cheap")
    tool = _make_tool(chat)
    with patch(f"{_ST}.resolve_evidence_selection_llm", return_value=cheap):
        _run(tool)
    assert calls.expansion_llms == [chat, chat]  # query expansion stays on chat
    assert calls.selection_llm is cheap
    assert calls.classify_llms == [cheap, cheap]


def test_small_context_selection_model_falls_back_for_that_call(
    calls: _Calls,
) -> None:
    chat, tiny = _llm("chat"), _llm("tiny", max_input_tokens=4_000)
    tool = _make_tool(chat)
    with patch(f"{_ST}.resolve_evidence_selection_llm", return_value=tiny):
        _run(tool)
    assert calls.selection_llm is chat
    assert calls.classify_llms == [tiny, tiny]


@pytest.mark.usefixtures("calls")
def test_resolver_called_once_per_instance() -> None:
    chat, cheap = _llm("chat"), _llm("cheap")
    tool = _make_tool(chat)
    with patch(f"{_ST}.resolve_evidence_selection_llm", return_value=cheap) as resolver:
        _run(tool)
        _run(tool)
        assert tool.evidence_selection_llm is cheap
    resolver.assert_called_once_with(chat)


def test_selection_budget_uses_multiplier(calls: _Calls) -> None:
    chat = _llm("chat")
    tool = _make_tool(chat)
    with (
        patch(f"{_ST}.resolve_evidence_selection_llm", side_effect=lambda llm: llm),
        patch(f"{_ST}.EVIDENCE_SELECTION_BUDGET_MULTIPLIER", 2),
    ):
        _run(tool)
    assert calls.trim_budget == 2 * _base_budget()


def test_selection_budget_multiplier_one_is_previous_behaviour(
    calls: _Calls,
) -> None:
    chat = _llm("chat")
    tool = _make_tool(chat)
    with (
        patch(f"{_ST}.resolve_evidence_selection_llm", side_effect=lambda llm: llm),
        patch(f"{_ST}.EVIDENCE_SELECTION_BUDGET_MULTIPLIER", 1),
    ):
        _run(tool)
    assert calls.trim_budget == _base_budget()


# ---- _pick_section_selection_llm (budget + context-window guard) ----------


def test_pick_small_chat_model_keeps_previous_budget() -> None:
    chat = _llm("chat", max_input_tokens=20_000)
    with patch(f"{_ST}.EVIDENCE_SELECTION_BUDGET_MULTIPLIER", 2):
        llm, budget = st._pick_section_selection_llm(chat, chat, 12_800)
    assert llm is chat
    assert budget == 12_800


def test_pick_cheap_model_gets_doubled_budget() -> None:
    chat, cheap = _llm("chat"), _llm("cheap")
    with patch(f"{_ST}.EVIDENCE_SELECTION_BUDGET_MULTIPLIER", 2):
        llm, budget = st._pick_section_selection_llm(cheap, chat, 12_800)
    assert llm is cheap
    assert budget == 25_600


# ---- construct_tools path (agents in chat, workflow steps, deep research) --


def test_search_tool_built_by_construct_tools_is_routed() -> None:
    from om.tools import tool_constructor

    chat, cheap = _llm("chat"), _llm("cheap")
    agent = MagicMock()
    agent.tools = [SimpleNamespace(id=7, in_code_tool_id=1, name="internal_search")]
    user = MagicMock()
    user.oauth_accounts = []
    with (
        patch.object(tool_constructor, "get_current_search_settings"),
        patch.object(tool_constructor, "get_default_document_index"),
        patch.object(
            tool_constructor, "get_built_in_tool_by_id", return_value=SearchTool
        ),
        patch.object(SearchTool, "is_available", return_value=True),
        patch(f"{_ST}.resolve_evidence_selection_llm", return_value=cheap) as resolver,
    ):
        tools = tool_constructor.construct_tools(
            agent=agent,
            db_session=MagicMock(),
            emitter=MagicMock(),
            user=user,
            llm=chat,
        )
        search_tools = [
            t for ts in tools.values() for t in ts if isinstance(t, SearchTool)
        ]
        assert len(search_tools) == 1
        assert search_tools[0].llm is chat
        assert search_tools[0].evidence_selection_llm is cheap
    resolver.assert_called_once_with(chat)
