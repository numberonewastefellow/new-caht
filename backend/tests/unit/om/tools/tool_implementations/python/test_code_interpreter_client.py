"""Unit tests for CodeInterpreterClient auth + tenant headers and error mapping.

Requests go through a recording transport adapter mounted on the client's
``requests.Session``, so the headers asserted here are exactly what goes on the wire.
"""

import io
import json
from collections.abc import Callable

import pytest
import requests
from requests.adapters import BaseAdapter

from om.tools.tool_implementations.python.code_interpreter_client import (
    CodeInterpreterAuthError,
)
from om.tools.tool_implementations.python.code_interpreter_client import (
    CodeInterpreterClient,
)
from om.tools.tool_implementations.python.code_interpreter_client import (
    CodeInterpreterUnavailableError,
)
from om.tools.tool_implementations.python.code_interpreter_client import (
    RunFunctionUnsupportedError,
)
from om.tools.tool_implementations.python.code_interpreter_client import TENANT_HEADER
from shared_configs.configs import POSTGRES_DEFAULT_SCHEMA
from shared_configs.contextvars import CURRENT_TENANT_ID_CONTEXTVAR

BASE_URL = "http://code-interpreter.test:8000"

Responder = Callable[[requests.PreparedRequest], tuple[int, dict, dict[str, str]]]


class _RecordingAdapter(BaseAdapter):
    def __init__(self, responder: Responder) -> None:
        super().__init__()
        self.requests: list[requests.PreparedRequest] = []
        self._responder = responder

    def send(self, request, stream=False, timeout=None, verify=True, cert=None, proxies=None):  # type: ignore[no-untyped-def]  # noqa: ARG002
        self.requests.append(request)
        status, body, headers = self._responder(request)
        resp = requests.Response()
        resp.status_code = status
        resp._content = json.dumps(body).encode("utf-8")
        resp.raw = io.BytesIO(resp._content)
        resp.headers.update({"Content-Type": "application/json", **headers})
        resp.url = request.url or ""
        resp.request = request
        return resp

    def close(self) -> None:
        pass


def _ok(request: requests.PreparedRequest) -> tuple[int, dict, dict[str, str]]:
    path = request.path_url
    if path == "/v1/sessions" and request.method == "POST":
        return 201, {"session_id": "s" * 32}, {}
    if path == "/v1/execute":
        return (
            200,
            {
                "stdout": "2\n",
                "stderr": "",
                "exit_code": 0,
                "timed_out": False,
                "duration_ms": 1,
                "files": [],
            },
            {},
        )
    if path == "/v1/files" and request.method == "POST":
        return 201, {"file_id": "f", "filename": "a", "size_bytes": 1}, {}
    if path == "/v1/run_function":
        return 200, dict(RUN_FUNCTION_OK), {}
    return 200, {}, {}


RUN_FUNCTION_OK: dict = {
    "stdout": "frame",
    "stderr": "",
    "exit_code": 0,
    "timed_out": False,
    "duration_ms": 12,
    "error_kind": None,
    "stdout_truncated": False,
    "stderr_truncated": False,
    "result_payload": None,
    "result_error": None,
    "pool_hit": True,
}


def _client(
    responder: Responder = _ok, api_token: str | None = "test-token"
) -> tuple[CodeInterpreterClient, _RecordingAdapter]:
    client = CodeInterpreterClient(base_url=BASE_URL, api_token=api_token)
    adapter = _RecordingAdapter(responder)
    client.session.mount("http://", adapter)
    return client, adapter


def test_every_call_sends_bearer_token_and_tenant() -> None:
    client, adapter = _client()
    token = CURRENT_TENANT_ID_CONTEXTVAR.set("tenant_abc")
    try:
        client.create_session()
        client.execute(code="print(1+1)", session_id="s" * 32)
        client.upload_file(b"x", "a.txt")
        client.download_file("f")
        client.delete_file("f")
        client.delete_session("s" * 32)
    finally:
        CURRENT_TENANT_ID_CONTEXTVAR.reset(token)

    assert len(adapter.requests) == 6
    for req in adapter.requests:
        assert req.headers["Authorization"] == "Bearer test-token"
        assert req.headers[TENANT_HEADER] == "tenant_abc"


def test_tenant_header_is_resolved_per_request() -> None:
    client, adapter = _client()
    for tenant in ("tenant_one", "tenant_two"):
        token = CURRENT_TENANT_ID_CONTEXTVAR.set(tenant)
        try:
            client.create_session()
        finally:
            CURRENT_TENANT_ID_CONTEXTVAR.reset(token)
    assert [r.headers[TENANT_HEADER] for r in adapter.requests] == [
        "tenant_one",
        "tenant_two",
    ]


def test_single_tenant_default_schema_is_sent(monkeypatch: pytest.MonkeyPatch) -> None:
    import shared_configs.contextvars as ctx

    monkeypatch.setattr(ctx, "MULTI_TENANT", False)
    client, adapter = _client()
    token = CURRENT_TENANT_ID_CONTEXTVAR.set(None)
    try:
        client.create_session()
    finally:
        CURRENT_TENANT_ID_CONTEXTVAR.reset(token)
    assert adapter.requests[0].headers[TENANT_HEADER] == POSTGRES_DEFAULT_SCHEMA


def test_no_token_sends_no_authorization_header() -> None:
    client, adapter = _client(api_token="")
    client.create_session()
    assert "Authorization" not in adapter.requests[0].headers


def test_default_token_comes_from_config(monkeypatch: pytest.MonkeyPatch) -> None:
    import om.tools.tool_implementations.python.code_interpreter_client as mod

    monkeypatch.setattr(mod, "CODE_INTERPRETER_API_TOKEN", "from-config")
    client = CodeInterpreterClient(base_url=BASE_URL)
    assert client.session.headers["Authorization"] == "Bearer from-config"


@pytest.mark.parametrize("status", [401, 403])
def test_auth_failures_raise_clear_auth_error(status: int) -> None:
    client, _ = _client(lambda _r: (status, {"detail": "Missing or invalid bearer token."}, {}))
    with pytest.raises(CodeInterpreterAuthError) as exc_info:
        client.execute(code="print(1)")
    exc = exc_info.value
    assert isinstance(exc, requests.exceptions.HTTPError)
    assert exc.response is not None and exc.response.status_code == status
    assert "CODE_INTERPRETER_API_TOKEN" in str(exc)


def test_capacity_503_raises_unavailable_with_retry_after() -> None:
    client, _ = _client(
        lambda _r: (503, {"detail": "Code interpreter is at capacity"}, {"Retry-After": "5"})
    )
    with pytest.raises(CodeInterpreterUnavailableError) as exc_info:
        client.create_session()
    assert exc_info.value.retry_after == 5
    assert exc_info.value.response is not None
    assert exc_info.value.response.status_code == 503
    assert "at capacity" in str(exc_info.value)


def test_unconfigured_service_503_names_the_setting() -> None:
    client, _ = _client(
        lambda _r: (
            503,
            {"detail": "Code interpreter API token is not configured on the service."},
            {},
        )
    )
    with pytest.raises(CodeInterpreterUnavailableError) as exc_info:
        client.execute(code="print(1)")
    assert "CODE_INTERPRETER_API_TOKEN" in str(exc_info.value)


def test_stream_checks_auth_before_reading() -> None:
    client, adapter = _client(lambda _r: (401, {"detail": "nope"}, {}))
    with pytest.raises(CodeInterpreterAuthError):
        list(client.execute_stream(code="print(1)"))
    assert adapter.requests[0].headers["Authorization"] == "Bearer test-token"
    assert TENANT_HEADER in adapter.requests[0].headers


def test_other_errors_still_raise_http_error() -> None:
    client, _ = _client(lambda _r: (404, {"detail": "Session not found"}, {}))
    with pytest.raises(requests.exceptions.HTTPError) as exc_info:
        client.execute(code="print(1)", session_id="x")
    assert not isinstance(exc_info.value, CodeInterpreterAuthError)
    assert exc_info.value.response is not None
    assert exc_info.value.response.status_code == 404


def test_python_tool_treats_auth_error_as_non_retriable() -> None:
    """A wrong token must not trigger the fresh-session retry loop; capacity 503 may."""
    from om.tools.tool_implementations.python.python_tool import PythonTool

    tool = PythonTool.__new__(PythonTool)
    auth_resp = requests.Response()
    auth_resp.status_code = 401
    busy_resp = requests.Response()
    busy_resp.status_code = 503
    auth_err = CodeInterpreterAuthError(
        "Code interpreter rejected the request (HTTP 401)", response=auth_resp
    )
    busy_err = CodeInterpreterUnavailableError("at capacity", response=busy_resp)
    assert tool._is_retriable_error(auth_err) is False
    assert tool._is_retriable_error(busy_err) is True


# ── run_function ──────────────────────────────────────────────────────────


def test_run_function_sends_program_auth_and_tenant() -> None:
    client, adapter = _client()
    token = CURRENT_TENANT_ID_CONTEXTVAR.set("tenant_abc")
    try:
        result = client.run_function(program="print(1)", timeout_ms=5000)
    finally:
        CURRENT_TENANT_ID_CONTEXTVAR.reset(token)

    req = adapter.requests[0]
    assert req.method == "POST"
    assert req.path_url == "/v1/run_function"
    assert req.headers["Authorization"] == "Bearer test-token"
    assert req.headers[TENANT_HEADER] == "tenant_abc"
    assert json.loads(req.body or b"{}") == {"program": "print(1)", "timeout_ms": 5000}
    assert result.stdout == "frame"
    assert result.exit_code == 0
    assert result.pool_hit is True
    assert result.error_kind is None


def test_run_function_requests_and_returns_result_file() -> None:
    def responder(_r: requests.PreparedRequest) -> tuple[int, dict, dict[str, str]]:
        return 200, {**RUN_FUNCTION_OK, "result_payload": '{"a": 1}'}, {}

    client, adapter = _client(responder)
    result = client.run_function(program="x", timeout_ms=1000, read_result_file=True)
    assert json.loads(adapter.requests[0].body or b"{}")["read_result_file"] is True
    assert result.result_payload == '{"a": 1}'


@pytest.mark.parametrize(
    ("error_kind", "timed_out", "exit_code"),
    [("timeout", True, None), ("oom", False, 137), ("sandbox_error", False, None)],
)
def test_run_function_parses_error_kinds(
    error_kind: str, timed_out: bool, exit_code: int | None
) -> None:
    body = {
        **RUN_FUNCTION_OK,
        "error_kind": error_kind,
        "timed_out": timed_out,
        "exit_code": exit_code,
    }
    client, _ = _client(lambda _r: (200, body, {}))
    result = client.run_function(program="x", timeout_ms=1000)
    assert result.error_kind == error_kind
    assert result.timed_out is timed_out
    assert result.exit_code == exit_code


def test_run_function_tolerates_minimal_response() -> None:
    """Optional fields default, so a leaner (or older) response still parses."""
    minimal = {
        "stdout": "",
        "stderr": "",
        "exit_code": 0,
        "timed_out": False,
        "duration_ms": 1,
    }
    client, _ = _client(lambda _r: (200, minimal, {}))
    result = client.run_function(program="x", timeout_ms=1000)
    assert result.error_kind is None
    assert result.pool_hit is False


@pytest.mark.parametrize("status", [404, 501])
def test_run_function_unsupported_service(status: int) -> None:
    client, _ = _client(lambda _r: (status, {"detail": "Not Found"}, {}))
    with pytest.raises(RunFunctionUnsupportedError) as exc_info:
        client.run_function(program="x", timeout_ms=1000)
    assert isinstance(exc_info.value, requests.exceptions.HTTPError)
    assert exc_info.value.response is not None
    assert exc_info.value.response.status_code == status


@pytest.mark.parametrize("status", [401, 403])
def test_run_function_auth_error(status: int) -> None:
    client, _ = _client(lambda _r: (status, {"detail": "nope"}, {}))
    with pytest.raises(CodeInterpreterAuthError):
        client.run_function(program="x", timeout_ms=1000)


def test_run_function_capacity_503() -> None:
    client, _ = _client(
        lambda _r: (503, {"detail": "Code interpreter is at capacity"}, {"Retry-After": "5"})
    )
    with pytest.raises(CodeInterpreterUnavailableError) as exc_info:
        client.run_function(program="x", timeout_ms=1000)
    assert exc_info.value.retry_after == 5
    assert not isinstance(exc_info.value, RunFunctionUnsupportedError)


def test_run_function_validation_error_is_http_error() -> None:
    client, _ = _client(lambda _r: (422, {"detail": "timeout_ms exceeds maximum"}, {}))
    with pytest.raises(requests.exceptions.HTTPError) as exc_info:
        client.run_function(program="x", timeout_ms=10**9)
    assert not isinstance(exc_info.value, RunFunctionUnsupportedError)
