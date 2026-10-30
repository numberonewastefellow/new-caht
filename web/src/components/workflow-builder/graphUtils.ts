/**
 * Pure utility functions for converting between React Flow graph state and
 * the workflow API payloads. The step data itself is converted by the shared
 * `@/lib/workflows/serializer` (also used by the Wizard); this module only
 * adds what is specific to the canvas: node/edge layout, step ordering from
 * edges, and router branches expressed as edges.
 */

import type {
  OrchestrationMode,
  WorkflowCreate,
  WorkflowSnapshot,
  WorkflowUpdate,
} from "@/lib/workflows/interfaces";
import {
  type EditorStep,
  type WorkflowMeta,
  containerInfo,
} from "@/lib/workflows/editorModel";
import {
  type NodeCatalog,
  ROUTER_NODE_TYPE,
  editorKindFor,
  isAllowedInMode,
  labelFor,
  latestVersion,
} from "@/lib/workflows/nodeRegistry";
import {
  type RouterBranch,
  branchTargets,
  normalizeRouterConfig,
  withBranchTargets,
} from "@/lib/workflows/routerConfig";
import {
  buildWorkflowCreate,
  buildWorkflowUpdate,
  snapshotToEditorSteps,
} from "@/lib/workflows/serializer";
import { validateSteps } from "@/lib/workflows/validation";
import type {
  WorkflowNode,
  WorkflowEdge,
  StepFlowNode,
  StepNodeData,
  OrchestratorNodeData,
} from "./types";
import {
  FINISH_NODE_ID,
  ORCHESTRATOR_NODE_ID,
  NODE_SPACING_X,
  NODE_SPACING_Y,
  isStepNode,
} from "./types";

export { FINISH_NODE_ID } from "./types";

const ROUTER_BRANCHES: readonly RouterBranch[] = ["true", "false"];

// ── Step nodes ─────────────────────────────────────────────────────────

/**
 * A React Flow node for an editor step. Its id is the step's node key and its
 * React Flow type is the editor kind of its node type (see nodeUi.tsx).
 */
export function stepToFlowNode(
  step: EditorStep,
  catalog: NodeCatalog,
  extra: Partial<StepNodeData> = {},
  position = { x: 0, y: 0 }
): StepFlowNode {
  return {
    id: step.node_key,
    type: editorKindFor(catalog, step.step_type),
    position,
    data: {
      ...step,
      type_label: labelFor(catalog, step.step_type, step.type_version),
      type_description: latestVersion(catalog, step.step_type)?.description,
      ...extra,
    },
  };
}

function branchEdge(
  routerId: string,
  branch: RouterBranch,
  targetId: string,
  mode: OrchestrationMode
): WorkflowEdge {
  return {
    id: `edge-${routerId}-${branch}-${targetId}`,
    source: routerId,
    sourceHandle: branch,
    target: targetId,
    type: "step",
    data: {
      orchestration_mode: mode,
      branchLabel: branch === "true" ? "True" : "False",
    },
  };
}

// ── Snapshot → Graph ───────────────────────────────────────────────────

/**
 * Convert a WorkflowSnapshot (from API) into React Flow nodes + edges.
 */
export function snapshotToGraph(
  workflow: WorkflowSnapshot,
  catalog: NodeCatalog
): {
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
} {
  const mode: OrchestrationMode =
    workflow.orchestration_mode === "sequential" ? "sequential" : "llm_decision";
  const steps = snapshotToEditorSteps(workflow);
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

  // 2. One node per step, in execution order. Container children are shown
  // as normal nodes in order (group nodes come later) and keep their
  // parent_key/branch_index so a save doesn't flatten the container.
  steps.forEach((step, i) => {
    const { childCount, containerName } = containerInfo(step, steps);
    nodes.push(
      stepToFlowNode(step, catalog, {
        childCount,
        containerName,
        stepOrder: i,
        orchestration_mode: mode,
        modeConflict: !isAllowedInMode(
          catalog,
          step.step_type,
          step.type_version,
          mode
        ),
      })
    );
  });

  // 3. Edges
  const stepIds = steps.map((s) => s.node_key);

  if (mode === "sequential") {
    // Router branch targets hang off the router's True/False handles;
    // every other step chains from the step before it.
    const branchTargetIds = new Set<string>();
    for (const step of steps) {
      if (step.step_type !== ROUTER_NODE_TYPE) continue;
      const config = normalizeRouterConfig(step.config);
      for (const branch of ROUTER_BRANCHES) {
        for (const targetId of branchTargets(config, branch)) {
          if (!stepIds.includes(targetId)) continue;
          branchTargetIds.add(targetId);
          edges.push(branchEdge(step.node_key, branch, targetId, mode));
        }
      }
    }

    stepIds.forEach((nodeId, i) => {
      if (branchTargetIds.has(nodeId)) return;
      const sourceId = i === 0 ? ORCHESTRATOR_NODE_ID : stepIds[i - 1]!;
      edges.push({
        id: `edge-${sourceId}-${nodeId}`,
        source: sourceId,
        target: nodeId,
        type: "step",
        data: { stepOrder: i, orchestration_mode: mode },
      });
    });
  } else {
    // Star topology: orchestrator -> each step
    stepIds.forEach((nodeId, i) => {
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
  if (mode === "sequential" && stepIds.length > 0) {
    nodes.push({
      id: FINISH_NODE_ID,
      type: "finish",
      position: { x: 0, y: 0 },
      deletable: false,
      selectable: false,
      data: {},
    });
    const lastNodeId = stepIds[stepIds.length - 1]!;
    edges.push({
      id: `edge-${lastNodeId}-${FINISH_NODE_ID}`,
      source: lastNodeId,
      target: FINISH_NODE_ID,
      type: "step",
      data: { stepOrder: stepIds.length, orchestration_mode: mode },
    });
  }

  // 5. Auto-layout positions
  const laid = autoLayout(nodes, edges, mode);

  return { nodes: laid, edges };
}

// ── Graph → Steps / Payload ────────────────────────────────────────────

function withoutFinish(edges: WorkflowEdge[]): WorkflowEdge[] {
  return edges.filter(
    (e) => e.target !== FINISH_NODE_ID && e.source !== FINISH_NODE_ID
  );
}

/** A router's config with branch targets read from its True/False edges. */
function routerConfigFromEdges(
  node: StepFlowNode,
  edges: WorkflowEdge[],
  stepIds: ReadonlySet<string>
): Record<string, unknown> {
  let config = normalizeRouterConfig(node.data.config);
  for (const branch of ROUTER_BRANCHES) {
    const targets = edges
      .filter(
        (e) =>
          e.source === node.id &&
          e.sourceHandle === branch &&
          stepIds.has(e.target)
      )
      .map((e) => e.target);
    config = withBranchTargets(config, branch, Array.from(new Set(targets)));
  }
  return { ...config };
}

/**
 * The canvas as editor steps in execution order (BFS from the start node).
 * Router branch targets come from the router's outgoing edges, so what the
 * canvas shows is what gets saved.
 */
export function graphToSteps(
  nodes: WorkflowNode[],
  edges: WorkflowEdge[]
): EditorStep[] {
  const stepNodes = nodes.filter(isStepNode);
  const stepEdges = withoutFinish(edges);
  const stepOrders = computeStepOrders(nodes, stepEdges);
  const stepIds = new Set(stepNodes.map((n) => n.id));

  return [...stepNodes]
    .sort(
      (a, b) => (stepOrders.get(a.id) ?? 999) - (stepOrders.get(b.id) ?? 999)
    )
    .map((node) =>
      node.data.step_type === ROUTER_NODE_TYPE
        ? {
            ...node.data,
            config: routerConfigFromEdges(node, stepEdges, stepIds),
          }
        : node.data
    );
}

/**
 * Convert React Flow nodes + edges + meta into a create payload.
 */
export function graphToPayload(
  nodes: WorkflowNode[],
  edges: WorkflowEdge[],
  meta: WorkflowMeta
): WorkflowCreate {
  return buildWorkflowCreate(meta, graphToSteps(nodes, edges));
}

/** An update payload; `expectedVersion` guards against concurrent saves. */
export function graphToUpdatePayload(
  nodes: WorkflowNode[],
  edges: WorkflowEdge[],
  meta: WorkflowMeta,
  expectedVersion: number | null
): WorkflowUpdate {
  return buildWorkflowUpdate(
    meta,
    graphToSteps(nodes, edges),
    expectedVersion
  );
}

// ── Step Order Computation ─────────────────────────────────────────────

/** The order a step had when loaded or created (Infinity if unknown). */
function savedOrderOf(node: WorkflowNode | undefined): number {
  return node && isStepNode(node) && typeof node.data.stepOrder === "number"
    ? node.data.stepOrder
    : Infinity;
}

/**
 * BFS from orchestrator node to determine step_order for each step node.
 * Returns Map<nodeId, stepOrder>.
 */
export function computeStepOrders(
  nodes: WorkflowNode[],
  edges: WorkflowEdge[]
): Map<string, number> {
  const orders = new Map<string, number>();
  const adjacency = new Map<string, string[]>();
  const nodeMap = new Map(nodes.map((n) => [n.id, n]));

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

    const currentNode = nodeMap.get(current);
    if (currentNode && isStepNode(currentNode)) {
      orders.set(current, order++);
    }

    const neighbors = adjacency.get(current) || [];
    // Siblings (e.g. router branches) keep their saved order, so loading and
    // saving never re-orders steps; ties (new nodes) fall back to position:
    // X (column) first, then Y (row) for grid-aware ordering.
    neighbors.sort((a, b) => {
      const nodeA = nodeMap.get(a);
      const nodeB = nodeMap.get(b);
      const savedDiff = savedOrderOf(nodeA) - savedOrderOf(nodeB);
      if (savedDiff !== 0 && Number.isFinite(savedDiff)) return savedDiff;
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
    if (isStepNode(node) && !orders.has(node.id)) {
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
  const agentNodes = nodes.filter(isStepNode);
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
 * Validate the graph before saving: the shared step rules (same as the
 * Wizard) plus canvas-specific connectivity checks.
 * Returns an array of errors (empty = valid).
 */
export function validateGraph(
  nodes: WorkflowNode[],
  edges: WorkflowEdge[],
  meta: WorkflowMeta,
  catalog: NodeCatalog
): ValidationError[] {
  const errors: ValidationError[] = [];

  if (!meta.name.trim()) {
    errors.push({ message: "Workflow name is required" });
  }

  // Node ids are node keys, so step errors map straight onto nodes.
  const steps = graphToSteps(nodes, edges);
  for (const error of validateSteps(steps, meta.orchestration_mode, catalog)) {
    errors.push({ nodeId: error.nodeKey, message: error.message });
  }

  // Check for disconnected nodes (no incoming edge)
  const targetsWithEdges = new Set(edges.map((e) => e.target));
  for (const node of nodes.filter(isStepNode)) {
    if (!targetsWithEdges.has(node.id)) {
      const name =
        node.data.step_name || node.data.agent_name || node.data.type_label;
      errors.push({
        nodeId: node.id,
        message: `"${name ?? "Step"}" is not connected — draw an edge to it`,
      });
    }
  }

  return errors;
}
