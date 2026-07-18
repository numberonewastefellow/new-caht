"""AgentTool: Wraps an existing Agent as a callable tool for the workflow orchestrator.

This follows the same pattern as dr_mock_tools.py RESEARCH_AGENT_TOOL_DESCRIPTION,
but generalized to support any Agent as a sub-agent.
"""

import json
import re
from collections.abc import Callable
from typing import Any
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from om.chat.emitter import Emitter
from om.db.models import Agent
from om.server.query_and_chat.placement import Placement  # used by run() signature
from om.server.query_and_chat.streaming_models import Packet
from om.server.query_and_chat.streaming_models import SectionEnd
from om.tools.interface import Tool
from om.tools.models import ChatFile
from om.tools.models import ToolResponse
from om.utils.logger import setup_logger

logger = setup_logger()

if TYPE_CHECKING:
    from om.db.models import User
    from om.llm.interfaces import LLM


AGENT_TOOL_RESPONSE_ID = "agent_tool_response"


def _sanitize_tool_name(name: str) -> str:
    """Convert agent name to a valid tool name (alphanumeric + underscores only)."""
    sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", name.lower().strip())
    sanitized = re.sub(r"_+", "_", sanitized).strip("_")
    return f"delegate_to_{sanitized}"


# Max tokens of extracted attached-file text to inline into a NON-PythonTool
# agent's prompt. PythonTool agents read the bytes in their sandbox instead, so
# this budget only applies to agents that cannot open files themselves.
_MAX_ATTACHED_FILE_TEXT_TOKENS = 50000

# Image files have no useful extractable text — list them by name only.
_IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp")


def _build_attached_files_section(
    chat_files: list["ChatFile"],
    token_counter: Callable[[str], int],
) -> str:
    """Inline the *content* of attached files for a NON-PythonTool agent.

    Such agents (e.g. Policy Coverage Analyst) cannot open files themselves —
    without this they only ever see filenames. We extract each document's text
    with the production extractor and inline it under a token budget so the agent
    can actually read e.g. a policy ``.docx``.

    - Image files → listed by name only (no useful text).
    - Document/data files → extracted to text and inlined until the budget is
      hit; overflow and extraction failures fall back to filename-only so one
      large/bad file can't overflow context or break the prompt.
    """
    from io import BytesIO

    from om.file_processing.extract_file_text import extract_text_and_images

    inlined: list[str] = []
    listed_only: list[str] = []
    used_tokens = 0

    for f in chat_files:
        if f.filename.lower().endswith(_IMAGE_SUFFIXES):
            listed_only.append(f"{f.filename} (image)")
            continue
        try:
            result = extract_text_and_images(BytesIO(f.content), f.filename)
            text = (result.text_content or "").strip()
        except Exception:
            listed_only.append(f"{f.filename} (could not extract text)")
            continue
        if not text:
            listed_only.append(f"{f.filename} (no extractable text)")
            continue
        tokens = token_counter(text)
        if used_tokens + tokens > _MAX_ATTACHED_FILE_TEXT_TOKENS:
            listed_only.append(f"{f.filename} (content omitted — exceeds context budget)")
            continue
        used_tokens += tokens
        inlined.append(f"### {f.filename}\n{text}")

    parts = [
        "\n\n## Attached Document Contents\n"
        "The user attached the documents below; their extracted text follows. "
        "Treat this as the authoritative source data — do NOT ask the user to "
        "upload or re-send these, and do NOT generate synthetic data."
    ]
    if inlined:
        parts.append("\n\n".join(inlined))
    if listed_only:
        parts.append(
            "Files referenced by name only (no inlined text):\n"
            + "\n".join(f"- {n}" for n in listed_only)
        )
    return "\n\n".join(parts)


class AgentTool(Tool[None]):
    """Wraps an existing Agent as a callable tool for the orchestrator LLM.

    When the orchestrator decides to call this tool, it runs the agent's
    full LLM loop with its own tools and knowledge configuration.
    """

    def __init__(
        self,
        agent: Agent,
        emitter: Emitter,
        db_session: Session,
        step_name: str | None = None,
        step_order: int = 0,
        step_id: int | None = None,
        output_key: str = "output",
        user: "User | None" = None,
        llm: "LLM | None" = None,
        has_tools: bool | None = None,
        promote_output: bool = False,
        chat_files: list[ChatFile] | None = None,
        sandbox_session_id: str | None = None,
        # Step-level overrides (override agent defaults)
        max_cycles_override: int | None = None,
        max_output_tokens_override: int | None = None,
        system_prompt_override: str | None = None,
        task_prompt_override: str | None = None,
        tool_ids_override: list[int] | None = None,
        document_set_ids_override: list[int] | None = None,
        replace_base_system_prompt_override: bool | None = None,
    ) -> None:
        super().__init__(emitter=emitter)
        self._agent = agent
        self._db_session = db_session
        self._step_name = step_name or agent.name
        self._step_order = step_order
        self._step_id = step_id
        self._output_key = output_key
        self._cached_user = user
        self._cached_llm = llm
        # Pre-check whether agent has tools (avoids lazy-load in bg thread)
        self._has_tools = has_tools if has_tools is not None else bool(agent.tools)
        self._promote_output = promote_output
        self._chat_files = chat_files or []
        self._sandbox_session_id = sandbox_session_id
        # Step-level overrides
        self._max_cycles_override = max_cycles_override
        self._max_output_tokens_override = max_output_tokens_override
        self._system_prompt_override = system_prompt_override
        self._task_prompt_override = task_prompt_override
        self._tool_ids_override = tool_ids_override
        self._document_set_ids_override = document_set_ids_override
        self._replace_base_system_prompt_override = replace_base_system_prompt_override

    @property
    def id(self) -> int:
        return self._agent.id

    @property
    def step_id(self) -> int:
        """Return the workflow step ID (for execution tracking)."""
        return self._step_id if self._step_id is not None else self._agent.id

    @property
    def output_key(self) -> str:
        return self._output_key

    @property
    def promote_output(self) -> bool:
        return self._promote_output

    @property
    def name(self) -> str:
        return _sanitize_tool_name(self._agent.name)

    @property
    def description(self) -> str:
        return (
            f"Delegate task to agent '{self._agent.name}': "
            f"{self._agent.description or 'No description'}"
        )

    @property
    def display_name(self) -> str:
        return f"Agent: {self._agent.name}"

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
                                f"'{self._agent.name}' agent. "
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
        """Run the agent's full LLM loop as a sub-agent.

        This is the core of the multi-agent system: it reuses the existing
        llm_loop infrastructure to run a full agent cycle with the agent's
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
        from om.chat.chat_state import ChatStateContainer
        from om.chat.citation_processor import DynamicCitationProcessor
        from om.chat.llm_loop import construct_message_history
        from om.chat.llm_step import run_llm_step
        from om.chat.models import ChatMessageSimple
        from om.chat.models import ToolCallSimple
        from om.configs.constants import MessageType
        from om.llm.factory import get_llm_for_agent
        from om.llm.models import ToolChoiceOptions
        from om.llm.factory import get_llm_token_counter

        # Resolve user (use cached if pre-computed by workflow engine)
        from om.db.models import User

        user = self._cached_user
        if user is None:
            user = self._db_session.get(User, self._agent.user_id)
        if user is None:
            from sqlalchemy import select
            user = self._db_session.execute(select(User).limit(1)).scalar_one_or_none()
        if user is None:
            return ToolResponse(
                rich_response=None,
                llm_facing_response=json.dumps(
                    {"error": "Cannot run agent without user context"}
                ),
            )

        # Use cached LLM or create one (bug fix: pass user, not db_session)
        llm = self._cached_llm or get_llm_for_agent(self._agent, user)
        token_counter = get_llm_token_counter(llm)

        # Build agent's tools — skip entirely if agent has none (Tier 1.1)
        tools: list = []
        # Unique scope ID for MCP session persistence within this agent step
        mcp_scope_id = f"agent_step_{self._step_id}_{id(self)}"
        if self._has_tools:
            from om.tools.tool_constructor import construct_tools
            from om.tools.tool_constructor import SearchToolConfig

            tool_dict = construct_tools(
                agent=self._agent,
                db_session=self._db_session,
                emitter=self.emitter,
                user=user,
                llm=llm,
                search_tool_config=SearchToolConfig(),
                chat_session_id=mcp_scope_id,
                allowed_tool_ids=self._tool_ids_override,
            )
            for tool_list in tool_dict.values():
                tools.extend(tool_list)

        # Build system prompt: step override > agent value
        effective_system = (
            self._system_prompt_override
            if self._system_prompt_override is not None
            else (self._agent.system_prompt or "")
        )
        effective_task = (
            self._task_prompt_override
            if self._task_prompt_override is not None
            else (self._agent.task_prompt or "")
        )

        system_prompt_text = effective_system
        if effective_task:
            system_prompt_text += f"\n\n{effective_task}"
        if not system_prompt_text:
            system_prompt_text = (
                f"You are {self._agent.name}. {self._agent.description or ''}"
            )

        # Append tool-specific guidance (mirrors prompt_utils.py behaviour)
        from om.tools.tool_implementations.python.python_tool import PythonTool
        has_python_tool = any(isinstance(t, PythonTool) for t in tools)
        if has_python_tool:
            from om.prompts.tool_prompts import PYTHON_TOOL_GUIDANCE
            system_prompt_text += PYTHON_TOOL_GUIDANCE

        # Give the agent its attached files. PythonTool agents read the bytes
        # pre-loaded in their sandbox; agents without a PythonTool can't open
        # files, so we inline the extracted document text instead.
        if self._chat_files:
            if has_python_tool:
                file_names = [f.filename for f in self._chat_files]
                system_prompt_text += (
                    "\n\n## Available Files\n"
                    "The following files are pre-loaded in your working directory and can be "
                    f"read directly (e.g., `pd.read_csv('{file_names[0]}')`):\n"
                    + "\n".join(f"- {name}" for name in file_names)
                    + "\n\nDo NOT generate synthetic data — use these real files instead."
                )
            else:
                system_prompt_text += _build_attached_files_section(
                    self._chat_files, token_counter
                )

        logger.info(
            "[Trace] agent='%s' has_python_tool=%s files=%d branch=%s",
            self._agent.name,
            has_python_tool,
            len(self._chat_files),
            ("sandbox" if has_python_tool else "inlined")
            if self._chat_files
            else "none",
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

        # Pre-compute tool definitions once (they don't change between cycles)
        tool_defs = [t.tool_definition() for t in tools]
        tool_choice = ToolChoiceOptions.AUTO if tools else ToolChoiceOptions.NONE

        # Run a multi-turn loop (similar to research_agent.py pattern)
        max_cycles = self._max_cycles_override or 40
        final_answer = ""

        for cycle in range(max_cycles):
            truncated_history = construct_message_history(
                system_prompt=system_prompt,
                custom_agent_prompt=None,
                simple_chat_history=msg_history,
                reminder_message=None,
                workspace_files=None,
                available_tokens=llm.config.max_input_tokens,
            )

            # Resolve max output tokens: step override > agent > default 5000
            _max_tokens = (
                self._max_output_tokens_override
                or (self._agent.max_output_tokens if self._agent else None)
                or 5000
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
                max_tokens=_max_tokens,
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
                        # Tool not found — add structured error response
                        error_msg = f"Tool '{tc.tool_name}' not found"
                        tool_call_msg = ChatMessageSimple(
                            message="",
                            token_count=50,
                            message_type=MessageType.ASSISTANT,
                            tool_calls=[
                                ToolCallSimple(
                                    tool_call_id=tc.tool_call_id,
                                    tool_name=tc.tool_name,
                                    tool_arguments=tc.tool_args,
                                )
                            ],
                        )
                        msg_history.append(tool_call_msg)
                        msg_history.append(
                            ChatMessageSimple(
                                message=error_msg,
                                token_count=token_counter(error_msg),
                                message_type=MessageType.TOOL_CALL_RESPONSE,
                                tool_call_id=tc.tool_call_id,
                            )
                        )
                        continue

                    # Emit tool start (e.g., SearchToolStart) so the
                    # frontend can identify and render the tool group.
                    # Use tc.placement which has auto-incremented
                    # turn_index/tab_index from ToolCallKickoff.
                    matched_tool.emit_start(placement=tc.placement)

                    # Build override_kwargs for the tool (pass files + sandbox session to PythonTool)
                    override_kwargs = None
                    if isinstance(matched_tool, PythonTool):
                        from om.tools.models import PythonToolOverrideKwargs
                        override_kwargs = PythonToolOverrideKwargs(
                            chat_files=self._chat_files,
                            session_id=self._sandbox_session_id,
                        )

                    # Run the tool with the kickoff's placement
                    try:
                        tool_response = matched_tool.run(
                            tc.placement, override_kwargs, **tc.tool_args
                        )
                    except Exception as e:
                        # Gracefully handle tool errors (e.g., empty search results)
                        # so the agent can continue rather than crashing the workflow
                        from om.tools.models import ToolCallException
                        logger.warning(
                            f"Tool {tc.tool_name} failed: {e}"
                        )
                        error_msg = (
                            e.llm_facing_message
                            if isinstance(e, ToolCallException)
                            else str(e)
                        )
                        tool_response = ToolResponse(
                            rich_response=None,
                            llm_facing_response=f"Tool error: {error_msg}",
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

                    # Add assistant message with structured tool call
                    tool_call_msg = ChatMessageSimple(
                        message="",
                        token_count=50,
                        message_type=MessageType.ASSISTANT,
                        tool_calls=[
                            ToolCallSimple(
                                tool_call_id=tc.tool_call_id,
                                tool_name=tc.tool_name,
                                tool_arguments=tc.tool_args,
                            )
                        ],
                    )
                    msg_history.append(tool_call_msg)

                    # Add tool response with tool_call_id
                    tool_response_text = tool_response.llm_facing_response or ""
                    tool_response_msg = ChatMessageSimple(
                        message=tool_response_text,
                        token_count=token_counter(tool_response_text),
                        message_type=MessageType.TOOL_CALL_RESPONSE,
                        tool_call_id=tc.tool_call_id,
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

        # Post-step file capture: fetch any files tracked during this agent
        # step (e.g., DOCX/PPTX/PDF created by MCP tools) and save to MinIO.
        # This runs BEFORE the MCP session closes so the files are still
        # available on the MCP server.
        from om.tools.tool_implementations.mcp.mcp_tool import (
            collect_pending_files,
        )
        step_file_ids, step_file_details = collect_pending_files(
            scope_id=mcp_scope_id,
            emitter=self.emitter,
            placement=placement,
        )

        # Close any persistent MCP sessions opened during this agent step.
        # This ensures server-side resources (e.g., in-memory presentations)
        # are properly released after the agent finishes its work.
        from om.tools.tool_implementations.mcp.mcp_client import (
            mcp_session_manager,
        )
        mcp_session_manager.close_scope(mcp_scope_id)

        # The workflow engine streams emitter.bus via _stream_agent_packets()
        # in real-time while this method runs in a background thread, capturing
        # all intermediate packets (search, reasoning, etc.) as they are emitted.

        response_dict: dict[str, Any] = {
            "agent_name": self._agent.name,
            "agent_output": final_answer,
        }
        # Persist file metadata so session reload can reconstruct download
        # links and downstream workflow steps can access file info.
        if step_file_ids:
            response_dict["_file_ids"] = step_file_ids
            response_dict["_file_details"] = step_file_details

        return ToolResponse(
            rich_response=final_answer,
            llm_facing_response=json.dumps(response_dict),
        )
