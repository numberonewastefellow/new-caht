"""
IMPORTANT: familiarize yourself with the design concepts prior to contributing to this file.
An overview can be found in the README.md file in this directory.
"""

import re
import traceback
from collections.abc import Callable
from contextvars import Token
from uuid import UUID

from pydantic import BaseModel
from redis.client import Redis
from sqlalchemy.orm import Session

from om.chat.chat_processing_checker import set_processing_status
from om.chat.chat_state import ChatStateContainer
from om.chat.chat_state import run_chat_loop_with_state_containers
from om.chat.chat_utils import convert_chat_history
from om.chat.chat_utils import create_chat_history_chain
from om.chat.chat_utils import create_chat_session_from_request
from om.chat.chat_utils import get_custom_agent_prompt
from om.chat.chat_utils import is_last_assistant_message_clarification
from om.chat.chat_utils import load_all_chat_files
from om.chat.compression import calculate_total_history_tokens
from om.chat.compression import compress_chat_history
from om.chat.compression import find_summary_for_branch
from om.chat.compression import get_compression_params
from om.chat.emitter import get_default_emitter
from om.chat.llm_loop import run_llm_loop
from om.chat.models import AnswerStream
from om.chat.models import ChatBasicResponse
from om.chat.models import ChatFullResponse
from om.chat.models import ChatLoadedFile
from om.chat.models import ChatMessageSimple
from om.chat.models import CreateChatSessionID
from om.chat.models import ExtractedWorkspaceFiles
from om.chat.models import FileToolMetadata
from om.chat.models import WorkspaceFileMetadata
from om.chat.models import WorkspaceSearchConfig
from om.chat.models import StreamingError
from om.chat.models import ToolCallResponse
from om.chat.prompt_utils import calculate_reserved_tokens
from om.chat.save_chat import save_chat_turn
from om.chat.stop_signal_checker import is_connected as check_stop_signal
from om.chat.stop_signal_checker import reset_cancel_status
from om.configs.app_configs import DISABLE_VECTOR_DB
from om.configs.app_configs import INTEGRATION_TESTS_MODE
from om.configs.constants import DEFAULT_AGENT_ID
from om.configs.constants import DocumentSource
from om.configs.constants import MessageType
from om.configs.constants import MilestoneRecordType
from om.context.search.models import BaseFilters
from om.context.search.models import SearchDoc
from om.db.chat import create_new_chat_message
from om.db.chat import get_chat_session_by_id
from om.db.chat import get_or_create_root_message
from om.db.chat import reserve_message_id
from om.db.memory import get_memories
from om.db.models import ChatMessage
from om.db.models import ChatSession
from om.db.models import Agent
from om.db.models import User
from om.db.models import KnowledgeFile
from om.db.workspaces import get_workspace_token_count
from om.db.workspaces import get_knowledge_files_from_workspace
from om.db.tools import get_tools
from om.deep_research.dr_loop import run_deep_research_llm_loop
from om.file_store.models import ChatFileType
from om.file_store.utils import load_in_memory_chat_files
from om.file_store.utils import verify_knowledge_files
from om.llm.factory import get_llm_for_agent
from om.llm.factory import get_llm_token_counter
from om.llm.interfaces import LLM
from om.llm.interfaces import LLMUserIdentity
from om.llm.request_context import reset_llm_mock_response
from om.llm.request_context import set_llm_mock_response
from om.llm.utils import litellm_exception_to_error_msg
from om.onyxbot.slack.models import SlackContext
from om.redis.redis_pool import get_redis_client
from om.server.query_and_chat.models import AUTO_PLACE_AFTER_LATEST_MESSAGE
from om.server.query_and_chat.models import MessageResponseIDInfo
from om.server.query_and_chat.models import SendMessageRequest
from om.server.query_and_chat.streaming_models import AgentResponseDelta
from om.server.query_and_chat.streaming_models import AgentResponseStart
from om.server.query_and_chat.streaming_models import CitationInfo
from om.server.query_and_chat.streaming_models import Packet
from om.server.query_and_chat.streaming_models import StreamingType
from om.tools.constants import SEARCH_TOOL_ID
from om.tools.interface import Tool
from om.tools.models import ChatFile
from om.tools.models import SearchToolUsage
from om.tools.tool_constructor import construct_tools
from om.tools.tool_constructor import CustomToolConfig
from om.tools.tool_constructor import FileReaderToolConfig
from om.tools.tool_constructor import SearchToolConfig
from om.tools.tool_implementations.file_reader.file_reader_tool import (
    FileReaderTool,
)
from om.tools.tool_implementations.python.python_tool import PythonTool
from om.utils.logger import setup_logger
from om.utils.telemetry import mt_cloud_telemetry
from om.utils.timing import log_function_time
from shared_configs.contextvars import get_current_tenant_id

logger = setup_logger()
ERROR_TYPE_CANCELLED = "cancelled"


class _AvailableFiles(BaseModel):
    """Separated file IDs for the FileReaderTool so it knows which loader to use."""

    # IDs from the ``knowledge_file`` table (workspace / agent-attached files).
    knowledge_file_ids: list[UUID] = []
    # IDs from the ``file_record`` table (chat-attached files).
    chat_file_ids: list[UUID] = []


def _collect_available_file_ids(
    chat_history: list[ChatMessage],
    workspace_id: int | None,
    user_id: UUID | None,
    db_session: Session,
) -> _AvailableFiles:
    """Collect all file IDs the FileReaderTool should be allowed to access.

    Returns *separate* lists for chat-attached files (``file_record`` IDs) and
    workspace/user files (``knowledge_file`` IDs) so the tool can pick the right
    loader without a try/except fallback."""
    chat_file_ids: set[UUID] = set()
    knowledge_file_ids: set[UUID] = set()

    for msg in chat_history:
        if not msg.files:
            continue
        for fd in msg.files:
            try:
                chat_file_ids.add(UUID(fd["id"]))
            except (ValueError, KeyError):
                pass

    if workspace_id:
        workspace_files = get_knowledge_files_from_workspace(
            workspace_id=workspace_id,
            user_id=user_id,
            db_session=db_session,
        )
        for uf in workspace_files:
            knowledge_file_ids.add(uf.id)

    return _AvailableFiles(
        knowledge_file_ids=list(knowledge_file_ids),
        chat_file_ids=list(chat_file_ids),
    )


def _should_enable_slack_search(
    agent: Agent,
    filters: BaseFilters | None,
) -> bool:
    """Determine if Slack search should be enabled.

    Returns True if:
    - Source type filter exists and includes Slack, OR
    - Default agent with no source type filter
    """
    source_types = filters.source_type if filters else None
    return (source_types is not None and DocumentSource.SLACK in source_types) or (
        agent.id == DEFAULT_AGENT_ID and source_types is None
    )


def _convert_loaded_files_to_chat_files(
    loaded_files: list[ChatLoadedFile],
) -> list[ChatFile]:
    """Convert ChatLoadedFile objects to ChatFile for tool usage (e.g., PythonTool).

    Args:
        loaded_files: List of ChatLoadedFile objects from the chat history

    Returns:
        List of ChatFile objects that can be passed to tools
    """
    chat_files = []
    for loaded_file in loaded_files:
        if len(loaded_file.content) > 0:
            chat_files.append(
                ChatFile(
                    filename=loaded_file.filename or f"file_{loaded_file.file_id}",
                    content=loaded_file.content,
                )
            )
    return chat_files


def _extract_workspace_file_texts_and_images(
    workspace_id: int | None,
    user_id: UUID | None,
    llm_max_context_window: int,
    reserved_token_count: int,
    db_session: Session,
    # Because the tokenizer is a generic tokenizer, the token count may be incorrect.
    # to account for this, the maximum context that is allowed for this function is
    # 60% of the LLM's max context window. The other benefit is that for workspaces with
    # more files, this makes it so that we don't throw away the history too quickly every time.
    max_llm_context_percentage: float = 0.6,
) -> ExtractedWorkspaceFiles:
    """Extract text content from workspace files if they fit within the context window.

    Args:
        workspace_id: The workspace ID to load files from
        user_id: The user ID for authorization
        llm_max_context_window: Maximum tokens allowed in the LLM context window
        reserved_token_count: Number of tokens to reserve for other content
        db_session: Database session
        max_llm_context_percentage: Maximum percentage of the LLM context window to use.

    Returns:
        ExtractedWorkspaceFiles containing:
        - List of text content strings from workspace files (text files only)
        - List of image files from workspace (ChatLoadedFile objects)
        - Workspace id if the the workspace should be provided as a filter in search or None if not.
        - Total token count of all extracted files
    """
    # TODO I believe this is not handling all file types correctly.
    workspace_as_filter = False
    if not workspace_id:
        return ExtractedWorkspaceFiles(
            workspace_file_texts=[],
            workspace_image_files=[],
            workspace_as_filter=False,
            total_token_count=0,
            workspace_file_metadata=[],
            workspace_uncapped_token_count=None,
        )

    max_actual_tokens = (
        llm_max_context_window - reserved_token_count
    ) * max_llm_context_percentage

    # Calculate total token count for all user files in the workspace
    workspace_tokens = get_workspace_token_count(
        workspace_id=workspace_id,
        user_id=user_id,
        db_session=db_session,
    )

    workspace_file_texts: list[str] = []
    workspace_image_files: list[ChatLoadedFile] = []
    workspace_file_metadata: list[WorkspaceFileMetadata] = []
    total_token_count = 0
    if workspace_tokens < max_actual_tokens:
        # Load workspace files into memory using cached plaintext when available
        workspace_knowledge_files = get_knowledge_files_from_workspace(
            workspace_id=workspace_id,
            user_id=user_id,
            db_session=db_session,
        )
        if workspace_knowledge_files:
            # Create a mapping from file_id to KnowledgeFile for token count lookup
            user_file_map = {str(file.id): file for file in workspace_knowledge_files}

            workspace_file_ids = [file.id for file in workspace_knowledge_files]
            in_memory_workspace_files = load_in_memory_chat_files(
                knowledge_file_ids=workspace_file_ids,
                db_session=db_session,
            )

            # Extract text content from loaded files
            for file in in_memory_workspace_files:
                if file.file_type.is_text_file():
                    try:
                        text_content = file.content.decode("utf-8", errors="ignore")
                        # Strip null bytes
                        text_content = text_content.replace("\x00", "")
                        if text_content:
                            workspace_file_texts.append(text_content)
                            # Add metadata for citation support
                            workspace_file_metadata.append(
                                WorkspaceFileMetadata(
                                    file_id=str(file.file_id),
                                    filename=file.filename or f"file_{file.file_id}",
                                    file_content=text_content,
                                )
                            )
                            # Add token count for text file
                            knowledge_file = user_file_map.get(str(file.file_id))
                            if knowledge_file and knowledge_file.token_count:
                                total_token_count += knowledge_file.token_count
                    except Exception:
                        # Skip files that can't be decoded
                        pass
                elif file.file_type == ChatFileType.IMAGE:
                    # Convert InMemoryChatFile to ChatLoadedFile
                    knowledge_file = user_file_map.get(str(file.file_id))
                    token_count = (
                        knowledge_file.token_count
                        if knowledge_file and knowledge_file.token_count
                        else 0
                    )
                    total_token_count += token_count
                    chat_loaded_file = ChatLoadedFile(
                        file_id=file.file_id,
                        content=file.content,
                        file_type=file.file_type,
                        filename=file.filename,
                        content_text=None,  # Images don't have text content
                        token_count=token_count,
                    )
                    workspace_image_files.append(chat_loaded_file)
    else:
        if DISABLE_VECTOR_DB:
            # Without a vector DB we can't use workspace-as-filter search.
            # Instead, build lightweight metadata so the LLM can call the
            # FileReaderTool to inspect individual files on demand.
            file_metadata_for_tool = _build_file_tool_metadata_for_workspace(
                workspace_id=workspace_id,
                user_id=user_id,
                db_session=db_session,
            )
            return ExtractedWorkspaceFiles(
                workspace_file_texts=[],
                workspace_image_files=[],
                workspace_as_filter=False,
                total_token_count=0,
                workspace_file_metadata=[],
                workspace_uncapped_token_count=workspace_tokens,
                file_metadata_for_tool=file_metadata_for_tool,
            )
        workspace_as_filter = True

    return ExtractedWorkspaceFiles(
        workspace_file_texts=workspace_file_texts,
        workspace_image_files=workspace_image_files,
        workspace_as_filter=workspace_as_filter,
        total_token_count=total_token_count,
        workspace_file_metadata=workspace_file_metadata,
        workspace_uncapped_token_count=workspace_tokens,
    )


APPROX_CHARS_PER_TOKEN = 4


def _build_file_tool_metadata_for_workspace(
    workspace_id: int,
    user_id: UUID | None,
    db_session: Session,
) -> list[FileToolMetadata]:
    """Build lightweight FileToolMetadata for every file in a workspace.

    Used when files are too large to fit in context and the vector DB is
    disabled, so the LLM needs to know which files it can read via the
    FileReaderTool.
    """
    workspace_knowledge_files = get_knowledge_files_from_workspace(
        workspace_id=workspace_id,
        user_id=user_id,
        db_session=db_session,
    )
    return [
        FileToolMetadata(
            file_id=str(uf.id),
            filename=uf.name,
            approx_char_count=(uf.token_count or 0) * APPROX_CHARS_PER_TOKEN,
        )
        for uf in workspace_knowledge_files
    ]


def _build_file_tool_metadata_for_knowledge_files(
    knowledge_files: list[KnowledgeFile],
) -> list[FileToolMetadata]:
    """Build lightweight FileToolMetadata from a list of KnowledgeFile records."""
    return [
        FileToolMetadata(
            file_id=str(uf.id),
            filename=uf.name,
            approx_char_count=(uf.token_count or 0) * APPROX_CHARS_PER_TOKEN,
        )
        for uf in knowledge_files
    ]


def _get_workspace_search_availability(
    workspace_id: int | None,
    agent_id: int | None,
    loaded_workspace_files: bool,
    workspace_has_files: bool,
    forced_tool_id: int | None,
    search_tool_id: int | None,
    deep_research: bool = False,
) -> WorkspaceSearchConfig:
    """Determine search tool availability based on workspace context.

    Search is disabled when ALL of the following are true:
    - User is in a workspace
    - Using the default agent (not a custom agent)
    - Workspace files are already loaded in context

    When search is disabled and the user tried to force the search tool,
    that forcing is also disabled.

    Deep Research retrieves workspace documents via scoped search rather than
    loading them into context, so it always keeps the search tool available
    (regardless of whether the files would fit in context).

    Returns AUTO (follow agent config) in all other cases.
    """
    # Not in a workspace, this should have no impact on search tool availability
    if not workspace_id:
        return WorkspaceSearchConfig(
            search_usage=SearchToolUsage.AUTO, disable_forced_tool=False
        )

    # Deep Research relies on workspace-scoped retrieval instead of injecting the
    # workspace files into context, so keep the search tool enabled even when the
    # files would otherwise fit (which would normally disable it below).
    if deep_research:
        return WorkspaceSearchConfig(
            search_usage=SearchToolUsage.ENABLED, disable_forced_tool=False
        )

    # Custom agent in workspace - let agent config decide
    # Even if there are no files in the workspace, it's still guided by the agent config.
    if agent_id != DEFAULT_AGENT_ID:
        return WorkspaceSearchConfig(
            search_usage=SearchToolUsage.AUTO, disable_forced_tool=False
        )

    # If in a workspace with the default agent and the files have been already loaded into the context or
    # there are no files in the workspace, disable search as there is nothing to search for.
    if loaded_workspace_files or not workspace_has_files:
        user_forced_search = (
            forced_tool_id is not None
            and search_tool_id is not None
            and forced_tool_id == search_tool_id
        )
        return WorkspaceSearchConfig(
            search_usage=SearchToolUsage.DISABLED,
            disable_forced_tool=user_forced_search,
        )

    # Default agent in a workspace with files, but also the files have not been loaded into the context already.
    return WorkspaceSearchConfig(
        search_usage=SearchToolUsage.ENABLED, disable_forced_tool=False
    )


# Sentinel tool_id for workflow step ToolCall entries.
# ToolCall.tool_id is NOT a foreign key, so any integer works.
# session_loading.py checks for this value to reconstruct workflow packets.
WORKFLOW_STEP_TOOL_ID = 0


def _run_workflow_and_save(
    workflow: "AgentWorkflow",  # noqa: F821
    user_message: str,
    emitter: "Emitter",  # noqa: F821
    db_session: Session,
    user: User,
    is_connected: Callable[[], bool] | None,
    chat_session_id: UUID | None,
    assistant_message: ChatMessage,
    sandbox_session_id: str | None = None,
    chat_files: list[ChatFile] | None = None,
) -> AnswerStream:
    """Run a workflow and persist the assistant message + tool calls to DB.

    Wraps ``run_workflow()`` to intercept yielded packets, accumulate state
    (answer text, step outputs, orchestrator thinking), then call
    ``save_chat_turn()`` so the conversation survives page reloads.
    """
    from om.workflows.workflow_engine import run_workflow

    # Accumulators
    answer_parts: list[str] = []
    thinking_parts: list[str] = []

    # Per-step accumulators: list of dicts with step metadata + output
    step_records: list[dict] = []
    _cur_step: dict | None = None

    # Pause tracking
    pause_data: dict | None = None

    logger.info(
        "[Trace] workflow hand-off: chat_files=%d names=%s",
        len(chat_files or []),
        [f.filename for f in (chat_files or [])],
    )
    for packet in run_workflow(
        workflow=workflow,
        user_message=user_message,
        emitter=emitter,
        db_session=db_session,
        user=user,
        is_connected=is_connected,
        chat_session_id=chat_session_id,
        chat_files=chat_files,
        sandbox_session_id=sandbox_session_id,
        assistant_message_id=assistant_message.id,
    ):
        yield packet

        ptype = getattr(packet.obj, "type", None)

        # --- Main answer text (promoted output / pause questions) ---
        if ptype == StreamingType.MESSAGE_DELTA.value:
            answer_parts.append(getattr(packet.obj, "content", "") or "")

        # --- Orchestrator thinking ---
        elif ptype == StreamingType.WORKFLOW_ORCHESTRATOR_THINKING.value:
            thinking_parts.append(getattr(packet.obj, "content", "") or "")

        # --- Workflow step tracking ---
        elif ptype == StreamingType.WORKFLOW_STEP_START.value:
            _cur_step = {
                "step_name": getattr(packet.obj, "step_name", ""),
                "agent_name": getattr(packet.obj, "agent_name", ""),
                "step_order": getattr(packet.obj, "step_order", 0),
                "turn_index": packet.placement.turn_index,
                "content_parts": [],
            }
        elif ptype == StreamingType.WORKFLOW_STEP_DELTA.value:
            if _cur_step is not None:
                # Honor replace semantics (mirror the frontend fold): a
                # replace=True delta is the authoritative agent_output and
                # resets the accumulator, so live-streamed prose chunks are not
                # double-counted into the persisted step output.
                if getattr(packet.obj, "replace", False):
                    _cur_step["content_parts"] = [
                        getattr(packet.obj, "content", "") or ""
                    ]
                else:
                    _cur_step["content_parts"].append(
                        getattr(packet.obj, "content", "") or ""
                    )
        elif ptype == StreamingType.CUSTOM_TOOL_DELTA.value:
            # Track file_ids emitted by post-step file capture
            fids = getattr(packet.obj, "file_ids", None)
            if fids and _cur_step is not None:
                _cur_step.setdefault("file_ids", []).extend(fids)

        elif ptype == StreamingType.WORKFLOW_STEP_END.value:
            if _cur_step is not None:
                _cur_step["output"] = "".join(_cur_step.pop("content_parts", []))
                _cur_step["output_key"] = getattr(packet.obj, "output_key", "")
                step_records.append(_cur_step)
                _cur_step = None

        # --- Pause tracking ---
        elif ptype == StreamingType.WORKFLOW_PAUSE_FOR_INPUT.value:
            pause_data = {
                "step_name": getattr(packet.obj, "step_name", ""),
                "agent_name": getattr(packet.obj, "agent_name", ""),
                "questions": getattr(packet.obj, "questions", ""),
            }

    # Flush any unfinished step (e.g., step started but workflow paused before end)
    if _cur_step is not None:
        _cur_step["output"] = "".join(_cur_step.pop("content_parts", []))
        _cur_step["output_key"] = ""
        step_records.append(_cur_step)
        _cur_step = None

    # === Persist to DB ===
    from om.tools.models import ToolCallInfo

    final_answer = "".join(answer_parts)
    reasoning = "".join(thinking_parts) if thinking_parts else None

    # Build ToolCallInfo entries for each completed workflow step
    tool_calls: list[ToolCallInfo] = []
    for idx, rec in enumerate(step_records):
        tool_calls.append(
            ToolCallInfo(
                parent_tool_call_id=None,
                turn_index=rec["turn_index"],
                tab_index=0,
                tool_name=rec["step_name"],
                tool_call_id=f"wf_step_{idx}_{rec['step_name']}",
                tool_id=WORKFLOW_STEP_TOOL_ID,
                reasoning_tokens=None,
                tool_call_arguments={
                    "_workflow_step": True,
                    "step_name": rec["step_name"],
                    "agent_name": rec["agent_name"],
                    "step_order": rec["step_order"],
                    **({"_file_ids": rec["file_ids"]} if rec.get("file_ids") else {}),
                },
                tool_call_response=rec.get("output", ""),
            )
        )

    # If paused and no step records captured the pause (agent asked within its
    # first turn), record the pause as a step tool call so the timeline shows it
    if pause_data and not any(
        r["step_name"] == pause_data["step_name"] for r in step_records
    ):
        tool_calls.append(
            ToolCallInfo(
                parent_tool_call_id=None,
                turn_index=0,
                tab_index=0,
                tool_name=pause_data["step_name"],
                tool_call_id=f"wf_pause_{pause_data['step_name']}",
                tool_id=WORKFLOW_STEP_TOOL_ID,
                reasoning_tokens=None,
                tool_call_arguments={
                    "_workflow_step": True,
                    "_workflow_pause": True,
                    "step_name": pause_data["step_name"],
                    "agent_name": pause_data["agent_name"],
                },
                tool_call_response=pause_data["questions"],
            )
        )

    save_chat_turn(
        message_text=final_answer,
        reasoning_tokens=reasoning,
        tool_calls=tool_calls,
        citation_to_doc={},
        all_search_docs={},
        db_session=db_session,
        assistant_message=assistant_message,
    )


def stream_chat_message(
    new_msg_req: SendMessageRequest,
    user: User,
    db_session: Session,
    # if specified, uses the last user message and does not create a new user message based
    # on the `new_msg_req.message`. Currently, requires a state where the last message is a
    litellm_additional_headers: dict[str, str] | None = None,
    custom_tool_additional_headers: dict[str, str] | None = None,
    mcp_headers: dict[str, str] | None = None,
    bypass_acl: bool = False,
    # Additional context that should be included in the chat history, for example:
    # Slack threads where the conversation cannot be represented by a chain of User/Assistant
    # messages. Both of the below are used for Slack
    # NOTE: is not stored in the database, only passed in to the LLM as context
    additional_context: str | None = None,
    # Slack context for federated Slack search
    slack_context: SlackContext | None = None,
    # Optional external state container for non-streaming access to accumulated state
    external_state_container: ChatStateContainer | None = None,
) -> AnswerStream:
    tenant_id = get_current_tenant_id()
    mock_response_token: Token[str | None] | None = None

    llm: LLM | None = None
    chat_session: ChatSession | None = None
    redis_client: Redis | None = None

    user_id = user.id
    if user.is_anonymous:
        llm_user_identifier = "anonymous_user"
    else:
        llm_user_identifier = user.email or str(user_id)

    if new_msg_req.mock_llm_response is not None and not INTEGRATION_TESTS_MODE:
        raise ValueError(
            "mock_llm_response can only be used when INTEGRATION_TESTS_MODE=true"
        )

    try:
        if not new_msg_req.chat_session_id:
            if not new_msg_req.chat_session_info:
                raise RuntimeError(
                    "Must specify a chat session id or chat session info"
                )
            chat_session = create_chat_session_from_request(
                chat_session_request=new_msg_req.chat_session_info,
                user_id=user_id,
                db_session=db_session,
            )
            yield CreateChatSessionID(chat_session_id=chat_session.id)
        else:
            chat_session = get_chat_session_by_id(
                chat_session_id=new_msg_req.chat_session_id,
                user_id=user_id,
                db_session=db_session,
            )

        agent = chat_session.agent

        message_text = new_msg_req.message
        user_identity = LLMUserIdentity(
            user_id=llm_user_identifier, session_id=str(chat_session.id)
        )

        # Milestone tracking, most devs using the API don't need to understand this
        mt_cloud_telemetry(
            tenant_id=tenant_id,
            distinct_id=user.email if not user.is_anonymous else tenant_id,
            event=MilestoneRecordType.MULTIPLE_ASSISTANTS,
        )

        mt_cloud_telemetry(
            tenant_id=tenant_id,
            distinct_id=user.email if not user.is_anonymous else tenant_id,
            event=MilestoneRecordType.USER_MESSAGE_SENT,
            properties={
                "origin": new_msg_req.origin.value,
                "has_files": len(new_msg_req.file_descriptors) > 0,
                "has_workspace": chat_session.workspace_id is not None,
                "has_agent": agent is not None and agent.id != DEFAULT_AGENT_ID,
                "deep_research": new_msg_req.deep_research,
            },
        )

        llm = get_llm_for_agent(
            agent=agent,
            user=user,
            llm_override=new_msg_req.llm_override or chat_session.llm_override,
            additional_headers=litellm_additional_headers,
        )
        token_counter = get_llm_token_counter(llm)

        # Verify that the user specified files actually belong to the user
        verify_knowledge_files(
            knowledge_files=new_msg_req.file_descriptors,
            user_id=user_id,
            db_session=db_session,
            workspace_id=chat_session.workspace_id,
        )

        # re-create linear history of messages
        chat_history = create_chat_history_chain(
            chat_session_id=chat_session.id, db_session=db_session
        )

        # Determine the parent message based on the request:
        # - -1: auto-place after latest message in chain
        # - None: regeneration from root (first message)
        # - positive int: place after that specific parent message
        root_message = get_or_create_root_message(
            chat_session_id=chat_session.id, db_session=db_session
        )

        if new_msg_req.parent_message_id == AUTO_PLACE_AFTER_LATEST_MESSAGE:
            # Auto-place after the latest message in the chain
            parent_message = chat_history[-1] if chat_history else root_message
        elif (
            new_msg_req.parent_message_id is None
            or new_msg_req.parent_message_id == root_message.id
        ):
            # None = regeneration from root
            parent_message = root_message
            # Truncate history since we're starting from root
            chat_history = []
        else:
            # Specific parent message ID provided, find parent in chat_history
            parent_message = None
            for i in range(len(chat_history) - 1, -1, -1):
                if chat_history[i].id == new_msg_req.parent_message_id:
                    parent_message = chat_history[i]
                    # Truncate history to only include messages up to and including parent
                    chat_history = chat_history[: i + 1]
                    break

        if parent_message is None:
            raise ValueError(
                "The new message sent is not on the latest mainline of messages"
            )

        # If the parent message is a user message, it's a regeneration and we use the existing user message.
        if parent_message.message_type == MessageType.USER:
            user_message = parent_message
        else:
            user_message = create_new_chat_message(
                chat_session_id=chat_session.id,
                parent_message=parent_message,
                message=message_text,
                token_count=token_counter(message_text),
                message_type=MessageType.USER,
                files=new_msg_req.file_descriptors,
                db_session=db_session,
                commit=True,
            )

            chat_history.append(user_message)

        # Collect file IDs for the file reader tool *before* summary
        # truncation so that files attached to older (summarized-away)
        # messages are still accessible via the FileReaderTool.
        available_files = _collect_available_file_ids(
            chat_history=chat_history,
            workspace_id=chat_session.workspace_id,
            user_id=user_id,
            db_session=db_session,
        )

        # Find applicable summary for the current branch
        # Summary applies if its parent_message_id is in current chat_history
        summary_message = find_summary_for_branch(db_session, chat_history)
        # Collect file metadata from messages that will be dropped by
        # summary truncation.  These become "pre-summarized" file metadata
        # so the forgotten-file mechanism can still tell the LLM about them.
        summarized_file_metadata: dict[str, FileToolMetadata] = {}
        if summary_message and summary_message.last_summarized_message_id:
            cutoff_id = summary_message.last_summarized_message_id
            for msg in chat_history:
                if msg.id > cutoff_id or not msg.files:
                    continue
                for fd in msg.files:
                    file_id = fd.get("id")
                    if not file_id:
                        continue
                    summarized_file_metadata[file_id] = FileToolMetadata(
                        file_id=file_id,
                        filename=fd.get("name") or "unknown",
                        # We don't know the exact size without loading the
                        # file, but 0 signals "unknown" to the LLM.
                        approx_char_count=0,
                    )
            # Filter chat_history to only messages after the cutoff
            chat_history = [m for m in chat_history if m.id > cutoff_id]

        user_memory_context = get_memories(user, db_session)

        # This is the custom prompt which may come from the Agent or Workspace. We fetch it earlier because the inner loop
        # (run_llm_loop and run_deep_research_llm_loop) should not need to be aware of the Chat History in the DB form processed
        # here, however we need this early for token reservation.
        custom_agent_prompt = get_custom_agent_prompt(agent, chat_session)

        # When use_memories is disabled, strip memories from the prompt context
        # but keep user info/preferences. The full context is still passed
        # to the LLM loop for memory tool persistence.
        prompt_memory_context = (
            user_memory_context
            if user.use_memories
            else user_memory_context.without_memories()
        )

        max_reserved_system_prompt_tokens_str = (agent.system_prompt or "") + (
            custom_agent_prompt or ""
        )

        reserved_token_count = calculate_reserved_tokens(
            db_session=db_session,
            agent_system_prompt=max_reserved_system_prompt_tokens_str,
            token_counter=token_counter,
            files=new_msg_req.file_descriptors,
            user_memory_context=prompt_memory_context,
        )

        # Process workspaces, if all of the files fit in the context, it doesn't need to use RAG
        extracted_workspace_files = _extract_workspace_file_texts_and_images(
            workspace_id=chat_session.workspace_id,
            user_id=user_id,
            llm_max_context_window=llm.config.max_input_tokens,
            reserved_token_count=reserved_token_count,
            db_session=db_session,
        )

        # When the vector DB is disabled, agent-attached knowledge_files have no
        # search pipeline path. Inject them as file_metadata_for_tool so the
        # LLM can read them via the FileReaderTool.
        if DISABLE_VECTOR_DB and agent.knowledge_files:
            agent_file_metadata = _build_file_tool_metadata_for_knowledge_files(
                agent.knowledge_files
            )
            # Merge agent file metadata into the extracted workspace files
            extracted_workspace_files.file_metadata_for_tool.extend(agent_file_metadata)

        # Build a mapping of tool_id to tool_name for history reconstruction
        all_tools = get_tools(db_session)
        tool_id_to_name_map = {tool.id: tool.name for tool in all_tools}

        search_tool_id = next(
            (tool.id for tool in all_tools if tool.in_code_tool_id == SEARCH_TOOL_ID),
            None,
        )

        # Determine if search should be disabled for this workspace context
        forced_tool_id = new_msg_req.forced_tool_id
        workspace_search_config = _get_workspace_search_availability(
            workspace_id=chat_session.workspace_id,
            agent_id=agent.id,
            loaded_workspace_files=bool(extracted_workspace_files.workspace_file_texts),
            workspace_has_files=bool(
                extracted_workspace_files.workspace_uncapped_token_count
            ),
            forced_tool_id=new_msg_req.forced_tool_id,
            search_tool_id=search_tool_id,
            deep_research=bool(new_msg_req.deep_research),
        )
        if workspace_search_config.disable_forced_tool:
            forced_tool_id = None

        emitter = get_default_emitter()

        # Also grant access to agent-attached user files
        if agent.knowledge_files:
            existing = set(available_files.knowledge_file_ids)
            for uf in agent.knowledge_files:
                if uf.id not in existing:
                    available_files.knowledge_file_ids.append(uf.id)

        # Construct tools based on the agent configurations
        tool_dict = construct_tools(
            agent=agent,
            db_session=db_session,
            emitter=emitter,
            user=user,
            llm=llm,
            search_tool_config=SearchToolConfig(
                user_selected_filters=new_msg_req.internal_search_filters,
                # Deep Research always scopes retrieval to the workspace (it uses
                # search instead of loading files into context), so pass the
                # workspace_id even when the files would fit (workspace_as_filter False).
                workspace_id=(
                    chat_session.workspace_id
                    if (
                        extracted_workspace_files.workspace_as_filter
                        or (
                            new_msg_req.deep_research
                            and chat_session.workspace_id is not None
                        )
                    )
                    else None
                ),
                bypass_acl=bypass_acl,
                slack_context=slack_context,
                enable_slack_search=_should_enable_slack_search(
                    agent, new_msg_req.internal_search_filters
                ),
            ),
            custom_tool_config=CustomToolConfig(
                chat_session_id=chat_session.id,
                message_id=user_message.id if user_message else None,
                additional_headers=custom_tool_additional_headers,
                mcp_headers=mcp_headers,
            ),
            file_reader_tool_config=FileReaderToolConfig(
                knowledge_file_ids=available_files.knowledge_file_ids,
                chat_file_ids=available_files.chat_file_ids,
            ),
            allowed_tool_ids=new_msg_req.allowed_tool_ids,
            search_usage_forcing_setting=workspace_search_config.search_usage,
            chat_session_id=str(chat_session.id),
        )
        tools: list[Tool] = []
        for tool_list in tool_dict.values():
            tools.extend(tool_list)

        if forced_tool_id and forced_tool_id not in [tool.id for tool in tools]:
            raise ValueError(f"Forced tool {forced_tool_id} not found in tools")

        # TODO Once summarization is done, we don't need to load all the files from the beginning anymore.
        # load all files needed for this chat chain in memory
        files = load_all_chat_files(chat_history, db_session)

        # Convert loaded files to ChatFile format for tools like PythonTool
        chat_files_for_tools = _convert_loaded_files_to_chat_files(files)

        # TODO Need to think of some way to support selected docs from the sidebar

        # Reserve a message id for the assistant response for frontend to track packets
        assistant_response = reserve_message_id(
            db_session=db_session,
            chat_session_id=chat_session.id,
            parent_message=user_message.id,
            message_type=MessageType.ASSISTANT,
        )

        yield MessageResponseIDInfo(
            user_message_id=user_message.id,
            reserved_assistant_message_id=assistant_response.id,
        )

        # Check whether the FileReaderTool is among the constructed tools.
        has_file_reader_tool = any(isinstance(t, FileReaderTool) for t in tools)
        has_python_tool = any(isinstance(t, PythonTool) for t in tools)

        # Convert the chat history into a simple format that is free of any DB objects
        # and is easy to parse for the agent loop
        chat_history_result = convert_chat_history(
            chat_history=chat_history,
            files=files,
            workspace_image_files=extracted_workspace_files.workspace_image_files,
            additional_context=additional_context,
            token_counter=token_counter,
            tool_id_to_name_map=tool_id_to_name_map,
            has_python_tool=has_python_tool,
        )
        simple_chat_history = chat_history_result.simple_messages

        # Metadata for every text file injected into the history.  After
        # context-window truncation drops older messages, the LLM loop
        # compares surviving file_id tags against this map to discover
        # "forgotten" files and provide their metadata to FileReaderTool.
        all_injected_file_metadata: dict[str, FileToolMetadata] = (
            chat_history_result.all_injected_file_metadata
            if has_file_reader_tool
            else {}
        )

        # Merge in file metadata from messages dropped by summary
        # truncation.  These files are no longer in simple_chat_history
        # so they would otherwise be invisible to the forgotten-file
        # mechanism.  They will always appear as "forgotten" since no
        # surviving message carries their file_id tag.
        if summarized_file_metadata:
            for fid, meta in summarized_file_metadata.items():
                all_injected_file_metadata.setdefault(fid, meta)

        if all_injected_file_metadata:
            logger.debug(
                "FileReader: file metadata for LLM: "
                f"{[(fid, m.filename) for fid, m in all_injected_file_metadata.items()]}"
            )

        # Prepend summary message if compression exists
        if summary_message is not None:
            summary_simple = ChatMessageSimple(
                message=summary_message.message,
                token_count=summary_message.token_count,
                message_type=MessageType.ASSISTANT,
            )
            simple_chat_history.insert(0, summary_simple)

        redis_client = get_redis_client()

        reset_cancel_status(
            chat_session.id,
            redis_client,
        )

        def check_is_connected() -> bool:
            return check_stop_signal(chat_session.id, redis_client)

        set_processing_status(
            chat_session_id=chat_session.id,
            redis_client=redis_client,
            value=True,
        )

        # Use external state container if provided, otherwise create internal one
        # External container allows non-streaming callers to access accumulated state
        state_container = external_state_container or ChatStateContainer()

        def llm_loop_completion_callback(
            state_container: ChatStateContainer,
        ) -> None:
            llm_loop_completion_handle(
                state_container=state_container,
                is_connected=check_is_connected,
                db_session=db_session,
                assistant_message=assistant_response,
                llm=llm,
                reserved_tokens=reserved_token_count,
            )

        # The stream generator can resume on a different worker thread after early yields.
        # Set this right before launching the LLM loop so run_in_background copies the right context.
        if new_msg_req.mock_llm_response is not None:
            mock_response_token = set_llm_mock_response(new_msg_req.mock_llm_response)

        # Run the LLM loop with explicit wrapper for stop signal handling
        # The wrapper runs run_llm_loop in a background thread and polls every 300ms
        # for stop signals. run_llm_loop itself doesn't know about stopping.
        # Note: DB session is not thread safe but nothing else uses it and the
        # reference is passed directly so it's ok.

        # Multi-agent workflow routing — if the agent is a workflow wrapper,
        # route to the workflow engine instead of the standard LLM loop.
        if agent and agent.workflow_id:
            from om.db.workflow import get_workflow_by_id
            from om.workflows.workflow_engine import run_workflow

            workflow = get_workflow_by_id(
                db_session=db_session, workflow_id=agent.workflow_id
            )
            if workflow is None or not workflow.steps:
                raise ValueError(
                    f"Workflow {agent.workflow_id} not found or has no steps"
                )

            yield from _run_workflow_and_save(
                workflow=workflow,
                user_message=message_text,
                emitter=emitter,
                db_session=db_session,
                user=user,
                is_connected=check_is_connected,
                chat_session_id=chat_session.id,
                assistant_message=assistant_response,
                sandbox_session_id=chat_session.sandbox_session_id,
                chat_files=chat_files_for_tools,
            )

        elif new_msg_req.deep_research:
            # Skip clarification if the last assistant message was a clarification
            # (user has already responded to a clarification question)
            skip_clarification = is_last_assistant_message_clarification(chat_history)

            yield from run_chat_loop_with_state_containers(
                run_deep_research_llm_loop,
                llm_loop_completion_callback,
                is_connected=check_is_connected,
                emitter=emitter,
                state_container=state_container,
                simple_chat_history=simple_chat_history,
                tools=tools,
                custom_agent_prompt=custom_agent_prompt,
                llm=llm,
                token_counter=token_counter,
                db_session=db_session,
                skip_clarification=skip_clarification,
                user_identity=user_identity,
                chat_session_id=str(chat_session.id),
                all_injected_file_metadata=all_injected_file_metadata,
            )
        else:
            yield from run_chat_loop_with_state_containers(
                run_llm_loop,
                llm_loop_completion_callback,
                is_connected=check_is_connected,  # Not passed through to run_llm_loop
                emitter=emitter,
                state_container=state_container,
                simple_chat_history=simple_chat_history,
                tools=tools,
                custom_agent_prompt=custom_agent_prompt,
                workspace_files=extracted_workspace_files,
                agent=agent,
                user_memory_context=user_memory_context,
                llm=llm,
                token_counter=token_counter,
                db_session=db_session,
                forced_tool_id=forced_tool_id,
                user_identity=user_identity,
                chat_session_id=str(chat_session.id),
                sandbox_session_id=chat_session.sandbox_session_id,
                chat_files=chat_files_for_tools,
                include_citations=new_msg_req.include_citations,
                all_injected_file_metadata=all_injected_file_metadata,
                inject_memories_in_prompt=user.use_memories,
            )

    except ValueError as e:
        logger.exception("Failed to process chat message.")

        error_msg = str(e)
        yield StreamingError(
            error=error_msg,
            error_code="VALIDATION_ERROR",
            is_retryable=True,
        )
        db_session.rollback()
        return

    except Exception as e:
        logger.exception(f"Failed to process chat message due to {e}")
        error_msg = str(e)
        stack_trace = traceback.format_exc()

        if llm:
            client_error_msg, error_code, is_retryable = litellm_exception_to_error_msg(
                e, llm
            )
            if llm.config.api_key and len(llm.config.api_key) > 2:
                client_error_msg = client_error_msg.replace(
                    llm.config.api_key, "[REDACTED_API_KEY]"
                )
                stack_trace = stack_trace.replace(
                    llm.config.api_key, "[REDACTED_API_KEY]"
                )

            yield StreamingError(
                error=client_error_msg,
                stack_trace=stack_trace,
                error_code=error_code,
                is_retryable=is_retryable,
                details={
                    "model": llm.config.model_name,
                    "provider": llm.config.model_provider,
                },
            )
        else:
            # LLM was never initialized - early failure
            yield StreamingError(
                error="Failed to initialize the chat. Please check your configuration and try again.",
                stack_trace=stack_trace,
                error_code="INIT_FAILED",
                is_retryable=True,
            )

        db_session.rollback()
    finally:
        if mock_response_token is not None:
            reset_llm_mock_response(mock_response_token)

        try:
            if redis_client is not None and chat_session is not None:
                set_processing_status(
                    chat_session_id=chat_session.id,
                    redis_client=redis_client,
                    value=False,
                )
        except Exception:
            logger.exception("Error in setting processing status")


def llm_loop_completion_handle(
    state_container: ChatStateContainer,
    is_connected: Callable[[], bool],
    db_session: Session,
    assistant_message: ChatMessage,
    llm: LLM,
    reserved_tokens: int,
) -> None:
    chat_session_id = assistant_message.chat_session_id

    # Determine if stopped by user
    completed_normally = is_connected()
    # Build final answer based on completion status
    if completed_normally:
        if state_container.answer_tokens is None:
            raise RuntimeError(
                "LLM run completed normally but did not return an answer."
            )
        final_answer = state_container.answer_tokens
    else:
        # Stopped by user - append stop message
        logger.debug(f"Chat session {chat_session_id} stopped by user")
        if state_container.answer_tokens:
            final_answer = (
                state_container.answer_tokens
                + " ... \n\nGeneration was stopped by the user."
            )
        else:
            final_answer = "The generation was stopped by the user."

    save_chat_turn(
        message_text=final_answer,
        reasoning_tokens=state_container.reasoning_tokens,
        citation_to_doc=state_container.citation_to_doc,
        tool_calls=state_container.tool_calls,
        all_search_docs=state_container.get_all_search_docs(),
        db_session=db_session,
        assistant_message=assistant_message,
        is_clarification=state_container.is_clarification,
        emitted_citations=state_container.get_emitted_citations(),
        pre_answer_processing_time=state_container.get_pre_answer_processing_time(),
    )

    # Check if compression is needed after saving the message
    updated_chat_history = create_chat_history_chain(
        chat_session_id=chat_session_id,
        db_session=db_session,
    )
    total_tokens = calculate_total_history_tokens(updated_chat_history)

    compression_params = get_compression_params(
        max_input_tokens=llm.config.max_input_tokens,
        current_history_tokens=total_tokens,
        reserved_tokens=reserved_tokens,
    )
    if compression_params.should_compress:
        # Build tool mapping for formatting messages
        all_tools = get_tools(db_session)
        tool_id_to_name = {tool.id: tool.name for tool in all_tools}

        compress_chat_history(
            db_session=db_session,
            chat_history=updated_chat_history,
            llm=llm,
            compression_params=compression_params,
            tool_id_to_name=tool_id_to_name,
        )


def remove_answer_citations(answer: str) -> str:
    pattern = r"\s*\[\[\d+\]\]\(http[s]?://[^\s]+\)"

    return re.sub(pattern, "", answer)


@log_function_time()
def gather_stream(
    packets: AnswerStream,
) -> ChatBasicResponse:
    answer: str | None = None
    citations: list[CitationInfo] = []
    error_msg: str | None = None
    message_id: int | None = None
    top_documents: list[SearchDoc] = []

    for packet in packets:
        if isinstance(packet, Packet):
            # Handle the different packet object types
            if isinstance(packet.obj, AgentResponseStart):
                # AgentResponseStart contains the final documents
                if packet.obj.final_documents:
                    top_documents = packet.obj.final_documents
            elif isinstance(packet.obj, AgentResponseDelta):
                # AgentResponseDelta contains incremental content updates
                if answer is None:
                    answer = ""
                if packet.obj.content:
                    answer += packet.obj.content
            elif isinstance(packet.obj, CitationInfo):
                # CitationInfo contains citation information
                citations.append(packet.obj)
        elif isinstance(packet, StreamingError):
            error_msg = packet.error
        elif isinstance(packet, MessageResponseIDInfo):
            message_id = packet.reserved_assistant_message_id

    if message_id is None:
        raise ValueError("Message ID is required")

    if answer is None:
        # This should never be the case as these non-streamed flows do not have a stop-generation signal
        raise RuntimeError("Answer was not generated")

    return ChatBasicResponse(
        answer=answer,
        answer_citationless=remove_answer_citations(answer),
        citation_info=citations,
        message_id=message_id,
        error_msg=error_msg,
        top_documents=top_documents,
    )


@log_function_time()
def collect_stream_response(
    packets: AnswerStream,
    state_container: ChatStateContainer,
) -> ChatFullResponse:
    """
    Aggregate streaming packets and state container into a complete ChatFullResponse.

    This function consumes all packets from the stream and combines them with
    the accumulated state from the ChatStateContainer to build a complete response
    including answer, reasoning, citations, and tool calls.

    Args:
        packets: The stream of packets from stream_chat_message
        state_container: The state container that accumulates tool calls, reasoning, etc.

    Returns:
        ChatFullResponse with all available data
    """
    answer: str | None = None
    citations: list[CitationInfo] = []
    error_msg: str | None = None
    message_id: int | None = None
    top_documents: list[SearchDoc] = []
    chat_session_id: UUID | None = None

    for packet in packets:
        if isinstance(packet, Packet):
            if isinstance(packet.obj, AgentResponseStart):
                if packet.obj.final_documents:
                    top_documents = packet.obj.final_documents
            elif isinstance(packet.obj, AgentResponseDelta):
                if answer is None:
                    answer = ""
                if packet.obj.content:
                    answer += packet.obj.content
            elif isinstance(packet.obj, CitationInfo):
                citations.append(packet.obj)
        elif isinstance(packet, StreamingError):
            error_msg = packet.error
        elif isinstance(packet, MessageResponseIDInfo):
            message_id = packet.reserved_assistant_message_id
        elif isinstance(packet, CreateChatSessionID):
            chat_session_id = packet.chat_session_id

    if message_id is None:
        raise ValueError("Message ID is required")

    # Use state_container for complete answer (handles edge cases gracefully)
    final_answer = state_container.get_answer_tokens() or answer or ""

    # Get reasoning from state container (None when model doesn't produce reasoning)
    reasoning = state_container.get_reasoning_tokens()

    # Convert ToolCallInfo list to ToolCallResponse list
    tool_call_responses = [
        ToolCallResponse(
            tool_name=tc.tool_name,
            tool_arguments=tc.tool_call_arguments,
            tool_result=tc.tool_call_response,
            search_docs=tc.search_docs,
            generated_images=tc.generated_images,
            pre_reasoning=tc.reasoning_tokens,
        )
        for tc in state_container.get_tool_calls()
    ]

    return ChatFullResponse(
        answer=final_answer,
        answer_citationless=remove_answer_citations(final_answer),
        pre_answer_reasoning=reasoning,
        tool_calls=tool_call_responses,
        top_documents=top_documents,
        citation_info=citations,
        message_id=message_id,
        chat_session_id=chat_session_id,
        error_msg=error_msg,
    )
