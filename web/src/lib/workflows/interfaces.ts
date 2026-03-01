/**
 * TypeScript interfaces for the multi-agent workflow system.
 * Mirrors backend Pydantic schemas in backend/onyx/workflows/models.py
 */

export interface WorkflowStepSnapshot {
  id: number;
  workflow_id: number;
  persona_id: number;
  persona_name: string | null;
  step_order: number;
  step_name: string;
  step_description: string | null;
  input_mapping: Record<string, any> | null;
  output_key: string;
  condition: Record<string, any> | null;
  is_terminal: boolean;
  can_request_input: boolean;
}

export interface WorkflowSnapshot {
  id: number;
  name: string;
  description: string | null;
  user_id: string | null;
  orchestration_mode: string;
  orchestrator_prompt: string | null;
  orchestrator_llm_provider: string | null;
  orchestrator_llm_model: string | null;
  max_steps: number;
  max_calls_per_agent: number;
  timeout_seconds: number;
  is_public: boolean;
  is_visible: boolean;
  deleted: boolean;
  icon_name: string | null;
  created_at: string;
  updated_at: string;
  steps: WorkflowStepSnapshot[];
}

export interface WorkflowStepCreate {
  persona_id: number;
  step_order: number;
  step_name: string;
  step_description?: string | null;
  input_mapping?: Record<string, any> | null;
  output_key?: string;
  condition?: Record<string, any> | null;
  is_terminal?: boolean;
  can_request_input?: boolean;
}

export interface WorkflowCreate {
  name: string;
  description?: string | null;
  orchestration_mode?: string;
  orchestrator_prompt?: string | null;
  orchestrator_llm_provider?: string | null;
  orchestrator_llm_model?: string | null;
  max_steps?: number;
  max_calls_per_agent?: number;
  timeout_seconds?: number;
  is_public?: boolean;
  icon_name?: string | null;
  steps: WorkflowStepCreate[];
}

export interface WorkflowUpdate {
  name?: string | null;
  description?: string | null;
  orchestration_mode?: string | null;
  orchestrator_prompt?: string | null;
  orchestrator_llm_provider?: string | null;
  orchestrator_llm_model?: string | null;
  max_steps?: number | null;
  max_calls_per_agent?: number | null;
  timeout_seconds?: number | null;
  is_public?: boolean | null;
  icon_name?: string | null;
  steps?: WorkflowStepCreate[] | null;
}

export interface StepExecutionRecord {
  step_id: number;
  persona_id: number;
  step_name: string;
  input_text: string;
  output_text: string;
  duration_ms: number;
  tokens_used: number;
}

export interface WorkflowExecutionSnapshot {
  id: number;
  workflow_id: number;
  chat_session_id: number | null;
  user_id: string | null;
  status: string;
  steps_executed: StepExecutionRecord[] | null;
  total_tokens: number;
  total_duration_ms: number;
  error_message: string | null;
  started_at: string;
  completed_at: string | null;
}
