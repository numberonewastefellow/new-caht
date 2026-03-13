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

  // Sequential: solid arrow with "then #N" pill
  // LLM Decision: dashed with "may call" pill
  const edgeClass = [
    "wfb-edge",
    isLlmDecision ? "wfb-edge--dashed" : "wfb-edge--sequential",
    selected ? "wfb-edge--selected" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <>
      {/* Arrowhead marker for sequential edges */}
      {!isLlmDecision && (
        <defs>
          <marker
            id={`arrow-${id}`}
            viewBox="0 0 10 10"
            refX="8"
            refY="5"
            markerWidth="6"
            markerHeight="6"
            orient="auto-start-reverse"
          >
            <path
              d="M 0 0 L 10 5 L 0 10 z"
              fill="var(--virtualai-accent, #818cf8)"
            />
          </marker>
        </defs>
      )}
      <BaseEdge
        id={id}
        path={edgePath}
        className={edgeClass}
        style={
          !isLlmDecision
            ? { markerEnd: `url(#arrow-${id})` }
            : undefined
        }
      />
      {typeof data?.stepOrder === "number" && (
        <foreignObject
          x={labelX - (isLlmDecision ? 30 : 28)}
          y={labelY - 12}
          width={isLlmDecision ? 60 : 56}
          height={24}
          className="wfb-edge-label-container"
        >
          <div
            className={`wfb-edge-label-pill ${
              isLlmDecision
                ? "wfb-edge-label-pill--llm"
                : "wfb-edge-label-pill--seq"
            }`}
          >
            {isLlmDecision ? "may call" : `then #${data.stepOrder + 1}`}
          </div>
        </foreignObject>
      )}
    </>
  );
}
