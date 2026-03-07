"use client";

import React, { useState, useCallback, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { ReactFlowProvider } from "@xyflow/react";
import { useAgents } from "@/hooks/useAgents";
import { useWorkflow } from "@/hooks/useWorkflows";
import { useLLMProviders } from "@/lib/hooks/useLLMProviders";
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
import type { AgentNodeData, DragPersonaData } from "@/components/workflow-builder/types";
import { ORCHESTRATOR_NODE_ID } from "@/components/workflow-builder/types";

interface WorkflowVisualBuilderPageProps {
  workflowId?: number;
}

function WorkflowVisualBuilderInner({
  workflowId,
}: WorkflowVisualBuilderPageProps) {
  const router = useRouter();
  const { agents, isLoading: agentsLoading } = useAgents();
  const { workflow, isLoading: workflowLoading } = useWorkflow(
    workflowId ?? null
  );
  const { llmProviders } = useLLMProviders();
  const [isSaving, setIsSaving] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const enrichedRef = useRef(false);

  const {
    nodes,
    edges,
    onNodesChange,
    onEdgesChange,
    onConnect,
    meta,
    updateMeta,
    addAgentNode,
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
    if (!loaded || agentsLoading || agents.length === 0 || enrichedRef.current)
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
        persona_llm_provider: persona.llm_model_provider_override || null,
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
      />
      <div className="wfb-content">
        <AgentSidebar agents={agents} isLoading={agentsLoading} />
        <WorkflowCanvas
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onNodeClick={handleNodeClick}
          onDrop={handleDrop}
        />
        {showConfigPanel && (
          <NodeConfigPanel
            nodeId={selectedNodeId!}
            data={selectedNode!.data as AgentNodeData}
            agents={agents}
            onUpdate={updateNodeData}
            onDelete={(id) => {
              removeNode(id);
              selectNode(null);
            }}
            onClose={() => selectNode(null)}
          />
        )}
      </div>
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
