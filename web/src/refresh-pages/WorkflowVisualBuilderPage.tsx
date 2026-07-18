"use client";

import React, { useState, useCallback, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { ReactFlowProvider } from "@xyflow/react";
import { useAgents } from "@/hooks/useAgents";
import { useWorkflow } from "@/hooks/useWorkflows";
import { useLLMProviders } from "@/lib/hooks/useLLMProviders";
import { useAvailableTools } from "@/hooks/useAvailableTools";
import { useDocumentSets } from "@/lib/hooks/useDocumentSets";
import {
  createWorkflow,
  updateWorkflow,
} from "@/lib/workflows/api";
import { toast } from "@/hooks/useToast";

import { WorkflowCanvas } from "@/components/workflow-builder/WorkflowCanvas";
import { AgentSidebar } from "@/components/workflow-builder/AgentSidebar";
import { NodeConfigPanel } from "@/components/workflow-builder/NodeConfigPanel";
import { GlobalConfigToolbar } from "@/components/workflow-builder/GlobalConfigToolbar";
import { useWorkflowGraph } from "@/components/workflow-builder/useWorkflowGraph";
import {
  AgentTestModal,
  type AgentTestTarget,
} from "@/components/workflow-builder/AgentTestModal";
import { QuickCreateAgentModal } from "@/components/workflow-builder/QuickCreateAgentModal";
import { JsonViewModal } from "@/components/workflow-builder/JsonViewModal";
import type {
  AgentNodeData,
  ConditionalRouterNodeData,
  DragAgentData,
} from "@/components/workflow-builder/types";
import { ORCHESTRATOR_NODE_ID } from "@/components/workflow-builder/types";

// localStorage keys for panel state persistence
const LS_SIDEBAR_WIDTH = "wfb-sidebar-width";
const LS_CONFIG_WIDTH = "wfb-config-width";
const LS_SIDEBAR_COLLAPSED = "wfb-sidebar-collapsed";
const LS_CONFIG_COLLAPSED = "wfb-config-collapsed";

const DEFAULT_SIDEBAR_WIDTH = 264;
const DEFAULT_CONFIG_WIDTH = 320;
const MIN_SIDEBAR = 200;
const MAX_SIDEBAR = 400;
const MIN_CONFIG = 280;
const MAX_CONFIG = 500;

function readLsNumber(key: string, fallback: number): number {
  try {
    const v = localStorage.getItem(key);
    return v ? Number(v) || fallback : fallback;
  } catch {
    return fallback;
  }
}

function readLsBool(key: string, fallback: boolean): boolean {
  try {
    const v = localStorage.getItem(key);
    return v === "true" ? true : v === "false" ? false : fallback;
  } catch {
    return fallback;
  }
}

interface WorkflowVisualBuilderPageProps {
  workflowId?: number;
}

function WorkflowVisualBuilderInner({
  workflowId,
}: WorkflowVisualBuilderPageProps) {
  const router = useRouter();
  const { agents, isLoading: agentsLoading, refresh: refreshAgents } = useAgents();
  const { workflow, isLoading: workflowLoading } = useWorkflow(
    workflowId ?? null
  );
  const { llmProviders } = useLLMProviders();
  const { tools: availableTools } = useAvailableTools();
  const { documentSets } = useDocumentSets();
  const [isSaving, setIsSaving] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const enrichedRef = useRef(false);
  const [testTarget, setTestTarget] = useState<AgentTestTarget | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showJsonView, setShowJsonView] = useState(false);

  // ── Panel resize & collapse state ──────────────────────────────────
  const [sidebarWidth, setSidebarWidth] = useState(() => readLsNumber(LS_SIDEBAR_WIDTH, DEFAULT_SIDEBAR_WIDTH));
  const [configWidth, setConfigWidth] = useState(() => readLsNumber(LS_CONFIG_WIDTH, DEFAULT_CONFIG_WIDTH));
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => readLsBool(LS_SIDEBAR_COLLAPSED, false));
  const [configCollapsed, setConfigCollapsed] = useState(() => readLsBool(LS_CONFIG_COLLAPSED, false));

  // Persist panel state
  useEffect(() => { try { localStorage.setItem(LS_SIDEBAR_WIDTH, String(sidebarWidth)); } catch {} }, [sidebarWidth]);
  useEffect(() => { try { localStorage.setItem(LS_CONFIG_WIDTH, String(configWidth)); } catch {} }, [configWidth]);
  useEffect(() => { try { localStorage.setItem(LS_SIDEBAR_COLLAPSED, String(sidebarCollapsed)); } catch {} }, [sidebarCollapsed]);
  useEffect(() => { try { localStorage.setItem(LS_CONFIG_COLLAPSED, String(configCollapsed)); } catch {} }, [configCollapsed]);

  // Keyboard shortcuts: [ to toggle sidebar, ] to toggle config panel
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      // Don't trigger when typing in inputs/textareas
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
      if (e.key === "[") {
        e.preventDefault();
        setSidebarCollapsed((v) => !v);
      } else if (e.key === "]") {
        e.preventDefault();
        setConfigCollapsed((v) => !v);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  // Listen for agent test button clicks from ReactFlow nodes
  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail as AgentTestTarget;
      if (detail?.agentId) setTestTarget(detail);
    };
    window.addEventListener("wfb-test-agent", handler);
    return () => window.removeEventListener("wfb-test-agent", handler);
  }, []);

  const {
    nodes,
    edges,
    onNodesChange,
    onEdgesChange,
    onConnect,
    meta,
    updateMeta,
    addAgentNode,
    addConditionalRouterNode,
    removeNode,
    updateNodeData,
    selectedNodeId,
    selectedNode,
    selectNode,
    loadFromSnapshot,
    runAutoLayout,
    toPayload,
    validate,
  } = useWorkflowGraph();

  // Load existing workflow on mount
  useEffect(() => {
    if (workflow && !loaded) {
      loadFromSnapshot(workflow);
      setLoaded(true);
    }
  }, [workflow, loaded, loadFromSnapshot]);

  // Enrich agent nodes with agent details (LLM, tools, labels) once agents are loaded
  useEffect(() => {
    if (
      !loaded ||
      agentsLoading ||
      agents.length === 0 ||
      enrichedRef.current
    )
      return;
    enrichedRef.current = true;
    const agentMap = new Map(agents.map((a) => [a.id, a]));
    for (const node of nodes) {
      if (node.type !== "agent") continue;
      const d = node.data as AgentNodeData;
      const agent = agentMap.get(d.agent_id);
      if (!agent) continue;
      updateNodeData(node.id, {
        agent_icon_url: agent.uploaded_image_id
          ? `/api/agent/${agent.id}/uploaded_image`
          : null,
        agent_num_tools: agent.tools?.length || 0,
        agent_tool_names: (agent.tools || []).map((t) => t.name),
        agent_llm_model: agent.llm_model_version_override || null,
        agent_llm_provider:
          agent.llm_model_provider_override || null,
        agent_labels: [],
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loaded, agentsLoading, agents]);

  // Handle node click
  const handleNodeClick = useCallback(
    (nodeId: string) => {
      if (!nodeId || nodeId === ORCHESTRATOR_NODE_ID) {
        selectNode(null);
        return;
      }
      selectNode(nodeId);
    },
    [selectNode]
  );

  // Handle drop from sidebar
  const handleDrop = useCallback(
    (agent: DragAgentData, position: { x: number; y: number }) => {
      addAgentNode(agent, position);
    },
    [addAgentNode]
  );

  // Handle conditional router drop from sidebar
  const handleConditionDrop = useCallback(
    (position: { x: number; y: number }) => {
      addConditionalRouterNode(position);
    },
    [addConditionalRouterNode]
  );

  // Save workflow
  const handleSave = useCallback(async () => {
    const errors = validate();
    if (errors.length > 0) {
      toast.error(errors.map((e) => e.message).join(", "));
      return;
    }

    setIsSaving(true);
    try {
      const payload = toPayload();

      if (workflowId) {
        const resp = await updateWorkflow(workflowId, payload);
        if (!resp.ok) {
          const err = await resp.text();
          throw new Error(err);
        }
        toast.success(`"${meta.name}" has been updated.`);
      } else {
        const resp = await createWorkflow(payload as any);
        if (!resp.ok) {
          const err = await resp.text();
          throw new Error(err);
        }
        toast.success(`"${meta.name}" has been created.`);
        router.push("/admin/workflows");
      }
    } catch (err: any) {
      toast.error(err.message || "Save failed");
    } finally {
      setIsSaving(false);
    }
  }, [validate, toPayload, workflowId, meta.name, router]);

  // Navigate back
  const handleBack = useCallback(() => {
    router.push("/admin/workflows");
  }, [router]);

  // ── Resize handlers ────────────────────────────────────────────────
  const handleSidebarResize = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    const startX = e.clientX;
    const startW = sidebarWidth;

    const onMouseMove = (ev: MouseEvent) => {
      const delta = ev.clientX - startX;
      const newW = Math.min(MAX_SIDEBAR, Math.max(MIN_SIDEBAR, startW + delta));
      setSidebarWidth(newW);
    };
    const onMouseUp = () => {
      document.removeEventListener("mousemove", onMouseMove);
      document.removeEventListener("mouseup", onMouseUp);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onMouseUp);
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  }, [sidebarWidth]);

  const handleConfigResize = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    const startX = e.clientX;
    const startW = configWidth;

    const onMouseMove = (ev: MouseEvent) => {
      const delta = startX - ev.clientX; // reversed: drag left = wider
      const newW = Math.min(MAX_CONFIG, Math.max(MIN_CONFIG, startW + delta));
      setConfigWidth(newW);
    };
    const onMouseUp = () => {
      document.removeEventListener("mousemove", onMouseMove);
      document.removeEventListener("mouseup", onMouseUp);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onMouseUp);
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  }, [configWidth]);

  // Show loading state for edit mode
  if (workflowId && workflowLoading) {
    return (
      <div className="wfb-page">
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            height: "100%",
            color: "var(--text-03, #9ca3af)",
            fontSize: 14,
          }}
        >
          Loading workflow...
        </div>
      </div>
    );
  }

  const showConfigPanel =
    selectedNodeId &&
    selectedNodeId !== ORCHESTRATOR_NODE_ID &&
    selectedNode;
  // Compute sidebar style
  const sidebarStyle: React.CSSProperties = sidebarCollapsed
    ? { width: 36, minWidth: 36 }
    : { width: sidebarWidth, minWidth: sidebarWidth };

  // Compute config panel style
  const configStyle: React.CSSProperties = configCollapsed
    ? { width: 36, minWidth: 36 }
    : { width: configWidth, minWidth: configWidth };

  return (
    <div className="wfb-page">
      <GlobalConfigToolbar
        meta={meta}
        onUpdateMeta={updateMeta}
        onSave={handleSave}
        onAutoLayout={runAutoLayout}
        onBack={handleBack}
        isSaving={isSaving}
        isEditMode={!!workflowId}
        llmProviders={llmProviders ?? []}
        onViewJson={() => setShowJsonView(true)}
      />
      <div className="wfb-content">
        {/* Sidebar with dynamic width */}
        <div style={sidebarStyle}>
          <AgentSidebar
            agents={agents}
            isLoading={agentsLoading}
            onCreateNew={() => setShowCreateModal(true)}
            meta={meta}
            onUpdateMeta={updateMeta}
            llmProviders={llmProviders ?? []}
            collapsed={sidebarCollapsed}
            onToggleCollapse={() => setSidebarCollapsed((v) => !v)}
          />
        </div>

        {/* Resize handle: sidebar */}
        {!sidebarCollapsed && (
          <div
            className="wfb-resize-handle"
            onMouseDown={handleSidebarResize}
            onDoubleClick={() => setSidebarWidth(DEFAULT_SIDEBAR_WIDTH)}
            title="Drag to resize sidebar (double-click to reset)"
          />
        )}

        {/* Canvas (fills remaining space) */}
        <WorkflowCanvas
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onNodeClick={handleNodeClick}
          onDrop={handleDrop}
          onConditionDrop={handleConditionDrop}
        />

        {/* Resize handle: config panel */}
        {showConfigPanel && !configCollapsed && (
          <div
            className="wfb-resize-handle"
            onMouseDown={handleConfigResize}
            onDoubleClick={() => setConfigWidth(DEFAULT_CONFIG_WIDTH)}
            title="Drag to resize config panel (double-click to reset)"
          />
        )}

        {/* Config panel with dynamic width */}
        {showConfigPanel && (
          <div style={configStyle}>
            <NodeConfigPanel
              nodeId={selectedNodeId!}
              nodeType={selectedNode!.type}
              data={selectedNode!.data as AgentNodeData | ConditionalRouterNodeData}
              agents={agents}
              availableTools={availableTools}
              documentSets={documentSets}
              llmProviders={llmProviders ?? []}
              onUpdate={updateNodeData}
              onDelete={(id) => {
                removeNode(id);
                selectNode(null);
              }}
              onClose={() => selectNode(null)}
              collapsed={configCollapsed}
              onToggleCollapse={() => setConfigCollapsed((v) => !v)}
            />
          </div>
        )}
      </div>

      {/* Agent Test Modal */}
      {testTarget && (
        <AgentTestModal
          target={testTarget}
          onClose={() => setTestTarget(null)}
        />
      )}

      {/* Quick Create Agent Modal */}
      {showCreateModal && (
        <QuickCreateAgentModal
          onCreated={(dragData) => {
            refreshAgents();
            addAgentNode(dragData, { x: 400, y: 300 });
            setShowCreateModal(false);
            toast.success(`Agent "${dragData.agent_name}" created and added.`);
          }}
          onClose={() => setShowCreateModal(false)}
        />
      )}

      {/* JSON View Modal */}
      {showJsonView && (
        <JsonViewModal
          workflowJson={toPayload()}
          agentIds={nodes
            .filter((n) => n.type === "agent")
            .map((n) => (n.data as AgentNodeData).agent_id)}
          onClose={() => setShowJsonView(false)}
        />
      )}
    </div>
  );
}

export default function WorkflowVisualBuilderPage(
  props: WorkflowVisualBuilderPageProps
) {
  return (
    <ReactFlowProvider>
      <WorkflowVisualBuilderInner {...props} />
    </ReactFlowProvider>
  );
}
