import time
from uuid import uuid4

import requests

from om.server.team.models import Team
from tests.integration.common_utils.constants import API_SERVER_URL
from tests.integration.common_utils.constants import GENERAL_HEADERS
from tests.integration.common_utils.constants import MAX_DELAY
from tests.integration.common_utils.test_models import DATestUser
from tests.integration.common_utils.test_models import DATestTeam


class TeamManager:
    @staticmethod
    def create(
        name: str | None = None,
        user_ids: list[str] | None = None,
        cc_pair_ids: list[int] | None = None,
        user_performing_action: DATestUser | None = None,
    ) -> DATestTeam:
        name = f"{name}-user-group" if name else f"test-user-group-{uuid4()}"

        request = {
            "name": name,
            "user_ids": user_ids or [],
            "cc_pair_ids": cc_pair_ids or [],
        }
        response = requests.post(
            f"{API_SERVER_URL}/nexus/admin/user-group",
            json=request,
            headers=(
                user_performing_action.headers
                if user_performing_action
                else GENERAL_HEADERS
            ),
        )
        response.raise_for_status()
        test_team = DATestTeam(
            id=response.json()["id"],
            name=response.json()["name"],
            user_ids=[user["id"] for user in response.json()["users"]],
            cc_pair_ids=[cc_pair["id"] for cc_pair in response.json()["cc_pairs"]],
        )
        return test_team

    @staticmethod
    def edit(
        team: DATestTeam,
        user_performing_action: DATestUser | None = None,
    ) -> None:
        response = requests.patch(
            f"{API_SERVER_URL}/nexus/admin/user-group/{team.id}",
            json=team.model_dump(),
            headers=(
                user_performing_action.headers
                if user_performing_action
                else GENERAL_HEADERS
            ),
        )
        response.raise_for_status()

    @staticmethod
    def delete(
        team: DATestTeam,
        user_performing_action: DATestUser | None = None,
    ) -> None:
        response = requests.delete(
            f"{API_SERVER_URL}/nexus/admin/user-group/{team.id}",
            headers=(
                user_performing_action.headers
                if user_performing_action
                else GENERAL_HEADERS
            ),
        )
        response.raise_for_status()

    @staticmethod
    def add_users(
        team: DATestTeam,
        user_ids: list[str],
        user_performing_action: DATestUser | None = None,
    ) -> DATestTeam:
        request = {
            "user_ids": user_ids,
        }

        response = requests.post(
            f"{API_SERVER_URL}/nexus/admin/user-group/{team.id}/add-users",
            json=request,
            headers=(
                user_performing_action.headers
                if user_performing_action
                else GENERAL_HEADERS
            ),
        )
        response.raise_for_status()

        team.user_ids = [user["id"] for user in response.json()["users"]]
        team.cc_pair_ids = [
            cc_pair["id"] for cc_pair in response.json()["cc_pairs"]
        ]
        team.name = response.json()["name"]
        return team

    @staticmethod
    def set_curator_status(
        test_team: DATestTeam,
        user_to_set_as_curator: DATestUser,
        is_curator: bool = True,
        user_performing_action: DATestUser | None = None,
    ) -> None:
        set_curator_request = {
            "user_id": user_to_set_as_curator.id,
            "is_curator": is_curator,
        }
        response = requests.post(
            f"{API_SERVER_URL}/nexus/admin/user-group/{test_team.id}/set-curator",
            json=set_curator_request,
            headers=(
                user_performing_action.headers
                if user_performing_action
                else GENERAL_HEADERS
            ),
        )
        response.raise_for_status()

    @staticmethod
    def get_all(
        user_performing_action: DATestUser | None = None,
    ) -> list[Team]:
        response = requests.get(
            f"{API_SERVER_URL}/nexus/admin/user-group",
            headers=(
                user_performing_action.headers
                if user_performing_action
                else GENERAL_HEADERS
            ),
        )
        response.raise_for_status()
        return [Team(**ug) for ug in response.json()]

    @staticmethod
    def verify(
        team: DATestTeam,
        verify_deleted: bool = False,
        user_performing_action: DATestUser | None = None,
    ) -> None:
        all_teams = TeamManager.get_all(user_performing_action)
        for fetched_team in all_teams:
            if team.id == fetched_team.id:
                if verify_deleted:
                    raise ValueError(
                        f"User group {team.id} found but should be deleted"
                    )
                fetched_cc_ids = {cc_pair.id for cc_pair in fetched_team.cc_pairs}
                fetched_user_ids = {user.id for user in fetched_team.users}
                team_cc_ids = set(team.cc_pair_ids)
                team_user_ids = set(team.user_ids)
                if (
                    fetched_cc_ids == team_cc_ids
                    and fetched_user_ids == team_user_ids
                ):
                    return
        if not verify_deleted:
            raise ValueError(f"User group {team.id} not found")

    @staticmethod
    def wait_for_sync(
        teams_to_check: list[DATestTeam] | None = None,
        user_performing_action: DATestUser | None = None,
    ) -> None:
        start = time.time()
        while True:
            teams = TeamManager.get_all(user_performing_action)
            if teams_to_check:
                check_ids = {team.id for team in teams_to_check}
                team_ids = {team.id for team in teams}
                if not check_ids.issubset(team_ids):
                    raise RuntimeError("User group not found")
                teams = [
                    team
                    for team in teams
                    if team.id in check_ids
                ]
            if all(ug.is_up_to_date for ug in teams):
                print("User groups synced successfully.")
                return

            if time.time() - start > MAX_DELAY:
                raise TimeoutError(
                    f"User groups were not synced within the {MAX_DELAY} seconds"
                )
            else:
                print("User groups were not synced yet, waiting...")
            time.sleep(2)

    @staticmethod
    def wait_for_deletion_completion(
        teams_to_check: list[DATestTeam],
        user_performing_action: DATestUser | None = None,
    ) -> None:
        start = time.time()
        team_ids_to_check = {team.id for team in teams_to_check}
        while True:
            fetched_teams = TeamManager.get_all(user_performing_action)
            fetched_team_ids = {
                team.id for team in fetched_teams
            }
            if not team_ids_to_check.intersection(fetched_team_ids):
                return

            if time.time() - start > MAX_DELAY:
                raise TimeoutError(
                    f"User groups deletion was not completed within the {MAX_DELAY} seconds"
                )
            else:
                print("Some user groups are still being deleted, waiting...")
            time.sleep(2)
