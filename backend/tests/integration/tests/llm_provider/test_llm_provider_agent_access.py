"""
Integration tests for LLM Provider agent access authorization.
"""


import pytest
import requests

from om.llm.constants import LlmProviderNames
from tests.integration.common_utils.constants import API_SERVER_URL
from tests.integration.common_utils.managers.llm_provider import LLMProviderManager
from tests.integration.common_utils.managers.agent import AgentManager
from tests.integration.common_utils.managers.user import UserManager
from tests.integration.common_utils.managers.user_group import UserGroupManager
from tests.integration.common_utils.test_models import DATestUser




@pytest.fixture()
def users_and_groups(
    reset: None,  # noqa: ARG001
) -> tuple[DATestUser, DATestUser, int, int]:
    """Create admin, basic user, and two user groups."""
    admin_user = UserManager.create(name="admin_user")
    basic_user = UserManager.create(name="basic_user")

    # Create two user groups
    group1 = UserGroupManager.create(
        user_performing_action=admin_user,
        name="test_group_1",
        user_ids=[basic_user.id],
    )

    group2 = UserGroupManager.create(
        user_performing_action=admin_user,
        name="test_group_2",
        user_ids=[],  # basic_user is NOT in this group
    )

    return admin_user, basic_user, group1.id, group2.id


def test_unauthorized_agent_access_returns_403(
    users_and_groups: tuple[DATestUser, DATestUser, int, int],
) -> None:
    """Test that users cannot query providers for agents they don't have access to."""
    admin_user, basic_user, group1_id, group2_id = users_and_groups

    # Create a agent restricted to group2 (which basic_user is NOT in)
    restricted_agent = AgentManager.create(
        user_performing_action=admin_user,
        name="Restricted Agent",
        description="Only accessible to group2",
        is_public=False,
        groups=[group2_id],
    )

    # Try to query providers for the restricted agent as basic_user
    response = requests.get(
        f"{API_SERVER_URL}/llm/agent/{restricted_agent.id}/providers",
        headers=basic_user.headers,
    )

    # Should return 403 Forbidden
    assert response.status_code == 403
    assert "don't have access to this assistant" in response.json()["detail"]


def test_authorized_agent_access_returns_filtered_providers(
    users_and_groups: tuple[DATestUser, DATestUser, int, int],
) -> None:
    """Test that users can query providers for agents they have access to."""
    admin_user, basic_user, group1_id, group2_id = users_and_groups

    # Create a agent accessible to group1 (which basic_user IS in)
    accessible_agent = AgentManager.create(
        user_performing_action=admin_user,
        name="Accessible Agent",
        description="Accessible to group1",
        is_public=False,
        groups=[group1_id],
    )

    # Create a restricted provider accessible only to the agent
    restricted_provider = LLMProviderManager.create(
        user_performing_action=admin_user,
        name="Restricted Provider",
        provider=LlmProviderNames.OPENAI,
        api_key="test-key",
        default_model_name="gpt-4o",
        is_public=False,
        groups=[],
        agents=[accessible_agent.id],
    )

    # Query providers for the accessible agent as basic_user
    response = requests.get(
        f"{API_SERVER_URL}/llm/agent/{accessible_agent.id}/providers",
        headers=basic_user.headers,
    )

    # Should succeed
    assert response.status_code == 200
    providers = response.json()

    # Should include the restricted provider since basic_user can access the agent
    provider_names = [p["name"] for p in providers]
    assert restricted_provider.name in provider_names


def test_agent_id_zero_applies_rbac(
    users_and_groups: tuple[DATestUser, DATestUser, int, int],
) -> None:
    """Test that agent_id=0 (default agent) properly applies RBAC."""
    admin_user, basic_user, group1_id, group2_id = users_and_groups

    # Create a restricted provider accessible only to group2
    restricted_provider = LLMProviderManager.create(
        user_performing_action=admin_user,
        name="Group2 Only Provider",
        provider=LlmProviderNames.OPENAI,
        api_key="test-key",
        default_model_name="gpt-4o",
        is_public=False,
        groups=[group2_id],
        agents=[],
    )

    # Query providers with agent_id=0 as basic_user
    response = requests.get(
        f"{API_SERVER_URL}/llm/agent/0/providers",
        headers=basic_user.headers,
    )

    # Should succeed (agent_id=0 refers to default agent, which is public)
    assert response.status_code == 200
    providers = response.json()

    # Should NOT include the restricted provider since basic_user is not in group2
    provider_names = [p["name"] for p in providers]
    assert restricted_provider.name not in provider_names


def test_admin_can_query_any_agent(
    users_and_groups: tuple[DATestUser, DATestUser, int, int],
) -> None:
    """Test that admin users can query any agent's providers."""
    admin_user, basic_user, group1_id, group2_id = users_and_groups

    # Create a agent restricted to group2 (admin is not explicitly in this group)
    restricted_agent = AgentManager.create(
        user_performing_action=admin_user,
        name="Admin Test Agent",
        description="Only accessible to group2",
        is_public=False,
        groups=[group2_id],
    )

    # Create a restricted provider accessible only to the agent
    restricted_provider = LLMProviderManager.create(
        user_performing_action=admin_user,
        name="Admin Test Provider",
        provider=LlmProviderNames.OPENAI,
        api_key="test-key",
        default_model_name="gpt-4o",
        is_public=False,
        groups=[],
        agents=[restricted_agent.id],
    )

    # Query providers for the restricted agent as admin_user
    response = requests.get(
        f"{API_SERVER_URL}/llm/agent/{restricted_agent.id}/providers",
        headers=admin_user.headers,
    )

    # Should succeed - admins can access any agent
    assert response.status_code == 200
    providers = response.json()

    # Should include the restricted provider
    provider_names = [p["name"] for p in providers]
    assert restricted_provider.name in provider_names


def test_public_agent_accessible_to_all(
    users_and_groups: tuple[DATestUser, DATestUser, int, int],
) -> None:
    """Test that public agents are accessible to all users."""
    admin_user, basic_user, group1_id, group2_id = users_and_groups

    # Create a public LLM provider so there's something to return
    public_provider = LLMProviderManager.create(
        user_performing_action=admin_user,
        name="Public Provider",
        provider=LlmProviderNames.OPENAI,
        api_key="test-key",
        default_model_name="gpt-4o",
        is_public=True,
        set_as_default=True,
    )

    # Create a public agent
    public_agent = AgentManager.create(
        user_performing_action=admin_user,
        name="Public Agent",
        description="Accessible to everyone",
        is_public=True,
        groups=[],
    )

    # Query providers for the public agent as basic_user
    response = requests.get(
        f"{API_SERVER_URL}/llm/agent/{public_agent.id}/providers",
        headers=basic_user.headers,
    )

    # Should succeed
    assert response.status_code == 200
    providers = response.json()

    # Should return the public provider
    assert len(providers) > 0
    provider_names = [p["name"] for p in providers]
    assert public_provider.name in provider_names


def test_nonexistent_agent_returns_404(
    users_and_groups: tuple[DATestUser, DATestUser, int, int],
) -> None:
    """Test that querying a nonexistent agent returns 404."""
    admin_user, basic_user, group1_id, group2_id = users_and_groups

    # Query providers for a nonexistent agent
    response = requests.get(
        f"{API_SERVER_URL}/llm/agent/99999/providers",
        headers=basic_user.headers,
    )

    # Should return 404
    assert response.status_code == 404
    assert "Agent not found" in response.json()["detail"]
