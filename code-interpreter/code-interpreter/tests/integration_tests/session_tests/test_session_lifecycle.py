"""Tests for session create / delete / error handling lifecycle."""

from __future__ import annotations

import requests

from .conftest import BASE_URL, execute_in_session


# ------------------------------------------------------------------
# Create & delete
# ------------------------------------------------------------------


def test_create_session_returns_session_id(api: requests.Session) -> None:
    """POST /v1/sessions returns 201 with a session_id string."""
    resp = api.post(f"{BASE_URL}/v1/sessions")
    assert resp.status_code == 201
    body = resp.json()
    assert "session_id" in body
    assert isinstance(body["session_id"], str)
    assert len(body["session_id"]) == 32  # hex uuid4

    # Cleanup
    api.delete(f"{BASE_URL}/v1/sessions/{body['session_id']}")


def test_delete_session_returns_204(
    api: requests.Session, session_id: str
) -> None:
    """DELETE /v1/sessions/{id} returns 204 and removes the session."""
    resp = api.delete(f"{BASE_URL}/v1/sessions/{session_id}")
    assert resp.status_code == 204

    # Verify session is gone
    resp2 = api.post(
        f"{BASE_URL}/v1/execute",
        json={"code": "print(1)", "timeout_ms": 5000, "session_id": session_id},
    )
    assert resp2.status_code == 404


def test_delete_nonexistent_session_returns_404(api: requests.Session) -> None:
    """DELETE on a fake session_id should 404."""
    resp = api.delete(f"{BASE_URL}/v1/sessions/does_not_exist_1234567890ab")
    assert resp.status_code == 404


def test_execute_with_invalid_session_returns_404(api: requests.Session) -> None:
    """Executing against a session that doesn't exist should 404."""
    resp = api.post(
        f"{BASE_URL}/v1/execute",
        json={
            "code": "print('nope')",
            "timeout_ms": 5000,
            "session_id": "nonexistent_session_id_abc123",
        },
    )
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


# ------------------------------------------------------------------
# Backward compatibility — ephemeral still works
# ------------------------------------------------------------------


def test_ephemeral_execution_still_works(api: requests.Session) -> None:
    """POST /v1/execute without session_id should still work (backward compat)."""
    resp = api.post(
        f"{BASE_URL}/v1/execute",
        json={"code": "print('ephemeral')", "timeout_ms": 10000},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["stdout"] == "ephemeral\n"
    assert body["exit_code"] == 0
    assert body["timed_out"] is False


# ------------------------------------------------------------------
# Multiple sessions are independent
# ------------------------------------------------------------------


def test_multiple_sessions_independent(api: requests.Session) -> None:
    """Two sessions should not share state."""
    # Create two sessions
    r1 = api.post(f"{BASE_URL}/v1/sessions")
    r2 = api.post(f"{BASE_URL}/v1/sessions")
    assert r1.status_code == 201
    assert r2.status_code == 201
    sid1 = r1.json()["session_id"]
    sid2 = r2.json()["session_id"]

    try:
        # Set x=100 in session 1
        out1 = execute_in_session(api, sid1, "x = 100\nprint(x)")
        assert out1["stdout"] == "100\n"

        # Set x=999 in session 2
        out2 = execute_in_session(api, sid2, "x = 999\nprint(x)")
        assert out2["stdout"] == "999\n"

        # Session 1 still has x=100
        out3 = execute_in_session(api, sid1, "print(x)")
        assert out3["stdout"] == "100\n"

        # Session 2 still has x=999
        out4 = execute_in_session(api, sid2, "print(x)")
        assert out4["stdout"] == "999\n"
    finally:
        api.delete(f"{BASE_URL}/v1/sessions/{sid1}")
        api.delete(f"{BASE_URL}/v1/sessions/{sid2}")
