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
import {
  depthFirst,
  groupByBlock,
  isTopLevel,
  type BlockPlace,
} from "@/lib/workflows/stepTree";
import { laneLabels } from "@/lib/workflows/containerLanes";
import { layoutWorkflow, type Size } from "./containerLayout";
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

/**
 * The edges of a workflow's steps: in Sequential mode each block is a chain and
 * router branches hang off their handles; in LLM Decision mode, a star.
 */
export function stepsToEdges(
  steps: readonly EditorStep[],
  mode: OrchestrationMode
): WorkflowEdge[] {
  const edges: WorkflowEdge[] = [];
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

    // Each block (the top level, or one container branch) is its own chain. The
    // top level starts at the Start node; a branch starts at its first step.
    for (const block of Array.from(groupByBlock(steps).values())) {
      block.forEach((step, position) => {
        const nodeId = step.node_key;
        if (branchTargetIds.has(nodeId)) return;
        const previous = block[position - 1];
        const sourceId = previous
          ? previous.node_key
          : isTopLevel(step)
            ? ORCHESTRATOR_NODE_ID
            : null;
        if (!sourceId) return;
        edges.push({
          id: `edge-${sourceId}-${nodeId}`,
          source: sourceId,
          target: nodeId,
          type: "step",
          data: {
            stepOrder: stepIds.indexOf(nodeId),
            orchestration_mode: mode,
          },
        });
      });
    }
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

  if (mode === "sequential" && stepIds.length > 0) {
    const topLevel = steps.filter(isTopLevel);
    const lastNodeId = topLevel[topLevel.length - 1]?.node_key ?? stepIds[stepIds.length - 1]!;
    edges.push({
      id: `edge-${lastNodeId}-${FINISH_NODE_ID}`,
      source: lastNodeId,
      target: FINISH_NODE_ID,
      type: "step",
      data: { stepOrder: stepIds.length, orchestration_mode: mode },
    });
  }
  return edges;
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

  // 2. One node per step, in execution order: containers come before their
  // children, as React Flow requires, and autoLayout puts children in their box.
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
  edges.push(...stepsToEdges(steps, mode));

  // 4. Add END node for sequential mode
  if (mode === "sequential" && steps.length > 0) {
    nodes.push({
      id: FINISH_NODE_ID,
      type: "finish",
      position: { x: 0, y: 0 },
      deletable: false,
      selectable: false,
      data: {},
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
 * The canvas as editor steps in execution order.
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

const AGENT_NODE_WIDTH = 300;
const AGENT_NODE_HEIGHT = 170;
const STEP_NODE_WIDTH = 260;
const STEP_NODE_HEIGHT = 100;
const START_NODE_GAP = 260;

function isContainerNode(node: StepFlowNode): boolean {
  return node.type === "container";
}

/** The order a step had when loaded or created (Infinity if unknown). */
function savedOrderOf(node: WorkflowNode | undefined): number {
  return node && isStepNode(node) && typeof node.data.stepOrder === "number"
    ? node.data.stepOrder
    : Infinity;
}

/** Which of two same-ready nodes runs first: saved order, then canvas position. */
function compareForOrder(a: StepFlowNode, b: StepFlowNode): number {
  const savedDiff = savedOrderOf(a) - savedOrderOf(b);
  if (savedDiff !== 0 && Number.isFinite(savedDiff)) return savedDiff;
  if (Number.isFinite(savedOrderOf(a)) !== Number.isFinite(savedOrderOf(b))) {
    return Number.isFinite(savedOrderOf(a)) ? -1 : 1;
  }
  // New nodes: X (column) first, then Y (row) for grid-aware ordering.
  const xDiff = a.position.x - b.position.x;
  if (Math.abs(xDiff) > 50) return xDiff;
  return a.position.y - b.position.y;
}

/**
 * One block's steps in execution order: a step runs once every step wired into it
 * has run, so wiring decides the order and loading then saving never changes it.
 * Edges from outside the block don't count. Steps caught in a cycle go last.
 */
function orderBlock(
  block: StepFlowNode[],
  edges: WorkflowEdge[]
): StepFlowNode[] {
  const ids = new Set(block.map((n) => n.id));
  const incoming = new Map(block.map((n) => [n.id, 0]));
  const outgoing = new Map<string, string[]>();
  for (const edge of edges) {
    if (!ids.has(edge.source) || !ids.has(edge.target)) continue;
    incoming.set(edge.target, (incoming.get(edge.target) ?? 0) + 1);
    outgoing.set(edge.source, [...(outgoing.get(edge.source) ?? []), edge.target]);
  }

  const remaining = new Map(block.map((n) => [n.id, n]));
  const ordered: StepFlowNode[] = [];
  while (remaining.size > 0) {
    const candidates = Array.from(remaining.values());
    const ready = candidates.filter((n) => (incoming.get(n.id) ?? 0) === 0);
    const next = (ready.length > 0 ? ready : candidates).sort(compareForOrder)[0]!;
    remaining.delete(next.id);
    ordered.push(next);
    for (const target of outgoing.get(next.id) ?? []) {
      incoming.set(target, (incoming.get(target) ?? 0) - 1);
    }
  }
  return ordered;
}

/**
 * The execution order of every step on the canvas: each block is ordered from its
 * own edges, then containers are followed by their branches.
 * Returns Map<nodeId, stepOrder>.
 */
export function computeStepOrders(
  nodes: WorkflowNode[],
  edges: WorkflowEdge[]
): Map<string, number> {
  const stepNodes = nodes.filter(isStepNode);
  const blocks = groupByBlock(
    stepNodes.map((node) => ({
      node_key: node.id,
      parent_key: node.data.parent_key,
      branch_index: node.data.branch_index,
      node,
    }))
  );
  const ordered = Array.from(blocks.values()).flatMap((block) => {
    const nodeOf = new Map(block.map((entry) => [entry.node.id, entry]));
    return orderBlock(block.map((entry) => entry.node), edges).map(
      (node) => nodeOf.get(node.id)!
    );
  });
  return new Map(depthFirst(ordered).map((entry, order) => [entry.node_key, order]));
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

  if (detectedMode === "sequential" && agentNodes.some(isContainerNode)) {
    return layoutWithContainers(orchestrator, agentNodes, finishNode, edges, nodes);
  }

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

/** The size a node is drawn at (the CSS widths; heights are typical). */
function drawnSize(node: StepFlowNode): Size {
  return node.type === "agent"
    ? { width: AGENT_NODE_WIDTH, height: AGENT_NODE_HEIGHT }
    : { width: STEP_NODE_WIDTH, height: STEP_NODE_HEIGHT };
}

/** Sequential workflows with containers: a row of steps and boxes. */
function layoutWithContainers(
  orchestrator: WorkflowNode,
  stepNodes: StepFlowNode[],
  finishNode: WorkflowNode | undefined,
  edges: WorkflowEdge[],
  nodes: WorkflowNode[]
): WorkflowNode[] {
  const orders = computeStepOrders(nodes, edges);
  const sorted = [...stepNodes].sort(
    (a, b) => (orders.get(a.id) ?? 999) - (orders.get(b.id) ?? 999)
  );
  const { placements, size } = layoutWorkflow(
    sorted.map((node) => ({
      node_key: node.id,
      parent_key: node.data.parent_key,
      branch_index: node.data.branch_index,
      size: drawnSize(node),
      lanes: isContainerNode(node)
        ? laneLabels(node.data, sorted.map((n) => n.data))
        : null,
    }))
  );

  const startX = 50 + START_NODE_GAP;
  const centerY = size.height / 2;
  const laidOut = sorted.map((node): WorkflowNode => {
    const placement = placements.get(node.id)!;
    const { parentId } = placement;
    return {
      ...node,
      position: parentId
        ? { x: placement.x, y: placement.y }
        : { x: startX + placement.x, y: placement.y },
      parentId: parentId ?? undefined,
      style: isContainerNode(node)
        ? { width: placement.size.width, height: placement.size.height }
        : node.style,
      data: { ...node.data, lanes: placement.lanes },
    };
  });

  return [
    { ...orchestrator, position: { x: 50, y: centerY - 60 } },
    ...laidOut,
    ...(finishNode
      ? [
          {
            ...finishNode,
            position: { x: startX + size.width + START_NODE_GAP / 2, y: centerY - 40 },
          } as WorkflowNode,
        ]
      : []),
  ];
}

/**
 * The canvas after a structural edit: nodes take the new steps, edges are rebuilt
 * from them, and everything is laid out again.
 */
export function graphFromSteps(
  nodes: WorkflowNode[],
  steps: readonly EditorStep[],
  mode: OrchestrationMode
): { nodes: WorkflowNode[]; edges: WorkflowEdge[] } {
  const byId = new Map(nodes.map((n) => [n.id, n]));
  const stepNodes = steps.flatMap((step, order): WorkflowNode[] => {
    const node = byId.get(step.node_key);
    if (!node || !isStepNode(node)) return [];
    const { parentId: _parentId, ...rest } = node;
    return [{ ...rest, data: { ...node.data, ...step, stepOrder: order } }];
  });
  const others = nodes.filter((n) => !isStepNode(n));
  const hasFinish = others.some((n) => n.id === FINISH_NODE_ID);
  const edges = stepsToEdges(steps, mode).filter(
    (e) => hasFinish || e.target !== FINISH_NODE_ID
  );
  return { nodes: autoLayout([...others, ...stepNodes], edges, mode), edges };
}

/** A node's position on the canvas, adding up the boxes around it. */
function absolutePosition(
  node: WorkflowNode,
  byId: ReadonlyMap<string, WorkflowNode>
): { x: number; y: number } {
  let { x, y } = node.position;
  let parent = node.parentId ? byId.get(node.parentId) : undefined;
  while (parent) {
    x += parent.position.x;
    y += parent.position.y;
    parent = parent.parentId ? byId.get(parent.parentId) : undefined;
  }
  return { x, y };
}

/** The center of a node on the canvas. */
export function nodeCenter(
  node: WorkflowNode,
  nodes: readonly WorkflowNode[]
): { x: number; y: number } {
  const { x, y } = absolutePosition(node, new Map(nodes.map((n) => [n.id, n])));
  return {
    x: x + (node.measured?.width ?? 0) / 2,
    y: y + (node.measured?.height ?? 0) / 2,
  };
}

/** The innermost container lane at a canvas point; null is the top level. */
export function laneAt(
  nodes: readonly WorkflowNode[],
  point: { x: number; y: number },
  exclude: ReadonlySet<string> = new Set()
): BlockPlace | null {
  const byId = new Map(nodes.map((n) => [n.id, n]));
  let found: BlockPlace | null = null;
  let foundDepth = -1;
  for (const node of nodes) {
    if (!isStepNode(node) || !isContainerNode(node) || exclude.has(node.id)) continue;
    const { x, y } = absolutePosition(node, byId);
    const width = Number(node.style?.width ?? 0);
    if (point.x < x || point.x > x + width) continue;
    (node.data.lanes ?? []).forEach((lane, branch) => {
      if (point.y < y + lane.y || point.y > y + lane.y + lane.height) return;
      let depth = 0;
      for (let p = node.parentId; p; p = byId.get(p)?.parentId) depth++;
      if (depth > foundDepth) {
        found = { parent_key: node.id, branch_index: branch };
        foundDepth = depth;
      }
    });
  }
  return found;
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
  const branchHeads = new Set(
    Array.from(groupByBlock(steps).values())
      .filter((block) => !isTopLevel(block[0]!))
      .map((block) => block[0]!.node_key)
  );
  for (const node of nodes.filter(isStepNode)) {
    if (!targetsWithEdges.has(node.id) && !branchHeads.has(node.id)) {
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
