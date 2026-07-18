import requests

from tests.integration.common_utils.constants import API_SERVER_URL
from tests.integration.common_utils.managers.agent import AgentManager
from tests.integration.common_utils.test_models import DATestUser


def _list_minimal_agents(user: DATestUser) -> list[dict]:
    response = requests.get(
        f"{API_SERVER_URL}/agent",
        headers=user.headers,
        cookies=user.cookies,
    )
    response.raise_for_status()
    return response.json()


def _share_agent(
    agent_id: int, user_ids: list[str], acting_user: DATestUser
) -> None:
    response = requests.patch(
        f"{API_SERVER_URL}/agent/{agent_id}/share",
        json={"user_ids": user_ids},
        headers=acting_user.headers,
        cookies=acting_user.cookies,
    )
    response.raise_for_status()


def test_agent_create_update_share_delete(
    reset: None, admin_user: DATestUser, basic_user: DATestUser  # noqa: ARG001
) -> None:
    # TODO: refactor `AgentManager.verify`, not a good pattern
    # Create a agent as admin and verify it can be fetched
    expected_agent = AgentManager.create(user_performing_action=admin_user)
    AgentManager.verify(expected_agent, user_performing_action=admin_user)

    # Update the agent and verify changes
    updated_agent = AgentManager.edit(
        expected_agent,
        name=f"updated-{expected_agent.name}",
        description=f"updated-{expected_agent.description}",
        num_chunks=expected_agent.num_chunks + 1,
        is_public=False,
        user_performing_action=admin_user,
    )
    assert AgentManager.verify(updated_agent, user_performing_action=admin_user)

    # Creator should see the agent in their minimal list
    creator_minimals = _list_minimal_agents(admin_user)
    assert any(p["id"] == updated_agent.id for p in creator_minimals)

    # Regular user should not see a non-public, non-shared agent
    other_minimals_before = _list_minimal_agents(basic_user)
    assert all(p["id"] != updated_agent.id for p in other_minimals_before)

    # Share agent with the regular user and verify visibility
    _share_agent(updated_agent.id, [basic_user.id], admin_user)
    other_minimals_after = _list_minimal_agents(basic_user)
    assert any(p["id"] == updated_agent.id for p in other_minimals_after)

    # Delete agent and verify it no longer appears in lists
    assert AgentManager.delete(updated_agent, user_performing_action=admin_user)

    # After deletion, list should not include it for either user
    creator_minimals_after_delete = _list_minimal_agents(admin_user)
    assert all(p["id"] != updated_agent.id for p in creator_minimals_after_delete)

    regular_minimals_after_delete = _list_minimal_agents(basic_user)
    assert all(p["id"] != updated_agent.id for p in regular_minimals_after_delete)
