from uuid import uuid4

import pytest
from requests.exceptions import HTTPError

from tests.integration.common_utils.managers.agent import (
    AgentLabelManager,
)
from tests.integration.common_utils.managers.user import UserManager
from tests.integration.common_utils.test_models import DATestAgentLabel
from tests.integration.common_utils.test_models import DATestUser


def test_agent_label_management(reset: None) -> None:  # noqa: ARG001
    admin_user: DATestUser = UserManager.create(name="admin_user")

    agent_label = DATestAgentLabel(
        id=None,
        name=f"Test label {uuid4()}",
    )
    agent_label = AgentLabelManager.create(
        label=agent_label,
        user_performing_action=admin_user,
    )
    print(f"Created agent label {agent_label.name} with id {agent_label.id}")

    assert AgentLabelManager.verify(
        label=agent_label,
        user_performing_action=admin_user,
    ), "Agent label was not found after creation"

    regular_user: DATestUser = UserManager.create(name="regular_user")

    updated_agent_label = DATestAgentLabel(
        id=agent_label.id,
        name=f"Updated {agent_label.name}",
    )
    with pytest.raises(HTTPError) as exc_info:
        AgentLabelManager.update(
            label=updated_agent_label,
            user_performing_action=regular_user,
        )
    assert exc_info.value.response is not None
    assert exc_info.value.response.status_code == 403

    assert AgentLabelManager.verify(
        label=agent_label,
        user_performing_action=admin_user,
    ), "Agent label should not have been updated by non-admin user"

    result = AgentLabelManager.delete(
        label=agent_label,
        user_performing_action=regular_user,
    )
    assert (
        result is False
    ), "Regular user should not be able to delete the agent label"

    assert AgentLabelManager.verify(
        label=agent_label,
        user_performing_action=admin_user,
    ), "Agent label should not have been deleted by non-admin user"

    updated_agent_label.name = f"Updated {agent_label.name}"
    updated_agent_label = AgentLabelManager.update(
        label=updated_agent_label,
        user_performing_action=admin_user,
    )
    print(f"Updated agent label to {updated_agent_label.name}")

    assert AgentLabelManager.verify(
        label=updated_agent_label,
        user_performing_action=admin_user,
    ), "Agent label was not updated by admin"

    success = AgentLabelManager.delete(
        label=agent_label,
        user_performing_action=admin_user,
    )
    assert success, "Admin user should be able to delete the agent label"
    print(f"Deleted agent label {agent_label.name} with id {agent_label.id}")

    assert not AgentLabelManager.verify(
        label=agent_label,
        user_performing_action=admin_user,
    ), "Agent label should not exist after deletion by admin"
