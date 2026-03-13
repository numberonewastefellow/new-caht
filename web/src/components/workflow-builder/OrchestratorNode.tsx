"use client";

import React, { memo } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import type { OrchestratorNodeData } from "./types";

function OrchestratorNodeComponent({
  data,
}: NodeProps & { data: OrchestratorNodeData }) {
  const isSequential = data.orchestration_mode === "sequential";
  const modeLabel = isSequential ? "Sequential" : "LLM Decision";
  const subtitle = isSequential
    ? "Runs agents in order"
    : "AI decides which agent";

  return (
    <div
      className={`wfb-orchestrator-node ${
        isSequential
          ? "wfb-orchestrator-node--sequential"
          : "wfb-orchestrator-node--llm-decision"
      }`}
    >
      <div className="wfb-orchestrator-icon">
        {isSequential ? (
          /* Waterfall / list icon for sequential */
          <svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <line x1="8" y1="6" x2="21" y2="6" />
            <line x1="8" y1="12" x2="21" y2="12" />
            <line x1="8" y1="18" x2="21" y2="18" />
            <line x1="3" y1="6" x2="3.01" y2="6" />
            <line x1="3" y1="12" x2="3.01" y2="12" />
            <line x1="3" y1="18" x2="3.01" y2="18" />
          </svg>
        ) : (
          /* Brain / routing icon for LLM decision */
          <svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M12 3l1.912 5.813a2 2 0 001.272 1.272L21 12l-5.813 1.912a2 2 0 00-1.272 1.272L12 21l-1.912-5.813a2 2 0 00-1.272-1.272L3 12l5.813-1.912a2 2 0 001.272-1.272z" />
          </svg>
        )}
      </div>
      <div className="wfb-orchestrator-label">START</div>
      <div className="wfb-orchestrator-mode">{modeLabel}</div>
      <div className="wfb-orchestrator-subtitle">{subtitle}</div>
      <Handle
        type="source"
        position={Position.Right}
        className="wfb-handle wfb-handle-source"
      />
    </div>
  );
}

export const OrchestratorNode = memo(OrchestratorNodeComponent);
