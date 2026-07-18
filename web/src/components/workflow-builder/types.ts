/**
 * TypeScript types for the visual workflow builder.
 * Node/edge data structures used by React Flow.
 */

import type { Node, Edge } from "@xyflow/react";

// ── Node Data ──────────────────────────────────────────────────────────

/** Data stored on each agent node */
export interface AgentNodeData {
  agent_id: number;
  agent_name: string;
  step_name: string;
  step_description: string;
  output_key: string;
  is_terminal: boolean;
  can_request_input: boolean;
  promote_output: boolean;
  input_mapping?: Record<string, any> | null;
  condition?: Record<string, any> | null;

  // Step-level overrides (saved to backend, override agent defaults)
  // null/undefined = use agent default (inheritance)
  llm_provider_override?: string | null;
  llm_model_override?: string | null;
  max_output_tokens_override?: number | null;
  system_prompt_override?: string | null;
  task_prompt_override?: string | null;
  tool_ids_override?: number[] | null;
  document_set_ids_override?: number[] | null;
  replace_base_system_prompt_override?: boolean | null;

  // Display-only fields from the agent (not saved to backend)
  agent_description?: string;
  agent_icon_url?: string | null;
  agent_num_tools?: number;
  agent_tool_names?: string[];
  agent_llm_model?: string | null;
  agent_llm_provider?: string | null;
  agent_labels?: string[];

  // Visual state
  isSelected?: boolean;
  stepOrder?: number;
  orchestration_mode?: "sequential" | "llm_decision";
  [key: string]: unknown;
}

/** Data stored on each conditional router node */
export interface ConditionalRouterNodeData {
  step_name: string;
  step_description: string;
  output_key: string;
  condition_field: string;
  operator: string;
  match_value: string;
  case_sensitive: boolean;
  true_steps: number[];
  false_steps: number[];

  // Visual state
  isSelected?: boolean;
  stepOrder?: number;
  orchestration_mode?: "sequential" | "llm_decision";
  [key: string]: unknown;
}

/** Data stored on the orchestrator (start) node */
export interface OrchestratorNodeData {
  label: string;
  orchestration_mode: "sequential" | "llm_decision";
  [key: string]: unknown;
}

/** Data stored on edges */
export interface StepEdgeData {
  stepOrder?: number;
  condition?: Record<string, any> | null;
  orchestration_mode?: "sequential" | "llm_decision";
  /** "True" or "False" label for edges from conditional router nodes */
  branchLabel?: "True" | "False" | null;
  [key: string]: unknown;
}

// ── Typed Node/Edge aliases ────────────────────────────────────────────

export type AgentFlowNode = Node<AgentNodeData, "agent">;
export type OrchestratorFlowNode = Node<OrchestratorNodeData, "orchestrator">;
export type ConditionalRouterFlowNode = Node<ConditionalRouterNodeData, "conditional_router">;
export type WorkflowNode = AgentFlowNode | OrchestratorFlowNode | ConditionalRouterFlowNode;
export type WorkflowEdge = Edge<StepEdgeData>;

// ── Workflow meta (global settings, not per-node) ──────────────────────

export interface WorkflowMeta {
  name: string;
  description: string;
  orchestration_mode: "sequential" | "llm_decision";
  orchestrator_prompt: string;
  orchestrator_llm_provider: string;
  orchestrator_llm_model: string;
  max_steps: number;
  max_calls_per_agent: number;
  timeout_seconds: number;
  is_public: boolean;
  icon_name: string;
}

export const DEFAULT_WORKFLOW_META: WorkflowMeta = {
  name: "",
  description: "",
  orchestration_mode: "llm_decision",
  orchestrator_prompt: "",
  orchestrator_llm_provider: "",
  orchestrator_llm_model: "",
  max_steps: 10,
  max_calls_per_agent: 2,
  timeout_seconds: 1800,
  is_public: true,
  icon_name: "",
};

// ── Sidebar agent item (minimal data for drag) ──────────────────────

export interface DragAgentData {
  agent_id: number;
  agent_name: string;
  agent_description: string;
  agent_icon_url?: string | null;
  agent_num_tools: number;
  agent_tool_names?: string[];
  agent_llm_model?: string | null;
  agent_llm_provider?: string | null;
}

// ── Constants ──────────────────────────────────────────────────────────

export const ORCHESTRATOR_NODE_ID = "orchestrator";
export const NODE_WIDTH = 300;
export const NODE_HEIGHT_ESTIMATE = 200;
export const NODE_SPACING_X = 400;
export const NODE_SPACING_Y = 250;
