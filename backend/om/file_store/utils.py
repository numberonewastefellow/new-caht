import base64
from collections.abc import Callable
from io import BytesIO
from typing import cast
from uuid import UUID

import requests
from sqlalchemy.orm import Session

from om.configs.app_configs import WEB_DOMAIN
from om.configs.constants import FileOrigin
from om.db.models import KnowledgeFile
from om.file_store.file_store import get_default_file_store
from om.file_store.models import ChatFileType
from om.file_store.models import FileDescriptor
from om.file_store.models import InMemoryChatFile
from om.server.query_and_chat.chat_utils import mime_type_to_chat_file_type
from om.utils.b64 import get_image_type
from om.utils.logger import setup_logger
from om.utils.threadpool_concurrency import run_functions_tuples_in_parallel
from om.utils.timing import log_function_time

logger = setup_logger()


def knowledge_file_id_to_plaintext_file_name(knowledge_file_id: UUID) -> str:
    """Generate a consistent file name for storing plaintext content of a user file."""
    return f"plaintext_{knowledge_file_id}"


def store_user_file_plaintext(knowledge_file_id: UUID, plaintext_content: str) -> bool:
    """
    Store plaintext content for a user file in the file store.

    Args:
        knowledge_file_id: The ID of the user file
        plaintext_content: The plaintext content to store

    Returns:
        bool: True if storage was successful, False otherwise
    """
    # Skip empty content
    if not plaintext_content:
        return False

    # Get plaintext file name
    plaintext_file_name = knowledge_file_id_to_plaintext_file_name(knowledge_file_id)

    try:
        file_store = get_default_file_store()
        file_content = BytesIO(plaintext_content.encode("utf-8"))
        file_store.save_file(
            content=file_content,
            display_name=f"Plaintext for user file {knowledge_file_id}",
            file_origin=FileOrigin.PLAINTEXT_CACHE,
            file_type="text/plain",
            file_id=plaintext_file_name,
        )
        return True
    except Exception as e:
        logger.warning(f"Failed to store plaintext for user file {knowledge_file_id}: {e}")
        return False


def load_chat_file_by_id(file_id: str) -> InMemoryChatFile:
    """Load a file directly from the file store using its file_record ID.

    This is the fallback path for chat-attached files that don't have a
    corresponding row in the ``knowledge_file`` table."""
    file_store = get_default_file_store()
    file_record = file_store.read_file_record(file_id)
    chat_file_type = mime_type_to_chat_file_type(file_record.file_type)

    file_io = file_store.read_file(file_id, mode="b")
    return InMemoryChatFile(
        file_id=file_id,
        content=file_io.read(),
        file_type=chat_file_type,
        filename=file_record.display_name,
    )


def load_user_file(file_id: UUID, db_session: Session) -> InMemoryChatFile:
    status = "not_loaded"

    knowledge_file = db_session.query(KnowledgeFile).filter(KnowledgeFile.id == file_id).first()
    if not knowledge_file:
        raise ValueError(f"User file with id {file_id} not found")

    # Get the file record to determine the appropriate chat file type
    file_store = get_default_file_store()
    file_record = file_store.read_file_record(knowledge_file.file_id)

    # Determine appropriate chat file type based on the original file's MIME type
    chat_file_type = mime_type_to_chat_file_type(file_record.file_type)

    # Try to load plaintext version first
    plaintext_file_name = knowledge_file_id_to_plaintext_file_name(file_id)

    # check for plain text normalized version first, then use original file otherwise
    try:
        file_io = file_store.read_file(plaintext_file_name, mode="b")
        # For plaintext versions, use PLAIN_TEXT type (unless it's an image which doesn't have plaintext)
        plaintext_chat_file_type = (
            ChatFileType.PLAIN_TEXT
            if chat_file_type != ChatFileType.IMAGE
            else chat_file_type
        )

        # if we have plaintext for image (which happens when image extraction is enabled), we use PLAIN_TEXT type
        if file_io is not None:
            plaintext_chat_file_type = ChatFileType.PLAIN_TEXT

        chat_file = InMemoryChatFile(
            file_id=str(knowledge_file.file_id),
            content=file_io.read(),
            file_type=plaintext_chat_file_type,
            filename=knowledge_file.name,
        )
        status = "plaintext"
        return chat_file
    except Exception as e:
        logger.warning(f"Failed to load plaintext for user file {knowledge_file.id}: {e}")
        # Fall back to original file if plaintext not available
        file_io = file_store.read_file(knowledge_file.file_id, mode="b")

        chat_file = InMemoryChatFile(
            file_id=str(knowledge_file.file_id),
            content=file_io.read(),
            file_type=chat_file_type,
            filename=knowledge_file.name,
        )
        status = "original"
        return chat_file
    finally:
        logger.debug(
            f"load_user_file finished: file_id={knowledge_file.file_id} "
            f"chat_file_type={chat_file_type} "
            f"status={status}"
        )


def load_in_memory_chat_files(
    knowledge_file_ids: list[UUID],
    db_session: Session,
) -> list[InMemoryChatFile]:
    """
    Loads the actual content of user files specified by individual IDs and those
    within specified workspace IDs into memory.

    Args:
        knowledge_file_ids: A list of specific KnowledgeFile IDs to load.
        db_session: The SQLAlchemy database session.

    Returns:
        A list of InMemoryChatFile objects, each containing the file content (as bytes),
        file ID, file type, and filename. Prioritizes loading plaintext versions if available.
    """
    # Use parallel execution to load files concurrently
    return cast(
        list[InMemoryChatFile],
        run_functions_tuples_in_parallel(
            # 1. Load files specified by individual IDs
            [(load_user_file, (file_id, db_session)) for file_id in knowledge_file_ids]
        ),
    )


def get_knowledge_files(
    knowledge_file_ids: list[UUID],
    db_session: Session,
) -> list[KnowledgeFile]:
    """
    Fetches KnowledgeFile database records based on provided file and workspace IDs.

    Args:
        knowledge_file_ids: A list of specific KnowledgeFile IDs to fetch.
        db_session: The SQLAlchemy database session.

    Returns:
        A list containing KnowledgeFile SQLAlchemy model objects corresponding to the
        specified file IDs and all files within the specified workspace IDs.
        It does NOT return the actual file content.
    """
    knowledge_files: list[KnowledgeFile] = []

    # 1. Fetch KnowledgeFile records for specific file IDs
    for knowledge_file_id in knowledge_file_ids:
        # Query the database for a KnowledgeFile with the matching ID
        knowledge_file = (
            db_session.query(KnowledgeFile).filter(KnowledgeFile.id == knowledge_file_id).first()
        )
        # If found, add it to the list
        if knowledge_file is not None:
            knowledge_files.append(knowledge_file)

    # 3. Return the combined list of KnowledgeFile database objects
    return knowledge_files


def validate_knowledge_files_ownership(
    knowledge_file_ids: list[UUID],
    user_id: UUID | None,
    db_session: Session,
) -> list[KnowledgeFile]:
    """
    Fetches all KnowledgeFile database records for a given user.
    """
    knowledge_files = get_knowledge_files(knowledge_file_ids, db_session)
    current_knowledge_files = []
    for knowledge_file in knowledge_files:
        # Note: if user_id is None, then all files should be None as well
        # (since auth must be disabled in this case)
        if knowledge_file.user_id != user_id:
            raise ValueError(
                f"User {user_id} does not have access to file {knowledge_file.id}"
            )
        current_knowledge_files.append(knowledge_file)

    return current_knowledge_files


def save_file_from_url(url: str) -> str:
    response = requests.get(url)
    response.raise_for_status()

    file_io = BytesIO(response.content)
    file_store = get_default_file_store()
    file_id = file_store.save_file(
        content=file_io,
        display_name="GeneratedImage",
        file_origin=FileOrigin.CHAT_IMAGE_GEN,
        file_type="image/png;base64",
    )
    return file_id


def save_file_from_base64(base64_string: str) -> str:
    file_store = get_default_file_store()
    file_id = file_store.save_file(
        content=BytesIO(base64.b64decode(base64_string)),
        display_name="GeneratedImage",
        file_origin=FileOrigin.CHAT_IMAGE_GEN,
        file_type=get_image_type(base64_string),
    )
    return file_id


def save_file(
    url: str | None = None,
    base64_data: str | None = None,
) -> str:
    """Save a file from either a URL or base64 encoded string.

    Args:
        url: URL to download file from
        base64_data: Base64 encoded file data

    Returns:
        The unique ID of the saved file

    Raises:
        ValueError: If neither url nor base64_data is provided, or if both are provided
    """
    if url is not None and base64_data is not None:
        raise ValueError("Cannot specify both url and base64_data")

    if url is not None:
        return save_file_from_url(url)
    elif base64_data is not None:
        return save_file_from_base64(base64_data)
    else:
        raise ValueError("Must specify either url or base64_data")


def save_files(urls: list[str], base64_files: list[str]) -> list[str]:
    # NOTE: be explicit about typing so that if we change things, we get notified
    funcs: list[
        tuple[
            Callable[[str | None, str | None], str],
            tuple[str | None, str | None],
        ]
    ] = [(save_file, (url, None)) for url in urls] + [
        (save_file, (None, base64_file)) for base64_file in base64_files
    ]

    return run_functions_tuples_in_parallel(funcs)


@log_function_time(print_only=True)
def verify_knowledge_files(
    knowledge_files: list[FileDescriptor],
    user_id: UUID | None,
    db_session: Session,
    workspace_id: int | None = None,
) -> None:
    """
    Verify that all provided file descriptors belong to the specified user.
    For workspace files (those without knowledge_file_id), verifies access through workspace ownership.

    Args:
        knowledge_files: List of file descriptors to verify
        user_id: The user ID to check ownership against
        db_session: The SQLAlchemy database session
        workspace_id: Optional workspace ID to verify workspace file access against

    Raises:
        ValueError: If any file does not belong to the user or is not found
    """
    from om.db.models import Workspace__KnowledgeFile
    from om.db.workspaces import check_workspace_ownership

    # Extract knowledge_file_ids and workspace file_ids from the file descriptors
    knowledge_file_ids = []
    workspace_file_ids = []

    for file_descriptor in knowledge_files:
        # Check if this file descriptor has a knowledge_file_id
        if file_descriptor.get("knowledge_file_id"):
            try:
                knowledge_file_ids.append(UUID(file_descriptor["knowledge_file_id"]))
            except (ValueError, TypeError):
                logger.warning(
                    f"Invalid knowledge_file_id in file descriptor: {file_descriptor['knowledge_file_id']}"
                )
                continue
        else:
            # This is a workspace file - use the 'id' field which is the file_id
            if file_descriptor.get("id"):
                workspace_file_ids.append(file_descriptor["id"])

    # Verify user files (existing logic)
    if knowledge_file_ids:
        validate_knowledge_files_ownership(knowledge_file_ids, user_id, db_session)

    # Verify workspace files
    if workspace_file_ids:
        if workspace_id is None:
            raise ValueError(
                "Workspace files provided but no workspace_id specified for verification"
            )

        # Verify user owns the workspace
        if not check_workspace_ownership(workspace_id, user_id, db_session):
            raise ValueError(
                f"User {user_id} does not have access to workspace {workspace_id}"
            )

        # Verify all workspace files belong to the specified workspace
        knowledge_files_in_workspace = (
            db_session.query(KnowledgeFile)
            .join(Workspace__KnowledgeFile)
            .filter(
                Workspace__KnowledgeFile.workspace_id == workspace_id,
                KnowledgeFile.file_id.in_(workspace_file_ids),
            )
            .all()
        )

        # Check if all files were found in the workspace
        found_file_ids = {uf.file_id for uf in knowledge_files_in_workspace}
        missing_files = set(workspace_file_ids) - found_file_ids

        if missing_files:
            raise ValueError(
                f"Files {missing_files} are not associated with workspace {workspace_id}"
            )


def build_frontend_file_url(file_id: str) -> str:
    return f"/api/converse/file/{file_id}"


def build_full_frontend_file_url(file_id: str) -> str:
    return f"{WEB_DOMAIN}/api/converse/file/{file_id}"
