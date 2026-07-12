from typing import Any
from unittest.mock import Mock

from om.configs.constants import MilestoneRecordType
from om.utils import telemetry as telemetry_utils


def test_mt_cloud_telemetry_noop_when_not_multi_tenant(monkeypatch: Any) -> None:
    event_telemetry = Mock()
    monkeypatch.setattr(telemetry_utils, "event_telemetry", event_telemetry)
    # mt_cloud_telemetry reads the module-local imported symbol, so patch this path.
    monkeypatch.setattr("om.utils.telemetry.MULTI_TENANT", False)

    telemetry_utils.mt_cloud_telemetry(
        tenant_id="tenant-1",
        distinct_id="user@example.com",
        event=MilestoneRecordType.USER_MESSAGE_SENT,
        properties={"origin": "web"},
    )

    event_telemetry.assert_not_called()


def test_mt_cloud_telemetry_calls_event_telemetry_when_multi_tenant(
    monkeypatch: Any,
) -> None:
    event_telemetry = Mock()
    monkeypatch.setattr(telemetry_utils, "event_telemetry", event_telemetry)
    # mt_cloud_telemetry reads the module-local imported symbol, so patch this path.
    monkeypatch.setattr("om.utils.telemetry.MULTI_TENANT", True)

    telemetry_utils.mt_cloud_telemetry(
        tenant_id="tenant-1",
        distinct_id="user@example.com",
        event=MilestoneRecordType.USER_MESSAGE_SENT,
        properties={"origin": "web"},
    )

    event_telemetry.assert_called_once_with(
        "user@example.com",
        MilestoneRecordType.USER_MESSAGE_SENT,
        {"origin": "web", "tenant_id": "tenant-1"},
    )
