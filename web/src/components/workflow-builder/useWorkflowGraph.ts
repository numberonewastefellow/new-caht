/**
 * Central state management hook for the visual workflow builder.
 * Manages React Flow nodes/edges and workflow metadata,
 * and converts between graph state and API payloads.
 */

"use client";

import { useCallback, useMemo, useState } from "react";
import {
  useNodesState,
  useEdgesState,
  type OnNodesChange,
  type OnEdgesChange,
  type OnConnect,
  type Connection,
  addEdge,
} from "@xyflow/react";
import type {
  NodeUpgradeResult,
  WorkflowSnapshot,
} from "@/lib/workflows/interfaces";
import {
  createEditorStep,
  newNodeKey,
  nextOutputKey,
} from "@/lib/workflows/editorModel";
import {
  type NodeCatalog,
  AGENT_NODE_TYPE,
  ROUTER_NODE_TYPE,
  isAllowedInMode,
  labelFor,
} from "@/lib/workflows/nodeRegistry";
import { snapshotToMeta } from "@/lib/workflows/serializer";
import { stepsNotAllowedInMode } from "@/lib/workflows/validation";
import type {
  WorkflowNode,
  WorkflowEdge,
  StepNodeData,
  WorkflowMeta,
  DragAgentData,
} from "./types";
import {
  DEFAULT_WORKFLOW_META,
  FINISH_NODE_ID,
  ORCHESTRATOR_NODE_ID,
  isStepNode,
} from "./types";
import {
  snapshotToGraph,
  graphToPayload,
  graphToSteps,
  graphToUpdatePayload,
  stepToFlowNode,
  validateGraph,
  autoLayout,
} from "./graphUtils";

// ── Initial state: just the orchestrator node ──────────────────────────

const INITIAL_NODES: WorkflowNode[] = [
  {
    id: ORCHESTRATOR_NODE_ID,
    type: "orchestrator",
    position: { x: 50, y: 250 },
    deletable: false,
    data: {
      label: "Start",
      orchestration_mode: "llm_decision",
    },
  },
];

const INITIAL_EDGES: WorkflowEdge[] = [];

// ── Hook ───────────────────────────────────────────────────────────────

/** @param catalog the backend node type catalog (see useNodeTypes) */
export function useWorkflowGraph(catalog: NodeCatalog) {
  const [nodes, setNodes, onNodesChange] =
    useNodesState<WorkflowNode>(INITIAL_NODES);
  const [edges, setEdges, onEdgesChange] =
    useEdgesState<WorkflowEdge>(INITIAL_EDGES);
  const [meta, setMeta] = useState<WorkflowMeta>({ ...DEFAULT_WORKFLOW_META });
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  /** The saved version the canvas is based on (sent as expected_version). */
  const [baseVersion, setBaseVersion] = useState<number | null>(null);

  const stepNodes = useMemo(() => nodes.filter(isStepNode), [nodes]);
  const takenKeys = useCallback(
    () => stepNodes.map((n) => n.id),
    [stepNodes]
  );

  // ── Add agent node (from sidebar drag-drop) ──────────────────────

  const addAgentNode = useCallback(
    (agent: DragAgentData, position: { x: number; y: number }) => {
      const agentCount = stepNodes.filter(
        (n) => n.data.step_type === AGENT_NODE_TYPE
      ).length;
      const step = createEditorStep(AGENT_NODE_TYPE, catalog, {
        node_key: newNodeKey(takenKeys()),
        agent_id: agent.agent_id,
        agent_name: agent.agent_name,
        step_name: agent.agent_name,
        step_description: agent.agent_description || "",
        output_key: nextOutputKey("step", stepNodes.map((n) => n.data)),
      });
      const newNode = stepToFlowNode(
        step,
        catalog,
        {
          agent_description: agent.agent_description,
          agent_icon_url: agent.agent_icon_url,
          agent_num_tools: agent.agent_num_tools,
          agent_tool_names: agent.agent_tool_names || [],
          agent_llm_model: agent.agent_llm_model || null,
          agent_llm_provider: agent.agent_llm_provider || null,
          stepOrder: agentCount,
          orchestration_mode: meta.orchestration_mode,
        },
        position
      );

      setNodes((nds) => [...nds, newNode]);
      return newNode.id;
    },
    [stepNodes, takenKeys, catalog, meta.orchestration_mode, setNodes]
  );

  // ── Add a node of any other type (from the Utils palette) ─────────

  const addTypedNode = useCallback(
    (stepType: string, position: { x: number; y: number }) => {
      const stepCount = stepNodes.length;
      const step = createEditorStep(stepType, catalog, {
        node_key: newNodeKey(takenKeys()),
        step_name: `${labelFor(catalog, stepType)} ${stepCount + 1}`,
        output_key: nextOutputKey(
          stepType === ROUTER_NODE_TYPE ? "condition" : stepType,
          stepNodes.map((n) => n.data)
        ),
      });
      const newNode = stepToFlowNode(
        step,
        catalog,
        {
          stepOrder: stepCount,
          orchestration_mode: meta.orchestration_mode,
          modeConflict: !isAllowedInMode(
            catalog,
            stepType,
            step.type_version,
            meta.orchestration_mode
          ),
        },
        position
      );

      setNodes((nds) => [...nds, newNode]);
      return newNode.id;
    },
    [stepNodes, takenKeys, catalog, meta.orchestration_mode, setNodes]
  );

  // ── Remove node ──────────────────────────────────────────────────

  const removeNode = useCallback(
    (nodeId: string) => {
      if (nodeId === ORCHESTRATOR_NODE_ID || nodeId === FINISH_NODE_ID) return;
      setNodes((nds) => nds.filter((n) => n.id !== nodeId));
      setEdges((eds) =>
        eds.filter((e) => e.source !== nodeId && e.target !== nodeId)
      );
      if (selectedNodeId === nodeId) setSelectedNodeId(null);
    },
    [setNodes, setEdges, selectedNodeId]
  );

  // ── Update node data ─────────────────────────────────────────────

  const updateNodeData = useCallback(
    (nodeId: string, partial: Partial<StepNodeData>) => {
      setNodes((nds) =>
        nds.map((n) => {
          if (n.id !== nodeId || !isStepNode(n)) return n;
          return { ...n, data: { ...n.data, ...partial } };
        })
      );
    },
    [setNodes]
  );

  /** Apply a node type upgrade; it persists with the next save. */
  const applyNodeUpgrade = useCallback(
    (nodeId: string, result: NodeUpgradeResult) => {
      const node = stepNodes.find((n) => n.id === nodeId);
      const latest = node?.data.latest_type_version ?? result.to_version;
      updateNodeData(nodeId, {
        type_version: result.to_version,
        config: result.config,
        upgrade_available: result.to_version < latest,
        type_label: node
          ? labelFor(catalog, node.data.step_type, result.to_version)
          : undefined,
      });
    },
    [stepNodes, updateNodeData, catalog]
  );

  // ── Update workflow meta ─────────────────────────────────────────

  const updateMeta = useCallback(
    (partial: Partial<WorkflowMeta>) => {
      setMeta((prev) => {
        const next = { ...prev, ...partial };

        // If orchestration mode changed, update orchestrator + step nodes
        if (partial.orchestration_mode) {
          const newMode = partial.orchestration_mode;
          setNodes((nds) => {
            // Remove finish node if switching away from sequential
            const updated = newMode !== "sequential"
              ? nds.filter((n) => n.id !== FINISH_NODE_ID)
              : nds;

            return updated.map((n): WorkflowNode => {
              if (n.type === "orchestrator") {
                return {
                  ...n,
                  data: { label: "Start", orchestration_mode: newMode },
                };
              }
              if (isStepNode(n)) {
                return {
                  ...n,
                  data: {
                    ...n.data,
                    orchestration_mode: newMode,
                    modeConflict: !isAllowedInMode(
                      catalog,
                      n.data.step_type,
                      n.data.type_version,
                      newMode
                    ),
                  },
                };
              }
              return n;
            });
          });
          // Remove finish node edges too
          if (newMode !== "sequential") {
            setEdges((eds) =>
              eds.filter((e) => e.source !== FINISH_NODE_ID && e.target !== FINISH_NODE_ID)
            );
          }
        }

        return next;
      });
    },
    [setNodes, setEdges, catalog]
  );

  // ── Handle connections ───────────────────────────────────────────

  const onConnect: OnConnect = useCallback(
    (connection: Connection) => {
      // Validate: no self-connections
      if (connection.source === connection.target) return;

      const sourceNode = nodes.find((n) => n.id === connection.source);
      const isRouter =
        !!sourceNode &&
        isStepNode(sourceNode) &&
        sourceNode.data.step_type === ROUTER_NODE_TYPE;

      // In sequential mode, enforce max 1 outgoing edge per node.
      // Routers instead have True/False branches; each branch may hold
      // several steps, but a step can't be in both branches.
      if (meta.orchestration_mode === "sequential") {
        if (isRouter) {
          const alreadyBranched = edges.some(
            (e) => e.source === connection.source && e.target === connection.target
          );
          if (alreadyBranched) return;
        } else {
          const hasOutgoing = edges.some(
            (e) => e.source === connection.source
          );
          if (hasOutgoing && connection.source !== ORCHESTRATOR_NODE_ID) return;
        }
      }

      // Determine branch label for conditional router edges
      const branchLabel = isRouter && connection.sourceHandle
        ? (connection.sourceHandle === "true" ? "True" : "False") as "True" | "False"
        : null;

      const edgeId = connection.sourceHandle
        ? `edge-${connection.source}-${connection.sourceHandle}-${connection.target}`
        : `edge-${connection.source}-${connection.target}`;

      const newEdge: WorkflowEdge = {
        id: edgeId,
        source: connection.source!,
        sourceHandle: connection.sourceHandle || undefined,
        target: connection.target!,
        type: "step",
        data: {
          orchestration_mode: meta.orchestration_mode,
          branchLabel,
        },
      };

      setEdges((eds) => addEdge(newEdge, eds) as WorkflowEdge[]);
    },
    [meta.orchestration_mode, nodes, edges, setEdges]
  );

  // ── Select node ──────────────────────────────────────────────────

  const selectNode = useCallback((nodeId: string | null) => {
    setSelectedNodeId(nodeId);
  }, []);

  // ── Load from existing workflow ──────────────────────────────────

  const loadFromSnapshot = useCallback(
    (workflow: WorkflowSnapshot) => {
      const { nodes: graphNodes, edges: graphEdges } = snapshotToGraph(
        workflow,
        catalog
      );
      setNodes(graphNodes);
      setEdges(graphEdges);
      setMeta(snapshotToMeta(workflow));
      setBaseVersion(workflow.version ?? null);
      setSelectedNodeId(null);
    },
    [setNodes, setEdges, catalog]
  );

  /** After a successful save: track the new version and server-side flags. */
  const markSaved = useCallback(
    (saved: WorkflowSnapshot) => {
      setBaseVersion(saved.version ?? null);
      const byKey = new Map(saved.steps.map((s) => [s.node_key, s]));
      setNodes((nds) =>
        nds.map((n) => {
          const step = isStepNode(n) ? byKey.get(n.id) : undefined;
          if (!step || !isStepNode(n)) return n;
          return {
            ...n,
            data: {
              ...n.data,
              type_version: step.type_version,
              latest_type_version: step.latest_type_version,
              upgrade_available: step.upgrade_available,
            },
          };
        })
      );
    },
    [setNodes]
  );

  // ── Auto-layout ──────────────────────────────────────────────────

  const runAutoLayout = useCallback(() => {
    setNodes((nds) =>
      autoLayout(nds, edges, meta.orchestration_mode) as WorkflowNode[]
    );
  }, [edges, meta.orchestration_mode, setNodes]);

  // ── Convert to API payload ───────────────────────────────────────

  const toPayload = useCallback(() => {
    return graphToPayload(nodes, edges, meta);
  }, [nodes, edges, meta]);

  const toUpdatePayload = useCallback(() => {
    return graphToUpdatePayload(nodes, edges, meta, baseVersion);
  }, [nodes, edges, meta, baseVersion]);

  /** Step order -> node key in the current canvas order. */
  const stepOrderToNodeKey = useCallback(() => {
    return Object.fromEntries(
      graphToSteps(nodes, edges).map((s, i) => [i, s.node_key])
    );
  }, [nodes, edges]);

  // ── Validate ─────────────────────────────────────────────────────

  const validate = useCallback(() => {
    return validateGraph(nodes, edges, meta, catalog);
  }, [nodes, edges, meta, catalog]);

  /** Steps whose type can't run in the current orchestration mode. */
  const modeConflicts = useMemo(
    () =>
      stepsNotAllowedInMode(
        stepNodes.map((n) => n.data),
        meta.orchestration_mode,
        catalog
      ),
    [stepNodes, meta.orchestration_mode, catalog]
  );

  // ── Get selected node ────────────────────────────────────────────

  const selectedNode =
    selectedNodeId !== null
      ? (nodes.find((n) => n.id === selectedNodeId) as
          | WorkflowNode
          | undefined)
      : null;

  return {
    // React Flow state
    nodes,
    edges,
    onNodesChange: onNodesChange as OnNodesChange<WorkflowNode>,
    onEdgesChange: onEdgesChange as OnEdgesChange<WorkflowEdge>,
    onConnect,

    // Workflow meta
    meta,
    updateMeta,
    baseVersion,

    // Node operations
    addAgentNode,
    addTypedNode,
    removeNode,
    updateNodeData,
    applyNodeUpgrade,

    // Selection
    selectedNodeId,
    selectedNode,
    selectNode,

    // Conversion
    loadFromSnapshot,
    markSaved,
    runAutoLayout,
    toPayload,
    toUpdatePayload,
    stepOrderToNodeKey,
    validate,
    modeConflicts,
  };
}
