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
