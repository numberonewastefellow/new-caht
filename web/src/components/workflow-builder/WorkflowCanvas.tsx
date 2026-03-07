"use client";

import React, { useCallback, useRef, type DragEvent } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
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
import { StepEdge } from "./StepEdge";
import type { WorkflowNode, WorkflowEdge, DragPersonaData } from "./types";

const nodeTypes: NodeTypes = {
  agent: AgentNode as any,
  orchestrator: OrchestratorNode as any,
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
      </ReactFlow>
    </div>
  );
}
