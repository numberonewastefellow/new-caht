"""Pydantic schemas for multi-agent workflow system."""

from datetime import datetime
from typing import Any
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from onyx.file_store.models import FileDescriptor

# Valid orchestration modes
OrchestrationMode = Literal["sequential", "llm_decision"]


# ========================
# Request / Create schemas
# ========================


class WorkflowStepCreate(BaseModel):
    persona_id: int
    step_order: int
    step_name: str
    step_description: str | None = None
    input_mapping: dict[str, Any] | None = None
    output_key: str = "output"
    condition: dict[str, Any] | None = None
    is_terminal: bool = False
    can_request_input: bool = False
    promote_output: bool = False

    # Step-level overrides (override persona defaults when set)
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


# ========================
# Response schemas
# ========================


class WorkflowStepResponse(BaseModel):
    id: int
    workflow_id: int
    persona_id: int
    persona_name: str | None = None
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
    created_at: datetime
    updated_at: datetime
    steps: list[WorkflowStepResponse]


class StepExecutionRecord(BaseModel):
    step_id: int
    persona_id: int
    step_name: str
    input_text: str
    output_text: str
    duration_ms: int
    tokens_used: int


class WorkflowExecutionResponse(BaseModel):
    id: int
    workflow_id: int
    chat_session_id: int | None
    user_id: str | None
    status: str
    steps_executed: list[StepExecutionRecord] | None
    total_tokens: int
    total_duration_ms: int
    error_message: str | None
    started_at: datetime
    completed_at: datetime | None


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
    """

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
