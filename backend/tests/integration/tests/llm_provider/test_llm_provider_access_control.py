
import pytest
import requests
from sqlalchemy.orm import Session

from om.context.search.enums import RecencyBiasSetting
from om.db.engine.sql_engine import get_session_with_current_tenant
from om.db.llm import can_user_access_llm_provider
from om.db.llm import fetch_team_ids
from om.db.models import LLMProvider as LLMProviderModel
from om.db.models import LLMProvider__Agent
from om.db.models import LLMProvider__Team
from om.db.models import Agent
from om.db.models import User
from om.db.models import User__Team
from om.db.models import Team
from om.llm.constants import LlmProviderNames
from om.llm.factory import get_llm_for_agent
from tests.integration.common_utils.constants import API_SERVER_URL
from tests.integration.common_utils.managers.llm_provider import LLMProviderManager
from tests.integration.common_utils.managers.agent import AgentManager
from tests.integration.common_utils.managers.user import UserManager
from tests.integration.common_utils.test_models import DATestUser




def _create_llm_provider(
    db_session: Session,
    *,
    name: str,
    default_model_name: str,
    is_public: bool,
    is_default: bool,
) -> LLMProviderModel:
    provider = LLMProviderModel(
        name=name,
        provider=LlmProviderNames.OPENAI,
        api_key=None,
        api_base=None,
        api_version=None,
        custom_config=None,
        default_model_name=default_model_name,
        deployment_name=None,
        is_public=is_public,
        # Use None instead of False to avoid unique constraint violation
        # The is_default_provider column has unique=True, so only one True and one False allowed
        is_default_provider=is_default if is_default else None,
        is_default_vision_provider=False,
        default_vision_model=None,
    )
    db_session.add(provider)
    db_session.flush()
    return provider


def _create_agent(
    db_session: Session,
    *,
    name: str,
    provider_name: str,
) -> Agent:
    agent = Agent(
        name=name,
        description=f"{name} description",
        num_chunks=5,
        chunks_above=2,
        chunks_below=2,
        llm_relevance_filter=True,
        llm_filter_extraction=True,
        recency_bias=RecencyBiasSetting.AUTO,
        llm_model_provider_override=provider_name,
        llm_model_version_override="gpt-4o-mini",
        system_prompt="System prompt",
        task_prompt="Task prompt",
        datetime_aware=True,
        is_public=True,
    )
    db_session.add(agent)
    db_session.flush()
    return agent


@pytest.fixture()
def users(reset: None) -> tuple[DATestUser, DATestUser]:  # noqa: ARG001
    admin_user = UserManager.create(name="admin_user")
    basic_user = UserManager.create(name="basic_user")
    return admin_user, basic_user


def test_can_user_access_llm_provider_or_logic(
    users: tuple[DATestUser, DATestUser],
) -> None:
    """Test LLM provider access control with is_public flag and AND logic.

    Tests the new access control logic:
    - is_public=True providers are accessible to everyone
    - is_public=False with no restrictions locks the provider
    - When both groups AND agents are set, AND logic applies (must satisfy both)
    """
    admin_user, basic_user = users

    with get_session_with_current_tenant() as db_session:
        # Public provider - accessible to everyone
        default_provider = _create_llm_provider(
            db_session,
            name="default-provider",
            default_model_name="gpt-4o",
            is_public=True,
            is_default=True,
        )
        # Locked provider - is_public=False with no restrictions
        locked_provider = _create_llm_provider(
            db_session,
            name="locked-provider",
            default_model_name="gpt-4o",
            is_public=False,
            is_default=False,
        )
        # Restricted provider - has both group AND agent restrictions (AND logic)
        restricted_provider = _create_llm_provider(
            db_session,
            name="restricted-provider",
            default_model_name="gpt-4o-mini",
            is_public=False,
            is_default=False,
        )

        allowed_agent = _create_agent(
            db_session,
            name="allowed-agent",
            provider_name=restricted_provider.name,
        )
        blocked_agent = _create_agent(
            db_session,
            name="blocked-agent",
            provider_name=restricted_provider.name,
        )

        access_group = Team(name="access-group")
        db_session.add(access_group)
        db_session.flush()

        # Add both group and agent restrictions to restricted_provider
        db_session.add(
            LLMProvider__Team(
                llm_provider_id=restricted_provider.id,
                team_id=access_group.id,
            )
        )
        db_session.add(
            LLMProvider__Agent(
                llm_provider_id=restricted_provider.id,
                agent_id=allowed_agent.id,
            )
        )
        # Only admin_user is in the access_group
        db_session.add(
            User__Team(
                team_id=access_group.id,
                user_id=admin_user.id,
            )
        )
        db_session.flush()

        db_session.refresh(restricted_provider)
        db_session.refresh(locked_provider)

        admin_model = db_session.get(User, admin_user.id)
        basic_model = db_session.get(User, basic_user.id)

        assert admin_model is not None
        assert basic_model is not None

        # Fetch user group IDs for both users
        admin_group_ids = fetch_team_ids(db_session, admin_model)
        basic_group_ids = fetch_team_ids(db_session, basic_model)

        # Test is_public flag
        assert default_provider.is_public
        assert not locked_provider.is_public
        assert not restricted_provider.is_public

        # Public provider - everyone can access
        assert can_user_access_llm_provider(
            default_provider,
            admin_group_ids,
            allowed_agent,
        )
        assert can_user_access_llm_provider(
            default_provider,
            basic_group_ids,
            blocked_agent,
        )

        # Locked provider (is_public=False, no restrictions) - nobody can access
        assert not can_user_access_llm_provider(
            locked_provider,
            admin_group_ids,
            allowed_agent,
        )
        assert not can_user_access_llm_provider(
            locked_provider,
            basic_group_ids,
            allowed_agent,
        )

        # Restricted provider with AND logic (both groups AND agents set)
        # admin_user in group + allowed_agent whitelisted → SUCCESS (both conditions met)
        assert can_user_access_llm_provider(
            restricted_provider,
            admin_group_ids,
            allowed_agent,
        )

        # admin_user in group + blocked_agent not whitelisted → FAIL (agent not allowed)
        assert not can_user_access_llm_provider(
            restricted_provider,
            admin_group_ids,
            blocked_agent,
        )

        # basic_user not in group + allowed_agent whitelisted → FAIL (user not in group)
        assert not can_user_access_llm_provider(
            restricted_provider,
            basic_group_ids,
            allowed_agent,
        )

        # basic_user not in group + blocked_agent not whitelisted → FAIL (neither condition met)
        assert not can_user_access_llm_provider(
            restricted_provider,
            basic_group_ids,
            blocked_agent,
        )


def test_get_llm_for_agent_falls_back_when_access_denied(
    users: tuple[DATestUser, DATestUser],
) -> None:
    admin_user, basic_user = users

    with get_session_with_current_tenant() as db_session:
        default_provider = _create_llm_provider(
            db_session,
            name="default-provider",
            default_model_name="gpt-4o",
            is_public=True,
            is_default=True,
        )
        restricted_provider = _create_llm_provider(
            db_session,
            name="restricted-provider",
            default_model_name="gpt-4o-mini",
            is_public=False,
            is_default=False,
        )

        agent = _create_agent(
            db_session,
            name="fallback-agent",
            provider_name=restricted_provider.name,
        )

        access_group = Team(name="agent-group")
        db_session.add(access_group)
        db_session.flush()

        db_session.add(
            LLMProvider__Team(
                llm_provider_id=restricted_provider.id,
                team_id=access_group.id,
            )
        )
        db_session.add(
            User__Team(
                team_id=access_group.id,
                user_id=admin_user.id,
            )
        )
        db_session.flush()
        db_session.commit()

        db_session.refresh(default_provider)
        db_session.refresh(restricted_provider)
        db_session.refresh(agent)

        admin_model = db_session.get(User, admin_user.id)
        basic_model = db_session.get(User, basic_user.id)

        assert admin_model is not None
        assert basic_model is not None

        allowed_llm = get_llm_for_agent(
            agent=agent,
            user=admin_model,
        )
        assert allowed_llm.config.model_name == restricted_provider.default_model_name

        fallback_llm = get_llm_for_agent(
            agent=agent,
            user=basic_model,
        )
        assert fallback_llm.config.model_name == default_provider.default_model_name


def test_list_llm_provider_basics_excludes_non_public_unrestricted(
    users: tuple[DATestUser, DATestUser],
) -> None:
    """Test that the /llm/provider endpoint correctly excludes non-public providers
    with no group/agent restrictions.

    This tests the fix for the bug where non-public providers with no restrictions
    were incorrectly shown to all users instead of being admin-only.
    """
    admin_user, basic_user = users

    # Create a public provider (should be visible to all)
    public_provider = LLMProviderManager.create(
        name="public-provider",
        is_public=True,
        set_as_default=True,
        user_performing_action=admin_user,
    )

    # Create a non-public provider with no restrictions (should be admin-only)
    non_public_provider = LLMProviderManager.create(
        name="non-public-unrestricted",
        is_public=False,
        groups=[],
        agents=[],
        set_as_default=False,
        user_performing_action=admin_user,
    )

    # Non-admin user calls the /llm/provider endpoint
    response = requests.get(
        f"{API_SERVER_URL}/llm/provider",
        headers=basic_user.headers,
    )
    assert response.status_code == 200
    providers = response.json()
    provider_names = [p["name"] for p in providers]

    # Public provider should be visible
    assert public_provider.name in provider_names

    # Non-public provider with no restrictions should NOT be visible to non-admin
    assert non_public_provider.name not in provider_names

    # Admin user should see both providers
    admin_response = requests.get(
        f"{API_SERVER_URL}/llm/provider",
        headers=admin_user.headers,
    )
    assert admin_response.status_code == 200
    admin_providers = admin_response.json()
    admin_provider_names = [p["name"] for p in admin_providers]

    assert public_provider.name in admin_provider_names
    assert non_public_provider.name in admin_provider_names


def test_provider_delete_clears_agent_references(reset: None) -> None:  # noqa: ARG001
    """Test that deleting a provider automatically clears agent references."""
    admin_user = UserManager.create(name="admin_user")

    # Create a default provider first so agents have something to fall back to
    LLMProviderManager.create(
        name="default-provider",
        is_public=True,
        set_as_default=True,
        user_performing_action=admin_user,
    )

    provider = LLMProviderManager.create(
        is_public=False,
        set_as_default=False,
        user_performing_action=admin_user,
    )
    agent = AgentManager.create(
        llm_model_provider_override=provider.name,
        user_performing_action=admin_user,
    )

    # Delete the provider - should succeed and automatically clear agent references
    assert LLMProviderManager.delete(
        provider,
        user_performing_action=admin_user,
    )

    # Verify the agent now falls back to default (llm_model_provider_override cleared)
    agent_response = requests.get(
        f"{API_SERVER_URL}/agent/{agent.id}",
        headers=admin_user.headers,
    )
    assert agent_response.status_code == 200
    updated_agent = agent_response.json()
    assert updated_agent["llm_model_provider_override"] is None
