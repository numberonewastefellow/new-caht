"""Guard: a question that names a source as its SUBJECT ("how much storage does
our Google Drive plan include") must not narrow search to that source. Only
explicit user / agent / Slack-channel filters may set source_type.

Our search never auto-detects a source filter (extract_source_filter is not
implemented). If a source-scope feature is ever added, it must only scope to a
source named as WHERE to look, never to the question's subject."""

import ast
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from om.configs.constants import DocumentSource
from om.context.search.models import BaseFilters
from om.context.search.models import ChunkSearchRequest
from om.context.search.models import IndexFilters
from om.context.search.pipeline import search_pipeline

_PIPE = "om.context.search.pipeline"

_SUBJECT_QUERIES = [
    "how much storage does our Google Drive plan include",
    "what is our Slack message retention policy",
    "which Confluence plan are we on and what does it cost",
    "how do I reset my Jira password",
]


def _run_pipeline(query: str, user_filters: BaseFilters | None) -> IndexFilters:
    captured: dict[str, Any] = {}

    def fake_search_chunks(**kwargs: Any) -> list:
        captured["filters"] = kwargs["query_request"].filters
        return []

    with (
        patch(f"{_PIPE}.build_access_filters_for_user", return_value=["PUBLIC"]),
        patch(f"{_PIPE}.search_chunks", side_effect=fake_search_chunks),
        patch(f"{_PIPE}.extract_source_filter") as source_detect,
        patch(f"{_PIPE}.extract_time_filter") as time_detect,
        patch(
            "om.external_permissions.post_query_censoring._post_query_chunk_censoring",
            side_effect=lambda chunks, **_: chunks,
        ),
    ):
        # Same call shape as SearchTool._run_search_for_query (no
        # auto_detect_filters, no llm).
        search_pipeline(
            db_session=MagicMock(),
            chunk_search_request=ChunkSearchRequest(
                query=query, user_selected_filters=user_filters
            ),
            document_index=MagicMock(),
            user=MagicMock(id=None),
            agent=None,
        )
        source_detect.assert_not_called()
        time_detect.assert_not_called()
    return captured["filters"]


@pytest.mark.parametrize("query", _SUBJECT_QUERIES)
def test_query_naming_a_source_does_not_narrow(query: str) -> None:
    filters = _run_pipeline(query, user_filters=None)
    assert filters.source_type is None


def test_explicit_user_source_filter_is_kept() -> None:
    filters = _run_pipeline(
        _SUBJECT_QUERIES[0],
        user_filters=BaseFilters(source_type=[DocumentSource.GOOGLE_DRIVE]),
    )
    assert filters.source_type == [DocumentSource.GOOGLE_DRIVE]


def test_no_caller_enables_auto_detect_filters() -> None:
    """Static guard over om/: nobody calls search_pipeline with
    auto_detect_filters=True (or a non-literal value)."""
    om_root = Path(__file__).resolve().parents[4] / "om"
    assert (om_root / "context" / "search" / "pipeline.py").is_file()
    offenders: list[str] = []
    calls_seen = 0
    for py in om_root.rglob("*.py"):
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            fn = node.func
            name = getattr(fn, "id", None) or getattr(fn, "attr", None)
            if name != "search_pipeline":
                continue
            calls_seen += 1
            for kw in node.keywords:
                if kw.arg == "auto_detect_filters" and not (
                    isinstance(kw.value, ast.Constant) and kw.value.value is False
                ):
                    offenders.append(f"{py}:{node.lineno}")
    assert calls_seen >= 1  # the search tool's call must be found
    assert offenders == []
