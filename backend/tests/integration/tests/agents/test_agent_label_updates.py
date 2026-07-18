from uuid import uuid4

import requests

from om.server.features.agent.models import AgentUpsertRequest
from tests.integration.common_utils.constants import API_SERVER_URL
from tests.integration.common_utils.managers.agent import AgentLabelManager
from tests.integration.common_utils.managers.agent import AgentManager
from tests.integration.common_utils.test_models import DATestAgentLabel
from tests.integration.common_utils.test_models import DATestUser


def test_update_agent_with_null_label_ids_preserves_labels(
    reset: None, admin_user: DATestUser  # noqa: ARG001
) -> None:
    agent_label = AgentLabelManager.create(
        label=DATestAgentLabel(name=f"Test label {uuid4()}"),
        user_performing_action=admin_user,
    )
    assert agent_label.id is not None
    agent = AgentManager.create(
        label_ids=[agent_label.id],
        user_performing_action=admin_user,
    )

    updated_description = f"{agent.description}-updated"
    update_request = AgentUpsertRequest(
        name=agent.name,
        description=updated_description,
        system_prompt=agent.system_prompt or "",
        task_prompt=agent.task_prompt or "",
        datetime_aware=agent.datetime_aware,
        document_set_ids=agent.document_set_ids,
        num_chunks=agent.num_chunks,
        is_public=agent.is_public,
        recency_bias=agent.recency_bias,
        llm_filter_extraction=agent.llm_filter_extraction,
        llm_relevance_filter=agent.llm_relevance_filter,
        llm_model_provider_override=agent.llm_model_provider_override,
        llm_model_version_override=agent.llm_model_version_override,
        tool_ids=agent.tool_ids,
        users=[],
        groups=[],
        label_ids=None,
    )

    response = requests.patch(
        f"{API_SERVER_URL}/agent/{agent.id}",
        json=update_request.model_dump(mode="json", exclude_none=False),
        headers=admin_user.headers,
        cookies=admin_user.cookies,
    )
    response.raise_for_status()

    fetched = requests.get(
        f"{API_SERVER_URL}/agent/{agent.id}",
        headers=admin_user.headers,
        cookies=admin_user.cookies,
    )
    fetched.raise_for_status()
    fetched_agent = fetched.json()

    assert fetched_agent["description"] == updated_description
    fetched_label_ids = {label["id"] for label in fetched_agent["labels"]}
    assert agent_label.id in fetched_label_ids
