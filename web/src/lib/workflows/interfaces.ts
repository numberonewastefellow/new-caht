/**
 * TypeScript interfaces for the multi-agent workflow system.
 * Mirrors backend Pydantic schemas in backend/onyx/workflows/models.py
 */

// Condition operators — single source of truth for frontend.
// Mirrors CONDITION_OPERATORS in backend/onyx/workflows/models.py
export const CONDITION_OPERATORS = [
  { value: "contains", label: "Contains" },
  { value: "not_contains", label: "Does not contain" },
  { value: "equals", label: "Equals" },
  { value: "not_equals", label: "Not equals" },
  { value: "starts_with", label: "Starts with" },
  { value: "ends_with", label: "Ends with" },
  { value: "regex_match", label: "Regex match" },
  { value: "is_empty", label: "Is empty" },
  { value: "is_not_empty", label: "Is not empty" },
  { value: "greater_than", label: "Greater than" },
  { value: "greater_than_or_equal", label: "Greater than or equal" },
  { value: "less_than", label: "Less than" },
  { value: "less_than_or_equal", label: "Less than or equal" },
] as const;

export type ConditionOperator = (typeof CONDITION_OPERATORS)[number]["value"];

export interface ConditionConfig {
  condition_field: string;
  operator: ConditionOperator;
  match_value: string;
  case_sensitive: boolean;
  true_steps: number[];
  false_steps: number[];
}

export interface WorkflowStepSnapshot {
  id: number;
  workflow_id: number;
  step_type: string;
  agent_id: number | null;
  agent_name: string | null;
  step_order: number;
  step_name: string;
  step_description: string | null;
  input_mapping: Record<string, any> | null;
  output_key: string;
  condition: Record<string, any> | null;
  is_terminal: boolean;
  can_request_input: boolean;
  promote_output: boolean;

  // Step-level overrides
  llm_provider_override?: string | null;
  llm_model_override?: string | null;
  max_output_tokens_override?: number | null;
  system_prompt_override?: string | null;
  task_prompt_override?: string | null;
  tool_ids_override?: number[] | null;
  document_set_ids_override?: number[] | null;
  replace_base_system_prompt_override?: boolean | null;
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
  step_type?: string;
  agent_id?: number | null;
  step_order: number;
  step_name: string;
  step_description?: string | null;
  input_mapping?: Record<string, any> | null;
  output_key?: string;
  condition?: Record<string, any> | null;
  is_terminal?: boolean;
  can_request_input?: boolean;
  promote_output?: boolean;

  // Step-level overrides
  llm_provider_override?: string | null;
  llm_model_override?: string | null;
  max_output_tokens_override?: number | null;
  system_prompt_override?: string | null;
  task_prompt_override?: string | null;
  tool_ids_override?: number[] | null;
  document_set_ids_override?: number[] | null;
  replace_base_system_prompt_override?: boolean | null;
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
  agent_id: number;
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
