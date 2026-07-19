import datetime
import json
import os
from collections.abc import Generator
from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import Request
from fastapi import Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from redis.client import Redis
from sqlalchemy.orm import Session

from om.auth.api_key import get_hashed_api_key_from_request
from om.auth.pat import get_hashed_pat_from_request
from om.auth.users import current_chat_accessible_user
from om.auth.users import current_user
from om.chat.chat_processing_checker import is_chat_session_processing
from om.chat.chat_state import ChatStateContainer
from om.chat.chat_utils import convert_chat_history_basic
from om.chat.chat_utils import create_chat_history_chain
from om.chat.chat_utils import create_chat_session_from_request
from om.chat.chat_utils import extract_headers
from om.chat.models import ChatFullResponse
from om.chat.models import CreateChatSessionID
from om.chat.message_handler import collect_stream_response
from om.chat.message_handler import stream_chat_message
from om.chat.prompt_utils import get_default_base_system_prompt
from om.chat.stop_signal_checker import set_fence
from om.configs.app_configs import WEB_DOMAIN
from om.configs.chat_configs import HARD_DELETE_CHATS
from om.configs.constants import MessageType
from om.configs.constants import MilestoneRecordType
from om.configs.constants import PUBLIC_API_TAGS
from om.configs.model_configs import LITELLM_PASS_THROUGH_HEADERS
from om.db.chat import add_chats_to_session_from_slack_thread
from om.db.chat import create_new_chat_message
from om.db.chat import delete_all_chat_sessions_for_user
from om.db.chat import delete_chat_session
from om.db.chat import duplicate_chat_session_for_user_from_slack
from om.db.chat import get_chat_message
from om.db.chat import get_chat_messages_by_session
from om.db.chat import get_chat_session_by_id
from om.db.chat import get_chat_sessions_by_user
from om.db.chat import set_as_latest_chat_message
from om.db.chat import translate_db_message_to_chat_message_detail
from om.db.chat import update_chat_session
from om.db.chat_search import search_chat_sessions
from om.db.engine.sql_engine import get_session
from om.db.engine.sql_engine import get_session_with_current_tenant
from om.db.feedback import create_chat_message_feedback
from om.db.feedback import remove_chat_message_feedback
from om.db.models import ChatSessionSharedStatus
from om.db.models import Agent
from om.db.models import User
from om.db.agent import get_agent_by_id
from om.db.usage import increment_usage
from om.db.usage import UsageType
from om.db.knowledge_file import get_file_id_by_knowledge_file_id
from om.file_processing.extract_file_text import docx_to_txt_filename
from om.file_store.file_store import get_default_file_store
from om.llm.constants import LlmProviderNames
from om.llm.factory import get_default_llm
from om.llm.factory import get_llm_for_agent
from om.llm.factory import get_llm_token_counter
from om.redis.redis_pool import get_redis_client
from om.secondary_llm_flows.chat_session_naming import generate_chat_session_name
from om.server.api_key_usage import check_api_key_usage
from om.server.query_and_chat.models import ChatFeedbackRequest
from om.server.query_and_chat.models import ChatMessageIdentifier
from om.server.query_and_chat.models import ChatRenameRequest
from om.server.query_and_chat.models import ChatSearchResponse
from om.server.query_and_chat.models import ChatSessionCreationRequest
from om.server.query_and_chat.models import ChatSessionDetailResponse
from om.server.query_and_chat.models import ChatSessionDetails
from om.server.query_and_chat.models import ChatSessionGroup
from om.server.query_and_chat.models import ChatSessionsResponse
from om.server.query_and_chat.models import ChatSessionSummary
from om.server.query_and_chat.models import ChatSessionUpdateRequest
from om.server.query_and_chat.models import MessageOrigin
from om.server.query_and_chat.models import RenameChatSessionResponse
from om.server.query_and_chat.models import ExecuteCodeRequest
from om.server.query_and_chat.models import ExecuteCodeResponse
from om.server.query_and_chat.models import SendMessageRequest
from om.server.query_and_chat.models import UpdateChatSessionTemperatureRequest
from om.server.query_and_chat.models import UpdateChatSessionThreadRequest
from om.server.query_and_chat.session_loading import (
    translate_assistant_message_to_packets,
)
from om.server.query_and_chat.streaming_models import Packet
from om.server.rate_limits.dependencies import enforce_rate_limits
from om.server.usage_limits import check_llm_cost_limit_for_provider
from om.server.usage_limits import check_usage_and_raise
from om.server.usage_limits import is_usage_limits_enabled
from om.server.utils import get_json_line
from om.tracing.framework.create import ensure_trace
from om.utils.headers import get_custom_tool_additional_request_headers
from om.utils.logger import setup_logger
from om.utils.telemetry import mt_cloud_telemetry
from shared_configs.contextvars import get_current_tenant_id

logger = setup_logger()

router = APIRouter(prefix="/converse")


def _get_available_tokens_for_agent(
    agent: Agent,
    db_session: Session,
    user: User,
) -> int:
    def _get_non_reserved_input_tokens(
        model_max_input_tokens: int,
        system_and_agent_prompt_tokens: int,
        num_tools: int,
        token_reserved_per_tool: int = 256,
        # Estimating for a long user input message, hard to know ahead of time
        default_reserved_tokens: int = 2000,
    ) -> int:
        return (
            model_max_input_tokens
            - system_and_agent_prompt_tokens
            - num_tools * token_reserved_per_tool
            - default_reserved_tokens
        )

    llm = get_llm_for_agent(agent=agent, user=user)
    token_counter = get_llm_token_counter(llm)

    if agent.replace_base_system_prompt and agent.system_prompt:
        # User has opted to replace the base system prompt entirely
        combined_prompt_tokens = token_counter(agent.system_prompt)
    else:
        # Default behavior: prepend custom prompt to base system prompt
        system_prompt = get_default_base_system_prompt(db_session)
        agent_prompt = agent.system_prompt + " " if agent.system_prompt else ""
        combined_prompt_tokens = token_counter(agent_prompt + system_prompt)

    return _get_non_reserved_input_tokens(
        model_max_input_tokens=llm.config.max_input_tokens,
        system_and_agent_prompt_tokens=combined_prompt_tokens,
        num_tools=len(agent.tools),
    )


@router.get("/get-user-chat-sessions", tags=PUBLIC_API_TAGS)
def get_user_chat_sessions(
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
    workspace_id: int | None = None,
    only_non_workspace_chats: bool = True,
    include_failed_chats: bool = False,
) -> ChatSessionsResponse:
    user_id = user.id

    try:
        chat_sessions = get_chat_sessions_by_user(
            user_id=user_id,
            deleted=False,
            db_session=db_session,
            workspace_id=workspace_id,
            only_non_workspace_chats=only_non_workspace_chats,
            include_failed_chats=include_failed_chats,
        )

    except ValueError:
        raise ValueError("Chat session does not exist or has been deleted")

    return ChatSessionsResponse(
        sessions=[
            ChatSessionDetails(
                id=chat.id,
                name=chat.description,
                agent_id=chat.agent_id,
                time_created=chat.time_created.isoformat(),
                time_updated=chat.time_updated.isoformat(),
                shared_status=chat.shared_status,
                current_alternate_model=chat.current_alternate_model,
                current_temperature_override=chat.temperature_override,
            )
            for chat in chat_sessions
        ]
    )


@router.put("/update-chat-session-temperature")
def update_chat_session_temperature(
    update_thread_req: UpdateChatSessionTemperatureRequest,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> None:
    chat_session = get_chat_session_by_id(
        chat_session_id=update_thread_req.chat_session_id,
        user_id=user.id,
        db_session=db_session,
    )

    # Validate temperature_override
    if update_thread_req.temperature_override is not None:
        if (
            update_thread_req.temperature_override < 0
            or update_thread_req.temperature_override > 2
        ):
            raise HTTPException(
                status_code=400, detail="Temperature must be between 0 and 2"
            )

        # Additional check for Anthropic models
        if (
            chat_session.current_alternate_model
            and LlmProviderNames.ANTHROPIC
            in chat_session.current_alternate_model.lower()
        ):
            if update_thread_req.temperature_override > 1:
                raise HTTPException(
                    status_code=400,
                    detail="Temperature for Anthropic models must be between 0 and 1",
                )

    chat_session.temperature_override = update_thread_req.temperature_override

    db_session.add(chat_session)
    db_session.commit()


@router.put("/update-chat-session-model")
def update_chat_session_model(
    update_thread_req: UpdateChatSessionThreadRequest,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> None:
    chat_session = get_chat_session_by_id(
        chat_session_id=update_thread_req.chat_session_id,
        user_id=user.id,
        db_session=db_session,
    )
    chat_session.current_alternate_model = update_thread_req.new_alternate_model

    db_session.add(chat_session)
    db_session.commit()


@router.get("/get-chat-session/{session_id}", tags=PUBLIC_API_TAGS)
def get_chat_session(
    session_id: UUID,
    is_shared: bool = False,
    include_deleted: bool = False,
    user: User = Depends(current_chat_accessible_user),
    db_session: Session = Depends(get_session),
) -> ChatSessionDetailResponse:
    user_id = user.id
    try:
        chat_session = get_chat_session_by_id(
            chat_session_id=session_id,
            user_id=user_id,
            db_session=db_session,
            is_shared=is_shared,
            include_deleted=include_deleted,
        )
    except ValueError:
        try:
            # If we failed to get a chat session, try to retrieve the session with
            # less restrictive filters in order to identify what exactly mismatched
            # so we can bubble up an accurate error code andmessage.
            existing_chat_session = get_chat_session_by_id(
                chat_session_id=session_id,
                user_id=None,
                db_session=db_session,
                is_shared=False,
                include_deleted=True,
            )
        except ValueError:
            raise HTTPException(status_code=404, detail="Chat session not found")

        if not include_deleted and existing_chat_session.deleted:
            raise HTTPException(status_code=404, detail="Chat session has been deleted")

        if is_shared:
            if existing_chat_session.shared_status != ChatSessionSharedStatus.PUBLIC:
                raise HTTPException(
                    status_code=403, detail="Chat session is not shared"
                )
        elif user_id is not None and existing_chat_session.user_id not in (
            user_id,
            None,
        ):
            raise HTTPException(status_code=403, detail="Access denied")

        raise HTTPException(status_code=404, detail="Chat session not found")

    # for chat-seeding: if the session is unassigned, assign it now. This is done here
    # to avoid another back and forth between FE -> BE before starting the first
    # message generation
    if chat_session.user_id is None and user_id is not None:
        chat_session.user_id = user_id
        db_session.commit()

    session_messages = get_chat_messages_by_session(
        chat_session_id=session_id,
        user_id=user_id,
        db_session=db_session,
        # we already did a permission check above with the call to
        # `get_chat_session_by_id`, so we can skip it here
        skip_permission_check=True,
        # we need the tool call objs anyways, so just fetch them in a single call
        prefetch_top_two_level_tool_calls=True,
    )

    # Convert messages to ChatMessageDetail format
    chat_message_details = [
        translate_db_message_to_chat_message_detail(msg) for msg in session_messages
    ]

    try:
        is_processing = is_chat_session_processing(session_id, get_redis_client())
        # Edit the last message to indicate loading (Overriding default message value)
        if is_processing and chat_message_details:
            last_msg = chat_message_details[-1]
            if last_msg.message_type == MessageType.ASSISTANT:
                last_msg.message = "Message is loading... Please refresh the page soon."
    except Exception:
        logger.exception(
            "An error occurred while checking if the chat session is processing"
        )

    # Every assistant message might have a set of tool calls associated with it, these need to be replayed back for the frontend
    # Each list is the set of tool calls for the given assistant message.
    replay_packet_lists: list[list[Packet]] = []
    for msg in session_messages:
        if msg.message_type == MessageType.ASSISTANT:
            replay_packet_lists.append(
                translate_assistant_message_to_packets(
                    chat_message=msg, db_session=db_session
                )
            )
            # msg_packet_list.append(Packet(ind=end_step_nr, obj=OverallStop()))

    return ChatSessionDetailResponse(
        chat_session_id=session_id,
        description=chat_session.description,
        agent_id=chat_session.agent_id,
        agent_name=chat_session.agent.name if chat_session.agent else None,
        personal_icon_name=chat_session.agent.icon_name,
        current_alternate_model=chat_session.current_alternate_model,
        messages=chat_message_details,
        time_created=chat_session.time_created,
        shared_status=chat_session.shared_status,
        current_temperature_override=chat_session.temperature_override,
        deleted=chat_session.deleted,
        owner_name=chat_session.user.personal_name if chat_session.user else None,
        # Packets are now directly serialized as Packet Pydantic models
        packets=replay_packet_lists,
    )


@router.post("/create-chat-session", tags=PUBLIC_API_TAGS)
def create_new_chat_session(
    chat_session_creation_request: ChatSessionCreationRequest,
    user: User = Depends(current_chat_accessible_user),
    db_session: Session = Depends(get_session),
) -> CreateChatSessionID:
    user_id = user.id

    try:
        new_chat_session = create_chat_session_from_request(
            chat_session_request=chat_session_creation_request,
            user_id=user_id,
            db_session=db_session,
        )
    except ValueError as e:
        # Workspace access denied
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.exception(e)
        raise HTTPException(status_code=400, detail="Invalid Agent provided.")

    return CreateChatSessionID(chat_session_id=new_chat_session.id)


@router.put("/rename-chat-session")
def rename_chat_session(
    rename_req: ChatRenameRequest,
    request: Request,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> RenameChatSessionResponse:
    # 3000 tokens is more than enough for a pair of messages which is enough to provide the required context for generating a
    # good name for the chat session. It's also small enough to fit on even the worst context window LLMs.
    max_tokens_for_naming = 3000

    name = rename_req.name
    chat_session_id = rename_req.chat_session_id
    user_id = user.id

    if name:
        update_chat_session(
            db_session=db_session,
            user_id=user_id,
            chat_session_id=chat_session_id,
            description=name,
        )
        return RenameChatSessionResponse(new_name=name)

    llm = get_default_llm(
        additional_headers=extract_headers(
            request.headers, LITELLM_PASS_THROUGH_HEADERS
        )
    )

    check_llm_cost_limit_for_provider(
        db_session=db_session,
        tenant_id=get_current_tenant_id(),
        llm_provider_api_key=llm.config.api_key,
    )

    full_history = create_chat_history_chain(
        chat_session_id=chat_session_id, db_session=db_session
    )

    token_counter = get_llm_token_counter(llm)

    simple_chat_history = convert_chat_history_basic(
        chat_history=full_history,
        token_counter=token_counter,
        max_individual_message_tokens=max_tokens_for_naming,
        max_total_tokens=max_tokens_for_naming,
    )

    with ensure_trace(
        "chat_session_naming",
        group_id=str(chat_session_id),
        metadata={
            "tenant_id": get_current_tenant_id(),
            "chat_session_id": str(chat_session_id),
        },
    ):
        new_name = generate_chat_session_name(chat_history=simple_chat_history, llm=llm)

    update_chat_session(
        db_session=db_session,
        user_id=user_id,
        chat_session_id=chat_session_id,
        description=new_name,
    )

    return RenameChatSessionResponse(new_name=new_name)


@router.patch("/chat-session/{session_id}")
def patch_chat_session(
    session_id: UUID,
    chat_session_update_req: ChatSessionUpdateRequest,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> None:
    user_id = user.id
    update_chat_session(
        db_session=db_session,
        user_id=user_id,
        chat_session_id=session_id,
        sharing_status=chat_session_update_req.sharing_status,
    )
    return None


@router.delete("/delete-all-chat-sessions", tags=PUBLIC_API_TAGS)
def delete_all_chat_sessions(
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> None:
    try:
        delete_all_chat_sessions_for_user(user=user, db_session=db_session)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/delete-chat-session/{session_id}", tags=PUBLIC_API_TAGS)
def delete_chat_session_by_id(
    session_id: UUID,
    hard_delete: bool | None = None,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> None:
    user_id = user.id
    try:
        # Use the provided hard_delete parameter if specified, otherwise use the default config
        actual_hard_delete = (
            hard_delete if hard_delete is not None else HARD_DELETE_CHATS
        )
        delete_chat_session(
            user_id, session_id, db_session, hard_delete=actual_hard_delete
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# NOTE: This endpoint is extremely central to the application, any changes to it should be reviewed and approved by an experienced
# team member. It is very important to 1. avoid bloat and 2. that this remains backwards compatible across versions.
@router.post(
    "/send-chat-message",
    response_model=ChatFullResponse,
    tags=PUBLIC_API_TAGS,
    responses={
        200: {
            "description": (
                "If `stream=true`, returns `text/event-stream`.\n"
                "If `stream=false`, returns `application/json` (ChatFullResponse)."
            ),
            "content": {
                "text/event-stream": {
                    "schema": {"type": "string"},
                    "examples": {
                        "stream": {
                            "summary": "Stream of NDJSON AnswerStreamPart's",
                            "value": "string",
                        }
                    },
                },
            },
        }
    },
)
def handle_send_chat_message(
    chat_message_req: SendMessageRequest,
    request: Request,
    user: User = Depends(current_chat_accessible_user),
    _rate_limit_check: None = Depends(enforce_rate_limits),
    _api_key_usage_check: None = Depends(check_api_key_usage),
) -> StreamingResponse | ChatFullResponse:
    """
    This endpoint is used to send a new chat message.

    Args:
        chat_message_req (SendMessageRequest): Details about the new chat message.
            - When stream=True (default): Returns StreamingResponse with SSE
            - When stream=False: Returns ChatFullResponse with complete data
        request (Request): The current HTTP request context.
        user (User): The current user, obtained via dependency injection.
        _ (None): Rate limit check is run if user/group/global rate limits are enabled.

    Returns:
        StreamingResponse | ChatFullResponse: Either streams or returns complete response.
    """
    logger.debug(f"Received new chat message: {chat_message_req.message}")

    tenant_id = get_current_tenant_id()
    mt_cloud_telemetry(
        tenant_id=tenant_id,
        distinct_id=tenant_id if user.is_anonymous else user.email,
        event=MilestoneRecordType.RAN_QUERY,
    )

    # Override origin to API when authenticated via API key or PAT
    # to prevent clients from polluting telemetry data
    if get_hashed_api_key_from_request(request) or get_hashed_pat_from_request(request):
        chat_message_req.origin = MessageOrigin.API

    # Non-streaming path: consume all packets and return complete response
    if not chat_message_req.stream:
        with get_session_with_current_tenant() as db_session:
            # Check and track non-streaming API usage limits
            if is_usage_limits_enabled():
                check_usage_and_raise(
                    db_session=db_session,
                    usage_type=UsageType.NON_STREAMING_API_CALLS,
                    tenant_id=tenant_id,
                    pending_amount=1,
                )
                increment_usage(
                    db_session=db_session,
                    usage_type=UsageType.NON_STREAMING_API_CALLS,
                    amount=1,
                )
                db_session.commit()

            state_container = ChatStateContainer()
            packets = stream_chat_message(
                new_msg_req=chat_message_req,
                user=user,
                db_session=db_session,
                litellm_additional_headers=extract_headers(
                    request.headers, LITELLM_PASS_THROUGH_HEADERS
                ),
                custom_tool_additional_headers=get_custom_tool_additional_request_headers(
                    request.headers
                ),
                mcp_headers=chat_message_req.mcp_headers,
                external_state_container=state_container,
            )
            result = collect_stream_response(packets, state_container)
            # Note: LLM cost tracking is now handled in multi_llm.py
            return result

    # Streaming path, normal Onyx UI behavior
    def stream_generator() -> Generator[str, None, None]:
        state_container = ChatStateContainer()
        try:
            with get_session_with_current_tenant() as db_session:
                for obj in stream_chat_message(
                    new_msg_req=chat_message_req,
                    user=user,
                    db_session=db_session,
                    litellm_additional_headers=extract_headers(
                        request.headers, LITELLM_PASS_THROUGH_HEADERS
                    ),
                    custom_tool_additional_headers=get_custom_tool_additional_request_headers(
                        request.headers
                    ),
                    mcp_headers=chat_message_req.mcp_headers,
                    external_state_container=state_container,
                ):
                    yield get_json_line(obj.model_dump())
                # Note: LLM cost tracking is now handled in multi_llm.py

        except Exception as e:
            logger.exception("Error in chat message streaming")
            yield json.dumps({"error": str(e)})

        finally:
            logger.debug("Stream generator finished")

    return StreamingResponse(stream_generator(), media_type="text/event-stream")


@router.put("/set-message-as-latest")
def set_message_as_latest(
    message_identifier: ChatMessageIdentifier,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> None:
    user_id = user.id

    chat_message = get_chat_message(
        chat_message_id=message_identifier.message_id,
        user_id=user_id,
        db_session=db_session,
    )

    set_as_latest_chat_message(
        chat_message=chat_message,
        user_id=user_id,
        db_session=db_session,
    )


@router.post("/create-chat-message-feedback")
def create_chat_feedback(
    feedback: ChatFeedbackRequest,
    user: User = Depends(current_chat_accessible_user),
    db_session: Session = Depends(get_session),
) -> None:
    user_id = user.id

    create_chat_message_feedback(
        is_positive=feedback.is_positive,
        feedback_text=feedback.feedback_text,
        predefined_feedback=feedback.predefined_feedback,
        chat_message_id=feedback.chat_message_id,
        user_id=user_id,
        db_session=db_session,
    )


@router.delete("/remove-chat-message-feedback")
def remove_chat_feedback(
    chat_message_id: int,
    user: User = Depends(current_chat_accessible_user),
    db_session: Session = Depends(get_session),
) -> None:
    user_id = user.id

    remove_chat_message_feedback(
        chat_message_id=chat_message_id,
        user_id=user_id,
        db_session=db_session,
    )


class MaxSelectedDocumentTokens(BaseModel):
    max_tokens: int


@router.get("/max-selected-document-tokens")
def get_max_document_tokens(
    agent_id: int,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> MaxSelectedDocumentTokens:
    try:
        agent = get_agent_by_id(
            agent_id=agent_id,
            user=user,
            db_session=db_session,
            is_for_edit=False,
        )
    except ValueError:
        raise HTTPException(status_code=404, detail="Agent not found")

    return MaxSelectedDocumentTokens(
        max_tokens=_get_available_tokens_for_agent(
            agent=agent,
            user=user,
            db_session=db_session,
        ),
    )


class AvailableContextTokensResponse(BaseModel):
    available_tokens: int


@router.get("/available-context-tokens/{session_id}")
def get_available_context_tokens_for_session(
    session_id: UUID,
    user: User = Depends(current_chat_accessible_user),
    db_session: Session = Depends(get_session),
) -> AvailableContextTokensResponse:
    """Return available context tokens for a chat session based on its agent."""

    try:
        chat_session = get_chat_session_by_id(
            chat_session_id=session_id,
            user_id=user.id,
            db_session=db_session,
            is_shared=False,
            include_deleted=False,
        )
    except ValueError:
        raise HTTPException(status_code=404, detail="Chat session not found")

    if not chat_session.agent:
        raise HTTPException(status_code=400, detail="Chat session has no agent")

    available = _get_available_tokens_for_agent(
        agent=chat_session.agent,
        user=user,
        db_session=db_session,
    )

    return AvailableContextTokensResponse(available_tokens=available)


"""Endpoints for chat seeding"""


class SeedChatFromSlackRequest(BaseModel):
    chat_session_id: UUID


class SeedChatFromSlackResponse(BaseModel):
    redirect_url: str


@router.post("/seed-chat-session-from-slack")
def seed_chat_from_slack(
    chat_seed_request: SeedChatFromSlackRequest,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> SeedChatFromSlackResponse:
    slack_chat_session_id = chat_seed_request.chat_session_id
    new_chat_session = duplicate_chat_session_for_user_from_slack(
        db_session=db_session,
        user=user,
        chat_session_id=slack_chat_session_id,
    )

    add_chats_to_session_from_slack_thread(
        db_session=db_session,
        slack_chat_session_id=slack_chat_session_id,
        new_chat_session_id=new_chat_session.id,
    )

    return SeedChatFromSlackResponse(
        redirect_url=f"{WEB_DOMAIN}/chat?chatId={new_chat_session.id}"
    )


@router.get("/file/{file_id:path}", tags=PUBLIC_API_TAGS)
def fetch_chat_file(
    file_id: str,
    request: Request,
    _: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> Response:

    # For user files, we need to get the file id from the user file id
    file_id_from_user_file = get_file_id_by_knowledge_file_id(file_id, db_session)
    if file_id_from_user_file:
        file_id = file_id_from_user_file

    file_store = get_default_file_store()
    file_record = file_store.read_file_record(file_id)
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")

    original_file_name = file_record.display_name
    if file_record.file_type.startswith(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ):
        # Check if a converted text file exists for .docx files
        txt_file_name = docx_to_txt_filename(original_file_name)
        txt_file_id = os.path.join(os.path.dirname(file_id), txt_file_name)
        try:
            txt_file_record = file_store.read_file_record(txt_file_id)
        except RuntimeError:
            txt_file_record = None
        if txt_file_record:
            file_record = txt_file_record
            file_id = txt_file_id

    media_type = file_record.file_type
    file_io = file_store.read_file(file_id, mode="b")

    # Files served here are immutable (content-addressed by file_id), so allow long-lived caching.
    # Use `private` because this is behind auth / tenant scoping.
    etag = f'"{file_id}"'
    cache_headers = {
        "Cache-Control": "private, max-age=31536000, immutable",
        "ETag": etag,
        "Vary": "Cookie",
    }

    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers=cache_headers)

    return StreamingResponse(file_io, media_type=media_type, headers=cache_headers)


@router.get("/search", tags=PUBLIC_API_TAGS)
async def search_chats(
    query: str | None = Query(None),
    page: int = Query(1),
    page_size: int = Query(10),
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> ChatSearchResponse:
    """
    Search for chat sessions based on the provided query.
    If no query is provided, returns recent chat sessions.
    """

    # Use the enhanced database function for chat search
    chat_sessions, has_more = search_chat_sessions(
        user_id=user.id,
        db_session=db_session,
        query=query,
        page=page,
        page_size=page_size,
        include_deleted=False,
        include_onyxbot_flows=False,
    )

    # Group chat sessions by time period
    today = datetime.datetime.now().date()
    yesterday = today - timedelta(days=1)
    this_week = today - timedelta(days=7)
    this_month = today - timedelta(days=30)

    today_chats: list[ChatSessionSummary] = []
    yesterday_chats: list[ChatSessionSummary] = []
    this_week_chats: list[ChatSessionSummary] = []
    this_month_chats: list[ChatSessionSummary] = []
    older_chats: list[ChatSessionSummary] = []

    for session in chat_sessions:
        session_date = session.time_created.date()

        chat_summary = ChatSessionSummary(
            id=session.id,
            name=session.description,
            agent_id=session.agent_id,
            time_created=session.time_created,
            shared_status=session.shared_status,
            current_alternate_model=session.current_alternate_model,
            current_temperature_override=session.temperature_override,
        )

        if session_date == today:
            today_chats.append(chat_summary)
        elif session_date == yesterday:
            yesterday_chats.append(chat_summary)
        elif session_date > this_week:
            this_week_chats.append(chat_summary)
        elif session_date > this_month:
            this_month_chats.append(chat_summary)
        else:
            older_chats.append(chat_summary)

    # Create groups
    groups = []
    if today_chats:
        groups.append(ChatSessionGroup(title="Today", chats=today_chats))
    if yesterday_chats:
        groups.append(ChatSessionGroup(title="Yesterday", chats=yesterday_chats))
    if this_week_chats:
        groups.append(ChatSessionGroup(title="This Week", chats=this_week_chats))
    if this_month_chats:
        groups.append(ChatSessionGroup(title="This Month", chats=this_month_chats))
    if older_chats:
        groups.append(ChatSessionGroup(title="Older", chats=older_chats))

    return ChatSearchResponse(
        groups=groups,
        has_more=has_more,
        next_page=page + 1 if has_more else None,
    )


@router.post("/stop-chat-session/{chat_session_id}", tags=PUBLIC_API_TAGS)
def stop_chat_session(
    chat_session_id: UUID,
    user: User = Depends(current_user),  # noqa: ARG001
    redis_client: Redis = Depends(get_redis_client),
) -> dict[str, str]:
    """
    Stop a chat session by setting a stop signal in Redis.
    This endpoint is called by the frontend when the user clicks the stop button.
    """
    set_fence(chat_session_id, redis_client, True)
    return {"message": "Chat session stopped"}


@router.post("/execute-code")
def execute_code_in_chat(
    request: ExecuteCodeRequest,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> ExecuteCodeResponse:
    """Execute code from a chat code block and save result as a sibling message.

    This powers the "Run" button on code blocks in the chat UI.
    The execution result is saved as a new ChatMessage that is a sibling of
    the original assistant response (same parent_message_id), enabling
    1/2 ↔ 2/2 navigation in the message switcher.
    """
    import mimetypes
    from io import BytesIO

    from om.configs.app_configs import CODE_INTERPRETER_BASE_URL
    from om.configs.constants import FileOrigin
    from om.file_store.models import ChatFileType
    from om.file_store.models import FileDescriptor
    from om.tools.tool_implementations.python.code_interpreter_client import (
        CodeInterpreterClient,
    )

    # 1. Validate chat session ownership
    chat_session = get_chat_session_by_id(
        chat_session_id=request.chat_session_id,
        user_id=user.id,
        db_session=db_session,
        is_shared=False,
        include_deleted=False,
    )

    # 2. Validate parent message exists and belongs to user
    parent_message = get_chat_message(
        chat_message_id=request.parent_message_id,
        user_id=user.id,
        db_session=db_session,
    )

    # 3. Initialize code interpreter client
    if not CODE_INTERPRETER_BASE_URL:
        raise HTTPException(
            status_code=400,
            detail="Code interpreter is not configured",
        )

    client = CodeInterpreterClient(base_url=CODE_INTERPRETER_BASE_URL)

    # Reuse existing sandbox session or create new one
    session_id = chat_session.sandbox_session_id
    if not session_id:
        try:
            session_id = client.create_session()
            chat_session.sandbox_session_id = session_id
            db_session.commit()
        except Exception as e:
            logger.error(f"Failed to create sandbox session: {e}")
            raise HTTPException(
                status_code=503,
                detail="Code interpreter service unavailable",
            )

    # 4. Execute code
    try:
        response = client.execute(
            code=request.code,
            timeout_ms=60000,
            session_id=session_id,
        )
    except Exception as first_err:
        # Retry with fresh session on retriable errors
        logger.warning(f"Code execution failed: {first_err}. Retrying with fresh session...")
        try:
            session_id = client.create_session()
            chat_session.sandbox_session_id = session_id
            db_session.commit()
            response = client.execute(
                code=request.code,
                timeout_ms=60000,
                session_id=session_id,
            )
        except Exception as retry_err:
            logger.error(f"Code execution retry failed: {retry_err}")
            raise HTTPException(
                status_code=503,
                detail="Code execution failed. The interpreter may be unavailable.",
            )

    # 5. Process generated files (plots, images, etc.)
    file_store = get_default_file_store()
    file_descriptors: list[FileDescriptor] = []

    for workspace_file in response.files:
        if workspace_file.kind != "file" or not workspace_file.file_id:
            continue
        try:
            file_content = client.download_file(workspace_file.file_id)
            filename = workspace_file.path.split("/")[-1]
            mime_type, _ = mimetypes.guess_type(filename)
            mime_type = mime_type or "application/octet-stream"

            onyx_file_id = file_store.save_file(
                content=BytesIO(file_content),
                display_name=filename,
                file_origin=FileOrigin.CHAT_UPLOAD,
                file_type=mime_type,
            )

            # Determine ChatFileType based on mime
            if mime_type.startswith("image/"):
                chat_file_type = ChatFileType.IMAGE
            else:
                chat_file_type = ChatFileType.DOC

            file_descriptors.append(
                FileDescriptor(
                    id=onyx_file_id,
                    type=chat_file_type,
                    name=filename,
                )
            )
        except Exception as e:
            logger.error(f"Failed to process file {workspace_file.path}: {e}")

    # 6. Build message content with execution results
    message_parts = []
    message_parts.append("**Code Execution Result**\n")
    message_parts.append(f"```\n{request.code}\n```\n")

    if response.stdout.strip():
        message_parts.append(f"**Output:**\n```\n{response.stdout.strip()}\n```\n")

    if response.stderr.strip():
        message_parts.append(f"**Errors:**\n```\n{response.stderr.strip()}\n```\n")

    if response.exit_code is not None and response.exit_code != 0:
        message_parts.append(f"Exit code: {response.exit_code}\n")

    if response.timed_out:
        message_parts.append("**Warning:** Execution timed out.\n")

    if file_descriptors:
        message_parts.append(
            f"**Generated {len(file_descriptors)} file(s)**\n"
        )

    message_content = "\n".join(message_parts)

    # 7. Create new ChatMessage as sibling (same parent as the assistant response)
    new_message = create_new_chat_message(
        chat_session_id=request.chat_session_id,
        parent_message=parent_message,
        message=message_content,
        token_count=0,
        message_type=MessageType.ASSISTANT,
        db_session=db_session,
        files=file_descriptors or None,
        commit=True,
    )

    logger.info(
        f"Created execution result message {new_message.id} "
        f"as sibling under parent {parent_message.id} "
        f"in session {request.chat_session_id}"
    )

    return ExecuteCodeResponse(
        message_id=new_message.id,
        parent_message_id=parent_message.id,
        stdout=response.stdout,
        stderr=response.stderr,
        exit_code=response.exit_code,
        files=file_descriptors,
    )
