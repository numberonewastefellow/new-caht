/**
 * Pure utility functions for converting between React Flow graph state
 * and the WorkflowCreate/WorkflowSnapshot API payloads.
 */

import type { WorkflowSnapshot, WorkflowStepCreate } from "@/lib/workflows/interfaces";
import type {
  WorkflowNode,
  WorkflowEdge,
  AgentNodeData,
  ConditionalRouterNodeData,
  WorkflowMeta,
  OrchestratorNodeData,
} from "./types";
import {
  ORCHESTRATOR_NODE_ID,
  NODE_SPACING_X,
  NODE_SPACING_Y,
} from "./types";

export const FINISH_NODE_ID = "finish";

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

  // 2. Nodes from steps (sorted by step_order)
  const sortedSteps = [...workflow.steps].sort(
    (a, b) => a.step_order - b.step_order
  );

  sortedSteps.forEach((step, i) => {
    if (step.step_type === "conditional_router") {
      // Conditional router node
      const condition = step.condition || {};
      const nodeId = `condition-${step.id}`;
      nodes.push({
        id: nodeId,
        type: "conditional_router",
        position: { x: 0, y: 0 },
        data: {
          step_name: step.step_name,
          step_description: step.step_description || "",
          output_key: step.output_key || "output",
          condition_field: condition.condition_field || "",
          operator: condition.operator || "contains",
          match_value: condition.match_value || "",
          case_sensitive: condition.case_sensitive || false,
          true_steps: condition.true_steps || [],
          false_steps: condition.false_steps || [],
          stepOrder: i,
          orchestration_mode: mode,
        },
      } as WorkflowNode);
    } else {
      // Agent node (default)
      const nodeId = `agent-${step.id}`;
      nodes.push({
        id: nodeId,
        type: "agent",
        position: { x: 0, y: 0 },
        data: {
          agent_id: step.agent_id!,
          agent_name: step.agent_name || `Agent ${step.agent_id}`,
          step_name: step.step_name,
          step_description: step.step_description || "",
          output_key: step.output_key || "output",
          is_terminal: step.is_terminal,
          can_request_input: step.can_request_input,
          promote_output: step.promote_output,
          input_mapping: step.input_mapping,
          condition: step.condition,
          stepOrder: i,
          orchestration_mode: mode,
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
    }
  });

  // 3. Edges
  // Build a map of step_order → nodeId for conditional routing
  const stepOrderToNodeId = new Map<number, string>();
  sortedSteps.forEach((step) => {
    const prefix = step.step_type === "conditional_router" ? "condition" : "agent";
    stepOrderToNodeId.set(step.step_order, `${prefix}-${step.id}`);
  });

  const allStepNodeIds = sortedSteps.map((s) => {
    const prefix = s.step_type === "conditional_router" ? "condition" : "agent";
    return `${prefix}-${s.id}`;
  });

  if (mode === "sequential") {
    // Linear chain: orchestrator -> node[0] -> node[1] -> ...
    // But conditional routers break the chain with true/false branches
    allStepNodeIds.forEach((nodeId, i) => {
      const step = sortedSteps[i]!;

      // Check if this node is a target of a conditional router branch
      // If so, the conditional router already created the edge
      const isConditionalTarget = sortedSteps.some((s) => {
        if (s.step_type !== "conditional_router") return false;
        const cond = s.condition || {};
        const trueSteps: number[] = cond.true_steps || [];
        const falseSteps: number[] = cond.false_steps || [];
        return trueSteps.includes(step.step_order) || falseSteps.includes(step.step_order);
      });

      if (!isConditionalTarget) {
        const sourceId = i === 0 ? ORCHESTRATOR_NODE_ID : (allStepNodeIds[i - 1] ?? ORCHESTRATOR_NODE_ID);
        edges.push({
          id: `edge-${sourceId}-${nodeId}`,
          source: sourceId,
          target: nodeId,
          type: "step",
          data: { stepOrder: i, orchestration_mode: mode },
        });
      }

      // If this is a conditional router, create true/false branch edges
      if (step.step_type === "conditional_router") {
        const cond = step.condition || {};
        const trueSteps: number[] = cond.true_steps || [];
        const falseSteps: number[] = cond.false_steps || [];

        for (const targetOrder of trueSteps) {
          const targetId = stepOrderToNodeId.get(targetOrder);
          if (targetId) {
            edges.push({
              id: `edge-${nodeId}-true-${targetId}`,
              source: nodeId,
              sourceHandle: "true",
              target: targetId,
              type: "step",
              data: { orchestration_mode: mode, branchLabel: "True" },
            });
          }
        }
        for (const targetOrder of falseSteps) {
          const targetId = stepOrderToNodeId.get(targetOrder);
          if (targetId) {
            edges.push({
              id: `edge-${nodeId}-false-${targetId}`,
              source: nodeId,
              sourceHandle: "false",
              target: targetId,
              type: "step",
              data: { orchestration_mode: mode, branchLabel: "False" },
            });
          }
        }
      }
    });
  } else {
    // Star topology: orchestrator -> each agent (conditional routers not used in llm_decision)
    allStepNodeIds.forEach((nodeId, i) => {
      edges.push({
        id: `edge-${ORCHESTRATOR_NODE_ID}-${nodeId}`,
        source: ORCHESTRATOR_NODE_ID,
        target: nodeId,
        type: "step",
        data: { stepOrder: i, orchestration_mode: mode },
      });
    });
  }

  // 4. Add END node for sequential mode
  if (mode === "sequential" && allStepNodeIds.length > 0) {
    nodes.push({
      id: FINISH_NODE_ID,
      type: "finish" as any,
      position: { x: 0, y: 0 },
      deletable: false,
      selectable: false,
      data: {} as any,
    });
    const lastNodeId = allStepNodeIds[allStepNodeIds.length - 1]!;
    edges.push({
      id: `edge-${lastNodeId}-${FINISH_NODE_ID}`,
      source: lastNodeId,
      target: FINISH_NODE_ID,
      type: "step",
      data: { stepOrder: allStepNodeIds.length, orchestration_mode: mode },
    });
  }

  // 5. Auto-layout positions
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
  // Filter to step nodes (agent + conditional_router), exclude orchestrator/finish
  const stepNodes = nodes.filter(
    (n) => n.type === "agent" || n.type === "conditional_router"
  );
  // Filter edges to exclude finish node connections
  const stepEdges = edges.filter(
    (e) => e.target !== FINISH_NODE_ID && e.source !== FINISH_NODE_ID
  );

  // Compute step ordering via BFS from orchestrator
  const stepOrders = computeStepOrders(nodes, stepEdges);

  // Sort by computed step order
  const sorted = [...stepNodes].sort((a, b) => {
    const orderA = stepOrders.get(a.id) ?? 999;
    const orderB = stepOrders.get(b.id) ?? 999;
    return orderA - orderB;
  });

  const steps: WorkflowStepCreate[] = sorted.map((node, i) => {
    if (node.type === "conditional_router") {
      const data = node.data as ConditionalRouterNodeData;
      return {
        step_type: "conditional_router",
        agent_id: null,
        step_order: i,
        step_name: data.step_name || "Condition",
        step_description: data.step_description || null,
        output_key: data.output_key || "output",
        condition: {
          condition_field: data.condition_field || "",
          operator: data.operator || "contains",
          match_value: data.match_value || "",
          case_sensitive: data.case_sensitive || false,
          true_steps: data.true_steps || [],
          false_steps: data.false_steps || [],
        },
      };
    }

    // Agent node
    const data = node.data as AgentNodeData;
    return {
      step_type: "agent",
      agent_id: data.agent_id,
      step_order: i,
      step_name: data.step_name || data.agent_name,
      step_description: data.step_description || null,
      output_key: data.output_key || "output",
      input_mapping: data.input_mapping || null,
      condition: data.condition || null,
      is_terminal: data.is_terminal ?? false,
      can_request_input: data.can_request_input ?? false,
      promote_output: data.promote_output ?? false,
      // Step-level overrides
      llm_provider_override: data.llm_provider_override || null,
      llm_model_override: data.llm_model_override || null,
      max_output_tokens_override: data.max_output_tokens_override ?? null,
      system_prompt_override: data.system_prompt_override || null,
      task_prompt_override: data.task_prompt_override || null,
      tool_ids_override: data.tool_ids_override ?? null,
      document_set_ids_override: data.document_set_ids_override ?? null,
      replace_base_system_prompt_override: data.replace_base_system_prompt_override ?? null,
    };
  });

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

  // Assign remaining unvisited step nodes (disconnected)
  for (const node of nodes) {
    if ((node.type === "agent" || node.type === "conditional_router") && !orders.has(node.id)) {
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
  const agentNodes = nodes.filter((n) => n.type === "agent" || n.type === "conditional_router");
  const finishNode = nodes.find((n) => n.id === FINISH_NODE_ID);

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

    // Place finish node after the last agent
    if (finishNode && sorted.length > 0) {
      const lastAgent = updated[updated.length - 1]!;
      updated.push({
        ...finishNode,
        position: {
          x: lastAgent.position.x + NODE_SPACING_X,
          y: lastAgent.position.y,
        },
      } as WorkflowNode);
    }

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
        message: `Agent "${data.agent_name}" needs a step name`,
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
      outputKeys.set(key, data.agent_name);
    }
  }

  // Validate conditional router nodes
  const conditionNodes = nodes.filter((n) => n.type === "conditional_router");
  for (const node of conditionNodes) {
    const data = node.data as ConditionalRouterNodeData;
    if (!data.step_name?.trim()) {
      errors.push({
        nodeId: node.id,
        message: "Conditional router needs a step name",
      });
    }
    if (!data.condition_field?.trim()) {
      errors.push({
        nodeId: node.id,
        message: `Condition "${data.step_name}" needs a condition field`,
      });
    }
    // Check it has outgoing edges
    const outgoing = edges.filter((e) => e.source === node.id);
    if (outgoing.length === 0) {
      errors.push({
        nodeId: node.id,
        message: `Condition "${data.step_name}" needs at least one outgoing branch`,
      });
    }
    // Include in duplicate output key check
    const key = data.output_key || "output";
    if (outputKeys.has(key)) {
      errors.push({
        nodeId: node.id,
        message: `Duplicate output key "${key}" — also used by "${outputKeys.get(key)}"`,
      });
    } else {
      outputKeys.set(key, data.step_name);
    }
  }

  // Check for disconnected nodes (no incoming edge, exclude finish node)
  const allStepNodes = [...agentNodes, ...conditionNodes];
  const targetsWithEdges = new Set(edges.map((e) => e.target));
  for (const node of allStepNodes.filter((n) => n.id !== FINISH_NODE_ID)) {
    if (!targetsWithEdges.has(node.id)) {
      const name = node.type === "conditional_router"
        ? (node.data as ConditionalRouterNodeData).step_name
        : (node.data as AgentNodeData).agent_name;
      errors.push({
        nodeId: node.id,
        message: `"${name}" is not connected — draw an edge to it`,
      });
    }
  }

  return errors;
}
