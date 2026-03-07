"use client";

import React from "react";
import {
  BaseEdge,
  getBezierPath,
  type EdgeProps,
} from "@xyflow/react";
import type { StepEdgeData } from "./types";

export function StepEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
  selected,
}: EdgeProps & { data?: StepEdgeData }) {
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
  });

  const isLlmDecision = data?.orchestration_mode === "llm_decision";

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        className={`wfb-edge ${isLlmDecision ? "wfb-edge--dashed" : ""} ${selected ? "wfb-edge--selected" : ""}`}
      />
      {typeof data?.stepOrder === "number" && (
        <foreignObject
          x={labelX - 12}
          y={labelY - 12}
          width={24}
          height={24}
          className="wfb-edge-label-container"
        >
          <div className="wfb-edge-label">
            {data.stepOrder + 1}
          </div>
        </foreignObject>
      )}
    </>
  );
}
