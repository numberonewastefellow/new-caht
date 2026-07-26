from uuid import uuid4

import requests

from tests.integration.common_utils.constants import API_SERVER_URL
from tests.integration.common_utils.constants import GENERAL_HEADERS
from tests.integration.common_utils.managers.user import UserManager
from tests.integration.common_utils.managers.team import TeamManager
from tests.integration.common_utils.test_models import DATestUser
from tests.integration.common_utils.test_models import DATestTeam


def test_add_users_to_group(reset: None) -> None:  # noqa: ARG001
    admin_user: DATestUser = UserManager.create(name="admin_for_add_user")
    user_to_add: DATestUser = UserManager.create(name="basic_user_to_add")

    team: DATestTeam = TeamManager.create(
        name="add-user-test-group",
        user_ids=[admin_user.id],
        user_performing_action=admin_user,
    )
    # A freshly-created team is marked is_up_to_date=False until its permission
    # sync finishes; the API rejects edits while syncing. Wait before add-users.
    TeamManager.wait_for_sync(
        teams_to_check=[team], user_performing_action=admin_user
    )

    updated_team = TeamManager.add_users(
        team=team,
        user_ids=[user_to_add.id],
        user_performing_action=admin_user,
    )

    fetched_teams = TeamManager.get_all(user_performing_action=admin_user)
    fetched_team = next(
        group for group in fetched_teams if group.id == updated_team.id
    )

    fetched_user_ids = {user.id for user in fetched_team.users}
    assert admin_user.id in fetched_user_ids
    assert user_to_add.id in fetched_user_ids


def test_add_users_to_group_invalid_user(reset: None) -> None:  # noqa: ARG001
    """Adding a non-existent user to a team must fail cleanly with a 400, not 500.

    Regression test for the WS-B team-RBAC bug where ``_add_memberships``
    (``om/db/team.py``) inserted ``User__Team`` rows without validating user
    existence, so the FK (``user__team_user_id_fkey``) raised an IntegrityError
    that surfaced as an opaque 500. ``_add_memberships`` now validates up front and
    raises ``ValueError``, which ``add_users`` converts to a 400.

    NOTE: verifies the code in this tree; it passes once the api_server container
    is rebuilt with this fix (a stale container still returns 500).
    """
    admin_user: DATestUser = UserManager.create(name="admin_for_add_user_invalid")

    team: DATestTeam = TeamManager.create(
        name="add-user-invalid-test-group",
        user_ids=[admin_user.id],
        user_performing_action=admin_user,
    )
    TeamManager.wait_for_sync(
        teams_to_check=[team], user_performing_action=admin_user
    )

    invalid_user_id = str(uuid4())
    # Current team router endpoint (legacy /manage/admin/user-group/... is removed).
    response = requests.post(
        f"{API_SERVER_URL}/teams/{team.id}/add-users",
        json={"user_ids": [invalid_user_id]},
        headers=admin_user.headers if admin_user else GENERAL_HEADERS,
    )

    assert response.status_code == 400
    assert "unknown user id" in response.text.lower()
