"use client";

import React, { useState, useCallback, useEffect, useMemo, useRef } from "react";
import { useRouter } from "next/navigation";
import { ReactFlowProvider } from "@xyflow/react";
import { useAgents } from "@/hooks/useAgents";
import { useWorkflow } from "@/hooks/useWorkflows";
import { useLLMProviders } from "@/lib/hooks/useLLMProviders";
import { useAvailableTools } from "@/hooks/useAvailableTools";
import { useDocumentSets } from "@/lib/hooks/useDocumentSets";
import { describeSaveError, saveWorkflow } from "@/lib/workflows/api";
import type { WorkflowSnapshot } from "@/lib/workflows/interfaces";
import { AGENT_NODE_TYPE } from "@/lib/workflows/nodeRegistry";
import { useNodeTypes } from "@/lib/workflows/useNodeTypes";
import { toast } from "@/hooks/useToast";

import { WorkflowCanvas } from "@/components/workflow-builder/WorkflowCanvas";
import { AgentSidebar } from "@/components/workflow-builder/AgentSidebar";
import { StepConfigPanel } from "@/components/workflow-builder/StepConfigPanel";
import { graphToSteps } from "@/components/workflow-builder/graphUtils";
import { GlobalConfigToolbar } from "@/components/workflow-builder/GlobalConfigToolbar";
import { useWorkflowGraph } from "@/components/workflow-builder/useWorkflowGraph";
import {
  AgentTestModal,
  type AgentTestTarget,
} from "@/components/workflow-builder/AgentTestModal";
import { QuickCreateAgentModal } from "@/components/workflow-builder/QuickCreateAgentModal";
import { JsonViewModal } from "@/components/workflow-builder/JsonViewModal";
import {
  UPGRADE_NODE_EVENT,
  type UpgradeNodeEventDetail,
} from "@/components/workflow-builder/NodeBadges";
import {
  NodeUpgradeDialog,
  type NodeUpgradeTarget,
} from "@/components/workflows/NodeUpgradeDialog";
import { WorkflowVersionsDialog } from "@/components/workflows/WorkflowVersionsDialog";
import type { DragAgentData } from "@/components/workflow-builder/types";
import {
  ORCHESTRATOR_NODE_ID,
  isStepNode,
} from "@/components/workflow-builder/types";

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
  const {
    workflow,
    isLoading: workflowLoading,
    refresh: refreshWorkflow,
  } = useWorkflow(workflowId ?? null);
  const {
    catalog,
    isReady: catalogReady,
    isLoading: catalogLoading,
  } = useNodeTypes();
  const { llmProviders } = useLLMProviders();
  const { tools: availableTools } = useAvailableTools();
  const { documentSets } = useDocumentSets();
  const [isSaving, setIsSaving] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const enrichedRef = useRef(false);
  const [testTarget, setTestTarget] = useState<AgentTestTarget | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showJsonView, setShowJsonView] = useState(false);
  const [showVersions, setShowVersions] = useState(false);
  const [upgradeTarget, setUpgradeTarget] = useState<
    (NodeUpgradeTarget & { nodeId: string }) | null
  >(null);

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
    addTypedNode,
    removeNode,
    moveNode,
    onNodeDragStop,
    updateNodeData,
    applyNodeUpgrade,
    selectedNode,
    selectNode,
    loadFromSnapshot,
    markSaved,
    baseVersion,
    runAutoLayout,
    toPayload,
    toUpdatePayload,
    stepOrderToNodeKey,
    validate,
    modeConflicts,
  } = useWorkflowGraph(catalog);

  // Load existing workflow on mount, once the node type catalog settled
  // (each node's view depends on whether its type is in the catalog).
  useEffect(() => {
    if (workflow && catalogReady && !loaded) {
      loadFromSnapshot(workflow);
      setLoaded(true);
    }
  }, [workflow, catalogReady, loaded, loadFromSnapshot]);

  // Listen for "Upgrade available" clicks from ReactFlow nodes
  useEffect(() => {
    const handler = (e: Event) => {
      const { nodeId } = (e as CustomEvent<UpgradeNodeEventDetail>).detail;
      const node = nodes.find((n) => n.id === nodeId);
      if (!node || !isStepNode(node)) return;
      setUpgradeTarget({
        nodeId,
        stepName: node.data.step_name || node.data.step_type,
        stepType: node.data.step_type,
        fromVersion: node.data.type_version ?? 1,
        config: node.data.config,
        stepOrderToNodeKey: stepOrderToNodeKey(),
      });
    };
    window.addEventListener(UPGRADE_NODE_EVENT, handler);
    return () => window.removeEventListener(UPGRADE_NODE_EVENT, handler);
  }, [nodes, stepOrderToNodeKey]);

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
      if (!isStepNode(node) || node.data.step_type !== AGENT_NODE_TYPE) continue;
      const d = node.data;
      const agent = d.agent_id != null ? agentMap.get(d.agent_id) : undefined;
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

  // Handle a node type dropped from the Utils palette
  const handleNodeTypeDrop = useCallback(
    (stepType: string, position: { x: number; y: number }) => {
      addTypedNode(stepType, position);
    },
    [addTypedNode]
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
      if (workflowId) {
        const saved = await saveWorkflow(workflowId, toUpdatePayload());
        markSaved(saved);
        refreshWorkflow(saved, { revalidate: false });
        toast.success(`"${meta.name}" has been updated (version ${saved.version}).`);
      } else {
        await saveWorkflow(null, toPayload());
        toast.success(`"${meta.name}" has been created.`);
        router.push("/admin/workflows");
      }
    } catch (err) {
      toast.error(describeSaveError(err));
    } finally {
      setIsSaving(false);
    }
  }, [
    validate,
    toPayload,
    toUpdatePayload,
    markSaved,
    refreshWorkflow,
    workflowId,
    meta.name,
    router,
  ]);

  // A version was restored: it is now the saved workflow
  const handleRestored = useCallback(
    (restored: WorkflowSnapshot) => {
      loadFromSnapshot(restored);
      refreshWorkflow(restored, { revalidate: false });
      setShowVersions(false);
      toast.success(`Restored; saved as version ${restored.version}.`);
    },
    [loadFromSnapshot, refreshWorkflow]
  );

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

  const selectedStep =
    selectedNode && isStepNode(selectedNode) ? selectedNode : null;
  const showConfigPanel = !!selectedStep;
  const selectedSteps = useMemo(
    () => (selectedStep ? graphToSteps(nodes, edges) : []),
    [selectedStep, nodes, edges]
  );
  const canvasWarnings =
    modeConflicts.length > 0
      ? [
          `${modeConflicts
            .map((s) => `"${s.step_name || s.step_type}"`)
            .join(", ")} can't run in ${
            meta.orchestration_mode === "llm_decision" ? "LLM Decision" : "Sequential"
          } mode. Remove ${modeConflicts.length === 1 ? "it" : "them"} or switch the orchestration mode.`,
        ]
      : [];
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
        onOpenVersions={workflowId ? () => setShowVersions(true) : undefined}
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
            catalog={catalog}
            catalogLoading={catalogLoading}
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
          onNodeDragStop={onNodeDragStop}
          onDrop={handleDrop}
          onNodeTypeDrop={handleNodeTypeDrop}
          warnings={canvasWarnings}
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
        {selectedStep && (
          <div style={configStyle}>
            <StepConfigPanel
              nodeId={selectedStep.id}
              kind={selectedStep.type}
              data={selectedStep.data}
              catalog={catalog}
              agents={agents}
              availableTools={availableTools}
              documentSets={documentSets}
              llmProviders={llmProviders ?? []}
              onUpdate={updateNodeData}
              onDelete={(id: string) => {
                removeNode(id);
                selectNode(null);
              }}
              onDeleteKeepingSteps={(id: string) => {
                removeNode(id, { keepChildren: true });
                selectNode(null);
              }}
              steps={selectedSteps}
              onMove={moveNode}
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
            .filter(isStepNode)
            .map((n) => n.data.agent_id)
            .filter((id): id is number => id != null)}
          onClose={() => setShowJsonView(false)}
        />
      )}

      {/* Node type upgrade preview */}
      {upgradeTarget && (
        <NodeUpgradeDialog
          target={upgradeTarget}
          onApply={(result) => {
            applyNodeUpgrade(upgradeTarget.nodeId, result);
            setUpgradeTarget(null);
            toast.success("Upgrade applied. Click Update to save it.");
          }}
          onClose={() => setUpgradeTarget(null)}
        />
      )}

      {/* Version history */}
      {showVersions && workflowId && (
        <WorkflowVersionsDialog
          workflowId={workflowId}
          currentVersion={baseVersion}
          catalog={catalog}
          onRestored={handleRestored}
          onClose={() => setShowVersions(false)}
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
