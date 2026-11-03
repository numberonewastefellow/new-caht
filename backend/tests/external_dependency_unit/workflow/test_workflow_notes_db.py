"""Sticky notes on a workflow, against a real Postgres.

Notes are documentation: saving one must never touch the workflow's definition or its
version history.

Requires Postgres with the notes migration applied. No LLM calls.
"""

from collections.abc import Generator

import pytest
from sqlalchemy import delete
from sqlalchemy import select
from sqlalchemy.orm import Session

from om.db.models import AgentWorkflow
from om.db.models import AgentWorkflowNote
from om.db.workflow import get_workflow_by_id
from om.db.workflow_notes import create_workflow_note
from om.db.workflow_notes import delete_workflow_note
from om.db.workflow_notes import list_workflow_notes
from om.db.workflow_notes import MAX_NOTES_PER_WORKFLOW
from om.db.workflow_notes import update_workflow_note
from om.db.workflow_notes import WorkflowNoteConflictError
from om.db.workflow_notes import WorkflowNoteError
from om.db.workflow_version import list_workflow_versions
from om.workflows.models import WorkflowCreate
from om.workflows.models import WorkflowStepCreate
from om.workflows.models import WorkflowUpdate
from om.workflows.note_models import WorkflowNoteCreate
from om.workflows.note_models import WorkflowNoteUpdate
from om.workflows.saving import restore_workflow_version
from om.workflows.saving import save_new_workflow
from om.workflows.saving import save_workflow_update

CODE = "def main(inputs):\n    return {'r': 'ok'}\n"


def _code_step(order: int, name: str) -> WorkflowStepCreate:
    return WorkflowStepCreate(
        step_type="code",
        step_order=order,
        step_name=name,
        output_key=f"out_{order}",
        is_terminal=order == 1,
        config={"code": CODE, "inputs": {}, "outputs": [{"name": "r", "type": "string"}], "timeout_seconds": 5},
    )


@pytest.fixture
def workflow(db_session: Session) -> Generator[AgentWorkflow, None, None]:
    created = save_new_workflow(
        db_session,
        WorkflowCreate(
            name="notes-db-test",
            orchestration_mode="sequential",
            steps=[_code_step(0, "First"), _code_step(1, "Second")],
        ),
        user_id=None,
    )
    db_session.commit()
    yield created
    db_session.rollback()
    db_session.execute(delete(AgentWorkflow).where(AgentWorkflow.id == created.id))
    db_session.commit()


def _key(workflow: AgentWorkflow, name: str) -> str:
    return next(s.node_key for s in workflow.steps if s.step_name == name)


def test_create_read_update_delete(db_session: Session, workflow: AgentWorkflow) -> None:
    note = create_workflow_note(
        db_session, workflow, WorkflowNoteCreate(x=40, y=60, text="**Reads** the FIR"), user_id=None
    )
    assert note.version == 1 and note.color == "yellow"
    assert [n.id for n in list_workflow_notes(db_session, workflow.id)] == [note.id]

    updated = update_workflow_note(
        db_session, workflow, note.id, WorkflowNoteUpdate(expected_version=1, text="changed", color="blue"), user_id=None
    )
    assert updated is not None
    assert (updated.text, updated.color, updated.version) == ("changed", "blue", 2)

    assert delete_workflow_note(db_session, workflow.id, note.id) is True
    assert list_workflow_notes(db_session, workflow.id) == []
    assert delete_workflow_note(db_session, workflow.id, note.id) is False


def test_a_stale_edit_is_refused(db_session: Session, workflow: AgentWorkflow) -> None:
    note = create_workflow_note(db_session, workflow, WorkflowNoteCreate(x=0, y=0), user_id=None)
    update_workflow_note(db_session, workflow, note.id, WorkflowNoteUpdate(expected_version=1, text="a"), user_id=None)
    with pytest.raises(WorkflowNoteConflictError):
        update_workflow_note(db_session, workflow, note.id, WorkflowNoteUpdate(expected_version=1, text="b"), user_id=None)
    assert list_workflow_notes(db_session, workflow.id)[0].text == "a"


def test_notes_never_touch_the_workflow_or_its_versions(db_session: Session, workflow: AgentWorkflow) -> None:
    version_before = workflow.version
    history_before = len(list_workflow_versions(db_session, workflow.id))

    note = create_workflow_note(db_session, workflow, WorkflowNoteCreate(x=0, y=0), user_id=None)
    for i in range(3):
        update_workflow_note(
            db_session, workflow, note.id, WorkflowNoteUpdate(expected_version=i + 1, text=f"v{i}"), user_id=None
        )
    delete_workflow_note(db_session, workflow.id, note.id)

    reloaded = get_workflow_by_id(db_session, workflow.id)
    assert reloaded is not None and reloaded.version == version_before
    assert len(list_workflow_versions(db_session, workflow.id)) == history_before


def test_linking_only_to_a_step_of_this_workflow(db_session: Session, workflow: AgentWorkflow) -> None:
    key = _key(workflow, "First")
    note = create_workflow_note(db_session, workflow, WorkflowNoteCreate(x=5, y=5, step_node_key=key), user_id=None)
    assert note.step_node_key == key

    with pytest.raises(WorkflowNoteError):
        create_workflow_note(db_session, workflow, WorkflowNoteCreate(x=0, y=0, step_node_key="n_nothere"), user_id=None)
    with pytest.raises(WorkflowNoteError):
        update_workflow_note(
            db_session, workflow, note.id, WorkflowNoteUpdate(expected_version=1, step_node_key="n_nothere"), user_id=None
        )

    unlinked = update_workflow_note(
        db_session, workflow, note.id, WorkflowNoteUpdate(expected_version=1, step_node_key=None), user_id=None
    )
    assert unlinked is not None and unlinked.step_node_key is None


def test_a_note_survives_its_step_being_removed(db_session: Session, workflow: AgentWorkflow) -> None:
    key = _key(workflow, "Second")
    note = create_workflow_note(db_session, workflow, WorkflowNoteCreate(x=0, y=0, step_node_key=key), user_id=None)

    first = next(s for s in workflow.steps if s.step_name == "First")
    only_first = WorkflowStepCreate(**{**_code_step(0, "First").model_dump(), "node_key": first.node_key, "is_terminal": True})
    save_workflow_update(db_session, workflow.id, WorkflowUpdate(steps=[only_first]), user_id=None)

    kept = list_workflow_notes(db_session, workflow.id)
    assert [(n.id, n.step_node_key) for n in kept] == [(note.id, key)]
    # Still editable while its step is gone, as long as the link isn't changed
    reloaded = get_workflow_by_id(db_session, workflow.id)
    assert reloaded is not None
    edited = update_workflow_note(
        db_session, reloaded, note.id, WorkflowNoteUpdate(expected_version=1, text="step went away"), user_id=None
    )
    assert edited is not None and edited.text == "step went away"


def test_restoring_an_old_version_keeps_the_notes(db_session: Session, workflow: AgentWorkflow) -> None:
    note = create_workflow_note(db_session, workflow, WorkflowNoteCreate(x=0, y=0, text="keep me"), user_id=None)
    save_workflow_update(db_session, workflow.id, WorkflowUpdate(name="renamed"), user_id=None)
    restore_workflow_version(db_session, workflow.id, 1, user_id=None)
    assert [n.text for n in list_workflow_notes(db_session, workflow.id)] == ["keep me"]
    assert note.id == list_workflow_notes(db_session, workflow.id)[0].id


def test_notes_go_when_the_workflow_is_deleted(db_session: Session, workflow: AgentWorkflow) -> None:
    create_workflow_note(db_session, workflow, WorkflowNoteCreate(x=0, y=0), user_id=None)
    workflow_id = workflow.id
    db_session.execute(delete(AgentWorkflow).where(AgentWorkflow.id == workflow_id))
    db_session.commit()
    remaining = db_session.execute(select(AgentWorkflowNote).where(AgentWorkflowNote.workflow_id == workflow_id))
    assert remaining.scalars().all() == []


def test_a_workflow_has_a_note_limit(db_session: Session, workflow: AgentWorkflow, monkeypatch: pytest.MonkeyPatch) -> None:
    import om.db.workflow_notes as notes_module

    monkeypatch.setattr(notes_module, "MAX_NOTES_PER_WORKFLOW", 2)
    for _ in range(2):
        create_workflow_note(db_session, workflow, WorkflowNoteCreate(x=0, y=0), user_id=None)
    with pytest.raises(WorkflowNoteError):
        create_workflow_note(db_session, workflow, WorkflowNoteCreate(x=0, y=0), user_id=None)
    assert MAX_NOTES_PER_WORKFLOW >= 100
