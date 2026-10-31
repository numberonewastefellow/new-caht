"use client";

import React, { memo } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import { humanizeNodeType } from "@/lib/workflows/nodeRegistry";
import { StepNodeBadges } from "./NodeBadges";
import { GenericNodeIcon } from "./nodeIcons";
import type { StepNodeData } from "./types";

/**
 * A Parallel or Loop step: a box holding its steps, with one lane per branch. Its
 * children are separate canvas nodes positioned inside it (see containerLayout.ts).
 */
function ContainerNodeComponent({
  id,
  data,
  selected,
}: NodeProps & { data: StepNodeData }) {
  const typeLabel = data.type_label || humanizeNodeType(data.step_type);

  return (
    <div
      className={[
        "wfb-container-node",
        selected ? "wfb-container-node--selected" : "",
      ].join(" ")}
    >
      <div className="wfb-container-header">
        <div className="wfb-generic-icon">
          <GenericNodeIcon size={16} />
        </div>
        <div className="wfb-generic-title">
          <div className="wfb-generic-name">{data.step_name || typeLabel}</div>
          <div className="wfb-generic-type">
            {typeLabel}
            {data.type_version != null ? ` · v${data.type_version}` : ""}
            {" · Output: "}
            <code>{data.output_key || "output"}</code>
          </div>
        </div>
        <StepNodeBadges nodeId={id} data={data} />
        {typeof data.stepOrder === "number" && (
          <span className="wfb-agent-order">#{data.stepOrder + 1}</span>
        )}
      </div>

      {(data.lanes ?? []).map((lane) => (
        <div
          key={lane.y}
          className="wfb-container-lane"
          style={{ top: lane.y, height: lane.height }}
        >
          <span className="wfb-container-lane-label">{lane.label}</span>
        </div>
      ))}

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

export const ContainerNode = memo(ContainerNodeComponent);
