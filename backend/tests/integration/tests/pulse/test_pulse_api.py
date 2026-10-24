"""Pulse API integration tests (live api_server + pulse_scheduler + pulse_worker).

Environment:
    PULSE_API_URL   base URL of the api server (default http://localhost:8090)
    PULSE_API_KEY   an ADMIN api key for that server
    PULSE_WORKFLOW_ID  a small, public workflow to execute (default 1)
The server must run with PULSE_MIN_INTERVAL_SECONDS<=60 for the auto-fire test.
These tests make real LLM calls (a few short workflow runs).
"""

import os
import time
import uuid
from collections.abc import Generator

import pytest
import requests

BASE = os.environ.get("PULSE_API_URL", "http://localhost:8090").rstrip("/")
KEY = os.environ.get("PULSE_API_KEY", "")
WORKFLOW_ID = int(os.environ.get("PULSE_WORKFLOW_ID", "1"))

pytestmark = pytest.mark.skipif(not KEY, reason="PULSE_API_KEY not set")

TERMINAL = {
    "succeeded",
    "needs_input",
    "failed",
    "timed_out",
    "cancelled",
    "interrupted",
    "skipped",
    "missed",
}


class Client:
    def __init__(self, key: str) -> None:
        self.s = requests.Session()
        self.s.headers["Authorization"] = f"Bearer {key}"

    def get(self, path: str, **kw: object) -> requests.Response:
        return self.s.get(BASE + path, timeout=60, **kw)  # type: ignore[arg-type]

    def post(self, path: str, json: object = None) -> requests.Response:
        return self.s.post(BASE + path, json=json, timeout=60)

    def patch(self, path: str, json: object) -> requests.Response:
        return self.s.patch(BASE + path, json=json, timeout=60)

    def delete(self, path: str) -> requests.Response:
        return self.s.delete(BASE + path, timeout=60)


@pytest.fixture(scope="module")
def admin() -> Client:
    return Client(KEY)


@pytest.fixture(scope="module")
def basic_user(admin: Client) -> Client:
    r = admin.post(
        "/admin/api-key", {"name": f"pulse-basic-{uuid.uuid4().hex[:6]}", "role": "basic"}
    )
    assert r.ok, r.text
    return Client(r.json()["api_key"])


@pytest.fixture
def schedules(admin: Client) -> Generator[list[int], None, None]:
    created: list[int] = []
    yield created
    for sid in created:
        admin.delete(f"/pulse/schedules/{sid}")


def _create(client: Client, created: list[int], **overrides: object) -> dict:
    body: dict = {
        "workflow_id": WORKFLOW_ID,
        "name": "it-" + uuid.uuid4().hex[:6],
        "schedule_type": "interval",
        "interval_seconds": 3600,
        "timezone": "UTC",
        "input_message": "Reply with one short sentence. Date: {{date}}.",
        "enabled": True,
    }
    body.update(overrides)
    r = client.post("/pulse/schedules", body)
    assert r.status_code == 200, r.text
    data = r.json()
    created.append(data["id"])
    return data


def _wait_run(client: Client, run_id: int, timeout: float = 240) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        run = client.get(f"/pulse/runs/{run_id}").json()
        if run["status"] in TERMINAL:
            return run
        time.sleep(3)
    raise AssertionError(f"run {run_id} did not finish in {timeout}s: {run}")


# ---------------------------------------------------------------- config / preview


def test_config(admin: Client) -> None:
    cfg = admin.get("/pulse/config").json()
    assert cfg["template_variables"] == ["date", "now", "window_start", "window_end"]
    assert cfg["min_interval_seconds"] > 0


def test_preview_valid_and_dst(admin: Client) -> None:
    r = admin.post(
        "/pulse/preview",
        {"schedule_type": "cron", "cron_expression": "0 9 * * 1-5", "timezone": "America/New_York"},
    ).json()
    assert r["valid"] is True
    assert r["description"] == "Every weekday at 09:00 (America/New_York)"
    assert len(r["next_runs"]) == 5


@pytest.mark.parametrize(
    "body,fragment",
    [
        ({"schedule_type": "cron", "cron_expression": "* * * * *", "timezone": "UTC"}, "too often"),
        ({"schedule_type": "cron", "cron_expression": "0 9 * *", "timezone": "UTC"}, "5 fields"),
        ({"schedule_type": "interval", "interval_seconds": 5, "timezone": "UTC"}, "at least"),
        ({"schedule_type": "cron", "cron_expression": "0 9 * * *", "timezone": "Mars/Base"}, "timezone"),
    ],
)
def test_preview_invalid(admin: Client, body: dict, fragment: str) -> None:
    if fragment == "too often" and admin.get("/pulse/config").json()["min_interval_seconds"] <= 60:
        pytest.skip("an every-minute cron is allowed when the server minimum is <= 60s")
    r = admin.post("/pulse/preview", body).json()
    assert r["valid"] is False
    assert fragment in r["error"]


# ---------------------------------------------------------------- CRUD + validation


def test_crud_lifecycle(admin: Client, schedules: list[int]) -> None:
    s = _create(admin, schedules, schedule_type="cron", interval_seconds=None,
                cron_expression="0 9 * * *", timezone="Asia/Kolkata")
    assert s["description"] == "Every day at 09:00 (Asia/Kolkata)"
    assert s["next_run_at"].endswith(("03:30:00Z", "03:30:00+00:00"))

    # edit timing -> next_run_at recomputed
    r = admin.patch(f"/pulse/schedules/{s['id']}", {"cron_expression": "30 18 * * 1-5"})
    assert r.ok, r.text
    s2 = r.json()
    assert s2["description"].startswith("Every weekday at 18:30")
    assert s2["next_run_at"] != s["next_run_at"]

    # switch type -> stale fields cleared
    s3 = admin.patch(f"/pulse/schedules/{s['id']}", {"schedule_type": "interval", "interval_seconds": 7200}).json()
    assert s3["cron_expression"] is None and s3["interval_seconds"] == 7200

    # pause / resume
    assert admin.patch(f"/pulse/schedules/{s['id']}", {"enabled": False}).json()["enabled"] is False
    resumed = admin.patch(f"/pulse/schedules/{s['id']}", {"enabled": True}).json()
    assert resumed["enabled"] is True and resumed["disabled_reason"] is None

    # duplicate starts paused
    dup = admin.post(f"/pulse/schedules/{s['id']}/duplicate").json()
    schedules.append(dup["id"])
    assert dup["enabled"] is False and dup["name"].endswith("(copy)")

    assert admin.delete(f"/pulse/schedules/{s['id']}").ok
    assert admin.get(f"/pulse/schedules/{s['id']}").status_code == 404


def test_create_validation_errors(admin: Client, schedules: list[int]) -> None:
    base = {
        "workflow_id": WORKFLOW_ID,
        "name": "bad",
        "timezone": "UTC",
        "input_message": "x",
    }
    assert admin.post("/pulse/schedules", {**base, "schedule_type": "interval", "interval_seconds": 1}).status_code == 400
    assert admin.post("/pulse/schedules", {**base, "schedule_type": "cron", "cron_expression": "nope"}).status_code == 400
    assert admin.post("/pulse/schedules", {**base, "schedule_type": "once", "run_at": "2020-01-01T00:00:00Z"}).status_code == 400
    assert admin.post("/pulse/schedules", {**base, "workflow_id": 99999999, "schedule_type": "interval", "interval_seconds": 3600}).status_code == 404
    assert admin.post("/pulse/schedules", {**base, "schedule_type": "interval", "interval_seconds": 3600, "retention_count": 0}).status_code == 400


def test_other_users_cannot_see_or_touch(admin: Client, basic_user: Client, schedules: list[int]) -> None:
    s = _create(admin, schedules)
    assert basic_user.get(f"/pulse/schedules/{s['id']}").status_code == 404
    assert basic_user.patch(f"/pulse/schedules/{s['id']}", {"enabled": False}).status_code == 404
    assert basic_user.post(f"/pulse/schedules/{s['id']}/run-now").status_code == 404
    assert basic_user.delete(f"/pulse/schedules/{s['id']}").status_code == 404
    assert all(x["id"] != s["id"] for x in basic_user.get("/pulse/schedules").json())
    # admins can list everyone's
    assert any(x["id"] == s["id"] for x in admin.get("/pulse/schedules?all_users=true").json())


# ---------------------------------------------------------------- execution


def test_run_now_end_to_end(admin: Client, schedules: list[int]) -> None:
    s = _create(admin, schedules, enabled=False)
    run = admin.post(f"/pulse/schedules/{s['id']}/run-now").json()
    assert run["trigger"] == "manual" and run["status"] in ("pending", "running")

    # a second run-now while the first is active is rejected
    assert admin.post(f"/pulse/schedules/{s['id']}/run-now").status_code == 409

    done = _wait_run(admin, run["id"])
    assert done["status"] == "succeeded", done
    assert done["chat_session_id"]
    assert done["output_preview"]
    assert done["duration_ms"] and done["duration_ms"] > 0

    cs = done["chat_session_id"]
    detail = admin.get(f"/converse/get-chat-session/{cs}").json()
    assert detail["pulse_schedule_id"] == s["id"]
    user_msgs = [m for m in detail["messages"] if m["message_type"] == "user"]
    assert user_msgs and "{{date}}" not in user_msgs[0]["message"]  # template rendered

    default_ids = {x["id"] for x in admin.get("/converse/get-user-chat-sessions").json()["sessions"]}
    all_ids = {x["id"] for x in admin.get("/converse/get-user-chat-sessions?include_scheduled=true").json()["sessions"]}
    assert cs not in default_ids
    assert cs in all_ids

    sched = admin.get(f"/pulse/schedules/{s['id']}").json()
    assert sched["last_run_status"] == "succeeded"
    assert sched["latest_chat_session_id"] == cs
    side = {x["schedule_id"]: x for x in admin.get("/pulse/sidebar").json()}
    assert side[s["id"]]["latest_chat_session_id"] == cs


def test_auto_fire_interval_no_duplicates(admin: Client, schedules: list[int]) -> None:
    cfg = admin.get("/pulse/config").json()
    if cfg["min_interval_seconds"] > 60:
        pytest.skip("server minimum interval > 60s")
    s = _create(admin, schedules, interval_seconds=60)
    deadline = time.time() + 200
    runs: list[dict] = []
    while time.time() < deadline:
        runs = [r for r in admin.get(f"/pulse/schedules/{s['id']}/runs").json() if r["trigger"] == "scheduled"]
        if sum(r["status"] in TERMINAL for r in runs) >= 2:
            break
        time.sleep(5)
    slots = [r["scheduled_for"] for r in runs]
    assert len(slots) == len(set(slots)), "a slot fired twice"
    assert sum(r["status"] == "succeeded" for r in runs) >= 2, runs


def test_paused_schedule_does_not_fire(admin: Client, schedules: list[int]) -> None:
    cfg = admin.get("/pulse/config").json()
    if cfg["min_interval_seconds"] > 60:
        pytest.skip("server minimum interval > 60s")
    s = _create(admin, schedules, interval_seconds=60, enabled=False)
    time.sleep(75)
    assert admin.get(f"/pulse/schedules/{s['id']}/runs").json() == []


def test_health_reports_replicas(admin: Client) -> None:
    h = admin.get("/admin/pulse/health").json()
    assert h["scheduler_replicas_alive"] >= 1
    assert h["scheduler_lag_seconds"] is not None and h["scheduler_lag_seconds"] < 60
