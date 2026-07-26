import datetime
import uuid
from typing import List
from uuid import UUID

from fastapi import HTTPException
from fastapi import UploadFile
from pydantic import BaseModel
from pydantic import ConfigDict
from sqlalchemy import func
from sqlalchemy.orm import Session

from om.background.celery.versioned_apps.client import app as client_app
from om.configs.constants import FileOrigin
from om.configs.constants import OmCeleryPriority
from om.configs.constants import OmCeleryQueues
from om.configs.constants import OmCeleryTask
from om.db.models import Workspace__KnowledgeFile
from om.db.models import User
from om.db.models import KnowledgeFile
from om.db.models import Workspace
from om.server.documents.connector import upload_files
from om.server.features.workspaces.workspaces_file_utils import categorize_uploaded_files
from om.server.features.workspaces.workspaces_file_utils import RejectedFile
from om.utils.logger import setup_logger
from shared_configs.contextvars import get_current_tenant_id

logger = setup_logger()


class CategorizedFilesResult(BaseModel):
    knowledge_files: list[KnowledgeFile]
    rejected_files: list[RejectedFile]
    id_to_temp_id: dict[str, str]
    # Allow SQLAlchemy ORM models inside this result container
    model_config = ConfigDict(arbitrary_types_allowed=True)


def build_hashed_file_key(file: UploadFile) -> str:
    name_prefix = (file.filename or "")[:50]
    return f"{file.size}|{name_prefix}"


def create_knowledge_files(
    files: List[UploadFile],
    workspace_id: int | None,
    user: User,
    db_session: Session,
    link_url: str | None = None,
    temp_id_map: dict[str, str] | None = None,
    temp_ids: list[str] | None = None,
) -> CategorizedFilesResult:

    # Categorize the files
    categorized_files = categorize_uploaded_files(files)
    # NOTE: At the moment, zip metadata is not used for user files.
    # Should revisit to decide whether this should be a feature.
    upload_response = upload_files(categorized_files.acceptable, FileOrigin.USER_FILE)
    knowledge_files = []
    rejected_files = categorized_files.rejected
    id_to_temp_id: dict[str, str] = {}
    # Correlate each uploaded file with its client-side temp_id. Prefer the ordered
    # `temp_ids` list (keyed by object identity of the original UploadFiles), which
    # is unambiguous even when two files share a name+size; fall back to the legacy
    # size|name map only for older clients that don't send `temp_ids`.
    file_to_temp: dict[int, str] = {}
    if temp_ids is not None:
        for idx, original_file in enumerate(files):
            if idx < len(temp_ids):
                file_to_temp[id(original_file)] = temp_ids[idx]
    # Pair returned storage paths with the same set of acceptable files we uploaded
    for file_path, file in zip(
        upload_response.file_paths, categorized_files.acceptable
    ):
        new_id = uuid.uuid4()
        if temp_ids is not None:
            new_temp_id = file_to_temp.get(id(file))
        else:
            new_temp_id = (
                temp_id_map.get(build_hashed_file_key(file)) if temp_id_map else None
            )
        if new_temp_id is not None:
            id_to_temp_id[str(new_id)] = new_temp_id
        new_file = KnowledgeFile(
            id=new_id,
            user_id=user.id,
            file_id=file_path,
            name=file.filename,
            token_count=categorized_files.acceptable_file_to_token_count[
                file.filename or ""
            ],
            link_url=link_url,
            content_type=file.content_type,
            file_type=file.content_type,
            last_accessed_at=datetime.datetime.now(datetime.timezone.utc),
        )
        # Persist the KnowledgeFile first to satisfy FK constraints for association table
        db_session.add(new_file)
        db_session.flush()
        if workspace_id:
            workspace_to_user_file = Workspace__KnowledgeFile(
                workspace_id=workspace_id,
                knowledge_file_id=new_file.id,
            )
            db_session.add(workspace_to_user_file)
        knowledge_files.append(new_file)
    db_session.commit()
    return CategorizedFilesResult(
        knowledge_files=knowledge_files,
        rejected_files=rejected_files,
        id_to_temp_id=id_to_temp_id,
    )


def upload_files_to_knowledge_files_with_indexing(
    files: List[UploadFile],
    workspace_id: int | None,
    user: User,
    temp_id_map: dict[str, str] | None,
    db_session: Session,
    temp_ids: list[str] | None = None,
) -> CategorizedFilesResult:
    # Validate workspace ownership if a workspace_id is provided
    if workspace_id is not None and user is not None:
        if not check_workspace_ownership(workspace_id, user.id, db_session):
            raise HTTPException(status_code=404, detail="Workspace not found")

    categorized_files_result = create_knowledge_files(
        files,
        workspace_id,
        user,
        db_session,
        temp_id_map=temp_id_map,
        temp_ids=temp_ids,
    )
    knowledge_files = categorized_files_result.knowledge_files
    rejected_files = categorized_files_result.rejected_files
    id_to_temp_id = categorized_files_result.id_to_temp_id
    # Trigger per-file processing immediately for the current tenant
    tenant_id = get_current_tenant_id()
    for rejected_file in rejected_files:
        logger.warning(
            f"File {rejected_file.filename} rejected for {rejected_file.reason}"
        )
    for knowledge_file in knowledge_files:
        task = client_app.send_task(
            OmCeleryTask.PROCESS_SINGLE_USER_FILE,
            kwargs={"knowledge_file_id": knowledge_file.id, "tenant_id": tenant_id},
            queue=OmCeleryQueues.USER_FILE_PROCESSING,
            priority=OmCeleryPriority.HIGH,
        )
        logger.info(
            f"Triggered indexing for knowledge_file_id={knowledge_file.id} with task_id={task.id}"
        )

    return CategorizedFilesResult(
        knowledge_files=knowledge_files,
        rejected_files=rejected_files,
        id_to_temp_id=id_to_temp_id,
    )


def get_owned_workspace(
    workspace_id: int, user_id: UUID | None, db_session: Session
) -> Workspace | None:
    """Return the non-deleted workspace with this id owned by user_id, else None.

    Excludes soft-deleted workspaces (``deleted == True``). In no-auth mode
    (``user_id is None``) the owner filter is skipped.
    """
    query = db_session.query(Workspace).filter(
        Workspace.id == workspace_id,
        Workspace.deleted.is_(False),
    )
    if user_id is not None:
        query = query.filter(Workspace.user_id == user_id)
    return query.one_or_none()


def check_workspace_ownership(
    workspace_id: int, user_id: UUID | None, db_session: Session
) -> bool:
    # In no-auth mode, all (non-deleted) workspaces are accessible
    return get_owned_workspace(workspace_id, user_id, db_session) is not None


def get_knowledge_files_from_workspace(
    workspace_id: int, user_id: UUID | None, db_session: Session
) -> list[KnowledgeFile]:
    # First check if the user owns the workspace
    if not check_workspace_ownership(workspace_id, user_id, db_session):
        return []

    return (
        db_session.query(KnowledgeFile)
        .join(Workspace__KnowledgeFile)
        .filter(Workspace__KnowledgeFile.workspace_id == workspace_id)
        .all()
    )


def get_workspace_instructions(db_session: Session, workspace_id: int | None) -> str | None:
    """Return the workspace's instruction text from the workspace, else None.

    Safe helper that swallows DB errors and returns None on any failure.
    """
    if not workspace_id:
        return None
    try:
        workspace = (
            db_session.query(Workspace)
            .filter(Workspace.id == workspace_id, Workspace.deleted.is_(False))
            .one_or_none()
        )
        if not workspace or not workspace.workspace_instructions:
            return None
        instructions = workspace.workspace_instructions.strip()
        return instructions or None
    except Exception:
        return None


def get_workspace_token_count(
    workspace_id: int | None,
    user_id: UUID | None,
    db_session: Session,
) -> int:
    """Return sum of token_count for all user files in the given workspace.

    If workspace_id is None, returns 0.
    """
    if workspace_id is None:
        return 0

    total_tokens = (
        db_session.query(func.coalesce(func.sum(KnowledgeFile.token_count), 0))
        .filter(
            KnowledgeFile.user_id == user_id,
            KnowledgeFile.workspaces.any(id=workspace_id),
        )
        .scalar()
        or 0
    )

    return int(total_tokens)
