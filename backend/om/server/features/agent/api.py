from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import UploadFile
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from om.auth.users import current_admin_user
from om.auth.users import current_chat_accessible_user
from om.auth.users import current_curator_or_admin_user
from om.auth.users import current_limited_user
from om.auth.users import current_user
from om.configs.app_configs import DISABLE_VECTOR_DB
from om.configs.constants import FileOrigin
from om.configs.constants import MilestoneRecordType
from om.configs.constants import PUBLIC_API_TAGS
from om.db.engine.sql_engine import get_session
from om.db.models import User
from om.db.agent import create_assistant_label
from om.db.agent import create_update_agent
from om.db.agent import delete_agent_label
from om.db.agent import get_assistant_labels
from om.db.agent import get_minimal_agent_snapshots_for_user
from om.db.agent import get_minimal_agent_snapshots_paginated
from om.db.agent import get_agent_by_id
from om.db.agent import get_agent_count_for_user
from om.db.agent import get_agent_snapshots_for_user
from om.db.agent import get_agent_snapshots_paginated
from om.db.agent import mark_agent_as_deleted
from om.db.agent import mark_agent_as_not_deleted
from om.db.agent import update_agent_is_default
from om.db.agent import update_agent_label
from om.db.agent import update_agent_public_status
from om.db.agent import update_agent_shared
from om.db.agent import update_agent_visibility
from om.db.agent import update_agents_display_priority
from om.file_store.file_store import get_default_file_store
from om.file_store.models import ChatFileType
from om.server.documents.models import PaginatedReturn
from om.server.features.agent.constants import ADMIN_AGENTS_RESOURCE
from om.server.features.agent.constants import AGENTS_RESOURCE
from om.server.features.agent.models import FullAgentSnapshot
from om.server.features.agent.models import MinimalAgentSnapshot
from om.server.features.agent.models import AgentLabelCreate
from om.server.features.agent.models import AgentLabelResponse
from om.server.features.agent.models import AgentSnapshot
from om.server.features.agent.models import AgentUpsertRequest
from om.server.manage.llm.api import get_valid_model_names_for_agent
from om.server.models import DisplayPriorityRequest
from om.server.settings.store import load_settings
from om.utils.logger import setup_logger
from om.utils.telemetry import mt_cloud_telemetry
from shared_configs.contextvars import get_current_tenant_id

logger = setup_logger()


def _validate_user_knowledge_enabled(
    agent_upsert_request: AgentUpsertRequest, action: str
) -> None:
    """Check if user knowledge is enabled when user files/workspaces are provided."""
    settings = load_settings()
    if not settings.user_knowledge_enabled:
        # Only user files are supported going forward; keep getattr for backward compat
        if agent_upsert_request.knowledge_file_ids or getattr(
            agent_upsert_request, "user_workspace_ids", None
        ):
            raise HTTPException(
                status_code=400,
                detail=f"User Knowledge is disabled. Cannot {action} assistant with user files or workspaces.",
            )


def _validate_vector_db_knowledge(
    agent_upsert_request: AgentUpsertRequest,
) -> None:
    """Reject connector-sourced knowledge types when vector DB is disabled.

    document_sets, hierarchy_nodes, and attached_documents all depend on
    the vector DB for search filtering. knowledge_files are still allowed because
    they use the FileReaderTool path instead.
    """
    if not DISABLE_VECTOR_DB:
        return

    if agent_upsert_request.document_set_ids:
        raise HTTPException(
            status_code=400,
            detail=(
                "Cannot attach document sets to an assistant when "
                "the vector database is disabled (DISABLE_VECTOR_DB is set)."
            ),
        )
    if agent_upsert_request.hierarchy_node_ids:
        raise HTTPException(
            status_code=400,
            detail=(
                "Cannot attach hierarchy nodes to an assistant when "
                "the vector database is disabled (DISABLE_VECTOR_DB is set)."
            ),
        )
    if agent_upsert_request.document_ids:
        raise HTTPException(
            status_code=400,
            detail=(
                "Cannot attach documents to an assistant when "
                "the vector database is disabled (DISABLE_VECTOR_DB is set)."
            ),
        )


admin_router = APIRouter(prefix="/admin/agent")
basic_router = APIRouter(prefix="/agent")

# NOTE: Users know this functionality as "agents", so we want to start moving
# nomenclature of these REST resources to match that.
admin_agents_router = APIRouter(prefix=ADMIN_AGENTS_RESOURCE)
agents_router = APIRouter(prefix=AGENTS_RESOURCE)


class IsVisibleRequest(BaseModel):
    is_visible: bool


class IsPublicRequest(BaseModel):
    is_public: bool


class IsDefaultRequest(BaseModel):
    is_default_agent: bool


@admin_router.patch("/{agent_id}/visible")
def patch_agent_visibility(
    agent_id: int,
    is_visible_request: IsVisibleRequest,
    user: User = Depends(current_curator_or_admin_user),
    db_session: Session = Depends(get_session),
) -> None:
    update_agent_visibility(
        agent_id=agent_id,
        is_visible=is_visible_request.is_visible,
        db_session=db_session,
        user=user,
    )


@basic_router.patch("/{agent_id}/public")
def patch_user_agent_public_status(
    agent_id: int,
    is_public_request: IsPublicRequest,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> None:
    try:
        update_agent_public_status(
            agent_id=agent_id,
            is_public=is_public_request.is_public,
            db_session=db_session,
            user=user,
        )
    except ValueError as e:
        logger.exception("Failed to update agent public status")
        raise HTTPException(status_code=403, detail=str(e))


@admin_router.patch("/{agent_id}/default")
def patch_agent_default_status(
    agent_id: int,
    is_default_request: IsDefaultRequest,
    user: User = Depends(current_curator_or_admin_user),
    db_session: Session = Depends(get_session),
) -> None:
    try:
        update_agent_is_default(
            agent_id=agent_id,
            is_default=is_default_request.is_default_agent,
            db_session=db_session,
            user=user,
        )
    except ValueError as e:
        logger.exception("Failed to update agent default status")
        raise HTTPException(status_code=403, detail=str(e))


@admin_agents_router.patch("/display-priorities")
def patch_agents_display_priorities(
    display_priority_request: DisplayPriorityRequest,
    user: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
) -> None:
    try:
        update_agents_display_priority(
            display_priority_map=display_priority_request.display_priority_map,
            db_session=db_session,
            user=user,
            commit_db_txn=True,
        )
    except ValueError as e:
        logger.exception("Failed to update agent display priorities.")
        raise HTTPException(status_code=403, detail=str(e))


@admin_router.get("", tags=PUBLIC_API_TAGS)
def list_agents_admin(
    user: User = Depends(current_curator_or_admin_user),
    db_session: Session = Depends(get_session),
    include_deleted: bool = False,
    get_editable: bool = Query(False, description="If true, return editable agents"),
) -> list[AgentSnapshot]:
    return get_agent_snapshots_for_user(
        user=user,
        db_session=db_session,
        get_editable=get_editable,
        include_deleted=include_deleted,
    )


@admin_agents_router.get("", tags=PUBLIC_API_TAGS)
def get_agents_admin_paginated(
    page_num: int = Query(0, ge=0, description="Page number (0-indexed)."),
    page_size: int = Query(10, ge=1, le=1000, description="Items per page."),
    user: User = Depends(current_curator_or_admin_user),
    db_session: Session = Depends(get_session),
    include_deleted: bool = Query(
        False, description="If true, includes deleted agents."
    ),
    get_editable: bool = Query(
        False, description="If true, only returns editable agents."
    ),
    include_default: bool = Query(
        True, description="If true, includes builtin/default agents."
    ),
    q: str | None = Query(
        None,
        description="Optional search term matched against agent name or description.",
    ),
) -> PaginatedReturn[AgentSnapshot]:
    """Paginated endpoint for listing agents (formerly agents) (admin view).

    Returns items for the requested page plus total count. When `q` is provided,
    results are filtered (case-insensitive substring on name OR description)
    across ALL pages before pagination.
    Agents are ordered by display_priority (ASC, nulls last) then by ID (ASC).
    """
    agents = get_agent_snapshots_paginated(
        user=user,
        db_session=db_session,
        page_num=page_num,
        page_size=page_size,
        get_editable=get_editable,
        include_default=include_default,
        include_deleted=include_deleted,
        search_query=q,
    )

    total_count = get_agent_count_for_user(
        user=user,
        db_session=db_session,
        get_editable=get_editable,
        include_default=include_default,
        include_deleted=include_deleted,
        search_query=q,
    )

    return PaginatedReturn(
        items=agents,
        total_items=total_count,
    )


@admin_router.patch("/{agent_id}/undelete", tags=PUBLIC_API_TAGS)
def undelete_agent(
    agent_id: int,
    user: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
) -> None:
    mark_agent_as_not_deleted(
        agent_id=agent_id,
        user=user,
        db_session=db_session,
    )


# used for assistant profile pictures
@admin_router.post("/upload-image")
def upload_file(
    file: UploadFile,
    _: User = Depends(current_user),
) -> dict[str, str]:
    file_store = get_default_file_store()
    file_type = ChatFileType.IMAGE
    file_id = file_store.save_file(
        content=file.file,
        display_name=file.filename,
        file_origin=FileOrigin.CHAT_UPLOAD,
        file_type=file.content_type or file_type.value,
    )
    return {"file_id": file_id}


"""Endpoints for all"""


@basic_router.post("", tags=PUBLIC_API_TAGS)
def create_agent(
    agent_upsert_request: AgentUpsertRequest,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> AgentSnapshot:
    tenant_id = get_current_tenant_id()

    _validate_user_knowledge_enabled(agent_upsert_request, "create")
    _validate_vector_db_knowledge(agent_upsert_request)

    agent_snapshot = create_update_agent(
        agent_id=None,
        create_agent_request=agent_upsert_request,
        user=user,
        db_session=db_session,
    )
    mt_cloud_telemetry(
        tenant_id=tenant_id,
        distinct_id=user.email,
        event=MilestoneRecordType.CREATED_ASSISTANT,
    )

    return agent_snapshot


# NOTE: This endpoint cannot update agent configuration options that
# are core to the agent, such as its display priority and
# whether or not the assistant is a built-in / default assistant
@basic_router.patch("/{agent_id}", tags=PUBLIC_API_TAGS)
def update_agent(
    agent_id: int,
    agent_upsert_request: AgentUpsertRequest,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> AgentSnapshot:
    _validate_user_knowledge_enabled(agent_upsert_request, "update")
    _validate_vector_db_knowledge(agent_upsert_request)

    agent_snapshot = create_update_agent(
        agent_id=agent_id,
        create_agent_request=agent_upsert_request,
        user=user,
        db_session=db_session,
    )
    return agent_snapshot


class AgentLabelPatchRequest(BaseModel):
    label_name: str


@basic_router.get("/labels")
def get_labels(
    db: Session = Depends(get_session),
    _: User = Depends(current_user),
) -> list[AgentLabelResponse]:
    return [
        AgentLabelResponse.from_model(label)
        for label in get_assistant_labels(db_session=db)
    ]


@basic_router.post("/labels")
def create_label(
    label: AgentLabelCreate,
    db: Session = Depends(get_session),
    _: User = Depends(current_user),
) -> AgentLabelResponse:
    """Create a new assistant label"""
    try:
        label_model = create_assistant_label(name=label.name, db_session=db)
        return AgentLabelResponse.from_model(label_model)
    except IntegrityError:
        raise HTTPException(
            status_code=400,
            detail=f"Label with name '{label.name}' already exists. Please choose a different name.",
        )


@admin_router.patch("/label/{label_id}")
def patch_agent_label(
    label_id: int,
    agent_label_patch_request: AgentLabelPatchRequest,
    _: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
) -> None:
    update_agent_label(
        label_id=label_id,
        label_name=agent_label_patch_request.label_name,
        db_session=db_session,
    )


@admin_router.delete("/label/{label_id}")
def delete_label(
    label_id: int,
    _: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
) -> None:
    delete_agent_label(label_id=label_id, db_session=db_session)


class AgentShareRequest(BaseModel):
    user_ids: list[UUID] | None = None
    group_ids: list[int] | None = None
    is_public: bool | None = None


# We notify each user when a user is shared with them
@basic_router.patch("/{agent_id}/share")
def share_agent(
    agent_id: int,
    agent_share_request: AgentShareRequest,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> None:
    update_agent_shared(
        agent_id=agent_id,
        user=user,
        db_session=db_session,
        user_ids=agent_share_request.user_ids,
        group_ids=agent_share_request.group_ids,
        is_public=agent_share_request.is_public,
    )


@basic_router.delete("/{agent_id}", tags=PUBLIC_API_TAGS)
def delete_agent(
    agent_id: int,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> None:
    mark_agent_as_deleted(
        agent_id=agent_id,
        user=user,
        db_session=db_session,
    )


@basic_router.get("")
def list_agents(
    user: User = Depends(current_chat_accessible_user),
    db_session: Session = Depends(get_session),
    include_deleted: bool = False,
    agent_ids: list[int] = Query(None),
) -> list[MinimalAgentSnapshot]:
    agents = get_minimal_agent_snapshots_for_user(
        user=user,
        include_deleted=include_deleted,
        db_session=db_session,
        get_editable=False,
    )

    if agent_ids:
        agents = [p for p in agents if p.id in agent_ids]

    return agents


@agents_router.get("", tags=PUBLIC_API_TAGS)
def get_agents_paginated(
    page_num: int = Query(0, ge=0, description="Page number (0-indexed)."),
    page_size: int = Query(10, ge=1, le=1000, description="Items per page."),
    user: User = Depends(current_chat_accessible_user),
    db_session: Session = Depends(get_session),
    include_deleted: bool = Query(
        False, description="If true, includes deleted agents."
    ),
    get_editable: bool = Query(
        False, description="If true, only returns editable agents."
    ),
    include_default: bool = Query(
        True, description="If true, includes builtin/default agents."
    ),
    q: str | None = Query(
        None,
        description="Optional search term matched against agent name or description.",
    ),
) -> PaginatedReturn[MinimalAgentSnapshot]:
    """Paginated endpoint for listing agents available to the user.

    Returns items for the requested page plus total count. When `q` is provided,
    results are filtered (case-insensitive substring on name OR description)
    across ALL pages before pagination.
    Agents are ordered by display_priority (ASC, nulls last) then by ID (ASC).

    NOTE: agent_ids filter is not supported with pagination. Use the
    non-paginated endpoint if filtering by specific IDs is needed.
    """
    agents = get_minimal_agent_snapshots_paginated(
        user=user,
        db_session=db_session,
        page_num=page_num,
        page_size=page_size,
        get_editable=get_editable,
        include_default=include_default,
        include_deleted=include_deleted,
        search_query=q,
    )

    total_count = get_agent_count_for_user(
        user=user,
        db_session=db_session,
        get_editable=get_editable,
        include_default=include_default,
        include_deleted=include_deleted,
        search_query=q,
    )

    return PaginatedReturn(
        items=agents,
        total_items=total_count,
    )


@basic_router.get("/{agent_id}", tags=PUBLIC_API_TAGS)
def get_agent(
    agent_id: int,
    user: User = Depends(current_limited_user),
    db_session: Session = Depends(get_session),
) -> FullAgentSnapshot:
    agent = get_agent_by_id(
        agent_id=agent_id,
        user=user,
        db_session=db_session,
        is_for_edit=False,
    )

    # Validate and fix default model if it's no longer valid for this agent's restrictions
    if agent.llm_model_version_override:
        valid_models = get_valid_model_names_for_agent(agent_id, user, db_session)

        # If current default model is not in the valid list, update to first valid or None
        if agent.llm_model_version_override not in valid_models:
            agent.llm_model_version_override = (
                valid_models[0] if valid_models else None
            )
            db_session.commit()

    return FullAgentSnapshot.from_model(agent)
