import json
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Literal
from typing import TypedDict

import requests
from pydantic import BaseModel

from om.configs.app_configs import CODE_INTERPRETER_API_TOKEN
from om.configs.app_configs import CODE_INTERPRETER_BASE_URL
from om.utils.logger import setup_logger
from shared_configs.contextvars import get_current_tenant_id

logger = setup_logger()

# Header naming the calling tenant. The service binds every session/file to it and
# answers 404 for another tenant's ids.
TENANT_HEADER = "X-OM-Tenant"

_warned_missing_token = False


def _warn_missing_token_once() -> None:
    global _warned_missing_token
    if _warned_missing_token:
        return
    _warned_missing_token = True
    logger.warning(
        "CODE_INTERPRETER_API_TOKEN is not set; the code interpreter will reject "
        "requests unless it runs with CODE_INTERPRETER_ALLOW_UNAUTHENTICATED=true "
        "(dev only)."
    )


class CodeInterpreterError(requests.exceptions.HTTPError):
    """An HTTP error from the code interpreter with an actionable message.

    Subclasses ``requests.HTTPError`` (with ``.response`` set) so existing callers
    that inspect ``exc.response.status_code`` keep working.
    """


class CodeInterpreterAuthError(CodeInterpreterError):
    """401/403: the shared API token is missing or does not match the service."""


class CodeInterpreterUnavailableError(CodeInterpreterError):
    """503: the service is at capacity, or has no API token configured."""

    def __init__(
        self,
        message: str,
        *,
        response: requests.Response | None = None,
        retry_after: int | None = None,
    ):
        super().__init__(message, response=response)
        self.retry_after = retry_after


class RunFunctionUnsupportedError(CodeInterpreterError):
    """The service has no ``/v1/run_function`` (an older service answers 404; a
    service on a backend without it, e.g. Kubernetes, answers 501).

    Callers can fall back to :meth:`CodeInterpreterClient.execute`.
    """


def _error_detail(response: requests.Response) -> str:
    try:
        detail = response.json().get("detail")
        if isinstance(detail, str):
            return detail
    except Exception:
        pass
    return (response.text or "")[:200]


def _check_response(response: requests.Response) -> None:
    """Raise a clear error for auth/capacity failures, else ``raise_for_status``."""
    status = response.status_code
    if status in (401, 403):
        raise CodeInterpreterAuthError(
            f"Code interpreter rejected the request (HTTP {status}): the API token is "
            "missing or wrong. Set CODE_INTERPRETER_API_TOKEN to the same value on the "
            "backend services and on the code-interpreter service.",
            response=response,
        )
    if status == 503:
        detail = _error_detail(response)
        retry_after_raw = response.headers.get("Retry-After")
        retry_after = (
            int(retry_after_raw) if retry_after_raw and retry_after_raw.isdigit() else None
        )
        if "token is not configured" in detail:
            msg = (
                "Code interpreter is refusing requests (HTTP 503) because it has no "
                "CODE_INTERPRETER_API_TOKEN configured. Set the same token on the "
                "code-interpreter service and the backend services, then restart them."
            )
        else:
            msg = (
                f"Code interpreter is unavailable or at capacity (HTTP 503): {detail}"
                + (f" Retry after {retry_after}s." if retry_after else "")
            )
        raise CodeInterpreterUnavailableError(
            msg, response=response, retry_after=retry_after
        )
    response.raise_for_status()


class FileInput(TypedDict):
    """Input file to be staged in execution workspace"""

    path: str
    file_id: str


class WorkspaceFile(BaseModel):
    """File in execution workspace"""

    path: str
    kind: Literal["file", "directory"]
    file_id: str | None = None


class ExecuteResponse(BaseModel):
    """Response from code execution"""

    stdout: str
    stderr: str
    exit_code: int | None
    timed_out: bool
    duration_ms: int
    files: list[WorkspaceFile]
    # Non-timeout failure mode when set: "oom", "kernel_died", or "timeout".
    error_kind: str | None = None


class RunFunctionResponse(BaseModel):
    """Response from ``/v1/run_function`` (one program in a fresh, single-use sandbox)."""

    stdout: str
    stderr: str
    exit_code: int | None
    timed_out: bool
    duration_ms: int
    # "timeout" (wall clock or CPU-time limit), "oom", "sandbox_error", or None.
    # Kept as ``str`` so a newer service's additional kinds don't break parsing.
    error_kind: str | None = None
    stdout_truncated: bool = False
    stderr_truncated: bool = False
    # The program's out-of-band result file, when requested with read_result_file.
    result_payload: str | None = None
    # Why a written result file was not returned: "too_large" or "invalid_utf8".
    result_error: str | None = None
    # True when the run used a pre-started (warm) sandbox.
    pool_hit: bool = False


@dataclass
class CIStreamEvent:
    """One event from :meth:`CodeInterpreterClient.execute_stream`.

    ``kind == "output"`` carries a live stdout/stderr chunk (``stream``/``data``);
    ``kind == "result"`` carries the terminal :class:`ExecuteResponse` (``result``)
    whose ``stdout``/``stderr`` are empty because the text was already streamed.
    """

    kind: Literal["output", "result"]
    stream: Literal["stdout", "stderr"] | None = None
    data: str | None = None
    result: ExecuteResponse | None = None


class CodeInterpreterClient:
    """Client for Code Interpreter service"""

    def __init__(
        self,
        base_url: str | None = CODE_INTERPRETER_BASE_URL,
        api_token: str | None = None,
    ):
        if not base_url:
            raise ValueError("CODE_INTERPRETER_BASE_URL not configured")
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        token = CODE_INTERPRETER_API_TOKEN if api_token is None else api_token
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"
        else:
            _warn_missing_token_once()

    @staticmethod
    def _tenant_headers() -> dict[str, str]:
        """Per-request tenant header (the current tenant, or the default schema in
        single-tenant mode). Resolved per call, not cached on the client."""
        return {TENANT_HEADER: get_current_tenant_id()}

    def create_session(self) -> str:
        """Create a persistent execution session. Returns session_id."""
        url = f"{self.base_url}/v1/sessions"
        response = self.session.post(url, headers=self._tenant_headers(), timeout=30)
        _check_response(response)
        return response.json()["session_id"]

    def delete_session(self, session_id: str) -> None:
        """Destroy a persistent execution session."""
        url = f"{self.base_url}/v1/sessions/{session_id}"
        response = self.session.delete(url, headers=self._tenant_headers(), timeout=10)
        _check_response(response)

    def execute(
        self,
        code: str,
        stdin: str | None = None,
        timeout_ms: int = 30000,
        files: list[FileInput] | None = None,
        session_id: str | None = None,
    ) -> ExecuteResponse:
        """Execute Python code.

        If session_id is provided, executes in a persistent session where
        variables survive between calls.
        """
        url = f"{self.base_url}/v1/execute"

        payload: dict = {
            "code": code,
            "timeout_ms": timeout_ms,
        }

        if stdin is not None:
            payload["stdin"] = stdin

        if files:
            payload["files"] = files

        if session_id is not None:
            payload["session_id"] = session_id

        response = self.session.post(
            url,
            json=payload,
            headers=self._tenant_headers(),
            timeout=timeout_ms / 1000 + 10,
        )
        _check_response(response)

        return ExecuteResponse(**response.json())

    def run_function(
        self,
        program: str,
        timeout_ms: int,
        *,
        read_result_file: bool = False,
    ) -> RunFunctionResponse:
        """Run a self-contained program in a fresh, single-use sandbox.

        Lower latency than :meth:`execute`: the program runs as-is (no last-line
        wrapper, figure prologue or workspace files), usually in a pre-started
        sandbox. With ``read_result_file`` the program may write its result to
        ``$OM_RESULT_PATH`` and it comes back as ``result_payload``.

        Raises:
            RunFunctionUnsupportedError: the service has no run_function endpoint
                (fall back to :meth:`execute`).
            CodeInterpreterAuthError / CodeInterpreterUnavailableError /
                requests.HTTPError: as for :meth:`execute`.
        """
        url = f"{self.base_url}/v1/run_function"
        payload: dict = {"program": program, "timeout_ms": timeout_ms}
        if read_result_file:
            payload["read_result_file"] = True

        response = self.session.post(
            url,
            json=payload,
            headers=self._tenant_headers(),
            timeout=timeout_ms / 1000 + 10,
        )
        if response.status_code in (404, 501):
            raise RunFunctionUnsupportedError(
                "The code interpreter does not support run_function "
                f"(HTTP {response.status_code}): {_error_detail(response)}",
                response=response,
            )
        _check_response(response)

        return RunFunctionResponse(**response.json())

    def execute_stream(
        self,
        code: str,
        timeout_ms: int = 30000,
        files: list[FileInput] | None = None,
        session_id: str | None = None,
    ) -> Iterator[CIStreamEvent]:
        """Execute Python code with live streaming output via Server-Sent Events.

        Yields ``CIStreamEvent(kind="output", ...)`` as stdout/stderr chunks arrive,
        then a final ``CIStreamEvent(kind="result", result=ExecuteResponse)``. Raises
        ``RuntimeError`` if the service emits an error event. If ``session_id`` is
        provided the code runs in the persistent kernel (state survives between calls).
        """
        url = f"{self.base_url}/v1/execute/stream"

        payload: dict = {
            "code": code,
            "timeout_ms": timeout_ms,
        }
        if files:
            payload["files"] = files
        if session_id is not None:
            payload["session_id"] = session_id

        # (connect timeout, read timeout). The read timeout is the wall-clock budget
        # plus headroom so a legitimately long cell isn't cut off client-side.
        with self.session.post(
            url,
            json=payload,
            headers=self._tenant_headers(),
            stream=True,
            timeout=(10, timeout_ms / 1000 + 30),
        ) as response:
            _check_response(response)

            event: str | None = None
            data: str | None = None
            buf = b""
            # Split the raw byte stream on "\n" ONLY. requests' iter_lines() uses
            # str.splitlines(), which also breaks on U+2028/U+2029/U+0085 — characters
            # that can legitimately appear inside streamed program output and would
            # otherwise corrupt the SSE framing (pydantic emits raw, non-ASCII JSON).
            for chunk in response.iter_content(chunk_size=8192):
                if not chunk:
                    continue
                buf += chunk
                while b"\n" in buf:
                    raw, buf = buf.split(b"\n", 1)
                    line = raw.rstrip(b"\r").decode("utf-8", errors="replace")
                    if line.startswith("event:"):
                        event = line[len("event:") :].strip()
                    elif line.startswith("data:"):
                        data = line[len("data:") :].strip()
                    elif line == "":
                        # Blank line terminates an SSE frame — dispatch it.
                        if event is None or data is None:
                            event = data = None
                            continue
                        obj = json.loads(data)
                        if event == "output":
                            yield CIStreamEvent(
                                kind="output",
                                stream=obj["stream"],
                                data=obj["data"],
                            )
                        elif event == "result":
                            yield CIStreamEvent(
                                kind="result",
                                result=ExecuteResponse(
                                    stdout="",
                                    stderr="",
                                    exit_code=obj.get("exit_code"),
                                    timed_out=obj.get("timed_out", False),
                                    duration_ms=obj.get("duration_ms", 0),
                                    error_kind=obj.get("error_kind"),
                                    files=[WorkspaceFile(**f) for f in obj.get("files", [])],
                                ),
                            )
                        elif event == "error":
                            raise RuntimeError(
                                obj.get("message", "code interpreter stream error")
                            )
                        event = data = None

    def upload_file(self, file_content: bytes, filename: str) -> str:
        """Upload file to Code Interpreter and return file_id"""
        url = f"{self.base_url}/v1/files"

        files = {"file": (filename, file_content)}
        response = self.session.post(
            url, files=files, headers=self._tenant_headers(), timeout=30
        )
        _check_response(response)

        return response.json()["file_id"]

    def download_file(self, file_id: str) -> bytes:
        """Download file from Code Interpreter"""
        url = f"{self.base_url}/v1/files/{file_id}"

        response = self.session.get(url, headers=self._tenant_headers(), timeout=30)
        _check_response(response)

        return response.content

    def delete_file(self, file_id: str) -> None:
        """Delete file from Code Interpreter"""
        url = f"{self.base_url}/v1/files/{file_id}"

        response = self.session.delete(url, headers=self._tenant_headers(), timeout=10)
        _check_response(response)
