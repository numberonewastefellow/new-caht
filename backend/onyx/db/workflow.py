"""DB CRUD operations for multi-agent workflows."""

import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm import selectinload

from onyx.configs.chat_configs import CONTEXT_CHUNKS_ABOVE
from onyx.configs.chat_configs import CONTEXT_CHUNKS_BELOW
from onyx.context.search.enums import RecencyBiasSetting
from onyx.db.models import AgentWorkflow
from onyx.db.models import AgentWorkflowStep
from onyx.db.models import Persona
from onyx.db.models import PersonaLabel
from onyx.db.models import WorkflowExecution
from onyx.utils.logger import setup_logger
from onyx.workflows.models import WorkflowCheckpoint
from onyx.workflows.models import WorkflowCreate
from onyx.workflows.models import WorkflowStepCreate
from onyx.workflows.models import WorkflowUpdate

logger = setup_logger()


# ========================
# Workflow CRUD
# ========================


def create_workflow(
    db_session: Session,
    workflow_create: WorkflowCreate,
    user_id: UUID | None = None,
) -> AgentWorkflow:
    workflow = AgentWorkflow(
        name=workflow_create.name,
        description=workflow_create.description,
        user_id=user_id,
        orchestration_mode=workflow_create.orchestration_mode,
        orchestrator_prompt=workflow_create.orchestrator_prompt,
        orchestrator_llm_provider=workflow_create.orchestrator_llm_provider,
        orchestrator_llm_model=workflow_create.orchestrator_llm_model,
        max_steps=workflow_create.max_steps,
        max_calls_per_agent=workflow_create.max_calls_per_agent,
        timeout_seconds=workflow_create.timeout_seconds,
        is_public=workflow_create.is_public,
        icon_name=workflow_create.icon_name,
    )
    db_session.add(workflow)
    db_session.flush()

    for step_create in workflow_create.steps:
        _add_step(db_session, workflow.id, step_create)

    db_session.commit()
    return workflow


def get_workflow_by_id(
    db_session: Session,
    workflow_id: int,
) -> AgentWorkflow | None:
    return db_session.execute(
        select(AgentWorkflow)
        .where(AgentWorkflow.id == workflow_id)
        .where(AgentWorkflow.deleted.is_(False))
        .options(
            selectinload(AgentWorkflow.steps)
            .selectinload(AgentWorkflowStep.persona)
            .selectinload(Persona.tools)
        )
    ).scalar_one_or_none()


def list_workflows(
    db_session: Session,
    user_id: UUID | None = None,
    include_public: bool = True,
) -> list[AgentWorkflow]:
    query = (
        select(AgentWorkflow)
        .where(AgentWorkflow.deleted.is_(False))
        .where(AgentWorkflow.is_visible.is_(True))
        .options(
            selectinload(AgentWorkflow.steps)
            .selectinload(AgentWorkflowStep.persona)
            .selectinload(Persona.tools)
        )
        .order_by(AgentWorkflow.created_at.desc())
    )

    if user_id and include_public:
        query = query.where(
            (AgentWorkflow.user_id == user_id) | (AgentWorkflow.is_public.is_(True))
        )
    elif user_id:
        query = query.where(AgentWorkflow.user_id == user_id)

    return list(db_session.execute(query).scalars().all())


def update_workflow(
    db_session: Session,
    workflow_id: int,
    workflow_update: WorkflowUpdate,
) -> AgentWorkflow | None:
    workflow = get_workflow_by_id(db_session, workflow_id)
    if workflow is None:
        return None

    if workflow_update.name is not None:
        workflow.name = workflow_update.name
    if workflow_update.description is not None:
        workflow.description = workflow_update.description
    if workflow_update.orchestration_mode is not None:
        workflow.orchestration_mode = workflow_update.orchestration_mode
    if workflow_update.orchestrator_prompt is not None:
        workflow.orchestrator_prompt = workflow_update.orchestrator_prompt
    if workflow_update.orchestrator_llm_provider is not None:
        workflow.orchestrator_llm_provider = workflow_update.orchestrator_llm_provider
    if workflow_update.orchestrator_llm_model is not None:
        workflow.orchestrator_llm_model = workflow_update.orchestrator_llm_model
    if workflow_update.max_steps is not None:
        workflow.max_steps = workflow_update.max_steps
    if workflow_update.max_calls_per_agent is not None:
        workflow.max_calls_per_agent = workflow_update.max_calls_per_agent
    if workflow_update.timeout_seconds is not None:
        workflow.timeout_seconds = workflow_update.timeout_seconds
    if workflow_update.is_public is not None:
        workflow.is_public = workflow_update.is_public
    if workflow_update.icon_name is not None:
        workflow.icon_name = workflow_update.icon_name

    # Replace steps if provided
    if workflow_update.steps is not None:
        # Delete existing steps
        for step in workflow.steps:
            db_session.delete(step)
        db_session.flush()

        # Add new steps
        for step_create in workflow_update.steps:
            _add_step(db_session, workflow.id, step_create)

    db_session.commit()
    return workflow


def delete_workflow(
    db_session: Session,
    workflow_id: int,
) -> bool:
    workflow = get_workflow_by_id(db_session, workflow_id)
    if workflow is None:
        return False

    workflow.deleted = True

    # Also soft-delete the wrapper persona
    wrapper_persona = _get_workflow_persona(db_session, workflow_id)
    if wrapper_persona:
        wrapper_persona.deleted = True

    db_session.commit()
    return True


# ========================
# Workflow ↔ Persona bridge
# ========================


def _get_workflow_persona(
    db_session: Session,
    workflow_id: int,
) -> Persona | None:
    """Find the wrapper persona for a given workflow."""
    return db_session.execute(
        select(Persona).where(Persona.workflow_id == workflow_id)
    ).scalar_one_or_none()


def _build_workflow_description(workflow: AgentWorkflow) -> str:
    """Build a user-facing description for the wrapper persona.

    Shows the workflow's own description plus a summary of its agent pipeline.
    """
    parts: list[str] = []
    if workflow.description:
        parts.append(workflow.description)

    step_names = [s.step_name for s in sorted(workflow.steps, key=lambda s: s.step_order)]
    if step_names:
        mode_label = {
            "llm_decision": "LLM-Orchestrated",
            "sequential": "Sequential",
            "conditional": "Conditional",
        }.get(workflow.orchestration_mode, workflow.orchestration_mode)
        parts.append(f"[{mode_label} Workflow: {' → '.join(step_names)}]")

    return "\n".join(parts) if parts else f"Multi-agent workflow: {workflow.name}"


def _get_or_create_label(db_session: Session, name: str) -> PersonaLabel:
    """Get a label by name, or create it if it doesn't exist."""
    label = db_session.execute(
        select(PersonaLabel).where(PersonaLabel.name == name)
    ).scalar_one_or_none()
    if label is None:
        label = PersonaLabel(name=name)
        db_session.add(label)
        db_session.flush()
    return label


def create_or_update_workflow_persona(
    db_session: Session,
    workflow: AgentWorkflow,
) -> Persona:
    """Create or update the wrapper Persona for a workflow.

    This ensures the workflow appears in the agent listing (/app/agents)
    and can be used in the chat page. The wrapper persona inherits the
    workflow's name, description, icon, and visibility settings.

    When a user starts a chat with this persona, the chat system detects
    persona.workflow_id and routes to the workflow engine instead of
    the standard LLM loop.
    """
    existing = _get_workflow_persona(db_session, workflow.id)
    description = _build_workflow_description(workflow)

    # Resolve the "Workflow" label (auto-create if missing)
    workflow_label = _get_or_create_label(db_session, "Workflow")

    if existing:
        # Update the existing wrapper persona to stay in sync
        existing.name = workflow.name
        existing.description = description
        existing.is_public = workflow.is_public
        existing.is_visible = workflow.is_visible
        existing.icon_name = workflow.icon_name
        existing.deleted = workflow.deleted
        # Ensure the Workflow label is attached
        if workflow_label not in existing.labels:
            existing.labels.append(workflow_label)
        db_session.commit()
        logger.info(
            f"Updated wrapper persona id={existing.id} for workflow id={workflow.id}"
        )
        return existing

    # Create a new wrapper persona
    persona = Persona(
        user_id=workflow.user_id,
        name=workflow.name,
        description=description,
        num_chunks=0,
        chunks_above=CONTEXT_CHUNKS_ABOVE,
        chunks_below=CONTEXT_CHUNKS_BELOW,
        llm_relevance_filter=False,
        llm_filter_extraction=False,
        recency_bias=RecencyBiasSetting.BASE_DECAY,
        llm_model_provider_override=workflow.orchestrator_llm_provider,
        llm_model_version_override=workflow.orchestrator_llm_model,
        starter_messages=None,
        system_prompt=None,
        task_prompt=None,
        datetime_aware=True,
        is_public=workflow.is_public,
        is_visible=workflow.is_visible,
        display_priority=None,
        icon_name=workflow.icon_name,
        replace_base_system_prompt=False,
        workflow_id=workflow.id,
    )
    persona.labels = [workflow_label]
    db_session.add(persona)
    db_session.commit()
    logger.info(
        f"Created wrapper persona id={persona.id} for workflow id={workflow.id}"
    )
    return persona


# ========================
# Step helpers
# ========================


def _add_step(
    db_session: Session,
    workflow_id: int,
    step_create: WorkflowStepCreate,
) -> AgentWorkflowStep:
    step = AgentWorkflowStep(
        workflow_id=workflow_id,
        persona_id=step_create.persona_id,
        step_order=step_create.step_order,
        step_name=step_create.step_name,
        step_description=step_create.step_description,
        input_mapping=step_create.input_mapping,
        output_key=step_create.output_key,
        condition=step_create.condition,
        is_terminal=step_create.is_terminal,
        can_request_input=step_create.can_request_input,
        promote_output=step_create.promote_output,
        # Step-level overrides
        llm_provider_override=step_create.llm_provider_override,
        llm_model_override=step_create.llm_model_override,
        max_output_tokens_override=step_create.max_output_tokens_override,
        system_prompt_override=step_create.system_prompt_override,
        task_prompt_override=step_create.task_prompt_override,
        tool_ids_override=step_create.tool_ids_override,
        document_set_ids_override=step_create.document_set_ids_override,
        replace_base_system_prompt_override=step_create.replace_base_system_prompt_override,
    )
    db_session.add(step)
    db_session.flush()
    return step


# ========================
# Workflow Execution CRUD
# ========================


def create_workflow_execution(
    db_session: Session,
    workflow_id: int,
    user_id: UUID | None = None,
    chat_session_id: UUID | None = None,
) -> WorkflowExecution:
    execution = WorkflowExecution(
        workflow_id=workflow_id,
        user_id=user_id,
        chat_session_id=chat_session_id,
        status="running",
        steps_executed=[],
        total_tokens=0,
        total_duration_ms=0,
    )
    db_session.add(execution)
    db_session.commit()
    return execution


def update_workflow_execution(
    db_session: Session,
    execution_id: int,
    status: str | None = None,
    steps_executed: list | None = None,
    total_tokens: int | None = None,
    total_duration_ms: int | None = None,
    error_message: str | None = None,
) -> WorkflowExecution | None:
    execution = db_session.get(WorkflowExecution, execution_id)
    if execution is None:
        return None

    if status is not None:
        execution.status = status
    if steps_executed is not None:
        execution.steps_executed = steps_executed
    if total_tokens is not None:
        execution.total_tokens = total_tokens
    if total_duration_ms is not None:
        execution.total_duration_ms = total_duration_ms
    if error_message is not None:
        execution.error_message = error_message

    if status in ("completed", "failed", "timeout"):
        execution.completed_at = datetime.datetime.now(datetime.timezone.utc)
        # Free checkpoint JSONB — no longer needed once execution is terminal
        execution.checkpoint_data = None
        execution.paused_at_step_id = None
        logger.info(
            "[Execution] FINALIZED execution_id=%d status=%s "
            "duration=%dms tokens=%d steps=%d error=%s",
            execution_id,
            status,
            total_duration_ms or 0,
            total_tokens or 0,
            len(steps_executed) if steps_executed else 0,
            error_message[:100] if error_message else None,
        )

    db_session.commit()
    return execution


def get_workflow_execution(
    db_session: Session,
    execution_id: int,
) -> WorkflowExecution | None:
    return db_session.get(WorkflowExecution, execution_id)


def list_workflow_executions(
    db_session: Session,
    workflow_id: int,
    limit: int = 20,
) -> list[WorkflowExecution]:
    return list(
        db_session.execute(
            select(WorkflowExecution)
            .where(WorkflowExecution.workflow_id == workflow_id)
            .order_by(WorkflowExecution.started_at.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )


# ========================
# Checkpoint / Pause-Resume
# ========================


def save_checkpoint(
    db_session: Session,
    execution_id: int,
    checkpoint: WorkflowCheckpoint,
    paused_at_step_id: int | None = None,
) -> None:
    """Save checkpoint after step completion or on pause.

    Called after every step (crash recovery) and when an agent
    requests user input (human-in-the-loop pause).
    """
    execution = db_session.get(WorkflowExecution, execution_id)
    if execution is None:
        logger.warning(
            "[Checkpoint] Cannot save — execution_id=%d not found",
            execution_id,
        )
        return
    execution.checkpoint_data = checkpoint.model_dump()
    execution.paused_at_step_id = paused_at_step_id
    if paused_at_step_id is not None:
        execution.status = "paused"
        logger.info(
            "[Checkpoint] PAUSED execution_id=%d at step_id=%d "
            "completed_steps=%s",
            execution_id,
            paused_at_step_id,
            checkpoint.completed_step_ids,
        )
    else:
        logger.debug(
            "[Checkpoint] Saved execution_id=%d completed_steps=%s",
            execution_id,
            checkpoint.completed_step_ids,
        )
    db_session.commit()


def get_paused_execution(
    db_session: Session,
    workflow_id: int,
    chat_session_id: UUID,
) -> WorkflowExecution | None:
    """Find a paused execution for this workflow + chat session."""
    result = db_session.execute(
        select(WorkflowExecution)
        .where(WorkflowExecution.workflow_id == workflow_id)
        .where(WorkflowExecution.chat_session_id == chat_session_id)
        .where(WorkflowExecution.status == "paused")
        .order_by(WorkflowExecution.started_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    if result:
        logger.info(
            "[Checkpoint] Found paused execution_id=%d for workflow=%d "
            "chat_session=%s paused_at_step=%s",
            result.id,
            workflow_id,
            chat_session_id,
            result.paused_at_step_id,
        )
    return result


def load_checkpoint(
    execution: WorkflowExecution,
) -> WorkflowCheckpoint | None:
    """Load checkpoint from a paused or crashed execution.

    Returns None (triggering fresh execution) if checkpoint data
    is missing or corrupted, rather than crashing.
    """
    if not execution.checkpoint_data:
        return None
    try:
        return WorkflowCheckpoint(**execution.checkpoint_data)
    except Exception:
        logger.warning(
            "Corrupted checkpoint data for execution %d, falling back to fresh run",
            execution.id,
        )
        return None
