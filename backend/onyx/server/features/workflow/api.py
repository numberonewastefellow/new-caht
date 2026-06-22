"""API endpoints for multi-agent workflow system."""

import json
from collections.abc import Generator
from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from onyx.auth.users import current_admin_user
from onyx.auth.users import current_user
from onyx.chat.emitter import Emitter
from onyx.chat.emitter import get_default_emitter
from onyx.db.engine.sql_engine import get_session
from onyx.db.models import ChatMessage
from onyx.db.models import Persona
from onyx.db.models import User
from onyx.db.workflow import create_or_update_workflow_persona
from onyx.db.workflow import create_workflow
from onyx.db.workflow import delete_workflow
from onyx.db.workflow import get_latest_execution_by_chat_session
from onyx.db.workflow import get_workflow_by_id
from onyx.db.workflow import list_workflow_executions
from onyx.db.workflow import list_workflows
from onyx.db.workflow import update_workflow
from onyx.server.utils import get_json_line
from onyx.utils.logger import setup_logger
from onyx.workflows.models import CONDITION_OPERATORS
from onyx.workflows.trace_models import load_workflow_trace
from onyx.workflows.trace_models import load_workflow_trace_by_message
from onyx.workflows.models import WorkflowCreate
from onyx.workflows.models import WorkflowExecutionResponse
from onyx.workflows.models import WorkflowResponse
from onyx.workflows.models import WorkflowRunRequest
from onyx.workflows.models import WorkflowStepResponse
from onyx.workflows.models import WorkflowUpdate

logger = setup_logger()

router = APIRouter(prefix="/workflow")
admin_router = APIRouter(prefix="/admin/workflow")


# ========================
# Helpers
# ========================


def _workflow_to_response(workflow) -> WorkflowResponse:
    """Convert a DB model to a response schema."""
    steps = []
    for step in sorted(workflow.steps, key=lambda s: s.step_order):
        persona = step.persona
        steps.append(
            WorkflowStepResponse(
                id=step.id,
                workflow_id=step.workflow_id,
                step_type=step.step_type or "agent",
                persona_id=step.persona_id,
                persona_name=persona.name if persona else None,
                step_order=step.step_order,
                step_name=step.step_name,
                step_description=step.step_description,
                input_mapping=step.input_mapping,
                output_key=step.output_key,
                condition=step.condition,
                is_terminal=step.is_terminal,
                can_request_input=step.can_request_input,
                promote_output=step.promote_output,
                llm_provider_override=step.llm_provider_override,
                llm_model_override=step.llm_model_override,
                max_output_tokens_override=step.max_output_tokens_override,
                system_prompt_override=step.system_prompt_override,
                task_prompt_override=step.task_prompt_override,
                tool_ids_override=step.tool_ids_override,
                document_set_ids_override=step.document_set_ids_override,
                replace_base_system_prompt_override=step.replace_base_system_prompt_override,
            )
        )

    return WorkflowResponse(
        id=workflow.id,
        name=workflow.name,
        description=workflow.description,
        user_id=str(workflow.user_id) if workflow.user_id else None,
        orchestration_mode=workflow.orchestration_mode,
        orchestrator_prompt=workflow.orchestrator_prompt,
        orchestrator_llm_provider=workflow.orchestrator_llm_provider,
        orchestrator_llm_model=workflow.orchestrator_llm_model,
        max_steps=workflow.max_steps,
        max_calls_per_agent=workflow.max_calls_per_agent,
        timeout_seconds=workflow.timeout_seconds,
        is_public=workflow.is_public,
        is_visible=workflow.is_visible,
        deleted=workflow.deleted,
        icon_name=workflow.icon_name,
        created_at=workflow.created_at,
        updated_at=workflow.updated_at,
        steps=steps,
    )


# ========================
# Metadata
# ========================


@router.get("/condition-operators")
def get_condition_operators(
    _: User = Depends(current_user),
) -> list[str]:
    """Return the list of valid condition operators for conditional router steps."""
    return CONDITION_OPERATORS


@router.get("/chat-session/{chat_session_id}/trace")
def get_workflow_trace(
    chat_session_id: UUID,
    user: User | None = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> dict:
    """Return the execution trace graph for the latest workflow run in a chat session."""
    execution = get_latest_execution_by_chat_session(db_session, chat_session_id)
    if execution is None:
        raise HTTPException(
            status_code=404, detail="No workflow execution for this chat session"
        )
    if (
        user is not None
        and execution.user_id is not None
        and execution.user_id != user.id
    ):
        raise HTTPException(status_code=403, detail="Not authorized")
    trace = load_workflow_trace(execution.id)
    if trace is None:
        raise HTTPException(
            status_code=404, detail="No trace available for this execution"
        )
    return trace.model_dump()


@router.get("/message/{message_id}/trace")
def get_workflow_trace_by_message(
    message_id: int,
    _: User | None = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> dict:
    """Return the execution trace graph for a specific assistant message.

    Lets the UI show the trace for *that* message's run, even when a chat
    session has multiple workflow runs.
    """
    trace = load_workflow_trace_by_message(message_id)
    if trace is None:
        # Fallback: some pause/resume turns historically did not write a
        # per-message blob. Resolve via the message's chat session → latest
        # execution → execution-keyed trace so the graph still shows.
        chat_session_id = db_session.execute(
            select(ChatMessage.chat_session_id).where(ChatMessage.id == message_id)
        ).scalar_one_or_none()
        if chat_session_id is not None:
            execution = get_latest_execution_by_chat_session(
                db_session, chat_session_id
            )
            if execution is not None:
                trace = load_workflow_trace(execution.id)
    if trace is None:
        raise HTTPException(
            status_code=404, detail="No trace available for this message"
        )
    return trace.model_dump()


# ========================
# CRUD Endpoints (Admin)
# ========================


@admin_router.post("")
def create_workflow_endpoint(
    workflow_data: WorkflowCreate,
    user: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
) -> WorkflowResponse:
    """Create a new multi-agent workflow."""
    # Validate that all referenced personas exist (skip conditional_router steps)
    for step in workflow_data.steps:
        if step.step_type == "conditional_router":
            continue
        persona = db_session.get(Persona, step.persona_id)
        if persona is None or persona.deleted:
            raise HTTPException(
                status_code=400,
                detail=f"Persona with id {step.persona_id} not found or deleted",
            )

    workflow = create_workflow(
        db_session=db_session,
        workflow_create=workflow_data,
        user_id=user.id,
    )

    # Create a wrapper persona so the workflow appears in the agent listing
    create_or_update_workflow_persona(db_session=db_session, workflow=workflow)

    return _workflow_to_response(workflow)


@admin_router.patch("/{workflow_id}")
def update_workflow_endpoint(
    workflow_id: int,
    workflow_data: WorkflowUpdate,
    user: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
) -> WorkflowResponse:
    """Update an existing workflow."""
    # Validate personas if steps are being updated
    if workflow_data.steps is not None:
        for step in workflow_data.steps:
            persona = db_session.get(Persona, step.persona_id)
            if persona is None or persona.deleted:
                raise HTTPException(
                    status_code=400,
                    detail=f"Persona with id {step.persona_id} not found or deleted",
                )

    workflow = update_workflow(
        db_session=db_session,
        workflow_id=workflow_id,
        workflow_update=workflow_data,
    )
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Keep wrapper persona in sync with workflow changes
    create_or_update_workflow_persona(db_session=db_session, workflow=workflow)

    return _workflow_to_response(workflow)


@admin_router.delete("/{workflow_id}")
def delete_workflow_endpoint(
    workflow_id: int,
    user: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
) -> dict:
    """Soft-delete a workflow."""
    success = delete_workflow(db_session=db_session, workflow_id=workflow_id)
    if not success:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {"detail": "Workflow deleted"}


@admin_router.post("/backfill-personas")
def backfill_workflow_personas_endpoint(
    user: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
) -> dict:
    """Create wrapper personas for all existing workflows that don't have one.

    Call this once after upgrading to populate the agent listing with
    previously created workflows.
    """
    workflows = list_workflows(db_session=db_session, user_id=None, include_public=True)
    created = 0
    for workflow in workflows:
        persona = create_or_update_workflow_persona(db_session=db_session, workflow=workflow)
        if persona:
            created += 1
    return {"detail": f"Backfilled {created} workflow persona(s)"}


# ========================
# Read Endpoints (User)
# ========================


@router.get("/{workflow_id}")
def get_workflow_endpoint(
    workflow_id: int,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> WorkflowResponse:
    """Get a workflow by ID."""
    workflow = get_workflow_by_id(db_session=db_session, workflow_id=workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Check access: public or owned by user
    if not workflow.is_public and workflow.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return _workflow_to_response(workflow)


@router.get("")
def list_workflows_endpoint(
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> list[WorkflowResponse]:
    """List all workflows accessible to the user."""
    workflows = list_workflows(
        db_session=db_session,
        user_id=user.id,
        include_public=True,
    )
    return [_workflow_to_response(w) for w in workflows]


# ========================
# Execution Endpoints
# ========================


@router.post("/{workflow_id}/run")
def run_workflow_endpoint(
    workflow_id: int,
    run_request: WorkflowRunRequest,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> StreamingResponse:
    """Execute a workflow with streaming output.

    Returns an SSE stream of workflow packets (step starts, deltas, ends).
    """
    workflow = get_workflow_by_id(db_session=db_session, workflow_id=workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")

    if not workflow.is_public and workflow.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    if not workflow.steps:
        raise HTTPException(
            status_code=400,
            detail="Workflow has no steps configured",
        )

    # Load uploaded files into memory for the code interpreter
    from onyx.file_store.utils import load_chat_file_by_id
    from onyx.tools.models import ChatFile

    chat_files: list[ChatFile] = []
    for fd in run_request.file_descriptors:
        try:
            loaded = load_chat_file_by_id(fd["id"])
            chat_files.append(ChatFile(
                filename=loaded.filename or f"file_{loaded.file_id}",
                content=loaded.content,
            ))
        except Exception as e:
            logger.warning(f"Failed to load workflow file {fd.get('id')}: {e}")

    from onyx.workflows.workflow_engine import run_workflow

    emitter = get_default_emitter()

    def stream_generator() -> Generator[str, None, None]:
        try:
            for packet in run_workflow(
                workflow=workflow,
                user_message=run_request.message,
                emitter=emitter,
                db_session=db_session,
                user=user,
                chat_session_id=run_request.chat_session_id,
                chat_files=chat_files or None,
            ):
                yield get_json_line(packet.model_dump())
        except Exception as e:
            logger.exception("Error in workflow execution streaming")
            yield json.dumps({"error": str(e)})

    return StreamingResponse(stream_generator(), media_type="text/event-stream")


@router.get("/{workflow_id}/executions")
def list_executions_endpoint(
    workflow_id: int,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
    limit: int = 20,
) -> list[WorkflowExecutionResponse]:
    """List recent executions of a workflow."""
    workflow = get_workflow_by_id(db_session=db_session, workflow_id=workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")

    if not workflow.is_public and workflow.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    executions = list_workflow_executions(
        db_session=db_session,
        workflow_id=workflow_id,
        limit=limit,
    )

    return [
        WorkflowExecutionResponse(
            id=ex.id,
            workflow_id=ex.workflow_id,
            chat_session_id=ex.chat_session_id,
            user_id=str(ex.user_id) if ex.user_id else None,
            status=ex.status,
            steps_executed=ex.steps_executed,
            total_tokens=ex.total_tokens,
            total_duration_ms=ex.total_duration_ms,
            error_message=ex.error_message,
            started_at=ex.started_at,
            completed_at=ex.completed_at,
        )
        for ex in executions
    ]
