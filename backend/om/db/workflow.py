"""DB CRUD operations for multi-agent workflows."""

import datetime
from uuid import UUID

from sqlalchemy import Select
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm import selectinload

from om.configs.chat_configs import CONTEXT_CHUNKS_ABOVE
from om.configs.chat_configs import CONTEXT_CHUNKS_BELOW
from om.context.search.enums import RecencyBiasSetting
from om.db.models import AgentWorkflow
from om.db.models import AgentWorkflowStep
from om.db.models import Agent
from om.db.models import AgentLabel
from om.db.models import WorkflowExecution
from om.utils.logger import setup_logger
from om.workflows.models import WorkflowCheckpoint
from om.workflows.models import WorkflowCreate
from om.workflows.models import WorkflowStepCreate
from om.workflows.models import WorkflowUpdate

logger = setup_logger()


# ========================
# Workflow CRUD
# ========================


def create_workflow(
    db_session: Session,
    workflow_create: WorkflowCreate,
    user_id: UUID | None = None,
    schema_version: int = 1,
    commit: bool = True,
) -> AgentWorkflow:
    workflow = AgentWorkflow(
        schema_version=schema_version,
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
    _link_parents(db_session, workflow.id, workflow_create.steps)

    if commit:
        db_session.commit()
    else:
        db_session.flush()
    return workflow


def _select_workflow(workflow_id: int) -> Select[tuple[AgentWorkflow]]:
    return (
        select(AgentWorkflow)
        .where(AgentWorkflow.id == workflow_id)
        .where(AgentWorkflow.deleted.is_(False))
        .options(
            selectinload(AgentWorkflow.steps)
            .selectinload(AgentWorkflowStep.agent)
            .selectinload(Agent.tools)
        )
    )


def get_workflow_by_id(
    db_session: Session,
    workflow_id: int,
) -> AgentWorkflow | None:
    return db_session.execute(_select_workflow(workflow_id)).scalar_one_or_none()


def get_workflow_for_update(
    db_session: Session,
    workflow_id: int,
) -> AgentWorkflow | None:
    """The workflow, freshly read, with its row locked until the transaction ends."""
    return db_session.execute(
        _select_workflow(workflow_id)
        .with_for_update(of=AgentWorkflow)
        .execution_options(populate_existing=True)
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
            .selectinload(AgentWorkflowStep.agent)
            .selectinload(Agent.tools)
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
    commit: bool = True,
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
    if workflow_update.schema_version is not None:
        workflow.schema_version = workflow_update.schema_version

    if workflow_update.steps is not None:
        _replace_steps(db_session, workflow, workflow_update.steps)

    if commit:
        db_session.commit()
    else:
        db_session.flush()
    # Steps were changed through the session; reload them on next access.
    db_session.expire(workflow, ["steps"])
    return workflow


def delete_workflow(
    db_session: Session,
    workflow_id: int,
) -> bool:
    workflow = get_workflow_by_id(db_session, workflow_id)
    if workflow is None:
        return False

    workflow.deleted = True

    # Also soft-delete the wrapper agent
    wrapper_agent = _get_workflow_agent(db_session, workflow_id)
    if wrapper_agent:
        wrapper_agent.deleted = True

    db_session.commit()
    return True


# ========================
# Workflow ↔ Agent bridge
# ========================


def _get_workflow_agent(
    db_session: Session,
    workflow_id: int,
) -> Agent | None:
    """Find the wrapper agent for a given workflow."""
    return db_session.execute(
        select(Agent).where(Agent.workflow_id == workflow_id)
    ).scalar_one_or_none()


def _build_workflow_description(workflow: AgentWorkflow) -> str:
    """Build a user-facing description for the wrapper agent.

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


def _get_or_create_label(db_session: Session, name: str) -> AgentLabel:
    """Get a label by name, or create it if it doesn't exist."""
    label = db_session.execute(
        select(AgentLabel).where(AgentLabel.name == name)
    ).scalar_one_or_none()
    if label is None:
        label = AgentLabel(name=name)
        db_session.add(label)
        db_session.flush()
    return label


def create_or_update_workflow_agent(
    db_session: Session,
    workflow: AgentWorkflow,
    commit: bool = True,
) -> Agent:
    """Create or update the wrapper Agent for a workflow.

    This ensures the workflow appears in the agent listing (/app/agents)
    and can be used in the chat page. The wrapper agent inherits the
    workflow's name, description, icon, and visibility settings.

    When a user starts a chat with this agent, the chat system detects
    agent.workflow_id and routes to the workflow engine instead of
    the standard LLM loop.
    """
    existing = _get_workflow_agent(db_session, workflow.id)
    description = _build_workflow_description(workflow)

    # Resolve the "Workflow" label (auto-create if missing)
    workflow_label = _get_or_create_label(db_session, "Workflow")

    if existing:
        # Update the existing wrapper agent to stay in sync
        existing.name = workflow.name
        existing.description = description
        existing.is_public = workflow.is_public
        existing.is_visible = workflow.is_visible
        existing.icon_name = workflow.icon_name
        existing.deleted = workflow.deleted
        # Ensure the Workflow label is attached
        if workflow_label not in existing.labels:
            existing.labels.append(workflow_label)
        if commit:
            db_session.commit()
        else:
            db_session.flush()
        logger.info(
            f"Updated wrapper agent id={existing.id} for workflow id={workflow.id}"
        )
        return existing

    # Create a new wrapper agent
    agent = Agent(
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
    agent.labels = [workflow_label]
    db_session.add(agent)
    if commit:
        db_session.commit()
    else:
        db_session.flush()
    logger.info(
        f"Created wrapper agent id={agent.id} for workflow id={workflow.id}"
    )
    return agent


# ========================
# Step helpers
# ========================


def _add_step(
    db_session: Session,
    workflow_id: int,
    step_create: WorkflowStepCreate,
) -> AgentWorkflowStep:
    step = AgentWorkflowStep(workflow_id=workflow_id)
    if step_create.node_key:
        step.node_key = step_create.node_key
    _apply_step_fields(step, step_create)
    db_session.add(step)
    db_session.flush()
    return step


def _replace_steps(
    db_session: Session,
    workflow: AgentWorkflow,
    step_creates: list[WorkflowStepCreate],
) -> None:
    """Make the workflow's steps match ``step_creates``, matching by node key.

    Steps whose ``node_key`` is sent again are updated in place, so their ids
    stay stable (paused runs, traces and router targets keep pointing at
    them). Steps not sent are deleted; steps without a known key are added.
    """
    existing = {step.node_key: step for step in workflow.steps}
    incoming_keys = {sc.node_key for sc in step_creates if sc.node_key}

    kept = [step for key, step in existing.items() if key in incoming_keys]
    # Detach kept steps from their containers first: deleting a removed
    # container would otherwise cascade to children that are being kept.
    for step in kept:
        step.parent_step_id = None
    db_session.flush()
    for key, step in existing.items():
        if key not in incoming_keys:
            db_session.delete(step)
    db_session.flush()

    # Park kept steps on temporary orders first so re-ordering them can't
    # trip the (workflow_id, step_order) unique constraint mid-update.
    for i, step in enumerate(kept):
        step.step_order = -(i + 1)
    db_session.flush()

    for step_create in step_creates:
        current = existing.get(step_create.node_key) if step_create.node_key else None
        if current is not None and current in kept:
            _apply_step_fields(current, step_create)
        else:
            _add_step(db_session, workflow.id, step_create)
    db_session.flush()
    _link_parents(db_session, workflow.id, step_creates)


def _link_parents(
    db_session: Session,
    workflow_id: int,
    step_creates: list[WorkflowStepCreate],
) -> None:
    """Point each step at its container (by node key), once all rows exist."""
    rows = (
        db_session.execute(
            select(AgentWorkflowStep).where(AgentWorkflowStep.workflow_id == workflow_id)
        )
        .scalars()
        .all()
    )
    id_by_key = {row.node_key: row.id for row in rows}
    parent_key_by_key = {sc.node_key: sc.parent_key for sc in step_creates if sc.node_key}
    for row in rows:
        parent_key = parent_key_by_key.get(row.node_key)
        row.parent_step_id = id_by_key.get(parent_key) if parent_key else None
    db_session.flush()


def _apply_step_fields(step: AgentWorkflowStep, step_create: WorkflowStepCreate) -> None:
    """Copy a step payload onto a (new or existing) step row."""
    step.step_type = step_create.step_type
    step.type_version = step_create.type_version or 1
    step.config = step_create.config
    step.agent_id = step_create.agent_id
    step.step_order = step_create.step_order
    step.step_name = step_create.step_name
    step.step_description = step_create.step_description
    step.input_mapping = step_create.input_mapping
    step.output_key = step_create.output_key
    step.condition = (
        step_create.condition.model_dump() if step_create.condition else None
    )
    step.is_terminal = step_create.is_terminal
    step.can_request_input = step_create.can_request_input
    step.promote_output = step_create.promote_output
    # parent_step_id is set by _link_parents once every row exists.
    step.branch_index = step_create.branch_index
    # Step-level overrides
    step.llm_provider_override = step_create.llm_provider_override
    step.llm_model_override = step_create.llm_model_override
    step.max_output_tokens_override = step_create.max_output_tokens_override
    step.system_prompt_override = step_create.system_prompt_override
    step.task_prompt_override = step_create.task_prompt_override
    step.tool_ids_override = step_create.tool_ids_override
    step.document_set_ids_override = step_create.document_set_ids_override
    step.replace_base_system_prompt_override = (
        step_create.replace_base_system_prompt_override
    )


# ========================
# Workflow Execution CRUD
# ========================


def create_workflow_execution(
    db_session: Session,
    workflow_id: int,
    user_id: UUID | None = None,
    chat_session_id: UUID | None = None,
    workflow_version_id: int | None = None,
) -> WorkflowExecution:
    execution = WorkflowExecution(
        workflow_id=workflow_id,
        user_id=user_id,
        chat_session_id=chat_session_id,
        workflow_version_id=workflow_version_id,
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


def get_latest_execution_by_chat_session(
    db_session: Session,
    chat_session_id: UUID,
) -> WorkflowExecution | None:
    """Most recent workflow execution for a chat session (for trace lookup)."""
    return db_session.execute(
        select(WorkflowExecution)
        .where(WorkflowExecution.chat_session_id == chat_session_id)
        .order_by(WorkflowExecution.started_at.desc())
        .limit(1)
    ).scalar_one_or_none()


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
    paused: bool = False,
) -> None:
    """Save checkpoint after step completion or on pause.

    Called after every step (crash recovery) and when an agent
    requests user input (human-in-the-loop pause). A run is paused when
    ``paused`` is set or a ``paused_at_step_id`` is given; ``paused`` covers
    runs pinned to a definition whose paused step row no longer exists (the
    checkpoint's ``paused_node_key`` identifies the node instead).
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
    if paused or paused_at_step_id is not None:
        execution.status = "paused"
        logger.info(
            "[Checkpoint] PAUSED execution_id=%d at step_id=%s node=%s "
            "completed_steps=%s",
            execution_id,
            paused_at_step_id,
            checkpoint.paused_node_key,
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
