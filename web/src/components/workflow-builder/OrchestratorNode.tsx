"use client";

import React, { memo } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import type { OrchestratorNodeData } from "./types";

function OrchestratorNodeComponent({
  data,
}: NodeProps & { data: OrchestratorNodeData }) {
  const modeLabel =
    data.orchestration_mode === "sequential" ? "Sequential" : "LLM Decision";

  return (
    <div className="wfb-orchestrator-node">
      <div className="wfb-orchestrator-icon">
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
      </div>
      <div className="wfb-orchestrator-label">START</div>
      <div className="wfb-orchestrator-mode">{modeLabel}</div>
      <Handle
        type="source"
        position={Position.Right}
        className="wfb-handle wfb-handle-source"
      />
    </div>
  );
}

export const OrchestratorNode = memo(OrchestratorNodeComponent);
