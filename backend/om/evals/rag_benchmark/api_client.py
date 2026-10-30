"""Minimal HTTP client for the stack under test (admin API key auth).

``api_base`` is the API server root: ``http://host:8080`` when talking to the
API server directly, or ``http://host:3000/api`` when going through the web
proxy. Every call retries on 429 / 5xx / connection errors with exponential
backoff, and records its wall-clock latency.
"""

import time
from collections.abc import Callable
from typing import Any

import requests

from om.evals.rag_benchmark.models import RetrievedDoc

RETRY_STATUSES = {429, 500, 502, 503, 504}


class RagBenchmarkApiError(RuntimeError):
    def __init__(self, method: str, path: str, status: int | None, detail: str) -> None:
        super().__init__(f"{method} {path} -> {status}: {detail[:500]}")
        self.status = status


class RagBenchmarkApiClient:
    def __init__(
        self,
        api_base: str,
        api_key: str,
        timeout_s: float = 180.0,
        max_retries: int = 4,
        backoff_s: float = 2.0,
        session: requests.Session | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if not api_key:
            raise ValueError("An admin API key is required (RAG_BENCHMARK_API_KEY)")
        self.api_base = api_base.rstrip("/")
        self.timeout_s = timeout_s
        self.max_retries = max_retries
        self.backoff_s = backoff_s
        self.session = session or requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {api_key}"})
        self._sleep = sleep
        self.last_latency_ms: float | None = None

    # -- transport -----------------------------------------------------------

    def request(self, method: str, path: str, **kwargs: Any) -> Any:
        url = f"{self.api_base}{path}"
        attempt = 0
        while True:
            started = time.perf_counter()
            try:
                response = self.session.request(
                    method, url, timeout=self.timeout_s, **kwargs
                )
            except requests.ConnectionError as exc:
                if attempt >= self.max_retries:
                    raise RagBenchmarkApiError(method, path, None, str(exc)) from exc
            else:
                self.last_latency_ms = (time.perf_counter() - started) * 1000.0
                if response.status_code not in RETRY_STATUSES:
                    if not response.ok:
                        raise RagBenchmarkApiError(
                            method, path, response.status_code, response.text
                        )
                    if not response.content:
                        return None
                    try:
                        return response.json()
                    except ValueError:
                        return response.text
                if attempt >= self.max_retries:
                    raise RagBenchmarkApiError(
                        method, path, response.status_code, response.text
                    )
            self._sleep(self.backoff_s * (2**attempt))
            attempt += 1

    # -- search / chat -------------------------------------------------------

    def search(
        self,
        query: str,
        run_query_expansion: bool,
        num_hits: int = 50,
        document_sets: list[str] | None = None,
    ) -> tuple[list[RetrievedDoc], list[str] | None, float]:
        body: dict[str, Any] = {
            "search_query": query,
            "run_query_expansion": run_query_expansion,
            "num_hits": num_hits,
            "include_content": False,
            "stream": False,
        }
        if document_sets:
            body["filters"] = {"document_set": document_sets}
        data = self.request("POST", "/search/send-search-message", json=body)
        if data.get("error"):
            raise RagBenchmarkApiError(
                "POST", "/search/send-search-message", 200, data["error"]
            )
        docs = [parse_search_doc(d) for d in data.get("search_docs") or []]
        return docs, data.get("llm_selected_doc_ids"), self.last_latency_ms or 0.0

    def chat(
        self,
        message: str,
        model_provider: str | None,
        model_version: str | None,
        forced_tool_id: int | None,
        agent_id: int = 0,
        temperature: float | None = None,
    ) -> tuple[dict[str, Any], float]:
        body: dict[str, Any] = {
            "message": message,
            "stream": False,
            "chat_session_info": {"agent_id": agent_id, "description": "rag-benchmark"},
        }
        if model_provider or model_version or temperature is not None:
            body["llm_override"] = {
                "model_provider": model_provider,
                "model_version": model_version,
                "temperature": temperature,
            }
        if forced_tool_id is not None:
            body["forced_tool_id"] = forced_tool_id
        data = self.request("POST", "/converse/send-chat-message", json=body)
        return data, self.last_latency_ms or 0.0

    def find_search_tool_id(self) -> int:
        for tool in self.request("GET", "/tool") or []:
            if tool.get("in_code_tool_id") == "SearchTool":
                return int(tool["id"])
        raise RagBenchmarkApiError("GET", "/tool", 200, "SearchTool not found")

    # -- settings ------------------------------------------------------------

    def get_expansion_settings(self) -> dict[str, Any]:
        return self.request("GET", "/search/expansion-settings")

    def put_expansion_settings(self, updates: dict[str, Any]) -> dict[str, Any]:
        return self.request("PUT", "/search/expansion-settings", json=updates)

    def get_search_settings(self) -> dict[str, Any]:
        return self.request("GET", "/search-settings/get-current-search-settings")

    # -- documents / index ---------------------------------------------------

    def document_size_info(self, document_id: str) -> dict[str, int]:
        return self.request(
            "GET", "/document/document-size-info", params={"document_id": document_id}
        )

    def set_boost(self, document_id: str, boost: int) -> None:
        self.request(
            "POST",
            "/nexus/admin/doc-boosts",
            json={"document_id": document_id, "boost": boost},
        )

    # -- corpus setup --------------------------------------------------------

    def upload_connector_files(
        self, files: list[tuple[str, bytes, str]]
    ) -> dict[str, Any]:
        multipart = [("files", (name, payload, mime)) for name, payload, mime in files]
        return self.request(
            "POST", "/nexus/admin/connector/file/upload", files=multipart
        )

    def create_file_connector(
        self,
        name: str,
        file_locations: list[str],
        file_names: list[str],
        zip_metadata_file_id: str | None,
    ) -> int:
        """File connector + mock credential + cc-pair in one call; returns the cc-pair id."""
        body = {
            "name": name,
            "source": "file",
            "input_type": "load_state",
            "connector_specific_config": {
                "file_locations": file_locations,
                "file_names": file_names,
                "zip_metadata_file_id": zip_metadata_file_id,
            },
            "refresh_freq": None,
            "prune_freq": None,
            "indexing_start": None,
            "access_type": "public",
            "groups": [],
        }
        data = self.request(
            "POST", "/nexus/admin/connector-with-mock-credential", json=body
        )
        cc_pair_id = data.get("data") if isinstance(data, dict) else None
        if cc_pair_id is None:
            raise RagBenchmarkApiError(
                "POST", "/nexus/admin/connector-with-mock-credential", 200, str(data)
            )
        return int(cc_pair_id)

    def get_cc_pair(self, cc_pair_id: int) -> dict[str, Any]:
        return self.request("GET", f"/nexus/admin/cc-pair/{cc_pair_id}")

    def get_cc_pair_doc_ids(self, cc_pair_id: int) -> list[str]:
        rows = self.request(
            "GET", f"/nexus/admin/cc-pair/{cc_pair_id}/get-docs-sync-status"
        )
        return [row["doc_id"] for row in rows or []]

    def create_document_set(
        self, name: str, cc_pair_ids: list[int], description: str
    ) -> int:
        body = {
            "name": name,
            "description": description,
            "cc_pair_ids": cc_pair_ids,
            "is_public": True,
        }
        return int(self.request("POST", "/nexus/admin/document-set", json=body))


def parse_search_doc(raw: dict[str, Any]) -> RetrievedDoc:
    return RetrievedDoc(
        document_id=str(raw.get("document_id", "")),
        semantic_identifier=str(raw.get("semantic_identifier") or ""),
        score=raw.get("score"),
        chunk_ind=raw.get("chunk_ind"),
    )
