"""Sticky notes over the real API: create, read, update, delete and who may do what.

Needs a running stack: PULSE_API_URL and an admin PULSE_API_KEY (the same settings the
Pulse live tests use).
"""

import os
import uuid
from collections.abc import Generator
from typing import Any

import pytest
import requests

API = os.environ.get("PULSE_API_URL", "").rstrip("/")
KEY = os.environ.get("PULSE_API_KEY", "")

pytestmark = pytest.mark.skipif(not (API and KEY), reason="stack not configured")

CODE = "def main(inputs):\n    return {'r': 'ok'}\n"


class Client:
    def __init__(self, key: str) -> None:
        self.s = requests.Session()
        self.s.headers["Authorization"] = f"Bearer {key}"

    def get(self, path: str) -> requests.Response:
        return self.s.get(API + path, timeout=60)

    def post(self, path: str, body: Any = None) -> requests.Response:
        return self.s.post(API + path, json=body, timeout=60)

    def patch(self, path: str, body: Any) -> requests.Response:
        return self.s.patch(API + path, json=body, timeout=60)

    def delete(self, path: str) -> requests.Response:
        return self.s.delete(API + path, timeout=60)


@pytest.fixture(scope="module")
def admin() -> Client:
    return Client(KEY)


@pytest.fixture(scope="module")
def basic(admin: Client) -> Client:
    r = admin.post("/admin/api-key", {"name": f"notes-basic-{uuid.uuid4().hex[:6]}", "role": "basic"})
    assert r.ok, r.text
    return Client(r.json()["api_key"])


def _step(order: int, name: str) -> dict:
    return {
        "step_type": "code",
        "step_order": order,
        "step_name": name,
        "output_key": f"out_{order}",
        "is_terminal": order == 1,
        "config": {"code": CODE, "inputs": {}, "outputs": [{"name": "r", "type": "string"}], "timeout_seconds": 5},
    }


def _new_workflow(admin: Client, *, public: bool = True) -> dict:
    r = admin.post(
        "/admin/workflow",
        {
            "name": f"notes-it-{uuid.uuid4().hex[:6]}",
            "orchestration_mode": "sequential",
            "is_public": public,
            "steps": [_step(0, "First"), _step(1, "Second")],
        },
    )
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture
def workflow(admin: Client) -> Generator[dict, None, None]:
    made = _new_workflow(admin)
    yield made
    admin.delete(f"/admin/workflow/{made['id']}")


def _notes_url(workflow: dict) -> str:
    return f"/admin/workflow/{workflow['id']}/notes"


def test_full_crud(admin: Client, workflow: dict) -> None:
    key = workflow["steps"][0]["node_key"]
    r = admin.post(_notes_url(workflow), {"x": 30, "y": 45, "text": "# Intake\nReads the FIR", "color": "green", "step_node_key": key})
    assert r.status_code == 200, r.text
    note = r.json()
    assert (note["color"], note["step_node_key"], note["version"]) == ("green", key, 1)

    listed = admin.get(f"/workflow/{workflow['id']}/notes").json()
    assert [n["id"] for n in listed] == [note["id"]]
    with_workflow = admin.get(f"/workflow/{workflow['id']}").json()
    assert [n["id"] for n in with_workflow["notes"]] == [note["id"]]

    r = admin.patch(f"{_notes_url(workflow)}/{note['id']}", {"expected_version": 1, "text": "edited", "width": 320, "height": 200})
    assert r.status_code == 200, r.text
    assert (r.json()["text"], r.json()["width"], r.json()["version"]) == ("edited", 320, 2)

    assert admin.delete(f"{_notes_url(workflow)}/{note['id']}").status_code == 200
    assert admin.get(f"/workflow/{workflow['id']}/notes").json() == []
    assert admin.delete(f"{_notes_url(workflow)}/{note['id']}").status_code == 404


def test_a_stale_edit_gets_409(admin: Client, workflow: dict) -> None:
    note = admin.post(_notes_url(workflow), {"x": 0, "y": 0}).json()
    assert admin.patch(f"{_notes_url(workflow)}/{note['id']}", {"expected_version": 1, "text": "a"}).ok
    r = admin.patch(f"{_notes_url(workflow)}/{note['id']}", {"expected_version": 1, "text": "b"})
    assert r.status_code == 409


def test_bad_input_gets_400_or_422(admin: Client, workflow: dict) -> None:
    assert admin.post(_notes_url(workflow), {"x": 0, "y": 0, "color": "red"}).status_code == 422
    assert admin.post(_notes_url(workflow), {"x": 0, "y": 0, "step_node_key": "n_nothere"}).status_code == 400
    assert admin.post("/admin/workflow/999999999/notes", {"x": 0, "y": 0}).status_code == 404


def test_notes_do_not_create_workflow_versions(admin: Client, workflow: dict) -> None:
    before = admin.get(f"/workflow/{workflow['id']}/versions").json()
    note = admin.post(_notes_url(workflow), {"x": 0, "y": 0}).json()
    admin.patch(f"{_notes_url(workflow)}/{note['id']}", {"expected_version": 1, "text": "x"})
    after = admin.get(f"/workflow/{workflow['id']}/versions").json()
    assert len(after) == len(before)
    assert admin.get(f"/workflow/{workflow['id']}").json()["version"] == workflow["version"]


def test_a_basic_user_can_read_but_not_change(admin: Client, basic: Client, workflow: dict) -> None:
    note = admin.post(_notes_url(workflow), {"x": 0, "y": 0, "text": "visible"}).json()
    assert [n["text"] for n in basic.get(f"/workflow/{workflow['id']}/notes").json()] == ["visible"]
    assert basic.post(_notes_url(workflow), {"x": 0, "y": 0}).status_code == 403
    assert basic.patch(f"{_notes_url(workflow)}/{note['id']}", {"expected_version": 1, "text": "no"}).status_code == 403
    assert basic.delete(f"{_notes_url(workflow)}/{note['id']}").status_code == 403


def test_a_private_workflows_notes_are_private(admin: Client, basic: Client) -> None:
    private = _new_workflow(admin, public=False)
    try:
        admin.post(f"/admin/workflow/{private['id']}/notes", {"x": 0, "y": 0, "text": "secret"})
        assert basic.get(f"/workflow/{private['id']}/notes").status_code == 403
    finally:
        admin.delete(f"/admin/workflow/{private['id']}")


def test_a_note_belongs_to_its_own_workflow(admin: Client, workflow: dict) -> None:
    other = _new_workflow(admin)
    try:
        note = admin.post(f"/admin/workflow/{other['id']}/notes", {"x": 0, "y": 0}).json()
        assert admin.patch(f"{_notes_url(workflow)}/{note['id']}", {"expected_version": 1, "text": "x"}).status_code == 404
        assert admin.delete(f"{_notes_url(workflow)}/{note['id']}").status_code == 404
    finally:
        admin.delete(f"/admin/workflow/{other['id']}")
