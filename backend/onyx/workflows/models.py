"""Pydantic schemas for multi-agent workflow system."""

from datetime import datetime
from typing import Any
from typing import Literal

from pydantic import BaseModel

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


class WorkflowCreate(BaseModel):
    name: str
    description: str | None = None
    orchestration_mode: OrchestrationMode = "llm_decision"
    orchestrator_prompt: str | None = None
    orchestrator_llm_provider: str | None = None
    orchestrator_llm_model: str | None = None
    max_steps: int = 10
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
    chat_session_id: int | None = None


# ========================
# Workflow context (runtime)
# ========================


class WorkflowContext(BaseModel):
    """Runtime context passed between agents in a workflow."""

    user_input: str
    step_outputs: dict[str, str] = {}
    current_step: str | None = None
    shared_data: dict[str, Any] = {}
