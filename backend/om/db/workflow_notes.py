"""Sticky notes on a workflow's canvas. None of this touches the workflow's definition or
its version history."""

from uuid import UUID

from sqlalchemy import delete
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.orm import Session

from om.db.models import AgentWorkflow
from om.db.models import AgentWorkflowNote
from om.workflows.note_models import WorkflowNoteCreate
from om.workflows.note_models import WorkflowNoteUpdate

MAX_NOTES_PER_WORKFLOW = 200


class WorkflowNoteError(Exception):
    """The request can't be applied as sent (400)."""


class WorkflowNoteConflictError(Exception):
    """Someone else changed the note since it was loaded (409)."""


def get_workflow_with_steps(db_session: Session, workflow_id: int) -> AgentWorkflow | None:
    """The workflow, unless deleted, with only its steps loaded: all a note needs."""
    return db_session.execute(
        select(AgentWorkflow)
        .where(AgentWorkflow.id == workflow_id)
        .where(AgentWorkflow.deleted.is_(False))
        .options(selectinload(AgentWorkflow.steps))
    ).scalar_one_or_none()


def _check_step_key(workflow: AgentWorkflow, step_node_key: str | None) -> None:
    if step_node_key is None:
        return
    if step_node_key not in {step.node_key for step in workflow.steps}:
        raise WorkflowNoteError(
            "That step isn't saved in this workflow. Save the workflow, then link the note."
        )


def list_workflow_notes(db_session: Session, workflow_id: int) -> list[AgentWorkflowNote]:
    return list(
        db_session.execute(
            select(AgentWorkflowNote)
            .where(AgentWorkflowNote.workflow_id == workflow_id)
            .order_by(AgentWorkflowNote.id)
        ).scalars()
    )


def create_workflow_note(
    db_session: Session,
    workflow: AgentWorkflow,
    note: WorkflowNoteCreate,
    user_id: UUID | None,
) -> AgentWorkflowNote:
    count = db_session.execute(
        select(func.count()).where(AgentWorkflowNote.workflow_id == workflow.id)
    ).scalar_one()
    if count >= MAX_NOTES_PER_WORKFLOW:
        raise WorkflowNoteError(f"A workflow can have at most {MAX_NOTES_PER_WORKFLOW} notes")
    _check_step_key(workflow, note.step_node_key)

    row = AgentWorkflowNote(
        workflow_id=workflow.id,
        **note.model_dump(),
        version=1,
        created_by_id=user_id,
        updated_by_id=user_id,
    )
    db_session.add(row)
    db_session.commit()
    return row


def update_workflow_note(
    db_session: Session,
    workflow: AgentWorkflow,
    note_id: int,
    update: WorkflowNoteUpdate,
    user_id: UUID | None,
) -> AgentWorkflowNote | None:
    """None if the note isn't on this workflow."""
    row = db_session.execute(
        select(AgentWorkflowNote)
        .where(AgentWorkflowNote.id == note_id)
        .where(AgentWorkflowNote.workflow_id == workflow.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).scalar_one_or_none()
    if row is None:
        return None
    if row.version != update.expected_version:
        raise WorkflowNoteConflictError(
            "This note was changed somewhere else. Reload to see the latest text."
        )

    changes = update.model_dump(exclude_unset=True, exclude={"expected_version"})
    # Only a new link is checked: a note keeps a link to a step that was removed later
    if "step_node_key" in changes and changes["step_node_key"] != row.step_node_key:
        _check_step_key(workflow, changes["step_node_key"])
    for field, value in changes.items():
        if value is None and field != "step_node_key":
            continue
        setattr(row, field, value)

    row.version += 1
    row.updated_by_id = user_id
    db_session.commit()
    return row


def delete_workflow_note(db_session: Session, workflow_id: int, note_id: int) -> bool:
    deleted = db_session.execute(
        delete(AgentWorkflowNote)
        .where(AgentWorkflowNote.id == note_id)
        .where(AgentWorkflowNote.workflow_id == workflow_id)
    )
    db_session.commit()
    return deleted.rowcount > 0
