"""Builds the ``AgentTool`` that runs an ``agent`` node, once per node per run.

LLMs are cached per (provider, model) and agents are loaded on the
coordinator thread (agent.tools is read here, not lazily in the agent thread).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from om.llm.factory import get_llm_for_agent
from om.llm.interfaces import LLM
from om.llm.override_models import LLMOverride
from om.tools.tool_implementations.agent_tool import AgentTool
from om.workflows.nodes.agent import AgentStepConfigV1
from om.workflows.nodes.agent import load_step_agent

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from om.chat.emitter import Emitter
    from om.db.models import Agent
    from om.db.models import User
    from om.tools.models import ChatFile
    from om.workflows.graph import WorkflowNode


class AgentToolCache:
    """Creates and caches one AgentTool per agent node for a single run."""

    def __init__(
        self,
        *,
        db_session: Session,
        user: User,
        emitter: Emitter,
        chat_files: list[ChatFile] | None = None,
        sandbox_session_id: str | None = None,
    ) -> None:
        self._db_session = db_session
        self._user = user
        self._emitter = emitter
        self._chat_files = chat_files
        self._sandbox_session_id = sandbox_session_id
        self._tools: dict[str, AgentTool] = {}
        self._llms: dict[tuple[int, str | None, str | None], LLM] = {}

    def get(self, node: WorkflowNode, config: AgentStepConfigV1) -> AgentTool:
        """The AgentTool for ``node``.

        Raises:
            UnusableStepAgentError: the node's agent can't run workflow steps.
        """
        if node.node_key not in self._tools:
            self._tools[node.node_key] = self._build(node, config)
        return self._tools[node.node_key]

    def _build(self, node: WorkflowNode, config: AgentStepConfigV1) -> AgentTool:
        agent = load_step_agent(self._db_session, config.agent_id)
        has_tools = (
            bool(config.tool_ids_override)
            if config.tool_ids_override is not None
            else bool(agent.tools)
        )
        return AgentTool(
            agent=agent,
            emitter=self._emitter,
            db_session=self._db_session,
            step_name=node.name,
            step_order=node.step_order,
            step_id=node.step_id,
            output_key=node.output_key,
            user=self._user,
            llm=self._llm_for(agent, config),
            has_tools=has_tools,
            promote_output=node.promote_output,
            chat_files=self._chat_files,
            sandbox_session_id=self._sandbox_session_id,
            # Step-level overrides (applied in AgentTool.run())
            max_output_tokens_override=config.max_output_tokens_override,
            system_prompt_override=config.system_prompt_override,
            task_prompt_override=config.task_prompt_override,
            tool_ids_override=config.tool_ids_override,
            document_set_ids_override=config.document_set_ids_override,
            replace_base_system_prompt_override=config.replace_base_system_prompt_override,
        )

    def _llm_for(self, agent: Agent, config: AgentStepConfigV1) -> LLM:
        """The agent's LLM, honouring the step's provider/model override."""
        key = (agent.id, config.llm_provider_override, config.llm_model_override)
        if key not in self._llms:
            if config.llm_provider_override:
                self._llms[key] = get_llm_for_agent(
                    agent,
                    self._user,
                    llm_override=LLMOverride(
                        model_provider=config.llm_provider_override,
                        model_version=config.llm_model_override,
                    ),
                )
            else:
                self._llms[key] = get_llm_for_agent(agent, self._user)
        return self._llms[key]
