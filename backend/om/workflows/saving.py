"""Validate and save workflows through the node type registry.

The API calls these functions instead of the raw DB helpers. Each save:

1. gives new steps a stable ``node_key`` and resolves each step's node type
   version (latest when not given);
2. lets the node type validate/normalize the step (``NodeTypeSpec.prepare_step``,
   or its config model) and checks it may be used in the workflow's mode;
3. persists the workflow (steps upserted by node key);
4. records an immutable version of the result.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from om.db.models import AgentWorkflow
from om.db.models import new_workflow_node_key
from om.db.workflow import create_workflow
from om.db.workflow import get_workflow_for_update
from om.db.workflow import update_workflow
from om.db.workflow_version import get_workflow_version_by_number
from om.workflows.graph import graph_from_definition
from om.workflows.graph import graph_from_workflow
from om.workflows.graph import WorkflowGraph
from om.workflows.graph import WorkflowNode
from om.workflows.models import WorkflowCreate
from om.workflows.models import WorkflowStepCreate
from om.workflows.models import WorkflowUpdate
from om.workflows.nodes.base import SaveContext
from om.workflows.nodes.base import StepSaveError
from om.workflows.nodes.base import StepSummary
from om.workflows.nodes.builtin import get_node_registry
from om.workflows.nodes.registry import NodeTypeRegistry
from om.workflows.nodes.registry import UnknownNodeTypeError
from om.workflows.versioning import pin_workflow_version


MAX_WORKFLOW_STEPS = 100
MAX_CONTAINER_DEPTH = 3
# ``$user_input`` and ``$loop.*`` resolve before step outputs, so a step using one
# of these output keys could never be read.
RESERVED_OUTPUT_KEYS = frozenset({"loop", "user_input"})


class WorkflowSaveError(ValueError):
    """The workflow definition is invalid (reported as HTTP 400)."""


class WorkflowVersionConflictError(Exception):
    """The workflow was saved by someone else since it was loaded (HTTP 409)."""


# ── Step preparation ──────────────────────────────────────────────────────


def prepare_steps(
    db_session: Session,
    steps: list[WorkflowStepCreate],
    orchestration_mode: str,
    registry: NodeTypeRegistry | None = None,
) -> list[WorkflowStepCreate]:
    """Validate step payloads and normalize them for persistence.

    Raises:
        WorkflowSaveError: A step is invalid, uses an unknown node type, or is
            not allowed in ``orchestration_mode``.
    """
    registry = registry or get_node_registry()
    keyed = [
        step if step.node_key else step.model_copy(update={"node_key": new_workflow_node_key()})
        for step in steps
    ]
    _check_unique(keyed)
    if len(keyed) > MAX_WORKFLOW_STEPS:
        raise WorkflowSaveError(f"A workflow can have at most {MAX_WORKFLOW_STEPS} steps")
    ctx = SaveContext(
        db_session=db_session,
        orchestration_mode=orchestration_mode,
        step_order_to_node_key={s.step_order: s.node_key or "" for s in keyed},
        steps={
            s.node_key or "": StepSummary(
                node_type=s.step_type,
                step_order=s.step_order,
                parent_key=s.parent_key,
                branch_index=s.branch_index,
            )
            for s in keyed
        },
    )
    _check_containers(keyed, ctx, registry)
    return [_prepare_step(step, ctx, registry) for step in keyed]


def _prepare_step(
    step: WorkflowStepCreate, ctx: SaveContext, registry: NodeTypeRegistry
) -> WorkflowStepCreate:
    try:
        spec = registry.resolve(step.step_type, step.type_version)
    except UnknownNodeTypeError as e:
        raise WorkflowSaveError(f"Step '{step.step_name}': {e}") from e
    if ctx.orchestration_mode not in spec.capabilities.modes:
        raise WorkflowSaveError(
            f"'{spec.label}' steps can't be used in {ctx.orchestration_mode} "
            f"workflows (step '{step.step_name}')"
        )

    step = step.model_copy(update={"type_version": spec.version})
    if spec.prepare_step is not None:
        try:
            return spec.prepare_step(step, ctx)
        except StepSaveError as e:
            raise WorkflowSaveError(str(e)) from e
    try:
        config = spec.validate_config(step.config or {})
    except ValidationError as e:
        raise WorkflowSaveError(
            f"Step '{step.step_name}': {e.errors()[0]['msg']}"
        ) from e
    return step.model_copy(update={"config": config.model_dump(mode="json")})


def _check_unique(steps: list[WorkflowStepCreate]) -> None:
    keys = [s.node_key for s in steps]
    if len(keys) != len(set(keys)):
        raise WorkflowSaveError("Steps must have unique node keys")
    orders = [s.step_order for s in steps]
    if len(orders) != len(set(orders)):
        raise WorkflowSaveError("Steps must have unique step orders")
    owners: dict[str, str] = {}
    for step in sorted(steps, key=lambda s: s.step_order):
        if step.output_key in RESERVED_OUTPUT_KEYS:
            raise WorkflowSaveError(
                f'"{step.step_name}" can\'t use the reserved output key "{step.output_key}"'
            )
        if step.output_key in owners:
            raise WorkflowSaveError(
                f'Duplicate output key "{step.output_key}" '
                f'(also used by "{owners[step.output_key]}")'
            )
        owners[step.output_key] = step.step_name


def _check_containers(
    steps: list[WorkflowStepCreate], ctx: SaveContext, registry: NodeTypeRegistry
) -> None:
    """Rules every container type shares (see docs/flow-nodes/DESIGN.md)."""
    for step in steps:
        if step.parent_key is None:
            if step.branch_index is not None:
                raise WorkflowSaveError(
                    f"Step '{step.step_name}' has a branch but no container"
                )
            continue
        parent = ctx.steps.get(step.parent_key)
        if parent is None:
            raise WorkflowSaveError(
                f"Step '{step.step_name}' is inside an unknown container"
            )
        try:
            parent_spec = registry.resolve(parent.node_type, None)
        except UnknownNodeTypeError as e:
            raise WorkflowSaveError(str(e)) from e
        if not parent_spec.capabilities.is_container:
            raise WorkflowSaveError(
                f"Step '{step.step_name}' is inside '{parent_spec.label}', "
                f"which can't contain steps"
            )
        if step.branch_index is None or step.branch_index < 0:
            raise WorkflowSaveError(f"Step '{step.step_name}' needs a branch")
        if step.step_order <= parent.step_order:
            raise WorkflowSaveError(
                f"Step '{step.step_name}' must come after its container"
            )
        if len(ctx.ancestors(step.node_key or "")) > MAX_CONTAINER_DEPTH:
            raise WorkflowSaveError(
                f"Containers can be nested at most {MAX_CONTAINER_DEPTH} levels deep"
            )
        if step.can_request_input or step.promote_output or step.is_terminal:
            raise WorkflowSaveError(
                f"Step '{step.step_name}' is inside a container, so it can't ask for "
                f"input, promote its output, or end the workflow"
            )


def _check_modes(graph: WorkflowGraph, mode: str, registry: NodeTypeRegistry) -> None:
    """Existing steps must support the workflow's (possibly new) mode."""
    for node in graph.nodes:
        spec = registry.get(node.node_type, node.type_version)
        if mode not in spec.capabilities.modes:
            raise WorkflowSaveError(
                f"'{spec.label}' steps can't be used in {mode} workflows "
                f"(step '{node.name}')"
            )


# ── Saving ────────────────────────────────────────────────────────────────


def save_new_workflow(
    db_session: Session, workflow_create: WorkflowCreate, user_id: UUID | None
) -> AgentWorkflow:
    """Create a workflow and record its first version."""
    steps = prepare_steps(
        db_session, workflow_create.steps, workflow_create.orchestration_mode
    )
    workflow = create_workflow(
        db_session=db_session,
        workflow_create=workflow_create.model_copy(update={"steps": steps}),
        user_id=user_id,
    )
    _record_version(db_session, workflow, user_id)
    db_session.commit()
    return workflow


def save_workflow_update(
    db_session: Session,
    workflow_id: int,
    workflow_update: WorkflowUpdate,
    user_id: UUID | None,
) -> AgentWorkflow | None:
    """Update a workflow and record a new version if its content changed.

    The save is one transaction holding the workflow's row lock, so concurrent
    saves run one after the other and the live steps always match a version row.

    Raises:
        WorkflowVersionConflictError: ``expected_version`` is stale, or a run
            recorded the same version number at the same moment.
        WorkflowSaveError: The new definition is invalid.
    """
    try:
        workflow = _apply_update(db_session, workflow_id, workflow_update, user_id)
        db_session.commit()
        return workflow
    except Exception:
        db_session.rollback()
        raise


def _apply_update(
    db_session: Session,
    workflow_id: int,
    workflow_update: WorkflowUpdate,
    user_id: UUID | None,
) -> AgentWorkflow | None:
    registry = get_node_registry()
    workflow = get_workflow_for_update(db_session, workflow_id)
    if workflow is None:
        return None
    if (
        workflow_update.expected_version is not None
        and workflow_update.expected_version != workflow.version
    ):
        raise WorkflowVersionConflictError(
            f"Workflow was saved by someone else (now at version {workflow.version}, "
            f"you loaded version {workflow_update.expected_version})"
        )

    mode = workflow_update.orchestration_mode or workflow.orchestration_mode
    if workflow_update.steps is not None:
        steps = prepare_steps(db_session, workflow_update.steps, mode, registry)
        workflow_update = workflow_update.model_copy(update={"steps": steps})
    elif mode != workflow.orchestration_mode:
        _check_modes(graph_from_workflow(workflow, registry), mode, registry)

    _snapshot_current_definition(db_session, workflow, registry)
    updated = update_workflow(db_session, workflow_id, workflow_update, commit=False)
    if updated is None:
        return None
    _record_version(db_session, updated, user_id)
    return updated


def _snapshot_current_definition(
    db_session: Session, workflow: AgentWorkflow, registry: NodeTypeRegistry
) -> None:
    """Make sure the definition about to be replaced can be restored.

    A workflow from before version history has no rows until its first run, so
    without this its first save would lose the definition it replaces.
    """
    try:
        graph = graph_from_workflow(workflow, registry)
    except (UnknownNodeTypeError, ValidationError) as e:
        raise WorkflowSaveError(
            f"Workflow {workflow.id} can't be loaded, so it needs upgrading: {e}"
        ) from e
    _pin(db_session, workflow, graph, user_id=None)


def restore_workflow_version(
    db_session: Session, workflow_id: int, version: int, user_id: UUID | None
) -> AgentWorkflow | None:
    """Make an earlier version current again (recorded as a new version)."""
    row = get_workflow_version_by_number(db_session, workflow_id, version)
    if row is None:
        return None
    graph = graph_from_definition(row.definition)
    registry = get_node_registry()
    # model_validate: the stored mode is a plain string and is re-validated here.
    update = WorkflowUpdate.model_validate(
        {
            "name": graph.name,
            "orchestration_mode": graph.orchestration_mode,
            "timeout_seconds": graph.timeout_seconds,
            "steps": [_node_to_step_create(node, registry) for node in graph.nodes],
            **_settings_fields(graph),
        }
    )
    return save_workflow_update(db_session, workflow_id, update, user_id)


def _settings_fields(graph: WorkflowGraph) -> dict[str, object]:
    """The workflow settings a restore applies; older definitions recorded none."""
    if graph.settings is None:
        return {}
    settings = graph.settings
    # An update treats None as "no change", so an empty text clears a value.
    return {
        "description": settings.description or "",
        "orchestrator_prompt": settings.orchestrator_prompt or "",
        "orchestrator_llm_provider": settings.orchestrator_llm_provider or "",
        "orchestrator_llm_model": settings.orchestrator_llm_model or "",
        "max_steps": settings.max_steps,
        "max_calls_per_agent": settings.max_calls_per_agent,
        "is_public": settings.is_public,
        "icon_name": settings.icon_name or "",
    }


def _node_to_step_create(node: WorkflowNode, registry: NodeTypeRegistry) -> WorkflowStepCreate:
    """Turn a stored node back into a step payload."""
    spec = registry.get(node.node_type, node.type_version)
    config_fields = (
        spec.store_legacy_config(node.config)
        if spec.store_legacy_config is not None
        else {"config": node.config}
    )
    return WorkflowStepCreate(
        node_key=node.node_key,
        step_type=node.node_type,
        type_version=node.type_version,
        step_order=node.step_order,
        step_name=node.name,
        step_description=node.description,
        input_mapping=node.input_mapping,
        output_key=node.output_key,
        is_terminal=node.is_terminal,
        can_request_input=node.can_request_input,
        promote_output=node.promote_output,
        parent_key=node.parent_key,
        branch_index=node.branch_index,
        **config_fields,
    )


def _record_version(
    db_session: Session, workflow: AgentWorkflow, user_id: UUID | None
) -> None:
    graph = graph_from_workflow(workflow, get_node_registry())
    _pin(db_session, workflow, graph, user_id)


def _pin(
    db_session: Session,
    workflow: AgentWorkflow,
    graph: WorkflowGraph,
    user_id: UUID | None,
) -> None:
    try:
        pin_workflow_version(db_session, workflow, graph, created_by_id=user_id)
    except IntegrityError as e:
        # A run recording a version doesn't take the save's lock.
        raise WorkflowVersionConflictError(
            "Workflow changed while saving; reload it and try again"
        ) from e
