"""API endpoints for multi-agent workflow system."""

import json
from collections.abc import Generator
from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from om.auth.users import current_admin_user
from om.auth.users import current_user
from om.chat.emitter import Emitter
from om.chat.emitter import get_default_emitter
from om.db.engine.sql_engine import get_session
from om.db.models import AgentWorkflow
from om.db.models import AgentWorkflowVersion
from om.db.models import ChatMessage
from om.db.models import User
from om.db.workflow import create_or_update_workflow_agent
from om.db.workflow import delete_workflow
from om.db.workflow import get_latest_execution_by_chat_session
from om.db.workflow import get_workflow_by_id
from om.db.workflow import list_workflow_executions
from om.db.workflow import list_workflows
from om.db.workflow_version import get_workflow_version_by_number
from om.db.workflow_version import list_workflow_versions
from om.server.utils import get_json_line
from om.utils.logger import setup_logger
from om.workflows.models import CONDITION_OPERATORS
from om.workflows.trace_models import load_workflow_trace
from om.workflows.trace_models import load_workflow_trace_by_message
from om.workflows.models import NodeUpgradeRequest
from om.workflows.models import WorkflowCreate
from om.workflows.models import WorkflowExecutionResponse
from om.workflows.models import WorkflowResponse
from om.workflows.models import WorkflowRunRequest
from om.workflows.models import WorkflowStepResponse
from om.workflows.models import WorkflowUpdate
from om.workflows.models import WorkflowVersionDetail
from om.workflows.models import WorkflowVersionSummary
from om.workflows.nodes.base import UpgradeContext
from om.workflows.nodes.builtin import get_node_registry
from om.workflows.nodes.registry import NodeTypeInfo
from om.workflows.nodes.registry import NodeUpgradeError
from om.workflows.nodes.registry import NodeUpgradeResult
from om.workflows.nodes.registry import UnknownNodeTypeError
from om.workflows.saving import restore_workflow_version
from om.workflows.saving import save_new_workflow
from om.workflows.saving import save_workflow_update
from om.workflows.saving import WorkflowSaveError
from om.workflows.saving import WorkflowVersionConflictError

logger = setup_logger()

router = APIRouter(prefix="/workflow")
admin_router = APIRouter(prefix="/admin/workflow")


# ========================
# Helpers
# ========================


def _workflow_to_response(workflow: AgentWorkflow) -> WorkflowResponse:
    """Convert a DB model to a response schema."""
    registry = get_node_registry()
    key_by_step_id = {s.id: s.node_key for s in workflow.steps}
    steps = []
    for step in sorted(workflow.steps, key=lambda s: s.step_order):
        agent = step.agent
        step_type = step.step_type or "agent"
        type_version = step.type_version or 1
        latest_version = (
            registry.latest(step_type).version
            if step_type in registry.types()
            else type_version
        )
        steps.append(
            WorkflowStepResponse(
                id=step.id,
                workflow_id=step.workflow_id,
                node_key=step.node_key,
                step_type=step_type,
                type_version=type_version,
                latest_type_version=latest_version,
                upgrade_available=latest_version > type_version,
                config=step.config,
                parent_key=(
                    key_by_step_id.get(step.parent_step_id)
                    if step.parent_step_id is not None
                    else None
                ),
                branch_index=step.branch_index,
                agent_id=step.agent_id,
                agent_name=agent.name if agent else None,
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
        version=workflow.version,
        schema_version=workflow.schema_version,
        created_at=workflow.created_at,
        updated_at=workflow.updated_at,
        steps=steps,
    )


def _get_accessible_workflow(
    db_session: Session, workflow_id: int, user: User
) -> AgentWorkflow:
    workflow = get_workflow_by_id(db_session=db_session, workflow_id=workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if not workflow.is_public and workflow.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return workflow


def _version_summary(row: AgentWorkflowVersion) -> WorkflowVersionSummary:
    return WorkflowVersionSummary(
        version=row.version,
        schema_version=row.schema_version,
        content_hash=row.content_hash,
        created_by_id=row.created_by_id,
        created_at=row.created_at,
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


# Declared before "/{workflow_id}" so the path is not captured by it.
@router.get("/node-types")
def get_node_types(
    _: User = Depends(current_user),
) -> list[NodeTypeInfo]:
    """The node type catalog: every type, version, config schema and capability.

    The editors build their palettes and config forms from this.
    """
    return get_node_registry().catalog()


@router.post("/node-types/{node_type}/upgrade")
def upgrade_node_config(
    node_type: str,
    request: NodeUpgradeRequest,
    _: User = Depends(current_user),
) -> NodeUpgradeResult:
    """Convert a node's config to the latest version of its type (no save).

    The editor shows the result as a diff; the upgrade only takes effect when
    the workflow is saved. Returns 409 when the upgrade is a breaking change.
    """
    try:
        return get_node_registry().upgrade_config(
            node_type,
            request.from_version,
            request.config,
            context=UpgradeContext(
                step_order_to_node_key=request.step_order_to_node_key
            ),
        )
    except UnknownNodeTypeError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except NodeUpgradeError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.errors()[0]["msg"])


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
    """Create a new multi-agent workflow (records version 1)."""
    try:
        workflow = save_new_workflow(db_session, workflow_data, user_id=user.id)
    except WorkflowSaveError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return _workflow_to_response(workflow)


@admin_router.patch("/{workflow_id}")
def update_workflow_endpoint(
    workflow_id: int,
    workflow_data: WorkflowUpdate,
    user: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
) -> WorkflowResponse:
    """Update an existing workflow (records a new version if content changed).

    Send each step's ``node_key`` back unchanged so it keeps its identity; send
    ``expected_version`` to be told (409) when someone else saved in between.
    """
    try:
        workflow = save_workflow_update(
            db_session, workflow_id, workflow_data, user_id=user.id
        )
    except WorkflowSaveError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except WorkflowVersionConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Keep wrapper agent in sync with workflow changes
    create_or_update_workflow_agent(db_session=db_session, workflow=workflow)

    return _workflow_to_response(workflow)


@admin_router.post("/{workflow_id}/versions/{version}/restore")
def restore_workflow_version_endpoint(
    workflow_id: int,
    version: int,
    user: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
) -> WorkflowResponse:
    """Make an earlier version current again (saved as a new version)."""
    try:
        workflow = restore_workflow_version(
            db_session, workflow_id, version, user_id=user.id
        )
    except WorkflowSaveError as e:
        # e.g. an agent used by that version has since been deleted
        raise HTTPException(status_code=400, detail=str(e))
    except WorkflowVersionConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow or version not found")
    create_or_update_workflow_agent(db_session=db_session, workflow=workflow)
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


@admin_router.post("/backfill-agents")
def backfill_workflow_agents_endpoint(
    user: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
) -> dict:
    """Create wrapper agents for all existing workflows that don't have one.

    Call this once after upgrading to populate the agent listing with
    previously created workflows.
    """
    workflows = list_workflows(db_session=db_session, user_id=None, include_public=True)
    created = 0
    for workflow in workflows:
        agent = create_or_update_workflow_agent(db_session=db_session, workflow=workflow)
        if agent:
            created += 1
    return {"detail": f"Backfilled {created} workflow agent(s)"}


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
    return _workflow_to_response(
        _get_accessible_workflow(db_session, workflow_id, user)
    )


@router.get("/{workflow_id}/versions")
def list_workflow_versions_endpoint(
    workflow_id: int,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> list[WorkflowVersionSummary]:
    """Version history, newest first."""
    _get_accessible_workflow(db_session, workflow_id, user)
    return [_version_summary(v) for v in list_workflow_versions(db_session, workflow_id)]


@router.get("/{workflow_id}/versions/{version}")
def get_workflow_version_endpoint(
    workflow_id: int,
    version: int,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> WorkflowVersionDetail:
    """One version with its full definition (for viewing and diffs)."""
    _get_accessible_workflow(db_session, workflow_id, user)
    row = get_workflow_version_by_number(db_session, workflow_id, version)
    if row is None:
        raise HTTPException(status_code=404, detail="Version not found")
    return WorkflowVersionDetail(
        **_version_summary(row).model_dump(), definition=row.definition
    )


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
    from om.file_store.utils import load_chat_file_by_id
    from om.tools.models import ChatFile

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

    from om.workflows.workflow_engine import run_workflow

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
