from uuid import UUID
from uuid import uuid4

import requests

from om.context.search.enums import RecencyBiasSetting
from om.server.features.agent.models import FullAgentSnapshot
from om.server.features.agent.models import AgentUpsertRequest
from tests.integration.common_utils.constants import API_SERVER_URL
from tests.integration.common_utils.constants import GENERAL_HEADERS
from tests.integration.common_utils.test_models import DATestAgent
from tests.integration.common_utils.test_models import DATestAgentLabel
from tests.integration.common_utils.test_models import DATestUser


class AgentManager:
    @staticmethod
    def create(
        name: str | None = None,
        description: str | None = None,
        system_prompt: str | None = None,
        task_prompt: str | None = None,
        num_chunks: float = 5,
        llm_relevance_filter: bool = True,
        is_public: bool = True,
        llm_filter_extraction: bool = True,
        recency_bias: RecencyBiasSetting = RecencyBiasSetting.AUTO,
        datetime_aware: bool = False,
        document_set_ids: list[int] | None = None,
        tool_ids: list[int] | None = None,
        llm_model_provider_override: str | None = None,
        llm_model_version_override: str | None = None,
        users: list[str] | None = None,
        groups: list[int] | None = None,
        label_ids: list[int] | None = None,
        knowledge_file_ids: list[str] | None = None,
        user_performing_action: DATestUser | None = None,
        display_priority: int | None = None,
    ) -> DATestAgent:
        name = name or f"test-agent-{uuid4()}"
        description = description or f"Description for {name}"
        system_prompt = system_prompt or f"System prompt for {name}"
        task_prompt = task_prompt or f"Task prompt for {name}"

        agent_creation_request = AgentUpsertRequest(
            name=name,
            description=description,
            system_prompt=system_prompt,
            task_prompt=task_prompt,
            datetime_aware=datetime_aware,
            num_chunks=num_chunks,
            llm_relevance_filter=llm_relevance_filter,
            is_public=is_public,
            llm_filter_extraction=llm_filter_extraction,
            recency_bias=recency_bias,
            document_set_ids=document_set_ids or [],
            tool_ids=tool_ids or [],
            llm_model_provider_override=llm_model_provider_override,
            llm_model_version_override=llm_model_version_override,
            users=[UUID(user) for user in (users or [])],
            groups=groups or [],
            label_ids=label_ids or [],
            knowledge_file_ids=knowledge_file_ids or [],
            display_priority=display_priority,
        )

        response = requests.post(
            f"{API_SERVER_URL}/agent",
            json=agent_creation_request.model_dump(mode="json"),
            headers=(
                user_performing_action.headers
                if user_performing_action
                else GENERAL_HEADERS
            ),
        )
        response.raise_for_status()
        agent_data = response.json()

        return DATestAgent(
            id=agent_data["id"],
            name=name,
            description=description,
            num_chunks=num_chunks,
            llm_relevance_filter=llm_relevance_filter,
            is_public=is_public,
            llm_filter_extraction=llm_filter_extraction,
            recency_bias=recency_bias,
            system_prompt=system_prompt,
            task_prompt=task_prompt,
            datetime_aware=datetime_aware,
            document_set_ids=document_set_ids or [],
            tool_ids=tool_ids or [],
            llm_model_provider_override=llm_model_provider_override,
            llm_model_version_override=llm_model_version_override,
            users=users or [],
            groups=groups or [],
            label_ids=label_ids or [],
        )

    @staticmethod
    def edit(
        agent: DATestAgent,
        name: str | None = None,
        description: str | None = None,
        system_prompt: str | None = None,
        task_prompt: str | None = None,
        num_chunks: float | None = None,
        llm_relevance_filter: bool | None = None,
        is_public: bool | None = None,
        llm_filter_extraction: bool | None = None,
        recency_bias: RecencyBiasSetting | None = None,
        datetime_aware: bool = False,
        document_set_ids: list[int] | None = None,
        tool_ids: list[int] | None = None,
        llm_model_provider_override: str | None = None,
        llm_model_version_override: str | None = None,
        users: list[str] | None = None,
        groups: list[int] | None = None,
        label_ids: list[int] | None = None,
        user_performing_action: DATestUser | None = None,
    ) -> DATestAgent:
        system_prompt = system_prompt or f"System prompt for {agent.name}"
        task_prompt = task_prompt or f"Task prompt for {agent.name}"

        agent_update_request = AgentUpsertRequest(
            name=name or agent.name,
            description=description or agent.description,
            system_prompt=system_prompt,
            task_prompt=task_prompt,
            datetime_aware=datetime_aware,
            num_chunks=num_chunks or agent.num_chunks,
            llm_relevance_filter=llm_relevance_filter or agent.llm_relevance_filter,
            is_public=agent.is_public if is_public is None else is_public,
            llm_filter_extraction=(
                llm_filter_extraction or agent.llm_filter_extraction
            ),
            recency_bias=recency_bias or agent.recency_bias,
            document_set_ids=document_set_ids or agent.document_set_ids,
            tool_ids=tool_ids or agent.tool_ids,
            llm_model_provider_override=(
                llm_model_provider_override or agent.llm_model_provider_override
            ),
            llm_model_version_override=(
                llm_model_version_override or agent.llm_model_version_override
            ),
            users=[UUID(user) for user in (users or agent.users)],
            groups=groups or agent.groups,
            label_ids=label_ids or agent.label_ids,
        )

        response = requests.patch(
            f"{API_SERVER_URL}/agent/{agent.id}",
            json=agent_update_request.model_dump(mode="json"),
            headers=(
                user_performing_action.headers
                if user_performing_action
                else GENERAL_HEADERS
            ),
        )
        response.raise_for_status()
        updated_agent_data = response.json()

        return DATestAgent(
            id=updated_agent_data["id"],
            name=updated_agent_data["name"],
            description=updated_agent_data["description"],
            num_chunks=updated_agent_data["num_chunks"],
            llm_relevance_filter=updated_agent_data["llm_relevance_filter"],
            is_public=updated_agent_data["is_public"],
            llm_filter_extraction=updated_agent_data["llm_filter_extraction"],
            recency_bias=recency_bias or agent.recency_bias,
            system_prompt=system_prompt,
            task_prompt=task_prompt,
            datetime_aware=datetime_aware,
            document_set_ids=updated_agent_data["document_sets"],
            tool_ids=updated_agent_data["tools"],
            llm_model_provider_override=updated_agent_data[
                "llm_model_provider_override"
            ],
            llm_model_version_override=updated_agent_data[
                "llm_model_version_override"
            ],
            users=[user["email"] for user in updated_agent_data["users"]],
            groups=updated_agent_data["groups"],
            label_ids=updated_agent_data["labels"],
        )

    @staticmethod
    def get_all(
        user_performing_action: DATestUser | None = None,
    ) -> list[FullAgentSnapshot]:
        response = requests.get(
            f"{API_SERVER_URL}/admin/agent",
            headers=(
                user_performing_action.headers
                if user_performing_action
                else GENERAL_HEADERS
            ),
        )
        response.raise_for_status()
        return [FullAgentSnapshot(**agent) for agent in response.json()]

    @staticmethod
    def get_one(
        agent_id: int,
        user_performing_action: DATestUser | None = None,
    ) -> list[FullAgentSnapshot]:
        response = requests.get(
            f"{API_SERVER_URL}/agent/{agent_id}",
            headers=(
                user_performing_action.headers
                if user_performing_action
                else GENERAL_HEADERS
            ),
        )
        response.raise_for_status()
        return [FullAgentSnapshot(**response.json())]

    @staticmethod
    def verify(
        agent: DATestAgent,
        user_performing_action: DATestUser | None = None,
    ) -> bool:
        all_agents = AgentManager.get_one(
            agent_id=agent.id,
            user_performing_action=user_performing_action,
        )
        for fetched_agent in all_agents:
            if fetched_agent.id == agent.id:
                mismatches: list[tuple[str, object, object]] = []

                if fetched_agent.name != agent.name:
                    mismatches.append(("name", agent.name, fetched_agent.name))
                if fetched_agent.description != agent.description:
                    mismatches.append(
                        (
                            "description",
                            agent.description,
                            fetched_agent.description,
                        )
                    )
                if fetched_agent.num_chunks != agent.num_chunks:
                    mismatches.append(
                        ("num_chunks", agent.num_chunks, fetched_agent.num_chunks)
                    )
                if fetched_agent.llm_relevance_filter != agent.llm_relevance_filter:
                    mismatches.append(
                        (
                            "llm_relevance_filter",
                            agent.llm_relevance_filter,
                            fetched_agent.llm_relevance_filter,
                        )
                    )
                if fetched_agent.is_public != agent.is_public:
                    mismatches.append(
                        ("is_public", agent.is_public, fetched_agent.is_public)
                    )
                if (
                    fetched_agent.llm_filter_extraction
                    != agent.llm_filter_extraction
                ):
                    mismatches.append(
                        (
                            "llm_filter_extraction",
                            agent.llm_filter_extraction,
                            fetched_agent.llm_filter_extraction,
                        )
                    )
                if (
                    fetched_agent.llm_model_provider_override
                    != agent.llm_model_provider_override
                ):
                    mismatches.append(
                        (
                            "llm_model_provider_override",
                            agent.llm_model_provider_override,
                            fetched_agent.llm_model_provider_override,
                        )
                    )
                if (
                    fetched_agent.llm_model_version_override
                    != agent.llm_model_version_override
                ):
                    mismatches.append(
                        (
                            "llm_model_version_override",
                            agent.llm_model_version_override,
                            fetched_agent.llm_model_version_override,
                        )
                    )
                if fetched_agent.system_prompt != agent.system_prompt:
                    mismatches.append(
                        (
                            "system_prompt",
                            agent.system_prompt,
                            fetched_agent.system_prompt,
                        )
                    )
                if fetched_agent.task_prompt != agent.task_prompt:
                    mismatches.append(
                        (
                            "task_prompt",
                            agent.task_prompt,
                            fetched_agent.task_prompt,
                        )
                    )
                if fetched_agent.datetime_aware != agent.datetime_aware:
                    mismatches.append(
                        (
                            "datetime_aware",
                            agent.datetime_aware,
                            fetched_agent.datetime_aware,
                        )
                    )

                fetched_document_set_ids = {
                    document_set.id for document_set in fetched_agent.document_sets
                }
                expected_document_set_ids = set(agent.document_set_ids)
                if fetched_document_set_ids != expected_document_set_ids:
                    mismatches.append(
                        (
                            "document_set_ids",
                            sorted(expected_document_set_ids),
                            sorted(fetched_document_set_ids),
                        )
                    )

                fetched_tool_ids = {tool.id for tool in fetched_agent.tools}
                expected_tool_ids = set(agent.tool_ids)
                if fetched_tool_ids != expected_tool_ids:
                    mismatches.append(
                        (
                            "tool_ids",
                            sorted(expected_tool_ids),
                            sorted(fetched_tool_ids),
                        )
                    )

                fetched_user_emails = {user.email for user in fetched_agent.users}
                expected_user_emails = set(agent.users)
                if fetched_user_emails != expected_user_emails:
                    mismatches.append(
                        (
                            "users",
                            sorted(expected_user_emails),
                            sorted(fetched_user_emails),
                        )
                    )

                fetched_group_ids = set(fetched_agent.groups)
                expected_group_ids = set(agent.groups)
                if fetched_group_ids != expected_group_ids:
                    mismatches.append(
                        (
                            "groups",
                            sorted(expected_group_ids),
                            sorted(fetched_group_ids),
                        )
                    )

                fetched_label_ids = {label.id for label in fetched_agent.labels}
                expected_label_ids = set(agent.label_ids)
                if fetched_label_ids != expected_label_ids:
                    mismatches.append(
                        (
                            "label_ids",
                            sorted(expected_label_ids),
                            sorted(fetched_label_ids),
                        )
                    )

                if mismatches:
                    print(
                        f"Agent verification failed for id={agent.id}. Fields mismatched:"
                    )
                    for field_name, expected_value, actual_value in mismatches:
                        print(
                            f" - {field_name}: expected {expected_value!r}, got {actual_value!r}"
                        )
                    return False
                return True
        print(
            f"Agent verification failed: agent with id={agent.id} not found in fetched results."
        )
        return False

    @staticmethod
    def delete(
        agent: DATestAgent,
        user_performing_action: DATestUser | None = None,
    ) -> bool:
        response = requests.delete(
            f"{API_SERVER_URL}/agent/{agent.id}",
            headers=(
                user_performing_action.headers
                if user_performing_action
                else GENERAL_HEADERS
            ),
        )
        return response.ok


class AgentLabelManager:
    @staticmethod
    def create(
        label: DATestAgentLabel,
        user_performing_action: DATestUser | None = None,
    ) -> DATestAgentLabel:
        response = requests.post(
            f"{API_SERVER_URL}/agent/labels",
            json={
                "name": label.name,
            },
            headers=(
                user_performing_action.headers
                if user_performing_action
                else GENERAL_HEADERS
            ),
        )
        response.raise_for_status()
        response_data = response.json()
        label.id = response_data["id"]
        return label

    @staticmethod
    def get_all(
        user_performing_action: DATestUser | None = None,
    ) -> list[DATestAgentLabel]:
        response = requests.get(
            f"{API_SERVER_URL}/agent/labels",
            headers=(
                user_performing_action.headers
                if user_performing_action
                else GENERAL_HEADERS
            ),
        )
        response.raise_for_status()
        return [DATestAgentLabel(**label) for label in response.json()]

    @staticmethod
    def update(
        label: DATestAgentLabel,
        user_performing_action: DATestUser | None = None,
    ) -> DATestAgentLabel:
        response = requests.patch(
            f"{API_SERVER_URL}/admin/agent/label/{label.id}",
            json={
                "label_name": label.name,
            },
            headers=(
                user_performing_action.headers
                if user_performing_action
                else GENERAL_HEADERS
            ),
        )
        response.raise_for_status()
        return label

    @staticmethod
    def delete(
        label: DATestAgentLabel,
        user_performing_action: DATestUser | None = None,
    ) -> bool:
        response = requests.delete(
            f"{API_SERVER_URL}/admin/agent/label/{label.id}",
            headers=(
                user_performing_action.headers
                if user_performing_action
                else GENERAL_HEADERS
            ),
        )
        return response.ok

    @staticmethod
    def verify(
        label: DATestAgentLabel,
        user_performing_action: DATestUser | None = None,
    ) -> bool:
        all_labels = AgentLabelManager.get_all(user_performing_action)
        for fetched_label in all_labels:
            if fetched_label.id == label.id:
                return fetched_label.name == label.name
        return False
