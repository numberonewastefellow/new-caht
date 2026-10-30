/**
 * TypeScript interfaces for the multi-agent workflow system.
 * Mirrors backend Pydantic schemas in backend/om/workflows/models.py
 */

// Condition operators — single source of truth for frontend.
// Mirrors CONDITION_OPERATORS in backend/om/workflows/models.py
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

/** Orchestration modes a workflow can run in. */
export type OrchestrationMode = "sequential" | "llm_decision";

/** The condition shared by every conditional_router version. */
export interface RouterCondition {
  condition_field: string;
  operator: ConditionOperator;
  match_value: string;
  case_sensitive: boolean;
}

/**
 * conditional_router v1 (deprecated): branch targets are step orders, which
 * break when steps are re-ordered. Stored in the step's legacy `condition`.
 */
export interface ConditionConfig extends RouterCondition {
  true_steps: number[];
  false_steps: number[];
}

/**
 * conditional_router v2: branch targets are stable node keys. Stored in the
 * step's `config`. Targets must be steps that come after the router.
 */
export interface RouterConfigV2 extends RouterCondition {
  true_node_keys: string[];
  false_node_keys: string[];
}

/** Step-level override fields (null/absent = use the agent's own setting). */
export interface StepOverrides {
  llm_provider_override?: string | null;
  llm_model_override?: string | null;
  max_output_tokens_override?: number | null;
  system_prompt_override?: string | null;
  task_prompt_override?: string | null;
  tool_ids_override?: number[] | null;
  document_set_ids_override?: number[] | null;
  replace_base_system_prompt_override?: boolean | null;
}

export interface WorkflowStepSnapshot extends StepOverrides {
  id: number;
  workflow_id: number;
  /** Stable identity of the step within its workflow. */
  node_key: string;
  step_type: string;
  /** The node type version this step is pinned to. */
  type_version: number;
  latest_type_version: number;
  /** True when a newer version of the step's node type exists. */
  upgrade_available: boolean;
  /** Settings for node types that have no legacy columns. */
  config: Record<string, unknown> | null;
  /** node_key of the container (parallel, loop) holding this step. */
  parent_key?: string | null;
  /** Which branch of the container the step is in. */
  branch_index?: number | null;
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
  /** Bumped on every save; send it back as `expected_version` on update. */
  version: number;
  /** Engine behaviour level (1 = legacy semantics). */
  schema_version: number;
  created_at: string;
  updated_at: string;
  steps: WorkflowStepSnapshot[];
}

export interface WorkflowStepCreate extends StepOverrides {
  /** Send back unchanged for existing steps so the step keeps its identity. */
  node_key?: string;
  step_type?: string;
  /** Omit to use the latest version of `step_type`. */
  type_version?: number;
  config?: Record<string, unknown> | null;
  /** Container membership; send back unchanged (or containers flatten). */
  parent_key?: string | null;
  branch_index?: number | null;
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
  /** The loaded `version`; the server answers 409 if someone saved since. */
  expected_version?: number | null;
}

export interface StepExecutionRecord {
  step_id: number | null;
  agent_id: number | null;
  step_name: string;
  input_text: string;
  output_text: string;
  duration_ms: number;
  tokens_used: number;
}

export interface WorkflowExecutionSnapshot {
  id: number;
  workflow_id: number;
  /** Chat session UUID. */
  chat_session_id: string | null;
  user_id: string | null;
  status: string;
  steps_executed: StepExecutionRecord[] | null;
  total_tokens: number;
  total_duration_ms: number;
  error_message: string | null;
  started_at: string;
  completed_at: string | null;
}

// ── Node type catalog (GET /workflow/node-types) ──────────────────────────

/** One version of a node type, as described by the backend registry. */
export interface NodeTypeVersionInfo {
  version: number;
  label: string;
  description: string;
  category: string;
  /** JSON Schema (from the pydantic config model) of the node's `config`. */
  config_schema: Record<string, unknown>;
  /** Orchestration modes the node type may be used in. */
  modes: string[];
  can_pause: boolean;
  is_container: boolean;
  deprecated: boolean;
  /** True when configs of the previous version convert automatically. */
  upgradable_from_previous: boolean;
}

export interface NodeTypeInfo {
  type: string;
  latest_version: number;
  versions: NodeTypeVersionInfo[];
}

export interface NodeUpgradeRequest {
  from_version: number;
  config: Record<string, unknown>;
  /** Lets order-based configs (router v1) be rewritten to node keys. */
  step_order_to_node_key: Record<number, string>;
}

export interface NodeUpgradeResult {
  from_version: number;
  to_version: number;
  config: Record<string, unknown>;
}

// ── Workflow versions ─────────────────────────────────────────────────────

export interface WorkflowVersionSummary {
  version: number;
  schema_version: number;
  content_hash: string;
  created_by_id: string | null;
  created_at: string;
}

/** One node of a saved workflow definition. */
export interface WorkflowDefinitionNode {
  node_key: string;
  step_id: number | null;
  node_type: string;
  type_version: number;
  step_order: number;
  name: string;
  description: string | null;
  output_key: string;
  input_mapping: Record<string, unknown> | null;
  config: Record<string, unknown> | null;
  is_terminal: boolean;
  can_request_input: boolean;
  promote_output: boolean;
  parent_key?: string | null;
  branch_index?: number | null;
}

/** The immutable workflow document stored with each version. */
export interface WorkflowDefinition {
  definition_format: number;
  workflow_id: number;
  name: string;
  orchestration_mode: string;
  schema_version: number;
  timeout_seconds: number;
  nodes: WorkflowDefinitionNode[];
}

export interface WorkflowVersionDetail extends WorkflowVersionSummary {
  definition: WorkflowDefinition;
}
