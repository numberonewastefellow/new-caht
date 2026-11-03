"""Sticky notes on the workflow canvas. Anyone who can see a workflow can read its notes;
the admins who can edit workflows can change them."""

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from sqlalchemy.orm import Session

from om.auth.users import current_admin_user
from om.auth.users import current_user
from om.db.engine.sql_engine import get_session
from om.db.models import AgentWorkflow
from om.db.models import User
from om.db.workflow_notes import create_workflow_note
from om.db.workflow_notes import delete_workflow_note
from om.db.workflow_notes import get_workflow_with_steps
from om.db.workflow_notes import list_workflow_notes
from om.db.workflow_notes import update_workflow_note
from om.db.workflow_notes import WorkflowNoteConflictError
from om.db.workflow_notes import WorkflowNoteError
from om.workflows.note_models import WorkflowNoteCreate
from om.workflows.note_models import WorkflowNoteResponse
from om.workflows.note_models import WorkflowNoteUpdate

router = APIRouter(prefix="/workflow")
admin_router = APIRouter(prefix="/admin/workflow")


def _workflow_or_404(db_session: Session, workflow_id: int) -> AgentWorkflow:
    workflow = get_workflow_with_steps(db_session, workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow


@router.get("/{workflow_id}/notes")
def list_notes(
    workflow_id: int,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> list[WorkflowNoteResponse]:
    workflow = _workflow_or_404(db_session, workflow_id)
    # The same rule as reading the workflow itself
    if not workflow.is_public and workflow.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return [WorkflowNoteResponse.model_validate(n) for n in list_workflow_notes(db_session, workflow_id)]


@admin_router.post("/{workflow_id}/notes")
def create_note(
    workflow_id: int,
    note: WorkflowNoteCreate,
    user: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
) -> WorkflowNoteResponse:
    workflow = _workflow_or_404(db_session, workflow_id)
    try:
        return WorkflowNoteResponse.model_validate(
            create_workflow_note(db_session, workflow, note, user.id)
        )
    except WorkflowNoteError as e:
        raise HTTPException(status_code=400, detail=str(e))


@admin_router.patch("/{workflow_id}/notes/{note_id}")
def update_note(
    workflow_id: int,
    note_id: int,
    update: WorkflowNoteUpdate,
    user: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
) -> WorkflowNoteResponse:
    workflow = _workflow_or_404(db_session, workflow_id)
    try:
        row = update_workflow_note(db_session, workflow, note_id, update, user.id)
    except WorkflowNoteError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except WorkflowNoteConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if row is None:
        raise HTTPException(status_code=404, detail="Note not found")
    return WorkflowNoteResponse.model_validate(row)


@admin_router.delete("/{workflow_id}/notes/{note_id}")
def delete_note(
    workflow_id: int,
    note_id: int,
    _: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
) -> dict:
    _workflow_or_404(db_session, workflow_id)
    if not delete_workflow_note(db_session, workflow_id, note_id):
        raise HTTPException(status_code=404, detail="Note not found")
    return {"detail": "Note deleted"}
