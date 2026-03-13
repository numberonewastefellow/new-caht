"use client";

import React, { memo } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import type { ConditionalRouterNodeData } from "./types";

function ConditionalRouterNodeComponent({
  data,
  selected,
}: NodeProps & { data: ConditionalRouterNodeData }) {
  const operator = data.operator || "contains";
  const field = data.condition_field || "";
  const value = data.match_value || "";

  // Build a short summary for display
  const summary = field
    ? `${field} ${operator} "${value}"`
    : "No condition set";

  return (
    <div
      className={`wfb-condition-node ${selected ? "wfb-condition-node--selected" : ""}`}
    >
      {/* Diamond icon header */}
      <div className="wfb-condition-header">
        <div className="wfb-condition-icon">
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            {/* Diamond / split path icon */}
            <path d="M16 3h5v5" />
            <path d="M8 3H3v5" />
            <path d="M12 22v-8.3a4 4 0 00-1.172-2.872L3 3" />
            <path d="M15 9l6-6" />
          </svg>
        </div>
        <div className="wfb-condition-title">
          <div className="wfb-condition-name">{data.step_name || "Condition"}</div>
          <div className="wfb-condition-type">If / Else</div>
        </div>
        {typeof data.stepOrder === "number" && (
          <span className="wfb-agent-order">#{data.stepOrder + 1}</span>
        )}
      </div>

      {/* Condition summary */}
      <div className="wfb-condition-summary">
        <code className="wfb-condition-expr">{summary}</code>
      </div>

      {/* Handles: one input (left), two outputs (right) */}
      <Handle
        type="target"
        position={Position.Left}
        className="wfb-handle wfb-handle-target"
      />
      <Handle
        type="source"
        position={Position.Right}
        id="true"
        className="wfb-handle wfb-handle-source wfb-handle-true"
        style={{ top: "35%" }}
      />
      <Handle
        type="source"
        position={Position.Right}
        id="false"
        className="wfb-handle wfb-handle-source wfb-handle-false"
        style={{ top: "65%" }}
      />

      {/* True/False labels next to handles */}
      <div className="wfb-condition-handle-labels">
        <span className="wfb-condition-label wfb-condition-label--true" style={{ top: "35%" }}>
          True
        </span>
        <span className="wfb-condition-label wfb-condition-label--false" style={{ top: "65%" }}>
          False
        </span>
      </div>
    </div>
  );
}

export const ConditionalRouterNode = memo(ConditionalRouterNodeComponent);
