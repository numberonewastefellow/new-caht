"""Shared fixtures for persistent session tests.

These tests require a running code-interpreter service at localhost:8000
with Docker available. They exercise the real session lifecycle
(container creation, kernel communication, cleanup).
"""

from __future__ import annotations

import io
import pathlib
from typing import Generator

import pytest
import requests

BASE_URL = "http://localhost:8000"
SAMPLE_DATA_DIR = pathlib.Path(__file__).parent / "sample_data"


def _is_service_running() -> bool:
    """Check if code-interpreter service is reachable."""
    try:
        resp = requests.get(f"{BASE_URL}/health", timeout=3)
        return resp.status_code == 200
    except requests.ConnectionError:
        return False


# Skip entire module if service is not running
pytestmark = pytest.mark.skipif(
    not _is_service_running(),
    reason="Code-interpreter service not running at localhost:8000",
)


@pytest.fixture()
def api() -> requests.Session:
    """Return a requests Session pointed at the service.

    Note: Do NOT set Content-Type globally — it interferes with
    multipart file uploads.  Use ``json=`` for JSON requests instead.
    """
    return requests.Session()


@pytest.fixture()
def session_id(api: requests.Session) -> Generator[str, None, None]:
    """Create a session, yield its id, then delete it."""
    resp = api.post(f"{BASE_URL}/v1/sessions")
    assert resp.status_code == 201, f"Failed to create session: {resp.text}"
    sid = resp.json()["session_id"]
    yield sid
    # Cleanup: delete session (ignore errors if already deleted by test)
    api.delete(f"{BASE_URL}/v1/sessions/{sid}")


def execute_in_session(
    api: requests.Session,
    session_id: str,
    code: str,
    timeout_ms: int = 30_000,
    files: list[dict] | None = None,
) -> dict:
    """Helper: execute code in a session and return the response payload."""
    payload: dict = {
        "code": code,
        "timeout_ms": timeout_ms,
        "session_id": session_id,
    }
    if files:
        payload["files"] = files
    resp = api.post(f"{BASE_URL}/v1/execute", json=payload)
    assert resp.status_code == 200, f"Execution failed ({resp.status_code}): {resp.text}"
    return resp.json()


def execute_ephemeral(
    api: requests.Session,
    code: str,
    timeout_ms: int = 10_000,
) -> dict:
    """Helper: execute code ephemerally (no session)."""
    resp = api.post(
        f"{BASE_URL}/v1/execute",
        json={"code": code, "timeout_ms": timeout_ms},
    )
    assert resp.status_code == 200, f"Execution failed: {resp.text}"
    return resp.json()


def upload_file(api: requests.Session, filename: str, content: bytes) -> str:
    """Upload a file and return its file_id."""
    resp = api.post(
        f"{BASE_URL}/v1/files",
        files={"file": (filename, io.BytesIO(content), "application/octet-stream")},
    )
    assert resp.status_code == 201, f"Upload failed: {resp.text}"
    return resp.json()["file_id"]


def read_sample(name: str) -> bytes:
    """Read a file from the sample_data directory."""
    return (SAMPLE_DATA_DIR / name).read_bytes()
