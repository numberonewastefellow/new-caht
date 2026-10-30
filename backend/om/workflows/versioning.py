"""Workflow versions: snapshot definitions and pin runs to them.

Every save records an immutable version (see ``AgentWorkflowVersion``), and
every run records the version it started on, so a paused run resumes against
the exact definition it began with. Versions are content-addressed: saving or
running an unchanged workflow reuses the latest version.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from om.db.models import AgentWorkflow
from om.db.models import AgentWorkflowVersion
from om.db.models import WorkflowExecution
from om.db.workflow_version import get_latest_workflow_version
from om.db.workflow_version import get_workflow_version
from om.db.workflow_version import insert_workflow_version
from om.utils.logger import setup_logger
from om.workflows.graph import graph_from_definition
from om.workflows.graph import graph_from_workflow
from om.workflows.graph import WorkflowGraph
from om.workflows.nodes.registry import NodeTypeRegistry

logger = setup_logger()


def pin_workflow_version(
    db_session: Session,
    workflow: AgentWorkflow,
    graph: WorkflowGraph,
    created_by_id: UUID | None = None,
) -> AgentWorkflowVersion:
    """The version row for ``graph``'s content, recording a new one if it changed.

    Also keeps ``workflow.version`` equal to the latest version number. The
    row is flushed, not committed; the caller owns the transaction.
    """
    content_hash = graph.content_hash()
    latest = get_latest_workflow_version(db_session, workflow.id)
    if latest is not None and latest.content_hash == content_hash:
        return latest

    next_version = latest.version + 1 if latest is not None else 1
    try:
        # Savepoint: a concurrent save/run may record the same version number.
        with db_session.begin_nested():
            row = insert_workflow_version(
                db_session,
                workflow_id=workflow.id,
                version=next_version,
                schema_version=graph.schema_version,
                content_hash=content_hash,
                definition=graph.to_definition(),
                created_by_id=created_by_id,
            )
    except IntegrityError:
        winner = get_latest_workflow_version(db_session, workflow.id)
        if winner is not None and winner.content_hash == content_hash:
            return winner
        raise

    workflow.version = row.version
    logger.info(
        "[Workflow] Recorded version %d of workflow_id=%d (hash=%s)",
        row.version,
        workflow.id,
        content_hash[:12],
    )
    return row


def graph_for_execution(
    db_session: Session,
    execution: WorkflowExecution,
    workflow: AgentWorkflow,
    registry: NodeTypeRegistry,
) -> WorkflowGraph:
    """The definition a run should continue with.

    Runs started before versions existed have no pinned version and continue
    with the workflow's current definition, as before.
    """
    if execution.workflow_version_id is not None:
        row = get_workflow_version(db_session, execution.workflow_version_id)
        if row is not None:
            return graph_from_definition(row.definition)
        logger.warning(
            "[Workflow] Pinned version %s of execution_id=%d is gone; "
            "using the current definition",
            execution.workflow_version_id,
            execution.id,
        )
    return graph_from_workflow(workflow, registry)
