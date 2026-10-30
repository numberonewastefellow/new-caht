/**
 * Workflow execution trace data (mirrors backend om/workflows/trace_models.py)
 * and helpers that keep the trace graph working for node types it doesn't
 * know: new backend node types (code, parallel, loop, ...) get a generic
 * label and lane instead of breaking the view.
 */

import { humanizeNodeType } from "./nodeRegistry";

export const KNOWN_TRACE_NODE_TYPES = [
  "start",
  "orchestrator",
  "agent",
  "pause",
  "finish",
  "router",
] as const;

export type KnownTraceNodeType = (typeof KNOWN_TRACE_NODE_TYPES)[number];

/** Any string: the backend may add trace node types at any time. */
export type TraceNodeType = KnownTraceNodeType | (string & {});

export const TRACE_STATUSES = [
  "running",
  "completed",
  "paused",
  "failed",
] as const;

export type KnownTraceStatus = (typeof TRACE_STATUSES)[number];
export type TraceStatus = KnownTraceStatus | (string & {});

export interface TraceNode {
  id: string;
  type: TraceNodeType;
  name: string;
  status: TraceStatus;
  input: string;
  output: string;
  reason?: string | null;
  step_id?: number | null;
  agent_id?: number | null;
  call_index?: number | null;
  duration_ms?: number | null;
  tokens?: number | null;
  file_ids: string[];
  file_names: string[];
  started_at?: string | null;
  ended_at?: string | null;
}

export interface TraceEdge {
  from_id: string;
  to_id: string;
  type: string;
  label?: string | null;
}

export interface WorkflowTrace {
  execution_id: number;
  workflow_id: number;
  workflow_name: string;
  mode: string;
  status: string;
  total_tokens: number;
  total_duration_ms: number;
  nodes: TraceNode[];
  edges: TraceEdge[];
}

const TYPE_LABEL: Record<KnownTraceNodeType, string> = {
  start: "Input",
  orchestrator: "Orchestrator",
  agent: "Agent",
  pause: "Paused",
  finish: "Final answer",
  router: "Decision",
};

/** Vertical lane of each known node type in the left-to-right layout. */
const TYPE_LANE_Y: Record<KnownTraceNodeType, number> = {
  start: 60,
  orchestrator: 0,
  agent: 130,
  pause: 130,
  finish: 60,
  router: 0,
};

/** Lane of node types the trace view doesn't know (the step lane). */
export const GENERIC_LANE_Y = 130;

export function isKnownTraceNodeType(type: string): type is KnownTraceNodeType {
  return (KNOWN_TRACE_NODE_TYPES as readonly string[]).includes(type);
}

export function isKnownTraceStatus(status: string): status is KnownTraceStatus {
  return (TRACE_STATUSES as readonly string[]).includes(status);
}

export function traceNodeLabel(type: string): string {
  return isKnownTraceNodeType(type)
    ? TYPE_LABEL[type]
    : humanizeNodeType(type || "step");
}

export function traceNodeLaneY(type: string): number {
  return isKnownTraceNodeType(type) ? TYPE_LANE_Y[type] : GENERIC_LANE_Y;
}

function text(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function stringList(value: unknown): string[] {
  return Array.isArray(value) ? value.map(String) : [];
}

/** Fill missing fields so a partial or newer-format node can't crash the view. */
export function normalizeTraceNode(
  raw: Partial<TraceNode>,
  index: number
): TraceNode {
  return {
    ...raw,
    id: text(raw.id) || `node-${index}`,
    type: text(raw.type) || "step",
    name: text(raw.name) || traceNodeLabel(text(raw.type)),
    status: text(raw.status) || "completed",
    input: text(raw.input),
    output: text(raw.output),
    file_ids: stringList(raw.file_ids),
    file_names: stringList(raw.file_names),
  };
}

export function normalizeTrace(trace: WorkflowTrace): WorkflowTrace {
  return {
    ...trace,
    nodes: (trace.nodes ?? []).map(normalizeTraceNode),
    edges: (trace.edges ?? []).filter(
      (e) => typeof e?.from_id === "string" && typeof e?.to_id === "string"
    ),
  };
}
