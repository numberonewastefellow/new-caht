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
        // Step-level overrides
        llm_provider_override: step.llm_provider_override ?? null,
        llm_model_override: step.llm_model_override ?? null,
        max_output_tokens_override: step.max_output_tokens_override ?? null,
        system_prompt_override: step.system_prompt_override ?? null,
        task_prompt_override: step.task_prompt_override ?? null,
        tool_ids_override: step.tool_ids_override ?? null,
        document_set_ids_override: step.document_set_ids_override ?? null,
        replace_base_system_prompt_override: step.replace_base_system_prompt_override ?? null,
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
    // Step-level overrides
    llm_provider_override: node.data.llm_provider_override || null,
    llm_model_override: node.data.llm_model_override || null,
    max_output_tokens_override: node.data.max_output_tokens_override ?? null,
    system_prompt_override: node.data.system_prompt_override || null,
    task_prompt_override: node.data.task_prompt_override || null,
    tool_ids_override: node.data.tool_ids_override ?? null,
    document_set_ids_override: node.data.document_set_ids_override ?? null,
    replace_base_system_prompt_override: node.data.replace_base_system_prompt_override ?? null,
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
    // Sort neighbors by X (column) first, then Y (row) for grid-aware ordering
    const nodeMap = new Map(nodes.map((n) => [n.id, n]));
    neighbors.sort((a, b) => {
      const nodeA = nodeMap.get(a);
      const nodeB = nodeMap.get(b);
      const xDiff = (nodeA?.position.x ?? 0) - (nodeB?.position.x ?? 0);
      if (Math.abs(xDiff) > 50) return xDiff;
      return (nodeA?.position.y ?? 0) - (nodeB?.position.y ?? 0);
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
 * Determine optimal grid columns based on agent count.
 * Aims to keep the layout compact and readable.
 */
function getGridColumns(count: number, mode: "sequential" | "llm_decision"): number {
  if (mode === "sequential") {
    // Sequential: wider rows since we read left-to-right
    if (count <= 3) return count;
    if (count <= 8) return 3;
    if (count <= 12) return 4;
    return 5;
  } else {
    // LLM Decision: prefer taller columns since all fan from orchestrator
    if (count <= 5) return 1;
    if (count <= 10) return 2;
    if (count <= 18) return 3;
    return 4;
  }
}

/**
 * Position nodes in an enterprise-grade grid layout.
 *
 * Sequential mode: Multi-row grid flowing left-to-right, top-to-bottom.
 *   Orchestrator connects to first node; nodes chain through rows.
 *   [START] → [A1] → [A2] → [A3]
 *             [A4] → [A5] → [A6]
 *
 * LLM Decision mode: Multi-column fan from orchestrator.
 *   Orchestrator centered on the left, agents in balanced columns.
 *   [START] →  [A1]  [A4]  [A7]
 *              [A2]  [A5]  [A8]
 *              [A3]  [A6]  [A9]
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

  const count = agentNodes.length;
  if (count === 0) {
    return [{ ...orchestrator, position: { x: 50, y: 250 } }];
  }

  const updated: WorkflowNode[] = [];

  if (detectedMode === "sequential") {
    // ── Sequential: Grid flowing left-to-right, top-to-bottom ──
    const cols = getGridColumns(count, "sequential");
    const rows = Math.ceil(count / cols);

    const stepOrders = computeStepOrders(nodes, edges);
    const sorted = [...agentNodes].sort((a, b) =>
      (stepOrders.get(a.id) ?? 999) - (stepOrders.get(b.id) ?? 999)
    );

    const gridStartX = 50 + NODE_SPACING_X;
    const totalHeight = rows * NODE_SPACING_Y;
    const gridStartY = 250 - totalHeight / 2 + NODE_SPACING_Y / 2;

    sorted.forEach((node, i) => {
      const row = Math.floor(i / cols);
      const col = i % cols;
      updated.push({
        ...node,
        position: {
          x: gridStartX + col * NODE_SPACING_X,
          y: gridStartY + row * NODE_SPACING_Y,
        },
      });
    });

    // Center orchestrator vertically relative to all rows
    const orchY = gridStartY + (rows - 1) * NODE_SPACING_Y / 2;
    updated.unshift({ ...orchestrator, position: { x: 50, y: orchY } });

  } else {
    // ── LLM Decision: Multi-column fan from orchestrator ──
    const numCols = getGridColumns(count, "llm_decision");
    // Distribute agents evenly across columns (balance from left)
    const basePerCol = Math.floor(count / numCols);
    const extraCols = count % numCols;

    let agentIdx = 0;
    let globalMinY = Infinity;
    let globalMaxY = -Infinity;

    for (let col = 0; col < numCols; col++) {
      // First `extraCols` columns get one extra agent for even distribution
      const colCount = basePerCol + (col < extraCols ? 1 : 0);
      const colHeight = colCount * NODE_SPACING_Y;
      const colStartY = 250 - colHeight / 2 + NODE_SPACING_Y / 2;

      for (let row = 0; row < colCount; row++) {
        const y = colStartY + row * NODE_SPACING_Y;
        const node = agentNodes[agentIdx]!;
        updated.push({
          ...node,
          id: node.id,
          position: {
            x: 50 + (col + 1) * NODE_SPACING_X,
            y,
          },
        } as WorkflowNode);
        globalMinY = Math.min(globalMinY, y);
        globalMaxY = Math.max(globalMaxY, y);
        agentIdx++;
      }
    }

    // Center orchestrator vertically across the full span of agents
    const orchY = (globalMinY + globalMaxY) / 2;
    updated.unshift({ ...orchestrator, position: { x: 50, y: orchY } });
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
