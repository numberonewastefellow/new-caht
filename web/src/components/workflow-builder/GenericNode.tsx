"use client";

import React, { memo } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import { humanizeNodeType } from "@/lib/workflows/nodeRegistry";
import { StepNodeBadges } from "./NodeBadges";
import { GenericNodeIcon } from "./nodeIcons";
import type { StepNodeData } from "./types";

/**
 * Canvas node for node types without a dedicated UI. Types in the catalog
 * are edited through their config schema; types the catalog doesn't know
 * (`unsupported`) are shown read-only and saved back unchanged.
 */
function GenericNodeComponent({
  id,
  type,
  data,
  selected,
}: NodeProps & { data: StepNodeData }) {
  const unsupported = type === "unsupported";
  const typeLabel = data.type_label || humanizeNodeType(data.step_type);

  return (
    <div
      className={[
        "wfb-generic-node",
        selected ? "wfb-generic-node--selected" : "",
        unsupported ? "wfb-generic-node--unsupported" : "",
      ].join(" ")}
    >
      <div className="wfb-generic-header">
        <div className="wfb-generic-icon">
          <GenericNodeIcon size={16} />
        </div>
        <div className="wfb-generic-title">
          <div className="wfb-generic-name">{data.step_name || typeLabel}</div>
          <div className="wfb-generic-type">
            {typeLabel}
            {data.type_version != null ? ` · v${data.type_version}` : ""}
          </div>
        </div>
        {typeof data.stepOrder === "number" &&
          data.orchestration_mode === "sequential" && (
            <span className="wfb-agent-order">#{data.stepOrder + 1}</span>
          )}
      </div>

      <div className="wfb-generic-body">
        {unsupported ? (
          <span>
            Unsupported node type <code>{data.step_type}</code>. It is kept
            as-is and can&apos;t be edited here.
          </span>
        ) : (
          <span>
            Output: <code>{data.output_key || "output"}</code>
          </span>
        )}
      </div>
      <StepNodeBadges nodeId={id} data={data} />

      <Handle
        type="target"
        position={Position.Left}
        className="wfb-handle wfb-handle-target"
      />
      <Handle
        type="source"
        position={Position.Right}
        className="wfb-handle wfb-handle-source"
      />
    </div>
  );
}

export const GenericNode = memo(GenericNodeComponent);
