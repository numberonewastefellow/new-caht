"""
This file tests the permissions for creating and editing agents for different user roles:
- Basic users can create agents and edit their own
- Curators can edit agents that belong exclusively to groups they curate
- Admins can edit all agents
"""


import pytest
from requests.exceptions import HTTPError

from tests.integration.common_utils.managers.agent import AgentManager
from tests.integration.common_utils.managers.user import DATestUser
from tests.integration.common_utils.managers.user import UserManager
from tests.integration.common_utils.managers.team import TeamManager


def test_agent_permissions(reset: None) -> None:  # noqa: ARG001
    # Creating an admin user (first user created is automatically an admin)
    admin_user: DATestUser = UserManager.create(name="admin_user")

    # Creating a curator user
    curator: DATestUser = UserManager.create(name="curator")

    # Creating a basic user
    basic_user: DATestUser = UserManager.create(name="basic_user")

    # Creating user groups
    team_1 = TeamManager.create(
        name="curated_team",
        user_ids=[curator.id],
        cc_pair_ids=[],
        user_performing_action=admin_user,
    )
    TeamManager.wait_for_sync(
        teams_to_check=[team_1], user_performing_action=admin_user
    )
    # Setting the user as a curator for the user group
    TeamManager.set_curator_status(
        test_team=team_1,
        user_to_set_as_curator=curator,
        user_performing_action=admin_user,
    )

    # Creating another user group that the user is not a curator of
    team_2 = TeamManager.create(
        name="uncurated_team",
        user_ids=[curator.id],
        cc_pair_ids=[],
        user_performing_action=admin_user,
    )
    TeamManager.wait_for_sync(
        teams_to_check=[team_2], user_performing_action=admin_user
    )

    """Test that any user can create a agent"""
    # Basic user creates a agent
    basic_user_agent = AgentManager.create(
        name="basic_user_agent",
        description="A agent created by basic user",
        is_public=False,
        groups=[],
        users=[admin_user.id],
        user_performing_action=basic_user,
    )
    AgentManager.verify(basic_user_agent, user_performing_action=basic_user)

    # Curator creates a agent
    curator_agent = AgentManager.create(
        name="curator_agent",
        description="A agent created by curator",
        is_public=False,
        groups=[],
        user_performing_action=curator,
    )
    AgentManager.verify(curator_agent, user_performing_action=curator)

    # Admin creates agents for different groups
    admin_agent_group_1 = AgentManager.create(
        name="admin_agent_group_1",
        description="A agent for group 1",
        is_public=False,
        groups=[team_1.id],
        user_performing_action=admin_user,
    )
    admin_agent_group_2 = AgentManager.create(
        name="admin_agent_group_2",
        description="A agent for group 2",
        is_public=False,
        groups=[team_2.id],
        user_performing_action=admin_user,
    )
    admin_agent_both_groups = AgentManager.create(
        name="admin_agent_both_groups",
        description="A agent for both groups",
        is_public=False,
        groups=[team_1.id, team_2.id],
        user_performing_action=admin_user,
    )

    """Test that users can edit their own agents"""
    # Basic user can edit their own agent
    AgentManager.edit(
        agent=basic_user_agent,
        description="Updated description by basic user",
        user_performing_action=basic_user,
    )
    AgentManager.verify(basic_user_agent, user_performing_action=basic_user)

    # Basic user cannot edit other's agents
    with pytest.raises(HTTPError):
        AgentManager.edit(
            agent=curator_agent,
            description="Invalid edit by basic user",
            user_performing_action=basic_user,
        )

    """Test curator permissions"""
    # Curator can edit agents that belong exclusively to groups they curate
    AgentManager.edit(
        agent=admin_agent_group_1,
        description="Updated by curator",
        user_performing_action=curator,
    )
    AgentManager.verify(admin_agent_group_1, user_performing_action=curator)

    # Curator cannot edit agents in groups they don't curate
    with pytest.raises(HTTPError):
        AgentManager.edit(
            agent=admin_agent_group_2,
            description="Invalid edit by curator",
            user_performing_action=curator,
        )

    # Curator cannot edit agents that belong to multiple groups, even if they curate one
    with pytest.raises(HTTPError):
        AgentManager.edit(
            agent=admin_agent_both_groups,
            description="Invalid edit by curator",
            user_performing_action=curator,
        )

    """Test admin permissions"""
    # Admin can edit any agent

    # the agent was shared with the admin user on creation
    # this edit call will simulate having the same user in the list twice.
    # The server side should dedupe and handle this correctly (prior bug)
    AgentManager.edit(
        agent=basic_user_agent,
        description="Updated by admin 2",
        users=[admin_user.id, admin_user.id],
        user_performing_action=admin_user,
    )
    AgentManager.verify(basic_user_agent, user_performing_action=admin_user)

    AgentManager.edit(
        agent=curator_agent,
        description="Updated by admin",
        user_performing_action=admin_user,
    )
    AgentManager.verify(curator_agent, user_performing_action=admin_user)

    AgentManager.edit(
        agent=admin_agent_group_1,
        description="Updated by admin",
        user_performing_action=admin_user,
    )
    AgentManager.verify(admin_agent_group_1, user_performing_action=admin_user)

    AgentManager.edit(
        agent=admin_agent_group_2,
        description="Updated by admin",
        user_performing_action=admin_user,
    )
    AgentManager.verify(admin_agent_group_2, user_performing_action=admin_user)

    AgentManager.edit(
        agent=admin_agent_both_groups,
        description="Updated by admin",
        user_performing_action=admin_user,
    )
    AgentManager.verify(admin_agent_both_groups, user_performing_action=admin_user)
