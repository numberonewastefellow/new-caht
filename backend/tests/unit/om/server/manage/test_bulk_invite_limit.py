"""Test bulk invite limit for free trial tenants."""

from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from om.server.manage.users import bulk_invite_users


@patch("om.server.manage.users.MULTI_TENANT", True)
@patch("om.server.manage.users.is_tenant_on_trial_fn", return_value=True)
@patch("om.server.manage.users.get_current_tenant_id", return_value="test_tenant")
@patch("om.server.manage.users.get_invited_users", return_value=[])
@patch("om.server.manage.users.get_all_users", return_value=[])
@patch("om.server.manage.users.NUM_FREE_TRIAL_USER_INVITES", 5)
def test_trial_tenant_cannot_exceed_invite_limit(*_mocks: None) -> None:
    """Trial tenants cannot invite more users than the configured limit."""
    emails = [f"user{i}@example.com" for i in range(6)]

    with pytest.raises(HTTPException) as exc_info:
        bulk_invite_users(emails=emails)

    assert exc_info.value.status_code == 403
    assert "invite limit" in exc_info.value.detail.lower()


@patch("om.server.manage.users.MULTI_TENANT", True)
@patch("om.server.manage.users.DEV_MODE", True)
@patch("om.server.manage.users.ENABLE_EMAIL_INVITES", False)
@patch("om.server.manage.users.is_tenant_on_trial_fn", return_value=True)
@patch("om.server.manage.users.get_current_tenant_id", return_value="test_tenant")
@patch("om.server.manage.users.get_invited_users", return_value=[])
@patch("om.server.manage.users.get_all_users", return_value=[])
@patch("om.server.manage.users.write_invited_users", return_value=3)
@patch("om.server.manage.users.NUM_FREE_TRIAL_USER_INVITES", 5)
@patch("om.server.tenants.user_mapping.remove_users_from_tenant")
@patch("om.server.tenants.billing.register_tenant_users")
@patch("om.server.tenants.provisioning.add_users_to_tenant")
@patch("om.db.license.check_seat_availability", return_value=None)
def test_trial_tenant_can_invite_within_limit(
    _mock_check_seats: MagicMock,
    mock_add_users_to_tenant: MagicMock,
    mock_register_tenant_users: MagicMock,
    mock_remove_users_from_tenant: MagicMock,
    *_mocks: None,
) -> None:
    """Trial tenants can invite users when under the limit."""
    emails = ["user1@example.com", "user2@example.com", "user3@example.com"]

    result = bulk_invite_users(emails=emails)

    assert result == 3
    # New invitees are added to the tenant...
    mock_add_users_to_tenant.assert_called_once_with(emails, "test_tenant")
    # ...and DEV_MODE short-circuits control-plane billing / rollback.
    mock_register_tenant_users.assert_not_called()
    mock_remove_users_from_tenant.assert_not_called()
