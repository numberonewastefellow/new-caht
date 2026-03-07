/**
 * Pure utility functions for converting between React Flow graph state
 * and the WorkflowCreate/WorkflowSnapshot API payloads.
 */

import type { WorkflowSnapshot, WorkflowStepCreate } from "@/lib/workflows/interfaces";
import type {
  WorkflowNode,
  WorkflowEdge,
  AgentNodeData,
  WorkflowMeta,
  OrchestratorNodeData,
} from "./types";
import {
  ORCHESTRATOR_NODE_ID,
  NODE_SPACING_X,
  NODE_SPACING_Y,
} from "./types";

// ── Snapshot → Graph ───────────────────────────────────────────────────

/**
 * Convert a WorkflowSnapshot (from API) into React Flow nodes + edges.
 */
export function snapshotToGraph(workflow: WorkflowSnapshot): {
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
} {
  const mode = workflow.orchestration_mode as "sequential" | "llm_decision";
  const nodes: WorkflowNode[] = [];
  const edges: WorkflowEdge[] = [];

  // 1. Orchestrator node
  nodes.push({
    id: ORCHESTRATOR_NODE_ID,
    type: "orchestrator",
    position: { x: 0, y: 250 },
    deletable: false,
    data: {
      label: "Start",
      orchestration_mode: mode,
    },
  });

  // 2. Agent nodes from steps (sorted by step_order)
  const sortedSteps = [...workflow.steps].sort(
    (a, b) => a.step_order - b.step_order
  );

  sortedSteps.forEach((step, i) => {
    const nodeId = `agent-${step.id}`;
    nodes.push({
      id: nodeId,
      type: "agent",
      position: { x: 0, y: 0 }, // Will be set by autoLayout
      data: {
        persona_id: step.persona_id,
        persona_name: step.persona_name || `Agent ${step.persona_id}`,
        step_name: step.step_name,
        step_description: step.step_description || "",
        output_key: step.output_key || "output",
        is_terminal: step.is_terminal,
        can_request_input: step.can_request_input,
        promote_output: step.promote_output,
        input_mapping: step.input_mapping,
        condition: step.condition,
        stepOrder: i,
      },
    });
  });

  // 3. Edges
  const agentNodeIds = sortedSteps.map((s) => `agent-${s.id}`);

  if (mode === "sequential") {
    // Linear chain: orchestrator -> agent[0] -> agent[1] -> ...
    agentNodeIds.forEach((nodeId, i) => {
      const sourceId = i === 0 ? ORCHESTRATOR_NODE_ID : (agentNodeIds[i - 1] ?? ORCHESTRATOR_NODE_ID);
      edges.push({
        id: `edge-${sourceId}-${nodeId}`,
        source: sourceId,
        target: nodeId,
        type: "step",
        data: { stepOrder: i, orchestration_mode: mode },
      });
    });
  } else {
    // Star topology: orchestrator -> each agent
    agentNodeIds.forEach((nodeId, i) => {
      edges.push({
        id: `edge-${ORCHESTRATOR_NODE_ID}-${nodeId}`,
        source: ORCHESTRATOR_NODE_ID,
        target: nodeId,
        type: "step",
        data: { stepOrder: i, orchestration_mode: mode },
      });
    });
  }

  // 4. Auto-layout positions
  const laid = autoLayout(nodes, edges, mode);

  return { nodes: laid, edges };
}

// ── Graph → Payload ────────────────────────────────────────────────────

/**
 * Convert React Flow nodes + edges + meta into a WorkflowCreate payload.
 */
export function graphToPayload(
  nodes: WorkflowNode[],
  edges: WorkflowEdge[],
  meta: WorkflowMeta
): {
  name: string;
  description?: string | null;
  orchestration_mode: string;
  orchestrator_prompt?: string | null;
  orchestrator_llm_provider?: string | null;
  orchestrator_llm_model?: string | null;
  max_steps: number;
  max_calls_per_agent: number;
  timeout_seconds: number;
  is_public: boolean;
  icon_name?: string | null;
  steps: WorkflowStepCreate[];
} {
  const agentNodes = nodes.filter(
    (n): n is WorkflowNode & { data: AgentNodeData } => n.type === "agent"
  );

  // Compute step ordering via BFS from orchestrator
  const stepOrders = computeStepOrders(nodes, edges);

  // Sort agent nodes by computed step order
  const sorted = [...agentNodes].sort((a, b) => {
    const orderA = stepOrders.get(a.id) ?? 999;
    const orderB = stepOrders.get(b.id) ?? 999;
    return orderA - orderB;
  });

  const steps: WorkflowStepCreate[] = sorted.map((node, i) => ({
    persona_id: node.data.persona_id,
    step_order: i,
    step_name: node.data.step_name || node.data.persona_name,
    step_description: node.data.step_description || null,
    output_key: node.data.output_key || "output",
    input_mapping: node.data.input_mapping || null,
    condition: node.data.condition || null,
    is_terminal: node.data.is_terminal ?? false,
    can_request_input: node.data.can_request_input ?? false,
    promote_output: node.data.promote_output ?? false,
  }));

  return {
    name: meta.name,
    description: meta.description || null,
    orchestration_mode: meta.orchestration_mode,
    orchestrator_prompt: meta.orchestrator_prompt || null,
    orchestrator_llm_provider: meta.orchestrator_llm_provider || null,
    orchestrator_llm_model: meta.orchestrator_llm_model || null,
    max_steps: meta.max_steps,
    max_calls_per_agent: meta.max_calls_per_agent,
    timeout_seconds: meta.timeout_seconds,
    is_public: meta.is_public,
    icon_name: meta.icon_name || null,
    steps,
  };
}

// ── Step Order Computation ─────────────────────────────────────────────

/**
 * BFS from orchestrator node to determine step_order for each agent node.
 * Returns Map<nodeId, stepOrder>.
 */
export function computeStepOrders(
  nodes: WorkflowNode[],
  edges: WorkflowEdge[]
): Map<string, number> {
  const orders = new Map<string, number>();
  const adjacency = new Map<string, string[]>();

  // Build adjacency list
  for (const edge of edges) {
    const list = adjacency.get(edge.source) || [];
    list.push(edge.target);
    adjacency.set(edge.source, list);
  }

  // BFS from orchestrator
  const queue: string[] = [ORCHESTRATOR_NODE_ID];
  const visited = new Set<string>();
  let order = 0;

  while (queue.length > 0) {
    const current = queue.shift()!;
    if (visited.has(current)) continue;
    visited.add(current);

    if (current !== ORCHESTRATOR_NODE_ID) {
      orders.set(current, order++);
    }

    const neighbors = adjacency.get(current) || [];
    // Sort neighbors by their Y position for consistent ordering
    const nodeMap = new Map(nodes.map((n) => [n.id, n]));
    neighbors.sort((a, b) => {
      const posA = nodeMap.get(a)?.position.y ?? 0;
      const posB = nodeMap.get(b)?.position.y ?? 0;
      return posA - posB;
    });

    for (const neighbor of neighbors) {
      if (!visited.has(neighbor)) {
        queue.push(neighbor);
      }
    }
  }

  // Assign remaining unvisited agent nodes (disconnected)
  for (const node of nodes) {
    if (node.type === "agent" && !orders.has(node.id)) {
      orders.set(node.id, order++);
    }
  }

  return orders;
}

// ── Auto Layout ────────────────────────────────────────────────────────

/**
 * Position nodes in a left-to-right layout.
 * Sequential: linear chain.
 * LLM Decision: orchestrator on left, agents stacked vertically to the right.
 */
export function autoLayout(
  nodes: WorkflowNode[],
  edges: WorkflowEdge[],
  mode?: "sequential" | "llm_decision"
): WorkflowNode[] {
  const orchestrator = nodes.find((n) => n.id === ORCHESTRATOR_NODE_ID);
  const agentNodes = nodes.filter((n) => n.type === "agent");

  if (!orchestrator) return nodes;

  const detectedMode =
    mode || (orchestrator.data as OrchestratorNodeData).orchestration_mode;

  // Position orchestrator
  const updated: WorkflowNode[] = [
    { ...orchestrator, position: { x: 50, y: 250 } },
  ];

  if (detectedMode === "sequential") {
    // Linear chain: left to right
    const stepOrders = computeStepOrders(nodes, edges);
    const sorted = [...agentNodes].sort((a, b) => {
      const orderA = stepOrders.get(a.id) ?? 999;
      const orderB = stepOrders.get(b.id) ?? 999;
      return orderA - orderB;
    });

    sorted.forEach((node, i) => {
      updated.push({
        ...node,
        position: { x: 50 + (i + 1) * NODE_SPACING_X, y: 250 },
      });
    });
  } else {
    // Star layout: agents stacked vertically to the right of orchestrator
    const totalHeight = agentNodes.length * NODE_SPACING_Y;
    const startY = 250 - totalHeight / 2 + NODE_SPACING_Y / 2;

    agentNodes.forEach((node, i) => {
      updated.push({
        ...node,
        position: { x: 50 + NODE_SPACING_X, y: startY + i * NODE_SPACING_Y },
      });
    });
  }

  return updated;
}

// ── Validation ─────────────────────────────────────────────────────────

export interface ValidationError {
  nodeId?: string;
  message: string;
}

/**
 * Validate the graph before saving.
 * Returns an array of errors (empty = valid).
 */
export function validateGraph(
  nodes: WorkflowNode[],
  edges: WorkflowEdge[],
  meta: WorkflowMeta
): ValidationError[] {
  const errors: ValidationError[] = [];

  // Must have a name
  if (!meta.name.trim()) {
    errors.push({ message: "Workflow name is required" });
  }

  // Must have at least one agent node
  const agentNodes = nodes.filter((n) => n.type === "agent");
  if (agentNodes.length === 0) {
    errors.push({ message: "Add at least one agent to the workflow" });
  }

  // Each agent must have a step_name
  for (const node of agentNodes) {
    const data = node.data as AgentNodeData;
    if (!data.step_name?.trim()) {
      errors.push({
        nodeId: node.id,
        message: `Agent "${data.persona_name}" needs a step name`,
      });
    }
  }

  // Check for duplicate output keys
  const outputKeys = new Map<string, string>();
  for (const node of agentNodes) {
    const data = node.data as AgentNodeData;
    const key = data.output_key || "output";
    if (outputKeys.has(key)) {
      errors.push({
        nodeId: node.id,
        message: `Duplicate output key "${key}" — also used by "${outputKeys.get(key)}"`,
      });
    } else {
      outputKeys.set(key, data.persona_name);
    }
  }

  // Check for disconnected agents (no incoming edge)
  const targetsWithEdges = new Set(edges.map((e) => e.target));
  for (const node of agentNodes) {
    if (!targetsWithEdges.has(node.id)) {
      errors.push({
        nodeId: node.id,
        message: `Agent "${(node.data as AgentNodeData).persona_name}" is not connected — draw an edge to it`,
      });
    }
  }

  return errors;
}
