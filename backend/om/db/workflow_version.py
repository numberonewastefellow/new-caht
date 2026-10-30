"""DB operations for immutable workflow versions (agent_workflow_version)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from om.db.models import AgentWorkflowVersion


def get_latest_workflow_version(
    db_session: Session, workflow_id: int
) -> AgentWorkflowVersion | None:
    return db_session.execute(
        select(AgentWorkflowVersion)
        .where(AgentWorkflowVersion.workflow_id == workflow_id)
        .order_by(AgentWorkflowVersion.version.desc())
        .limit(1)
    ).scalar_one_or_none()


def get_workflow_version(
    db_session: Session, version_id: int
) -> AgentWorkflowVersion | None:
    return db_session.get(AgentWorkflowVersion, version_id)


def get_workflow_version_by_number(
    db_session: Session, workflow_id: int, version: int
) -> AgentWorkflowVersion | None:
    return db_session.execute(
        select(AgentWorkflowVersion)
        .where(AgentWorkflowVersion.workflow_id == workflow_id)
        .where(AgentWorkflowVersion.version == version)
    ).scalar_one_or_none()


def list_workflow_versions(
    db_session: Session, workflow_id: int
) -> list[AgentWorkflowVersion]:
    return list(
        db_session.execute(
            select(AgentWorkflowVersion)
            .where(AgentWorkflowVersion.workflow_id == workflow_id)
            .order_by(AgentWorkflowVersion.version.desc())
        )
        .scalars()
        .all()
    )


def insert_workflow_version(
    db_session: Session,
    *,
    workflow_id: int,
    version: int,
    schema_version: int,
    content_hash: str,
    definition: dict[str, Any],
    created_by_id: UUID | None,
) -> AgentWorkflowVersion:
    """Add a version row (flushed, not committed; the caller owns the transaction)."""
    row = AgentWorkflowVersion(
        workflow_id=workflow_id,
        version=version,
        schema_version=schema_version,
        content_hash=content_hash,
        definition=definition,
        created_by_id=created_by_id,
    )
    db_session.add(row)
    db_session.flush()
    return row
