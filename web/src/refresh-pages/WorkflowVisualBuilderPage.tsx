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
  DragPersonaData,
} from "@/components/workflow-builder/types";
import { ORCHESTRATOR_NODE_ID } from "@/components/workflow-builder/types";

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

  // Listen for agent test button clicks from ReactFlow nodes
  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail as AgentTestTarget;
      if (detail?.personaId) setTestTarget(detail);
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

  // Enrich agent nodes with persona details (LLM, tools, labels) once agents are loaded
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
      const persona = agentMap.get(d.persona_id);
      if (!persona) continue;
      updateNodeData(node.id, {
        persona_icon_url: persona.uploaded_image_id
          ? `/api/persona/${persona.id}/uploaded_image`
          : null,
        persona_num_tools: persona.tools?.length || 0,
        persona_tool_names: (persona.tools || []).map((t) => t.name),
        persona_llm_model: persona.llm_model_version_override || null,
        persona_llm_provider:
          persona.llm_model_provider_override || null,
        persona_labels: [],
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
    (persona: DragPersonaData, position: { x: number; y: number }) => {
      addAgentNode(persona, position);
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
  const isConditionNode = selectedNode?.type === "conditional_router";

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
        <AgentSidebar
          agents={agents}
          isLoading={agentsLoading}
          onCreateNew={() => setShowCreateModal(true)}
        />
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
        {showConfigPanel && (
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
          />
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
            toast.success(`Agent "${dragData.persona_name}" created and added.`);
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
            .map((n) => (n.data as AgentNodeData).persona_id)}
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
