import json
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Literal
from typing import TypedDict

import requests
from pydantic import BaseModel

from om.configs.app_configs import CODE_INTERPRETER_BASE_URL
from om.utils.logger import setup_logger

logger = setup_logger()


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

    def __init__(self, base_url: str | None = CODE_INTERPRETER_BASE_URL):
        if not base_url:
            raise ValueError("CODE_INTERPRETER_BASE_URL not configured")
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()

    def create_session(self) -> str:
        """Create a persistent execution session. Returns session_id."""
        url = f"{self.base_url}/v1/sessions"
        response = self.session.post(url, timeout=30)
        response.raise_for_status()
        return response.json()["session_id"]

    def delete_session(self, session_id: str) -> None:
        """Destroy a persistent execution session."""
        url = f"{self.base_url}/v1/sessions/{session_id}"
        response = self.session.delete(url, timeout=10)
        response.raise_for_status()

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

        response = self.session.post(url, json=payload, timeout=timeout_ms / 1000 + 10)
        response.raise_for_status()

        return ExecuteResponse(**response.json())

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
            url, json=payload, stream=True, timeout=(10, timeout_ms / 1000 + 30)
        ) as response:
            response.raise_for_status()

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
        response = self.session.post(url, files=files, timeout=30)
        response.raise_for_status()

        return response.json()["file_id"]

    def download_file(self, file_id: str) -> bytes:
        """Download file from Code Interpreter"""
        url = f"{self.base_url}/v1/files/{file_id}"

        response = self.session.get(url, timeout=30)
        response.raise_for_status()

        return response.content

    def delete_file(self, file_id: str) -> None:
        """Delete file from Code Interpreter"""
        url = f"{self.base_url}/v1/files/{file_id}"

        response = self.session.delete(url, timeout=10)
        response.raise_for_status()
