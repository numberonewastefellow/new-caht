"""AgentTool: Wraps an existing Persona as a callable tool for the workflow orchestrator.

This follows the same pattern as dr_mock_tools.py RESEARCH_AGENT_TOOL_DESCRIPTION,
but generalized to support any Persona as a sub-agent.
"""

import json
import re
from typing import Any

from sqlalchemy.orm import Session

from onyx.chat.emitter import Emitter
from onyx.db.models import Persona
from onyx.server.query_and_chat.placement import Placement  # used by run() signature
from onyx.server.query_and_chat.streaming_models import Packet
from onyx.server.query_and_chat.streaming_models import SectionEnd
from onyx.tools.interface import Tool
from onyx.tools.models import ToolResponse


AGENT_TOOL_RESPONSE_ID = "agent_tool_response"


def _sanitize_tool_name(name: str) -> str:
    """Convert persona name to a valid tool name (alphanumeric + underscores only)."""
    sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", name.lower().strip())
    sanitized = re.sub(r"_+", "_", sanitized).strip("_")
    return f"delegate_to_{sanitized}"


class AgentTool(Tool[None]):
    """Wraps an existing Persona as a callable tool for the orchestrator LLM.

    When the orchestrator decides to call this tool, it runs the persona's
    full LLM loop with its own tools and knowledge configuration.
    """

    def __init__(
        self,
        persona: Persona,
        emitter: Emitter,
        db_session: Session,
        step_name: str | None = None,
        step_order: int = 0,
        step_id: int | None = None,
        output_key: str = "output",
    ) -> None:
        super().__init__(emitter=emitter)
        self._persona = persona
        self._db_session = db_session
        self._step_name = step_name or persona.name
        self._step_order = step_order
        self._step_id = step_id
        self._output_key = output_key

    @property
    def id(self) -> int:
        return self._persona.id

    @property
    def step_id(self) -> int:
        """Return the workflow step ID (for execution tracking)."""
        return self._step_id if self._step_id is not None else self._persona.id

    @property
    def output_key(self) -> str:
        return self._output_key

    @property
    def name(self) -> str:
        return _sanitize_tool_name(self._persona.name)

    @property
    def description(self) -> str:
        return (
            f"Delegate task to agent '{self._persona.name}': "
            f"{self._persona.description or 'No description'}"
        )

    @property
    def display_name(self) -> str:
        return f"Agent: {self._persona.name}"

    def tool_definition(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task": {
                            "type": "string",
                            "description": (
                                f"The task/query to delegate to the "
                                f"'{self._persona.name}' agent. "
                                f"Be specific about what you need this agent to do."
                            ),
                        }
                    },
                    "required": ["task"],
                },
            },
        }

    def emit_start(self, placement: Placement) -> None:
        """No-op: the workflow engine yields WorkflowStepStart directly."""
        pass

    def run(
        self,
        placement: Placement,
        override_kwargs: None = None,  # noqa: ARG002
        **llm_kwargs: Any,
    ) -> ToolResponse:
        """Run the persona's full LLM loop as a sub-agent.

        This is the core of the multi-agent system: it reuses the existing
        llm_loop infrastructure to run a full agent cycle with the persona's
        own LLM, tools, and knowledge configuration.
        """
        task = llm_kwargs.get("task", "")
        if not task:
            return ToolResponse(
                rich_response=None,
                llm_facing_response=json.dumps(
                    {"error": "No task provided to agent"}
                ),
            )

        # Import here to avoid circular imports
        from onyx.chat.chat_state import ChatStateContainer
        from onyx.chat.citation_processor import DynamicCitationProcessor
        from onyx.chat.llm_loop import construct_message_history
        from onyx.chat.llm_step import run_llm_step
        from onyx.chat.models import ChatMessageSimple
        from onyx.configs.constants import MessageType
        from onyx.llm.factory import get_llm_for_persona
        from onyx.llm.models import ToolChoiceOptions
        from onyx.tools.tool_constructor import construct_tools
        from onyx.tools.tool_constructor import SearchToolConfig
        from onyx.llm.factory import get_llm_token_counter

        # Get the persona's LLM
        llm = get_llm_for_persona(self._persona, self._db_session)
        token_counter = get_llm_token_counter(llm)

        # Build the persona's tools
        # We need a User object - get it from the persona's owner or use a minimal one
        from onyx.db.models import User

        user = self._db_session.get(User, self._persona.user_id)
        if user is None:
            # Fallback: try to get any admin user
            from sqlalchemy import select

            user = self._db_session.execute(select(User).limit(1)).scalar_one_or_none()

        if user is None:
            return ToolResponse(
                rich_response=None,
                llm_facing_response=json.dumps(
                    {"error": "Cannot run agent without user context"}
                ),
            )

        tool_dict = construct_tools(
            persona=self._persona,
            db_session=self._db_session,
            emitter=self.emitter,
            user=user,
            llm=llm,
            search_tool_config=SearchToolConfig(),
        )
        tools = []
        for tool_list in tool_dict.values():
            tools.extend(tool_list)

        # Build system prompt from persona
        system_prompt_text = self._persona.system_prompt or ""
        if self._persona.task_prompt:
            system_prompt_text += f"\n\n{self._persona.task_prompt}"
        if not system_prompt_text:
            system_prompt_text = (
                f"You are {self._persona.name}. {self._persona.description or ''}"
            )

        system_prompt = ChatMessageSimple(
            message=system_prompt_text,
            token_count=token_counter(system_prompt_text),
            message_type=MessageType.SYSTEM,
        )

        # Create user message from the delegated task
        user_message = ChatMessageSimple(
            message=task,
            token_count=token_counter(task),
            message_type=MessageType.USER,
        )

        msg_history: list[ChatMessageSimple] = [user_message]
        state_container = ChatStateContainer()
        citation_processor = DynamicCitationProcessor()

        # Run a multi-turn loop (similar to research_agent.py pattern)
        max_cycles = 5  # Sub-agent gets up to 5 tool-call cycles
        final_answer = ""

        for cycle in range(max_cycles):
            truncated_history = construct_message_history(
                system_prompt=system_prompt,
                custom_agent_prompt=None,
                simple_chat_history=msg_history,
                reminder_message=None,
                project_files=None,
                available_tokens=llm.config.max_input_tokens,
            )

            tool_defs = [t.tool_definition() for t in tools]
            tool_choice = (
                ToolChoiceOptions.AUTO if tools else ToolChoiceOptions.NONE
            )

            llm_step_result, _ = run_llm_step(
                emitter=self.emitter,
                history=truncated_history,
                tool_definitions=tool_defs,
                tool_choice=tool_choice,
                llm=llm,
                placement=placement,
                citation_processor=citation_processor,
                state_container=state_container,
                final_documents=None,
                user_identity=None,
            )

            # If LLM produced a text answer (no tool calls), we're done
            if llm_step_result.answer and not llm_step_result.tool_calls:
                final_answer = llm_step_result.answer
                break

            # If there are tool calls, execute them directly
            if llm_step_result.tool_calls:
                # Build a name→tool lookup for matching
                tool_by_name: dict[str, Tool] = {
                    t.name if hasattr(t, "name") else t.tool_definition()
                    .get("function", {})
                    .get("name", ""): t
                    for t in tools
                }

                for tc in llm_step_result.tool_calls:
                    matched_tool = tool_by_name.get(tc.tool_name)
                    if matched_tool is None:
                        # Tool not found — add error response to history
                        error_msg = f"Tool '{tc.tool_name}' not found"
                        tool_call_msg = ChatMessageSimple(
                            message=json.dumps(
                                {
                                    "tool_call_id": tc.tool_call_id,
                                    "name": tc.tool_name,
                                    "arguments": tc.tool_args,
                                }
                            ),
                            token_count=50,
                            message_type=MessageType.ASSISTANT,
                        )
                        msg_history.append(tool_call_msg)
                        msg_history.append(
                            ChatMessageSimple(
                                message=error_msg,
                                token_count=token_counter(error_msg),
                                message_type=MessageType.TOOL_CALL_RESPONSE,
                            )
                        )
                        continue

                    # Emit tool start (e.g., SearchToolStart) so the
                    # frontend can identify and render the tool group.
                    # Use tc.placement which has auto-incremented
                    # turn_index/tab_index from ToolCallKickoff.
                    matched_tool.emit_start(placement=tc.placement)

                    # Run the tool with the kickoff's placement
                    tool_response = matched_tool.run(
                        tc.placement, None, **tc.tool_args
                    )
                    tool_response.tool_call = tc

                    # Emit SectionEnd so the frontend marks the tool
                    # group as complete
                    self.emitter.emit(
                        Packet(
                            placement=tc.placement,
                            obj=SectionEnd(),
                        )
                    )

                    # Add assistant message with tool call
                    tool_call_msg = ChatMessageSimple(
                        message=json.dumps(
                            {
                                "tool_call_id": tc.tool_call_id,
                                "name": tc.tool_name,
                                "arguments": tc.tool_args,
                            }
                        ),
                        token_count=50,
                        message_type=MessageType.ASSISTANT,
                    )
                    msg_history.append(tool_call_msg)

                    # Add tool response
                    tool_response_msg = ChatMessageSimple(
                        message=tool_response.llm_facing_response or "",
                        token_count=token_counter(
                            tool_response.llm_facing_response or ""
                        ),
                        message_type=MessageType.TOOL_CALL_RESPONSE,
                    )
                    msg_history.append(tool_response_msg)

                # If the LLM also produced text alongside tool calls, save it
                if llm_step_result.answer:
                    final_answer = llm_step_result.answer
            else:
                # No tool calls and no answer — shouldn't happen, break
                final_answer = llm_step_result.answer or ""
                break

        if not final_answer:
            final_answer = "(Agent did not produce a final answer)"

        # The workflow engine streams emitter.bus via _stream_agent_packets()
        # in real-time while this method runs in a background thread, capturing
        # all intermediate packets (search, reasoning, etc.) as they are emitted.

        return ToolResponse(
            rich_response=final_answer,
            llm_facing_response=json.dumps(
                {
                    "agent_name": self._persona.name,
                    "agent_output": final_answer,
                }
            ),
        )
