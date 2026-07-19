"""Structured-logging tests: prove OpenSearch-style events carry the mandated
fields (Standard 9) and that emission never breaks the caller."""

import json
from unittest.mock import MagicMock

import pytest

import om.standard_answers.events as events
from om.standard_answers.events import (
    EVENT_LOG_PREFIX,
    SAAction,
    SAEntity,
    SAEvent,
    SAStatus,
    emit_event,
    logged_operation,
)

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


def _captured_payload(mock_logger: MagicMock) -> dict:
    # Prefer .info (success) but fall back to .error (failure path).
    call = mock_logger.info.call_args or mock_logger.error.call_args
    line = call.args[0]
    assert line.startswith(EVENT_LOG_PREFIX)
    return json.loads(line[len(EVENT_LOG_PREFIX) :])


def test_emit_event_has_all_required_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_logger = MagicMock()
    monkeypatch.setattr(events, "logger", mock_logger)

    emit_event(
        event=SAEvent.CREATED,
        entity=SAEntity.STANDARD_ANSWER,
        action=SAAction.CREATE,
        status=SAStatus.SUCCESS,
        entity_id=7,
        actor_user_id="user-1",
        duration_ms=12.345,
    )

    payload = _captured_payload(mock_logger)
    assert REQUIRED_FIELDS.issubset(payload.keys())
    assert payload["event"] == "standard_answer.created"
    assert payload["entity_id"] == 7
    assert payload["actor_user_id"] == "user-1"
    assert payload["status"] == "success"
    assert payload["duration_ms"] == 12.35  # rounded to 2dp


def test_logged_operation_success_and_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_logger = MagicMock()
    monkeypatch.setattr(events, "logger", mock_logger)

    # success path emits at info with status=success and captures a set entity_id
    with logged_operation(
        event=SAEvent.UPDATED, entity=SAEntity.STANDARD_ANSWER, action=SAAction.UPDATE
    ) as ctx:
        ctx["entity_id"] = 99
    assert mock_logger.info.called
    ok = json.loads(mock_logger.info.call_args.args[0][len(EVENT_LOG_PREFIX) :])
    assert ok["status"] == "success" and ok["entity_id"] == 99

    # error path emits at error, includes the error text, and re-raises
    mock_logger.reset_mock()
    with pytest.raises(ValueError):
        with logged_operation(
            event=SAEvent.DELETED,
            entity=SAEntity.STANDARD_ANSWER,
            action=SAAction.DELETE,
            entity_id=5,
        ):
            raise ValueError("boom")
    assert mock_logger.error.called
    bad = json.loads(mock_logger.error.call_args.args[0][len(EVENT_LOG_PREFIX) :])
    assert bad["status"] == "error"
    assert "boom" in bad["error"]


def test_emit_never_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    # Even if the underlying logger blows up, emit_event must swallow it.
    exploding = MagicMock()
    exploding.info.side_effect = RuntimeError("logger down")
    exploding.error.side_effect = RuntimeError("logger down")
    monkeypatch.setattr(events, "logger", exploding)

    # Should not raise despite the logger failing.
    emit_event(
        event=SAEvent.MATCHED,
        entity=SAEntity.STANDARD_ANSWER,
        action=SAAction.MATCH,
        status=SAStatus.SUCCESS,
        entity_id=1,
    )
