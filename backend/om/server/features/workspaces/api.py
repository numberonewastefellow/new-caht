import json
from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import File
from fastapi import Form
from fastapi import HTTPException
from fastapi import Response
from fastapi import UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from om.auth.users import current_user
from om.background.celery.versioned_apps.client import app as client_app
from om.configs.constants import OmCeleryPriority
from om.configs.constants import OmCeleryQueues
from om.configs.constants import OmCeleryTask
from om.configs.constants import PUBLIC_API_TAGS
from om.db.engine.sql_engine import get_session
from om.db.enums import KnowledgeFileStatus
from om.db.models import ChatSession
from om.db.models import Workspace__KnowledgeFile
from om.db.models import User
from om.db.models import KnowledgeFile
from om.db.models import Workspace
from om.db.persona import get_personas_by_ids
from om.db.workspaces import get_workspace_token_count
from om.db.workspaces import upload_files_to_knowledge_files_with_indexing
from om.server.features.workspaces.models import CategorizedFilesSnapshot
from om.server.features.workspaces.models import ChatSessionRequest
from om.server.features.workspaces.models import TokenCountResponse
from om.server.features.workspaces.models import KnowledgeFileSnapshot
from om.server.features.workspaces.models import WorkspaceSnapshot
from om.utils.logger import setup_logger
from shared_configs.contextvars import get_current_tenant_id

logger = setup_logger()


router = APIRouter(prefix="/workspaces")


class KnowledgeFileDeleteResult(BaseModel):
    has_associations: bool
    workspace_names: list[str] = []
    assistant_names: list[str] = []


@router.get("", tags=PUBLIC_API_TAGS)
def get_workspaces(
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> list[WorkspaceSnapshot]:
    user_id = user.id
    workspaces = (
        db_session.query(Workspace).filter(Workspace.user_id == user_id).all()
    )
    return [WorkspaceSnapshot.from_model(workspace) for workspace in workspaces]


@router.post("/create", tags=PUBLIC_API_TAGS)
def create_workspace(
    name: str,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> WorkspaceSnapshot:
    if name == "":
        raise HTTPException(status_code=400, detail="Workspace name cannot be empty")
    user_id = user.id
    workspace = Workspace(name=name, user_id=user_id)
    db_session.add(workspace)
    db_session.commit()
    return WorkspaceSnapshot.from_model(workspace)


@router.post("/file/upload", tags=PUBLIC_API_TAGS)
def upload_knowledge_files(
    files: list[UploadFile] = File(...),
    workspace_id: int | None = Form(None),
    temp_id_map: str | None = Form(None),  # JSON string mapping hashed key -> temp_id
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> CategorizedFilesSnapshot:
    try:
        parsed_temp_id_map: dict[str, str] | None = None
        if temp_id_map:
            try:
                parsed = json.loads(temp_id_map)
                if isinstance(parsed, dict):
                    # Ensure all keys/values are strings
                    parsed_temp_id_map = {str(k): str(v) for k, v in parsed.items()}
                else:
                    parsed_temp_id_map = None
            except json.JSONDecodeError:
                parsed_temp_id_map = None

        # Use our consolidated function that handles indexing properly
        categorized_files_result = upload_files_to_knowledge_files_with_indexing(
            files=files,
            workspace_id=workspace_id,
            user=user,
            temp_id_map=parsed_temp_id_map,
            db_session=db_session,
        )

        return CategorizedFilesSnapshot.from_result(categorized_files_result)

    except Exception as e:
        # Log error with type, message, and stack for easier debugging
        logger.exception(f"Error uploading files - {type(e).__name__}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to upload files. Please try again or contact support if the issue persists.",
        )


@router.get("/{workspace_id}", tags=PUBLIC_API_TAGS)
def get_workspace(
    workspace_id: int,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> WorkspaceSnapshot:
    user_id = user.id
    workspace = (
        db_session.query(Workspace)
        .filter(Workspace.id == workspace_id, Workspace.user_id == user_id)
        .one_or_none()
    )
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return WorkspaceSnapshot.from_model(workspace)


@router.get("/files/{workspace_id}", tags=PUBLIC_API_TAGS)
def get_files_in_workspace(
    workspace_id: int,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> list[KnowledgeFileSnapshot]:
    user_id = user.id
    knowledge_files = (
        db_session.query(KnowledgeFile)
        .join(Workspace__KnowledgeFile, KnowledgeFile.id == Workspace__KnowledgeFile.knowledge_file_id)
        .filter(
            Workspace__KnowledgeFile.workspace_id == workspace_id,
            KnowledgeFile.user_id == user_id,
            KnowledgeFile.status != KnowledgeFileStatus.FAILED,
        )
        .order_by(Workspace__KnowledgeFile.created_at.desc())
        .all()
    )
    return [KnowledgeFileSnapshot.from_model(knowledge_file) for knowledge_file in knowledge_files]


@router.delete("/{workspace_id}/files/{file_id}", tags=PUBLIC_API_TAGS)
def unlink_user_file_from_workspace(
    workspace_id: int,
    file_id: UUID,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> Response:
    """Unlink an existing user file from a specific workspace for the current user.

    Does not delete the underlying file; only removes the association.
    """
    user_id = user.id
    workspace = (
        db_session.query(Workspace)
        .filter(Workspace.id == workspace_id, Workspace.user_id == user_id)
        .one_or_none()
    )
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    user_id = user.id
    knowledge_file = (
        db_session.query(KnowledgeFile)
        .filter(KnowledgeFile.id == file_id, KnowledgeFile.user_id == user_id)
        .one_or_none()
    )
    if knowledge_file is None:
        raise HTTPException(status_code=404, detail="File not found")

    # Remove the association if it exists
    if knowledge_file in workspace.knowledge_files:
        workspace.knowledge_files.remove(knowledge_file)
        knowledge_file.needs_workspace_sync = True
        db_session.commit()

    tenant_id = get_current_tenant_id()
    task = client_app.send_task(
        OmCeleryTask.PROCESS_SINGLE_USER_FILE_PROJECT_SYNC,
        kwargs={"knowledge_file_id": knowledge_file.id, "tenant_id": tenant_id},
        queue=OmCeleryQueues.USER_FILE_PROJECT_SYNC,
        priority=OmCeleryPriority.HIGHEST,
    )
    logger.info(
        f"Triggered workspace sync for knowledge_file_id={knowledge_file.id} with task_id={task.id}"
    )

    return Response(status_code=204)


@router.post(
    "/{workspace_id}/files/{file_id}",
    response_model=KnowledgeFileSnapshot,
    tags=PUBLIC_API_TAGS,
)
def link_user_file_to_workspace(
    workspace_id: int,
    file_id: UUID,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> KnowledgeFileSnapshot:
    """Link an existing user file to a specific workspace for the current user.

    Creates the association in the Workspace__KnowledgeFile join table if it does not exist.
    Returns the linked user file snapshot.
    """
    user_id = user.id
    workspace = (
        db_session.query(Workspace)
        .filter(Workspace.id == workspace_id, Workspace.user_id == user_id)
        .one_or_none()
    )
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    knowledge_file = (
        db_session.query(KnowledgeFile)
        .filter(KnowledgeFile.id == file_id, KnowledgeFile.user_id == user_id)
        .one_or_none()
    )
    if knowledge_file is None:
        raise HTTPException(status_code=404, detail="File not found")

    if knowledge_file not in workspace.knowledge_files:
        knowledge_file.needs_workspace_sync = True
        workspace.knowledge_files.append(knowledge_file)
        db_session.commit()

    tenant_id = get_current_tenant_id()
    task = client_app.send_task(
        OmCeleryTask.PROCESS_SINGLE_USER_FILE_PROJECT_SYNC,
        kwargs={"knowledge_file_id": knowledge_file.id, "tenant_id": tenant_id},
        queue=OmCeleryQueues.USER_FILE_PROJECT_SYNC,
        priority=OmCeleryPriority.HIGHEST,
    )
    logger.info(
        f"Triggered workspace sync for knowledge_file_id={knowledge_file.id} with task_id={task.id}"
    )

    return KnowledgeFileSnapshot.from_model(knowledge_file)


class WorkspaceInstructionsResponse(BaseModel):
    instructions: str | None


@router.get(
    "/{workspace_id}/instructions",
    response_model=WorkspaceInstructionsResponse,
    tags=PUBLIC_API_TAGS,
)
def get_workspace_instructions(
    workspace_id: int,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> WorkspaceInstructionsResponse:
    user_id = user.id
    workspace = (
        db_session.query(Workspace)
        .filter(Workspace.id == workspace_id, Workspace.user_id == user_id)
        .one_or_none()
    )

    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    return WorkspaceInstructionsResponse(instructions=workspace.workspace_instructions)


class UpsertWorkspaceInstructionsRequest(BaseModel):
    instructions: str


@router.post(
    "/{workspace_id}/instructions",
    response_model=WorkspaceInstructionsResponse,
    tags=PUBLIC_API_TAGS,
)
def upsert_workspace_instructions(
    workspace_id: int,
    body: UpsertWorkspaceInstructionsRequest,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> WorkspaceInstructionsResponse:
    """Create or update this workspace's instructions stored on the workspace itself."""
    # Ensure the workspace exists and belongs to the user
    user_id = user.id
    workspace = (
        db_session.query(Workspace)
        .filter(Workspace.id == workspace_id, Workspace.user_id == user_id)
        .one_or_none()
    )
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    workspace.workspace_instructions = body.instructions

    db_session.commit()
    db_session.refresh(workspace)
    return WorkspaceInstructionsResponse(instructions=workspace.workspace_instructions)


class WorkspacePayload(BaseModel):
    workspace: WorkspaceSnapshot
    files: list[KnowledgeFileSnapshot] | None = None
    persona_id_to_is_default: dict[int, bool] | None = None


@router.get(
    "/{workspace_id}/details", response_model=WorkspacePayload, tags=PUBLIC_API_TAGS
)
def get_workspace_details(
    workspace_id: int,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> WorkspacePayload:
    workspace = get_workspace(workspace_id, user, db_session)
    files = get_files_in_workspace(workspace_id, user, db_session)
    persona_ids = [
        session.persona_id
        for session in workspace.chat_sessions
        if session.persona_id is not None
    ]
    personas = get_personas_by_ids(persona_ids, db_session)
    persona_id_to_is_default = {
        persona.id: persona.is_default_persona for persona in personas
    }
    return WorkspacePayload(
        workspace=workspace,
        files=files,
        persona_id_to_is_default=persona_id_to_is_default,
    )


class UpdateWorkspaceRequest(BaseModel):
    name: str | None = None
    description: str | None = None


@router.patch("/{workspace_id}", response_model=WorkspaceSnapshot, tags=PUBLIC_API_TAGS)
def update_workspace(
    workspace_id: int,
    body: UpdateWorkspaceRequest,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> WorkspaceSnapshot:
    user_id = user.id
    workspace = (
        db_session.query(Workspace)
        .filter(Workspace.id == workspace_id, Workspace.user_id == user_id)
        .one_or_none()
    )
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    if body.name is not None:
        workspace.name = body.name
    if body.description is not None:
        workspace.description = body.description

    db_session.commit()
    db_session.refresh(workspace)
    return WorkspaceSnapshot.from_model(workspace)


@router.delete("/{workspace_id}", tags=PUBLIC_API_TAGS)
def delete_workspace(
    workspace_id: int,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> Response:
    user_id = user.id
    workspace = (
        db_session.query(Workspace)
        .filter(Workspace.id == workspace_id, Workspace.user_id == user_id)
        .one_or_none()
    )
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # Unlink chat sessions from this workspace
    for chat in workspace.chat_sessions:
        chat.workspace_id = None

    # Unlink many-to-many user files association (Workspace__KnowledgeFile)
    for uf in list(workspace.knowledge_files):
        workspace.knowledge_files.remove(uf)

    db_session.delete(workspace)
    db_session.commit()
    return Response(status_code=204)


@router.delete("/file/{file_id}", tags=PUBLIC_API_TAGS)
def delete_user_file(
    file_id: UUID,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> KnowledgeFileDeleteResult:
    """Delete a user file belonging to the current user.

    This will also remove any workspace associations for the file.
    """
    user_id = user.id
    knowledge_file = (
        db_session.query(KnowledgeFile)
        .filter(KnowledgeFile.id == file_id, KnowledgeFile.user_id == user_id)
        .one_or_none()
    )
    if knowledge_file is None:
        raise HTTPException(status_code=404, detail="File not found")

    # Check associations with workspaces and assistants (personas)
    workspace_names = [workspace.name for workspace in knowledge_file.workspaces]
    assistant_names = [assistant.name for assistant in knowledge_file.assistants]

    if len(workspace_names) > 0 or len(assistant_names) > 0:
        return KnowledgeFileDeleteResult(
            has_associations=True,
            workspace_names=workspace_names,
            assistant_names=assistant_names,
        )

    # No associations found; mark as DELETING and enqueue delete task
    knowledge_file.status = KnowledgeFileStatus.DELETING
    db_session.commit()

    tenant_id = get_current_tenant_id()
    task = client_app.send_task(
        OmCeleryTask.DELETE_SINGLE_USER_FILE,
        kwargs={"knowledge_file_id": str(knowledge_file.id), "tenant_id": tenant_id},
        queue=OmCeleryQueues.USER_FILE_DELETE,
        priority=OmCeleryPriority.HIGH,
    )
    logger.info(
        f"Triggered delete for knowledge_file_id={knowledge_file.id} with task_id={task.id}"
    )
    return KnowledgeFileDeleteResult(
        has_associations=False, workspace_names=[], assistant_names=[]
    )


@router.get("/file/{file_id}", response_model=KnowledgeFileSnapshot, tags=PUBLIC_API_TAGS)
def get_user_file(
    file_id: UUID,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> KnowledgeFileSnapshot:
    """Fetch a single user file by ID for the current user.

    Includes files in any status (including FAILED) to allow status polling.
    """
    user_id = user.id
    knowledge_file = (
        db_session.query(KnowledgeFile)
        .filter(KnowledgeFile.id == file_id, KnowledgeFile.user_id == user_id)
        .filter(KnowledgeFile.status != KnowledgeFileStatus.DELETING)
        .one_or_none()
    )
    if knowledge_file is None:
        raise HTTPException(status_code=404, detail="File not found")
    return KnowledgeFileSnapshot.from_model(knowledge_file)


class KnowledgeFileIdsRequest(BaseModel):
    file_ids: list[UUID]


@router.post(
    "/file/statuses", response_model=list[KnowledgeFileSnapshot], tags=PUBLIC_API_TAGS
)
def get_user_file_statuses(
    body: KnowledgeFileIdsRequest,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> list[KnowledgeFileSnapshot]:
    """Fetch statuses for a set of user file IDs owned by the current user.

    Includes files in any status so the client can detect transitions to FAILED.
    """
    if not body.file_ids:
        return []

    user_id = user.id
    knowledge_files = (
        db_session.query(KnowledgeFile)
        .filter(KnowledgeFile.user_id == user_id)
        .filter(KnowledgeFile.id.in_(body.file_ids))
        .filter(KnowledgeFile.status != KnowledgeFileStatus.DELETING)
        .all()
    )

    return [KnowledgeFileSnapshot.from_model(knowledge_file) for knowledge_file in knowledge_files]


@router.post("/{workspace_id}/move_chat_session")
def move_chat_session(
    workspace_id: int,
    body: ChatSessionRequest,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> Response:
    user_id = user.id
    chat_session = (
        db_session.query(ChatSession)
        .filter(ChatSession.id == body.chat_session_id, ChatSession.user_id == user_id)
        .one_or_none()
    )
    if chat_session is None:
        raise HTTPException(status_code=404, detail="Chat session not found")
    chat_session.workspace_id = workspace_id
    db_session.commit()
    return Response(status_code=204)


@router.post("/remove_chat_session")
def remove_chat_session(
    body: ChatSessionRequest,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> Response:
    user_id = user.id
    chat_session = (
        db_session.query(ChatSession)
        .filter(ChatSession.id == body.chat_session_id, ChatSession.user_id == user_id)
        .one_or_none()
    )
    if chat_session is None:
        raise HTTPException(status_code=404, detail="Chat session not found")
    chat_session.workspace_id = None
    db_session.commit()
    return Response(status_code=204)


@router.get("/session/{chat_session_id}/token-count", response_model=TokenCountResponse)
def get_chat_session_workspace_token_count(
    chat_session_id: str,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> TokenCountResponse:
    """Return sum of token_count for all user files in the workspace linked to the given chat session.

    If the chat session has no workspace, returns 0.
    """
    user_id = user.id
    chat_session = (
        db_session.query(ChatSession)
        .filter(ChatSession.id == chat_session_id, ChatSession.user_id == user_id)
        .one_or_none()
    )
    if chat_session is None:
        raise HTTPException(status_code=404, detail="Chat session not found")

    total_tokens = get_workspace_token_count(
        workspace_id=chat_session.workspace_id,
        user_id=user_id,
        db_session=db_session,
    )

    return TokenCountResponse(total_tokens=total_tokens)


@router.get("/session/{chat_session_id}/files", tags=PUBLIC_API_TAGS)
def get_chat_session_workspace_files(
    chat_session_id: str,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> list[KnowledgeFileSnapshot]:
    """Return user files for the workspace linked to the given chat session.

    If the chat session has no workspace, returns an empty list.
    Only returns files owned by the current user and not FAILED.
    """
    user_id = user.id

    chat_session = (
        db_session.query(ChatSession)
        .filter(ChatSession.id == chat_session_id, ChatSession.user_id == user_id)
        .one_or_none()
    )
    if chat_session is None:
        raise HTTPException(status_code=404, detail="Chat session not found")

    if chat_session.workspace_id is None:
        return []

    knowledge_files = (
        db_session.query(KnowledgeFile)
        .filter(
            KnowledgeFile.workspaces.any(id=chat_session.workspace_id),
            KnowledgeFile.user_id == user_id,
            KnowledgeFile.status != KnowledgeFileStatus.FAILED,
        )
        .order_by(KnowledgeFile.created_at.desc())
        .all()
    )

    return [KnowledgeFileSnapshot.from_model(knowledge_file) for knowledge_file in knowledge_files]


@router.get("/{workspace_id}/token-count", response_model=TokenCountResponse)
def get_workspace_total_token_count(
    workspace_id: int,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> TokenCountResponse:
    """Return sum of token_count for all user files in the given workspace for the current user."""

    # Verify the workspace belongs to the current user
    user_id = user.id
    workspace = (
        db_session.query(Workspace)
        .filter(Workspace.id == workspace_id, Workspace.user_id == user_id)
        .one_or_none()
    )
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    total_tokens = get_workspace_token_count(
        workspace_id=workspace_id,
        user_id=user_id,
        db_session=db_session,
    )

    return TokenCountResponse(total_tokens=total_tokens)
