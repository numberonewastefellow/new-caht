"""Anything that talks to a third party must be opt-in: with no endpoint/recipient configured nothing leaves the box."""

from typing import Any
from unittest.mock import MagicMock

import pytest

from om.utils import telemetry
from om.utils.telemetry import RecordType


def test_telemetry_sends_nothing_without_an_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    thread_cls = MagicMock()
    monkeypatch.setattr(telemetry.threading, "Thread", thread_cls)
    monkeypatch.setattr(telemetry, "DISABLE_TELEMETRY", False)
    monkeypatch.setattr(telemetry, "OM_TELEMETRY_ENDPOINT", "")
    telemetry.optional_telemetry(record_type=RecordType.USAGE, data={"a": 1}, tenant_id="t")
    thread_cls.assert_not_called()


def test_telemetry_is_off_when_disabled_even_with_an_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    thread_cls = MagicMock()
    monkeypatch.setattr(telemetry.threading, "Thread", thread_cls)
    monkeypatch.setattr(telemetry, "DISABLE_TELEMETRY", True)
    monkeypatch.setattr(telemetry, "OM_TELEMETRY_ENDPOINT", "https://collector.example.test/t")
    telemetry.optional_telemetry(record_type=RecordType.USAGE, data={}, tenant_id="t")
    thread_cls.assert_not_called()


def test_telemetry_posts_to_the_configured_endpoint_only(monkeypatch: pytest.MonkeyPatch) -> None:
    posted: list[str] = []
    monkeypatch.setattr(telemetry.requests, "post", lambda url, **kw: posted.append(url))
    monkeypatch.setattr(telemetry, "DISABLE_TELEMETRY", False)
    monkeypatch.setattr(telemetry, "OM_TELEMETRY_ENDPOINT", "https://collector.example.test/t")
    monkeypatch.setattr(telemetry, "get_or_generate_uuid", lambda: "uuid-1")
    monkeypatch.setattr(telemetry, "_get_or_generate_instance_domain", lambda: "example.test")

    class _InlineThread:
        def __init__(self, target: Any, daemon: bool = False) -> None:
            self._target = target

        def start(self) -> None:
            self._target()

    monkeypatch.setattr(telemetry.threading, "Thread", _InlineThread)
    telemetry.optional_telemetry(record_type=RecordType.USAGE, data={"a": 1}, tenant_id="t")
    assert posted == ["https://collector.example.test/t"]
    assert not any("onyx" in u for u in posted)


# ---- connector request email -------------------------------------------------------------

from om.server.documents import connector as connector_module  # noqa: E402
from om.server.documents.models import ConnectorRequestSubmission  # noqa: E402


@pytest.fixture
def sent_emails(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    sent: list[dict[str, Any]] = []
    monkeypatch.setattr(connector_module, "send_email", lambda **kw: sent.append(kw))
    monkeypatch.setattr(connector_module, "get_current_tenant_id", lambda: "public")
    monkeypatch.setattr(connector_module, "EMAIL_CONFIGURED", True)
    return sent


def test_connector_request_sends_no_email_without_a_configured_recipient(
    monkeypatch: pytest.MonkeyPatch, sent_emails: list[dict[str, Any]]
) -> None:
    monkeypatch.setattr(connector_module, "OM_CONNECTOR_REQUEST_EMAIL", "")
    connector_module.submit_connector_request(ConnectorRequestSubmission(connector_name="Foo"), user=None)
    assert sent_emails == []


def test_connector_request_emails_only_the_configured_recipient(
    monkeypatch: pytest.MonkeyPatch, sent_emails: list[dict[str, Any]]
) -> None:
    monkeypatch.setattr(connector_module, "OM_CONNECTOR_REQUEST_EMAIL", "ops@example.test")
    connector_module.submit_connector_request(ConnectorRequestSubmission(connector_name="Foo"), user=None)
    assert [e["user_email"] for e in sent_emails] == ["ops@example.test"]
