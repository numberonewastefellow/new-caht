/**
 * Central state management hook for the visual workflow builder.
 * Manages React Flow nodes/edges and workflow metadata,
 * and converts between graph state and API payloads.
 */

"use client";

import { useCallback, useState } from "react";
import {
  useNodesState,
  useEdgesState,
  type OnNodesChange,
  type OnEdgesChange,
  type OnConnect,
  type Connection,
  addEdge,
} from "@xyflow/react";
import type { WorkflowSnapshot } from "@/lib/workflows/interfaces";
import type {
  WorkflowNode,
  WorkflowEdge,
  AgentNodeData,
  WorkflowMeta,
  DragPersonaData,
} from "./types";
import {
  DEFAULT_WORKFLOW_META,
  ORCHESTRATOR_NODE_ID,
  NODE_SPACING_X,
} from "./types";
import {
  snapshotToGraph,
  graphToPayload,
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

export function useWorkflowGraph() {
  const [nodes, setNodes, onNodesChange] =
    useNodesState<WorkflowNode>(INITIAL_NODES);
  const [edges, setEdges, onEdgesChange] =
    useEdgesState<WorkflowEdge>(INITIAL_EDGES);
  const [meta, setMeta] = useState<WorkflowMeta>({ ...DEFAULT_WORKFLOW_META });
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  // ── Add agent node (from sidebar drag-drop) ──────────────────────

  const addAgentNode = useCallback(
    (persona: DragPersonaData, position: { x: number; y: number }) => {
      const nodeId = `agent-${Date.now()}`;
      const agentCount = nodes.filter((n) => n.type === "agent").length;

      const newNode: WorkflowNode = {
        id: nodeId,
        type: "agent",
        position,
        data: {
          persona_id: persona.persona_id,
          persona_name: persona.persona_name,
          step_name: persona.persona_name,
          step_description: persona.persona_description || "",
          output_key: `step_${agentCount}`,
          is_terminal: false,
          can_request_input: false,
          promote_output: false,
          persona_description: persona.persona_description,
          persona_icon_url: persona.persona_icon_url,
          persona_num_tools: persona.persona_num_tools,
          persona_tool_names: persona.persona_tool_names || [],
          persona_llm_model: persona.persona_llm_model || null,
          persona_llm_provider: persona.persona_llm_provider || null,
          stepOrder: agentCount,
        },
      };

      setNodes((nds) => [...nds, newNode]);
      return nodeId;
    },
    [nodes, setNodes]
  );

  // ── Remove node ──────────────────────────────────────────────────

  const removeNode = useCallback(
    (nodeId: string) => {
      if (nodeId === ORCHESTRATOR_NODE_ID) return; // Can't delete start
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
    (nodeId: string, partial: Partial<AgentNodeData>) => {
      setNodes((nds) =>
        nds.map((n) => {
          if (n.id !== nodeId || n.type !== "agent") return n;
          return { ...n, data: { ...n.data, ...partial } };
        })
      );
    },
    [setNodes]
  );

  // ── Update workflow meta ─────────────────────────────────────────

  const updateMeta = useCallback(
    (partial: Partial<WorkflowMeta>) => {
      setMeta((prev) => {
        const next = { ...prev, ...partial };

        // If orchestration mode changed, update the orchestrator node
        if (partial.orchestration_mode) {
          setNodes((nds) =>
            nds.map((n) => {
              if (n.id !== ORCHESTRATOR_NODE_ID) return n;
              return {
                ...n,
                data: {
                  label: "Start",
                  orchestration_mode: partial.orchestration_mode!,
                },
              } as WorkflowNode;
            })
          );
        }

        return next;
      });
    },
    [setNodes]
  );

  // ── Handle connections ───────────────────────────────────────────

  const onConnect: OnConnect = useCallback(
    (connection: Connection) => {
      // Validate: no self-connections
      if (connection.source === connection.target) return;

      // In sequential mode, enforce max 1 outgoing edge per node
      if (meta.orchestration_mode === "sequential") {
        const hasOutgoing = edges.some(
          (e) => e.source === connection.source
        );
        if (hasOutgoing && connection.source !== ORCHESTRATOR_NODE_ID) return;
      }

      const newEdge: WorkflowEdge = {
        id: `edge-${connection.source}-${connection.target}`,
        source: connection.source!,
        target: connection.target!,
        type: "step",
        data: { orchestration_mode: meta.orchestration_mode },
      };

      setEdges((eds) => addEdge(newEdge, eds) as WorkflowEdge[]);
    },
    [meta.orchestration_mode, edges, setEdges]
  );

  // ── Select node ──────────────────────────────────────────────────

  const selectNode = useCallback((nodeId: string | null) => {
    setSelectedNodeId(nodeId);
  }, []);

  // ── Load from existing workflow ──────────────────────────────────

  const loadFromSnapshot = useCallback(
    (workflow: WorkflowSnapshot) => {
      const { nodes: graphNodes, edges: graphEdges } =
        snapshotToGraph(workflow);
      setNodes(graphNodes);
      setEdges(graphEdges);
      setMeta({
        name: workflow.name,
        description: workflow.description || "",
        orchestration_mode:
          (workflow.orchestration_mode as "sequential" | "llm_decision") ||
          "llm_decision",
        orchestrator_prompt: workflow.orchestrator_prompt || "",
        orchestrator_llm_provider: workflow.orchestrator_llm_provider || "",
        orchestrator_llm_model: workflow.orchestrator_llm_model || "",
        max_steps: workflow.max_steps,
        max_calls_per_agent: workflow.max_calls_per_agent,
        timeout_seconds: workflow.timeout_seconds,
        is_public: workflow.is_public,
        icon_name: workflow.icon_name || "",
      });
    },
    [setNodes, setEdges]
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

  // ── Validate ─────────────────────────────────────────────────────

  const validate = useCallback(() => {
    return validateGraph(nodes, edges, meta);
  }, [nodes, edges, meta]);

  // ── Get selected node ────────────────────────────────────────────

  const selectedNode =
    selectedNodeId !== null
      ? (nodes.find((n) => n.id === selectedNodeId) as
          | (WorkflowNode & { data: AgentNodeData })
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

    // Node operations
    addAgentNode,
    removeNode,
    updateNodeData,

    // Selection
    selectedNodeId,
    selectedNode,
    selectNode,

    // Conversion
    loadFromSnapshot,
    runAutoLayout,
    toPayload,
    validate,
  };
}
