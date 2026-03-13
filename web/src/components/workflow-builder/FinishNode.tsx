"use client";

import React, { memo } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";

function FinishNodeComponent(_props: NodeProps) {
  return (
    <div className="wfb-finish-node">
      <Handle
        type="target"
        position={Position.Left}
        className="wfb-handle wfb-handle-target"
      />
      <div className="wfb-finish-icon">
        <svg
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <polyline points="20 6 9 17 4 12" />
        </svg>
      </div>
      <div className="wfb-finish-label">END</div>
    </div>
  );
}

export const FinishNode = memo(FinishNodeComponent);
