"""Pydantic schemas for multi-agent workflow system."""

from datetime import datetime
from typing import Any
from typing import Literal
from uuid import UUID

from pydantic import BaseModel
from pydantic import model_validator

from om.file_store.models import FileDescriptor

# Valid orchestration modes
OrchestrationMode = Literal["sequential", "llm_decision"]

# Step (node) type names are validated against the node type registry
# (om/workflows/nodes) when a workflow is saved, so new node types need no
# schema change here.
StepType = str

# Condition operators — single source of truth (also exposed via API)
CONDITION_OPERATORS = [
    "equals",
    "not_equals",
    "contains",
    "not_contains",
    "starts_with",
    "ends_with",
    "regex_match",
    "greater_than",
    "greater_than_or_equal",
    "less_than",
    "less_than_or_equal",
    "is_empty",
    "is_not_empty",
]

ConditionOperator = Literal[
    "equals",
    "not_equals",
    "contains",
    "not_contains",
    "starts_with",
    "ends_with",
    "regex_match",
    "greater_than",
    "greater_than_or_equal",
    "less_than",
    "less_than_or_equal",
    "is_empty",
    "is_not_empty",
]


class ConditionConfig(BaseModel):
    """Typed schema for conditional router step conditions.

    Validated on workflow create/update to catch config errors early
    rather than at runtime.
    """

    condition_field: str
    operator: ConditionOperator = "contains"
    match_value: str = ""
    case_sensitive: bool = False
    true_steps: list[int] = []
    false_steps: list[int] = []


# ========================
# Request / Create schemas
# ========================


class WorkflowStepCreate(BaseModel):
    step_type: StepType = "agent"
    # Stable identity within the workflow. Send it back unchanged when
    # updating a workflow so the step keeps its id (and paused runs, traces
    # and router targets keep pointing at it); omit it for new steps.
    node_key: str | None = None
    # Node type version; None means the latest version of ``step_type``.
    type_version: int | None = None
    # Settings for node types without legacy columns (validated against the
    # node type's config model). Agent and router steps may keep using their
    # legacy fields below.
    config: dict[str, Any] | None = None
    # Container membership: the enclosing container's node_key and the branch
    # within it (parallel / loop). Omit both for top-level steps.
    parent_key: str | None = None
    branch_index: int | None = None
    agent_id: int | None = None
    step_order: int
    step_name: str
    step_description: str | None = None
    input_mapping: dict[str, Any] | None = None
    output_key: str = "output"
    condition: ConditionConfig | None = None
    is_terminal: bool = False
    can_request_input: bool = False
    promote_output: bool = False

    @model_validator(mode="after")
    def validate_step_type_fields(self) -> "WorkflowStepCreate":
        if (
            self.step_type == "conditional_router"
            and self.condition is None
            and self.config is None
        ):
            raise ValueError(
                "conditional_router steps must have a 'condition' configuration"
            )
        if self.step_type == "agent" and self.agent_id is None:
            raise ValueError("agent steps must have a 'agent_id'")
        return self

    # Step-level overrides (override agent defaults when set)
    llm_provider_override: str | None = None
    llm_model_override: str | None = None
    max_output_tokens_override: int | None = None
    system_prompt_override: str | None = None
    task_prompt_override: str | None = None
    tool_ids_override: list[int] | None = None
    document_set_ids_override: list[int] | None = None
    replace_base_system_prompt_override: bool | None = None


class WorkflowCreate(BaseModel):
    name: str
    description: str | None = None
    orchestration_mode: OrchestrationMode = "llm_decision"
    orchestrator_prompt: str | None = None
    orchestrator_llm_provider: str | None = None
    orchestrator_llm_model: str | None = None
    max_steps: int = 10
    max_calls_per_agent: int = 2
    timeout_seconds: int = 1800
    is_public: bool = True
    icon_name: str | None = None
    steps: list[WorkflowStepCreate] = []


class WorkflowUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    orchestration_mode: OrchestrationMode | None = None
    orchestrator_prompt: str | None = None
    orchestrator_llm_provider: str | None = None
    orchestrator_llm_model: str | None = None
    max_steps: int | None = None
    max_calls_per_agent: int | None = None
    timeout_seconds: int | None = None
    is_public: bool | None = None
    icon_name: str | None = None
    steps: list[WorkflowStepCreate] | None = None
    # Run semantics: 2 = safe references. Raising it upgrades an existing workflow.
    schema_version: int | None = None
    # Optimistic concurrency: when set, the update is rejected if the workflow
    # was saved by someone else since this version was loaded.
    expected_version: int | None = None


# ========================
# Response schemas
# ========================


class WorkflowStepResponse(BaseModel):
    id: int
    workflow_id: int
    node_key: str
    step_type: str = "agent"
    type_version: int = 1
    latest_type_version: int = 1
    # True when a newer version of this node type is available (opt-in).
    upgrade_available: bool = False
    config: dict[str, Any] | None = None
    parent_key: str | None = None
    branch_index: int | None = None
    agent_id: int | None = None
    agent_name: str | None = None
    step_order: int
    step_name: str
    step_description: str | None = None
    input_mapping: dict[str, Any] | None = None
    output_key: str
    condition: dict[str, Any] | None = None
    is_terminal: bool
    can_request_input: bool
    promote_output: bool

    # Step-level overrides
    llm_provider_override: str | None = None
    llm_model_override: str | None = None
    max_output_tokens_override: int | None = None
    system_prompt_override: str | None = None
    task_prompt_override: str | None = None
    tool_ids_override: list[int] | None = None
    document_set_ids_override: list[int] | None = None
    replace_base_system_prompt_override: bool | None = None


class WorkflowResponse(BaseModel):
    id: int
    name: str
    description: str | None
    user_id: str | None
    orchestration_mode: str
    orchestrator_prompt: str | None
    orchestrator_llm_provider: str | None
    orchestrator_llm_model: str | None
    max_steps: int
    max_calls_per_agent: int
    timeout_seconds: int
    is_public: bool
    is_visible: bool
    deleted: bool
    icon_name: str | None
    version: int = 1
    schema_version: int = 1
    created_at: datetime
    updated_at: datetime
    steps: list[WorkflowStepResponse]


class StepExecutionRecord(BaseModel):
    # None for steps without a row (pinned definitions) or without an agent
    # (e.g. condition steps).
    step_id: int | None
    agent_id: int | None
    step_name: str
    input_text: str
    output_text: str
    duration_ms: int
    tokens_used: int


class WorkflowExecutionResponse(BaseModel):
    id: int
    workflow_id: int
    chat_session_id: UUID | None
    user_id: str | None
    status: str
    steps_executed: list[StepExecutionRecord] | None
    total_tokens: int
    total_duration_ms: int
    error_message: str | None
    started_at: datetime
    completed_at: datetime | None


class WorkflowVersionSummary(BaseModel):
    """One entry of a workflow's version history."""

    version: int
    schema_version: int
    content_hash: str
    created_by_id: UUID | None
    created_at: datetime


class WorkflowVersionDetail(WorkflowVersionSummary):
    """A version with its full definition (see om/workflows/graph.py)."""

    definition: dict[str, Any]


class NodeUpgradeRequest(BaseModel):
    """Convert a node config from ``from_version`` to the latest version."""

    from_version: int
    config: dict[str, Any]
    # The workflow's steps (step order -> node key), for upgrades that
    # re-target references (e.g. router branches).
    step_order_to_node_key: dict[int, str] = {}


# ========================
# Execution request
# ========================


class WorkflowRunRequest(BaseModel):
    """Request to execute a workflow."""

    message: str
    chat_session_id: UUID | None = None
    file_descriptors: list[FileDescriptor] = []


# ========================
# Workflow context (runtime)
# ========================


class WorkflowContext(BaseModel):
    """Runtime context passed between agents in a workflow."""

    user_input: str
    step_outputs: dict[str, str] = {}
    current_step: str | None = None
    shared_data: dict[str, Any] = {}


# ========================
# Checkpoint (pause/resume + crash recovery)
# ========================


class WorkflowCheckpoint(BaseModel):
    """Serialized workflow state for pause/resume and crash recovery.

    Saved to WorkflowExecution.checkpoint_data (JSONB) after each step
    completes, and on pause when an agent requests user input.

    Versions:
        1: legacy; completion is derived from ``completed_step_ids``.
        2: completion, branch skips and output order are tracked by node key
           (``completed_node_keys`` / ``skipped_node_keys`` / ``output_order``).
           ``completed_step_ids`` is still written so older servers can resume.
    """

    checkpoint_version: int = 1
    step_outputs: dict[str, str] = {}
    shared_data: dict[str, Any] = {}
    completed_step_ids: list[int] = []
    # Serialized orchestrator message history (for llm_decision mode)
    orchestrator_history: list[dict] = []
    cycle_count: int = 0
    agent_call_counts: dict[str, int] = {}
    turn_index: int = 0

    # --- Clarification conversation (enterprise pause/resume) ---
    # Accumulated agent-user dialog across multiple pause/resume rounds.
    # Each entry: {"role": "agent"|"user", "content": "..."}
    # Grows across rounds; cleared when the agent produces a final output.
    clarification_conversation: list[dict[str, str]] = []
    # The original task string given to the paused agent, so we can
    # reconstruct the exact same context on resume without re-deriving it.
    paused_agent_original_task: str = ""

    # --- Version 2 (node-key based state) ---
    completed_node_keys: list[str] = []
    # Nodes deactivated by a router; restored on resume so the losing branch
    # stays skipped.
    skipped_node_keys: list[str] = []
    # Output keys in completion order. JSONB does not preserve object key
    # order, so step_outputs alone cannot tell which output came last.
    output_order: list[str] = []
    paused_node_key: str | None = None
