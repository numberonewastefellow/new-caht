"use client";

import React, { useCallback, useMemo, useRef, useState, type DragEvent } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  Panel,
  BackgroundVariant,
  useReactFlow,
  type NodeTypes,
  type EdgeTypes,
  type OnNodesChange,
  type OnEdgesChange,
  type OnConnect,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import "./WorkflowCanvas.css";

import { AgentNode } from "./AgentNode";
import { OrchestratorNode } from "./OrchestratorNode";
import { FinishNode } from "./FinishNode";
import { StepEdge } from "./StepEdge";
import type { WorkflowNode, WorkflowEdge, DragPersonaData, OrchestratorNodeData } from "./types";
import { ORCHESTRATOR_NODE_ID } from "./types";

const nodeTypes: NodeTypes = {
  agent: AgentNode as any,
  orchestrator: OrchestratorNode as any,
  finish: FinishNode as any,
};

const edgeTypes: EdgeTypes = {
  step: StepEdge as any,
};

interface WorkflowCanvasProps {
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  onNodesChange: OnNodesChange<WorkflowNode>;
  onEdgesChange: OnEdgesChange<WorkflowEdge>;
  onConnect: OnConnect;
  onNodeClick: (nodeId: string) => void;
  onDrop: (persona: DragPersonaData, position: { x: number; y: number }) => void;
}

function FlowLegend({ nodes }: { nodes: WorkflowNode[] }) {
  const [dismissed, setDismissed] = useState(false);

  const mode = useMemo(() => {
    const orch = nodes.find((n) => n.id === ORCHESTRATOR_NODE_ID);
    if (!orch) return null;
    return (orch.data as OrchestratorNodeData).orchestration_mode;
  }, [nodes]);

  if (dismissed || !mode) return null;

  const isSequential = mode === "sequential";

  return (
    <Panel position="top-left">
      <div className="wfb-legend">
        <div className="wfb-legend-header">
          <div className="wfb-legend-title">
            {isSequential ? "Pipeline Mode" : "AI Routing Mode"}
          </div>
          <button
            className="wfb-legend-close"
            onClick={() => setDismissed(true)}
            title="Dismiss"
          >
            <svg width="10" height="10" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5" fill="none">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>
        {isSequential ? (
          <>
            <div className="wfb-legend-line">
              <span className="wfb-legend-solid" />
              <span>Agents run one after another</span>
            </div>
            <div className="wfb-legend-line wfb-legend-flow">
              Step 1 &rarr; Step 2 &rarr; Step 3
            </div>
          </>
        ) : (
          <>
            <div className="wfb-legend-line">
              <span className="wfb-legend-dashed" />
              <span>AI picks the best agent</span>
            </div>
            <div className="wfb-legend-line wfb-legend-flow">
              Any agent may be called
            </div>
          </>
        )}
      </div>
    </Panel>
  );
}

export function WorkflowCanvas({
  nodes,
  edges,
  onNodesChange,
  onEdgesChange,
  onConnect,
  onNodeClick,
  onDrop,
}: WorkflowCanvasProps) {
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const { screenToFlowPosition } = useReactFlow();

  const handleDragOver = useCallback((event: DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
  }, []);

  const handleDrop = useCallback(
    (event: DragEvent) => {
      event.preventDefault();

      const raw = event.dataTransfer.getData("application/reactflow");
      if (!raw) return;

      try {
        const persona: DragPersonaData = JSON.parse(raw);
        const position = screenToFlowPosition({
          x: event.clientX,
          y: event.clientY,
        });
        onDrop(persona, position);
      } catch {
        // Invalid drag data
      }
    },
    [screenToFlowPosition, onDrop]
  );

  const handleNodeClick = useCallback(
    (_: React.MouseEvent, node: WorkflowNode) => {
      onNodeClick(node.id);
    },
    [onNodeClick]
  );

  const handlePaneClick = useCallback(() => {
    onNodeClick(""); // Deselect
  }, [onNodeClick]);

  return (
    <div ref={reactFlowWrapper} className="wfb-canvas-wrapper">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeClick={handleNodeClick}
        onPaneClick={handlePaneClick}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        defaultEdgeOptions={{ type: "step" }}
        fitView
        fitViewOptions={{ padding: 0.3 }}
        deleteKeyCode="Delete"
        multiSelectionKeyCode="Shift"
        snapToGrid
        snapGrid={[15, 15]}
      >
        <Background variant={BackgroundVariant.Dots} gap={20} size={1} />
        <Controls showInteractive={false} />
        <MiniMap
          nodeStrokeWidth={3}
          pannable
          zoomable
          style={{ width: 150, height: 100 }}
        />
        <FlowLegend nodes={nodes} />
      </ReactFlow>
    </div>
  );
}
