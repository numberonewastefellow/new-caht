/**
 * TypeScript types for the visual workflow builder.
 * Node/edge data structures used by React Flow.
 */

import type { ComponentType } from "react";
import type { Node, Edge } from "@xyflow/react";
import type { MinimalAgentSnapshot } from "@/app/admin/assistants/interfaces";
import type { ToolSnapshot } from "@/lib/tools/interfaces";
import type { DocumentSetSummary } from "@/lib/types";
import type { LLMProviderDescriptor } from "@/app/admin/configuration/llm/interfaces";
import type { OrchestrationMode } from "@/lib/workflows/interfaces";
import type { EditorStep } from "@/lib/workflows/editorModel";
import type { NodeCatalog, NodeEditorKind } from "@/lib/workflows/nodeRegistry";
import type { BlockPlace } from "@/lib/workflows/stepTree";
import type { LaneBox } from "./containerLayout";

export type { WorkflowMeta } from "@/lib/workflows/editorModel";
export { DEFAULT_WORKFLOW_META } from "@/lib/workflows/editorModel";

// ── Node Data ──────────────────────────────────────────────────────────

/** Display-only data on a step node (never saved). */
export interface StepNodeDisplay {
  // From the agent (agent steps)
  agent_description?: string;
  agent_icon_url?: string | null;
  agent_num_tools?: number;
  agent_tool_names?: string[];
  agent_llm_model?: string | null;
  agent_llm_provider?: string | null;
  agent_labels?: string[];

  // From the node type catalog
  type_label?: string;
  type_description?: string;

  // Visual state
  isSelected?: boolean;
  stepOrder?: number;
  orchestration_mode?: OrchestrationMode;
  /** The step's type is not allowed in the workflow's orchestration mode. */
  modeConflict?: boolean;
  /** Containers: steps inside it. Children: the container they're in. */
  childCount?: number;
  containerName?: string | null;
  /** Containers: the lanes drawn inside the box (see containerLayout.ts). */
  lanes?: LaneBox[] | null;
}

/**
 * Data of every step node, whatever its type: the shared editor step model
 * (saved through `serializer.ts`) plus display-only fields. Router branch
 * targets are derived from the node's outgoing edges when saving.
 */
export type StepNodeData = EditorStep &
  StepNodeDisplay & { [key: string]: unknown };

/** Kept for the agent config panel, which predates other node types. */
export type AgentNodeData = StepNodeData;

/** Data stored on the orchestrator (start) node */
export interface OrchestratorNodeData {
  label: string;
  orchestration_mode: OrchestrationMode;
  [key: string]: unknown;
}

/** Data stored on edges */
export interface StepEdgeData {
  stepOrder?: number;
  condition?: Record<string, any> | null;
  orchestration_mode?: OrchestrationMode;
  /** "True" or "False" label for edges from conditional router nodes */
  branchLabel?: "True" | "False" | null;
  [key: string]: unknown;
}

// ── Typed Node/Edge aliases ────────────────────────────────────────────

/** A step node; its React Flow `type` is the editor kind of its node type. */
export type StepFlowNode = Node<StepNodeData, NodeEditorKind>;
export type OrchestratorFlowNode = Node<OrchestratorNodeData, "orchestrator">;
export type FinishFlowNode = Node<Record<string, never>, "finish">;
export type WorkflowNode = StepFlowNode | OrchestratorFlowNode | FinishFlowNode;
export type WorkflowEdge = Edge<StepEdgeData>;

export function isStepNode(node: WorkflowNode): node is StepFlowNode {
  return node.type !== "orchestrator" && node.type !== "finish";
}

// ── Config panel contract (one panel component per editor kind) ────────

export interface StepConfigPanelProps {
  nodeId: string;
  data: StepNodeData;
  catalog: NodeCatalog;
  agents: MinimalAgentSnapshot[];
  availableTools: ToolSnapshot[];
  documentSets: DocumentSetSummary[];
  llmProviders: LLMProviderDescriptor[];
  onUpdate: (nodeId: string, partial: Partial<StepNodeData>) => void;
  onDelete: (nodeId: string) => void;
  /** Remove a container but keep its steps, in its place. */
  onDeleteKeepingSteps?: (nodeId: string) => void;
  onClose: () => void;
  onToggleCollapse?: () => void;
  /** The workflow's steps, in execution order. */
  steps: EditorStep[];
  onMove: (nodeId: string, place: BlockPlace) => void;
  /** A container's settings changed; its lanes may need redrawing. */
  onContainerConfig: (
    nodeId: string,
    config: Record<string, unknown>,
    removedBranch?: number
  ) => void;
}

export type StepConfigPanel = ComponentType<StepConfigPanelProps>;

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
export const FINISH_NODE_ID = "finish";

/** Drag-and-drop payload types from the sidebar onto the canvas. */
export const AGENT_DRAG_MIME = "application/reactflow";
export const NODE_TYPE_DRAG_MIME = "application/reactflow-node-type";
export const NODE_WIDTH = 300;
export const NODE_HEIGHT_ESTIMATE = 200;
export const NODE_SPACING_X = 400;
export const NODE_SPACING_Y = 250;
