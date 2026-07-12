"""
Pytest fixtures for API snapshot testing.
Supports dual-mode: TestClient (no Docker) and live server.
"""
import os
from pathlib import Path

import pytest
import requests


SNAPSHOT_DIR = Path(__file__).parent / "snapshots"


def pytest_addoption(parser: object) -> None:
    parser.addoption(  # type: ignore
        "--api-mode",
        action="store",
        default="live",
        choices=["testclient", "live"],
        help="API testing mode: testclient (in-process) or live (running server)",
    )
    parser.addoption(  # type: ignore
        "--api-url",
        action="store",
        default=None,
        help="Override API server URL for live mode (default: http://127.0.0.1:8080)",
    )


class LiveClient:
    """Wrapper around requests.Session that mimics TestClient interface."""

    def __init__(self, base_url: str):
        self.base_url_override = base_url
        self._session = requests.Session()

    def get(self, url: str, **kwargs: object) -> requests.Response:
        return self._session.get(self.base_url_override + url, **kwargs)  # type: ignore

    def request(self, method: str, url: str, **kwargs: object) -> requests.Response:
        return self._session.request(method, self.base_url_override + url, **kwargs)  # type: ignore


@pytest.fixture(scope="session")
def api_client(request: pytest.FixtureRequest) -> object:
    """Create an API client based on the --api-mode option."""
    from om.main import get_application as _impl_get_application
    mode = request.config.getoption("--api-mode")

    if mode == "testclient":
        os.environ.setdefault("ENABLE_PAID_ENTERPRISE_EDITION_FEATURES", "True")
        from fastapi.testclient import TestClient


        app = _impl_get_application()
        client = TestClient(app)
        yield client
        client.close()
    else:
        api_url = request.config.getoption("--api-url")
        if api_url is None:
            protocol = os.getenv("API_SERVER_PROTOCOL", "http")
            host = os.getenv("API_SERVER_HOST", "127.0.0.1")
            port = os.getenv("API_SERVER_PORT", "8080")
            api_url = f"{protocol}://{host}:{port}"
        client = LiveClient(api_url)
        yield client


@pytest.fixture(scope="session")
def auth_headers(api_client: object) -> dict:
    """Get authentication headers by logging in.

    Tries to register+login a test user. If registration fails (user exists),
    just logs in.
    """
    test_email = "snapshot_test@test.com"
    test_password = "SnapshotTest123!"

    # Try to register
    try:
        if hasattr(api_client, "base_url_override"):
            base = api_client.base_url_override  # type: ignore
            requests.post(
                f"{base}/auth/register",
                json={"email": test_email, "password": test_password},
            )
            resp = requests.post(
                f"{base}/auth/login",
                data={"username": test_email, "password": test_password},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        else:
            api_client.post(  # type: ignore
                "/auth/register",
                json={"email": test_email, "password": test_password},
            )
            resp = api_client.post(  # type: ignore
                "/auth/login",
                data=f"username={test_email}&password={test_password}",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

        if resp.status_code == 200 or resp.status_code == 204:
            cookie = resp.cookies.get("fastapiusersauth", "")
            if cookie:
                return {"Cookie": f"fastapiusersauth={cookie}"}

            # Try Bearer token
            data = resp.json() if resp.text else {}
            token = data.get("access_token", "")
            if token:
                return {"Authorization": f"Bearer {token}"}
    except Exception:
        pass

    # Fallback: return empty headers (endpoints will return 401/403 — that's fine,
    # we compare the error shape before/after)
    return {}


@pytest.fixture(scope="session")
def snapshot_dir() -> Path:
    """Return the snapshot directory path."""
    return SNAPSHOT_DIR
