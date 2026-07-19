"""Clean-room tests for SCIM structured logging (Standard 9)."""

import json

import pytest

from om.server.scim import scim_logging


class _CaptureLogger:
    def __init__(self) -> None:
        self.records: list[tuple[str, str]] = []

    def info(self, msg: str) -> None:
        self.records.append(("info", msg))

    def error(self, msg: str) -> None:
        self.records.append(("error", msg))

    def exception(self, msg: str) -> None:  # pragma: no cover - safety net
        self.records.append(("exception", msg))


REQUIRED_FIELDS = {
    "event",
    "entity",
    "entity_id",
    "tenant_id",
    "actor_user_id",
    "action",
    "status",
    "duration_ms",
    "error",
}


@pytest.fixture
def capture(monkeypatch: pytest.MonkeyPatch) -> _CaptureLogger:
    logger = _CaptureLogger()
    monkeypatch.setattr(scim_logging, "logger", logger)
    return logger


def test_log_scim_event_emits_all_standard9_fields(capture: _CaptureLogger) -> None:
    scim_logging.log_scim_event(
        event=scim_logging.EVENT_USER_PROVISIONED,
        entity=scim_logging.ENTITY_USER,
        action="create",
        status=scim_logging.STATUS_SUCCESS,
        entity_id="u1",
        actor_user_id="admin-1",
        tenant_id="public",
        duration_ms=12.345,
    )
    level, msg = capture.records[-1]
    payload = json.loads(msg)
    assert REQUIRED_FIELDS <= set(payload)
    assert level == "info"
    assert payload["event"] == "scim.user_provisioned"
    assert payload["entity_id"] == "u1"
    assert payload["duration_ms"] == 12.35  # rounded to 2dp


def test_scim_operation_logs_success_with_duration(capture: _CaptureLogger) -> None:
    with scim_logging.scim_operation(
        event=scim_logging.EVENT_GROUP_SYNCED,
        entity=scim_logging.ENTITY_TEAM,
        action="create",
        tenant_id="public",
    ) as op:
        op.entity_id = 7
    payload = json.loads(capture.records[-1][1])
    assert payload["status"] == "success"
    assert payload["entity_id"] == "7"
    assert payload["duration_ms"] is not None


def test_scim_operation_logs_error_and_reraises(capture: _CaptureLogger) -> None:
    with pytest.raises(ValueError):
        with scim_logging.scim_operation(
            event=scim_logging.EVENT_USER_UPDATED,
            entity=scim_logging.ENTITY_USER,
            action="update",
        ):
            raise ValueError("boom")
    level, msg = capture.records[-1]
    payload = json.loads(msg)
    assert level == "error"
    assert payload["status"] == "error"
    assert "boom" in payload["error"]
