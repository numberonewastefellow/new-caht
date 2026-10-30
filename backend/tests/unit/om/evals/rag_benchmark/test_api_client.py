"""Mocked-HTTP tests for RagBenchmarkApiClient and corpus setup."""

import io
import json
import zipfile
from pathlib import Path
from typing import Any

import pytest
import requests

from om.evals.rag_benchmark.api_client import RagBenchmarkApiClient
from om.evals.rag_benchmark.api_client import RagBenchmarkApiError
from om.evals.rag_benchmark.corpus_setup import build_corpus_zip
from om.evals.rag_benchmark.corpus_setup import load_manifest
from om.evals.rag_benchmark.corpus_setup import map_doc_ids
from om.evals.rag_benchmark.corpus_setup import setup_scratch_corpus
from om.evals.rag_benchmark.corpus_setup import wait_for_indexing
from tests.rag_benchmark import gen_gov_rag_corpus as gen


class FakeResponse:
    def __init__(self, status: int, payload: Any = None) -> None:
        self.status_code = status
        self._payload = payload
        self.content = b"" if payload is None else json.dumps(payload).encode()
        self.text = self.content.decode()

    @property
    def ok(self) -> bool:
        return self.status_code < 400

    def json(self) -> Any:
        return self._payload


class FakeSession:
    """Replays queued responses per (method, path) and records requests."""

    def __init__(self, routes: dict[tuple[str, str], list[Any]]) -> None:
        self.routes = routes
        self.calls: list[tuple[str, str, dict[str, Any]]] = []
        self.headers: dict[str, str] = {}

    def request(
        self, method: str, url: str, timeout: float, **kwargs: Any
    ) -> FakeResponse:
        path = url.split("://", 1)[1].split("/", 1)[1]
        path = "/" + path
        self.calls.append((method, path, kwargs))
        queue = self.routes[(method, path)]
        item = queue.pop(0) if len(queue) > 1 else queue[0]
        if isinstance(item, Exception):
            raise item
        return item


def _client(
    routes: dict[tuple[str, str], list[Any]],
) -> tuple[RagBenchmarkApiClient, FakeSession, list[float]]:
    session = FakeSession(routes)
    sleeps: list[float] = []
    client = RagBenchmarkApiClient(
        "http://scratch:18080/", "key-123", session=session, sleep=sleeps.append, backoff_s=1.0  # type: ignore[arg-type]
    )
    return client, session, sleeps


SEARCH_PAYLOAD = {
    "all_executed_queries": ["q"],
    "search_docs": [
        {
            "document_id": "FILE_CONNECTOR__a",
            "semantic_identifier": "land_go_2026_te.pdf",
            "score": 0.9,
            "chunk_ind": 3,
        },
        {
            "document_id": "FILE_CONNECTOR__a",
            "semantic_identifier": "land_go_2026_te.pdf",
            "score": 0.8,
            "chunk_ind": 1,
        },
        {
            "document_id": "FILE_CONNECTOR__b",
            "semantic_identifier": "land_sop_te.docx",
            "score": 0.5,
            "chunk_ind": 0,
        },
    ],
    "llm_selected_doc_ids": ["FILE_CONNECTOR__b"],
    "error": None,
}


def test_requires_api_key() -> None:
    with pytest.raises(ValueError):
        RagBenchmarkApiClient("http://x", "")


def test_search_parses_search_docs_and_sends_raw_request() -> None:
    client, session, _ = _client(
        {("POST", "/search/send-search-message"): [FakeResponse(200, SEARCH_PAYLOAD)]}
    )
    docs, selected, latency = client.search(
        "fee?", run_query_expansion=False, num_hits=50
    )
    assert [d.semantic_identifier for d in docs] == [
        "land_go_2026_te.pdf",
        "land_go_2026_te.pdf",
        "land_sop_te.docx",
    ]
    assert docs[0].chunk_ind == 3 and docs[0].score == 0.9
    assert selected == ["FILE_CONNECTOR__b"]
    assert latency >= 0
    body = session.calls[0][2]["json"]
    assert body == {
        "search_query": "fee?",
        "run_query_expansion": False,
        "num_hits": 50,
        "include_content": False,
        "stream": False,
    }
    assert session.headers["Authorization"] == "Bearer key-123"


def test_search_scope_filter_and_error_field() -> None:
    payload = dict(SEARCH_PAYLOAD, error="index unavailable")
    client, session, _ = _client(
        {("POST", "/search/send-search-message"): [FakeResponse(200, payload)]}
    )
    with pytest.raises(RagBenchmarkApiError):
        client.search("q", True, document_sets=["rag-benchmark-gov_v1"])
    assert session.calls[0][2]["json"]["filters"] == {
        "document_set": ["rag-benchmark-gov_v1"]
    }


@pytest.mark.parametrize("status", [429, 500, 502, 503, 504])
def test_retries_on_429_and_5xx_with_backoff(status: int) -> None:
    client, session, sleeps = _client(
        {
            ("POST", "/search/send-search-message"): [
                FakeResponse(status, {}),
                FakeResponse(status, {}),
                FakeResponse(200, SEARCH_PAYLOAD),
            ]
        }
    )
    docs, _, _ = client.search("q", False)
    assert len(docs) == 3
    assert len(session.calls) == 3
    assert sleeps == [1.0, 2.0]


def test_retries_connection_errors_then_gives_up() -> None:
    client, session, sleeps = _client(
        {("GET", "/tool"): [requests.ConnectionError("down")]}
    )
    with pytest.raises(RagBenchmarkApiError):
        client.find_search_tool_id()
    assert len(session.calls) == client.max_retries + 1
    assert sleeps == [1.0, 2.0, 4.0, 8.0]


def test_no_retry_on_4xx() -> None:
    client, session, sleeps = _client(
        {("GET", "/search/expansion-settings"): [FakeResponse(403, {"detail": "no"})]}
    )
    with pytest.raises(RagBenchmarkApiError) as excinfo:
        client.get_expansion_settings()
    assert excinfo.value.status == 403
    assert len(session.calls) == 1 and sleeps == []


def test_chat_request_and_response() -> None:
    chat_payload = {
        "answer": "The fee is Rs 1,250 [1].",
        "answer_citationless": "The fee is Rs 1,250.",
        "top_documents": [
            {"document_id": "d1", "semantic_identifier": "land_go_2026_en.pdf"}
        ],
        "citation_info": [{"citation_number": 1, "document_id": "d1"}],
        "tool_calls": [],
        "message_id": 7,
    }
    client, session, _ = _client(
        {("POST", "/converse/send-chat-message"): [FakeResponse(200, chat_payload)]}
    )
    data, _ = client.chat("fee?", None, "gpt-4o-mini", forced_tool_id=4)
    assert data["answer_citationless"] == "The fee is Rs 1,250."
    body = session.calls[0][2]["json"]
    assert body["stream"] is False
    assert body["forced_tool_id"] == 4
    assert body["llm_override"]["model_version"] == "gpt-4o-mini"
    assert body["chat_session_info"]["agent_id"] == 0
    assert "internal_search_filters" not in body  # scope is never narrowed by the tool


def test_find_search_tool_id() -> None:
    tools = [
        {"id": 1, "in_code_tool_id": "ImageGenerationTool"},
        {"id": 9, "in_code_tool_id": "SearchTool"},
    ]
    client, _, _ = _client({("GET", "/tool"): [FakeResponse(200, tools)]})
    assert client.find_search_tool_id() == 9


def test_map_doc_ids_uses_file_store_ids() -> None:
    mapping = map_doc_ids(
        ["fid1", "fid2"],
        ["a.pdf", "b.csv"],
        ["FILE_CONNECTOR__fid2", "FILE_CONNECTOR__fid1", "other"],
    )
    assert mapping == {"a.pdf": "FILE_CONNECTOR__fid1", "b.csv": "FILE_CONNECTOR__fid2"}


def test_corpus_zip_carries_metadata_dates() -> None:
    manifest = load_manifest(gen.DATASET_DIR)
    with zipfile.ZipFile(io.BytesIO(build_corpus_zip(gen.DATASET_DIR, manifest))) as zf:
        names = set(zf.namelist())
        metadata = json.loads(zf.read(".om_metadata.json"))
    assert names == {e.file_name for e in manifest.files} | {".om_metadata.json"}
    by_name = {m["filename"]: m for m in metadata}
    for entry in manifest.files:
        assert by_name[entry.file_name]["doc_updated_at"] == entry.doc_updated_at
        # No custom tags: they would be appended to chunk text and leak labels.
        assert set(by_name[entry.file_name]) == {"filename", "doc_updated_at"}


def test_wait_for_indexing_polls_until_success() -> None:
    states = [
        FakeResponse(
            200,
            {
                "last_index_attempt_status": "in_progress",
                "num_docs_indexed": 10,
                "indexing": True,
            },
        ),
        FakeResponse(
            200,
            {
                "last_index_attempt_status": "success",
                "num_docs_indexed": 58,
                "indexing": False,
            },
        ),
    ]
    client, _, _ = _client({("GET", "/nexus/admin/cc-pair/5"): states})
    sleeps: list[float] = []
    info = wait_for_indexing(
        client, 5, 58, timeout_s=60, poll_s=1, sleep=sleeps.append, log=lambda _: None
    )
    assert info["num_docs_indexed"] == 58
    assert sleeps == [1]


def test_wait_for_indexing_raises_on_failure() -> None:
    client, _, _ = _client(
        {
            ("GET", "/nexus/admin/cc-pair/5"): [
                FakeResponse(200, {"last_index_attempt_status": "failed"})
            ]
        }
    )
    with pytest.raises(RuntimeError):
        wait_for_indexing(
            client,
            5,
            58,
            timeout_s=60,
            poll_s=1,
            sleep=lambda _: None,
            log=lambda _: None,
        )


def test_setup_scratch_corpus_end_to_end_mocked(tmp_path: Path) -> None:
    manifest = load_manifest(gen.DATASET_DIR)
    names = [e.file_name for e in manifest.files]
    file_ids = [f"fid{i}" for i in range(len(names))]
    routes: dict[tuple[str, str], list[Any]] = {
        ("POST", "/nexus/admin/connector/file/upload"): [
            FakeResponse(
                200,
                {
                    "file_paths": file_ids,
                    "file_names": names,
                    "zip_metadata_file_id": "meta1",
                },
            )
        ],
        ("POST", "/nexus/admin/connector-with-mock-credential"): [
            FakeResponse(200, {"success": True, "data": 12})
        ],
        ("POST", "/nexus/admin/document-set"): [FakeResponse(200, 3)],
        ("GET", "/nexus/admin/cc-pair/12"): [
            FakeResponse(
                200,
                {
                    "last_index_attempt_status": "success",
                    "num_docs_indexed": len(names),
                    "indexing": False,
                },
            )
        ],
        ("GET", "/nexus/admin/cc-pair/12/get-docs-sync-status"): [
            FakeResponse(
                200, [{"doc_id": f"FILE_CONNECTOR__{fid}"} for fid in file_ids]
            )
        ],
        ("POST", "/nexus/admin/doc-boosts"): [FakeResponse(200, None)],
    }
    client, session, _ = _client(routes)
    state = setup_scratch_corpus(
        client, gen.DATASET_DIR, sleep=lambda _: None, log=lambda _: None
    )
    assert state.cc_pair_id == 12 and state.document_set_id == 3
    assert state.document_set_name == "rag-benchmark-gov_v1"
    assert len(state.docs) == len(names)
    assert state.boosts_applied == {
        e.file_name: e.boost for e in manifest.files if e.boost
    }
    connector_body = next(
        c[2]["json"]
        for c in session.calls
        if c[1] == "/nexus/admin/connector-with-mock-credential"
    )
    assert (
        connector_body["connector_specific_config"]["zip_metadata_file_id"] == "meta1"
    )
    assert (
        connector_body["source"] == "file" and connector_body["access_type"] == "public"
    )
    upload = next(
        c[2] for c in session.calls if c[1] == "/nexus/admin/connector/file/upload"
    )
    assert upload["files"][0][1][0] == "rag-benchmark-gov_v1.zip"
