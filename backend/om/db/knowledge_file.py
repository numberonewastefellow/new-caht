import datetime
from uuid import UUID

from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.orm import Session

from om.db.models import KnowledgeFile


def fetch_chunk_counts_for_knowledge_files(
    knowledge_file_ids: list[str],
    db_session: Session,
) -> list[tuple[str, int]]:
    """
    Return a list of (knowledge_file_id, chunk_count) tuples.
    If a knowledge_file_id is not found in the database, it will be returned with a chunk_count of 0.
    """
    stmt = select(KnowledgeFile.id, KnowledgeFile.chunk_count).where(
        KnowledgeFile.id.in_(knowledge_file_ids)
    )

    results = db_session.execute(stmt).all()

    # Create a dictionary of knowledge_file_id to chunk_count
    chunk_counts = {str(row.id): row.chunk_count or 0 for row in results}

    # Return a list of tuples, preserving `None` for documents not found or with
    # an unknown chunk count. Callers should handle the `None` case and fall
    # back to an existence check against the vector DB if necessary.
    return [
        (knowledge_file_id, chunk_counts.get(knowledge_file_id, 0))
        for knowledge_file_id in knowledge_file_ids
    ]


def calculate_knowledge_files_token_count(file_ids: list[UUID], db_session: Session) -> int:
    """Calculate total token count for specified files"""
    total_tokens = 0

    # Get tokens from individual files
    if file_ids:
        file_tokens = (
            db_session.query(func.sum(KnowledgeFile.token_count))
            .filter(KnowledgeFile.id.in_(file_ids))
            .scalar()
            or 0
        )
        total_tokens += file_tokens

    return total_tokens


def fetch_user_workspace_ids_for_knowledge_files(
    knowledge_file_ids: list[str],
    db_session: Session,
) -> dict[str, list[int]]:
    """Fetch user workspace ids for specified user files"""
    stmt = select(KnowledgeFile).where(KnowledgeFile.id.in_(knowledge_file_ids))
    results = db_session.execute(stmt).scalars().all()
    return {
        str(knowledge_file.id): [workspace.id for workspace in knowledge_file.workspaces]
        for knowledge_file in results
    }


def update_last_accessed_at_for_knowledge_files(
    knowledge_file_ids: list[UUID],
    db_session: Session,
) -> None:
    """Update `last_accessed_at` to now (UTC) for the given user files."""
    if not knowledge_file_ids:
        return
    now = datetime.datetime.now(datetime.timezone.utc)
    (
        db_session.query(KnowledgeFile)
        .filter(KnowledgeFile.id.in_(knowledge_file_ids))
        .update({KnowledgeFile.last_accessed_at: now}, synchronize_session=False)
    )
    db_session.commit()


def get_file_id_by_knowledge_file_id(knowledge_file_id: str, db_session: Session) -> str | None:
    knowledge_file = db_session.query(KnowledgeFile).filter(KnowledgeFile.id == knowledge_file_id).first()
    if knowledge_file:
        return knowledge_file.file_id
    return None


def get_file_ids_by_knowledge_file_ids(
    knowledge_file_ids: list[UUID], db_session: Session
) -> list[str]:
    knowledge_files = db_session.query(KnowledgeFile).filter(KnowledgeFile.id.in_(knowledge_file_ids)).all()
    return [knowledge_file.file_id for knowledge_file in knowledge_files]
