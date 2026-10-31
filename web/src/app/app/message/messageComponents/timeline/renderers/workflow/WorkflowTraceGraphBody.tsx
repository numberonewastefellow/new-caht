"use client";

// The ReactFlow graph inside the "Workflow execution trace" modal. Kept in its
// own module so @xyflow (and its CSS) is only loaded when the modal is opened.

import React, { useMemo, useState } from "react";
import useSWR from "swr";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  Handle,
  Position,
  BackgroundVariant,
  type Node,
  type Edge,
  type NodeProps,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import "@/components/workflow-builder/reactFlowControls.css";

import { errorHandlingFetcher } from "@/lib/fetcher";
import {
  type KnownTraceStatus,
  type TraceNode,
  type WorkflowTrace,
  isKnownTraceNodeType,
  isKnownTraceStatus,
  normalizeTrace,
  traceGrid,
  traceHasContainers,
  traceNodeLabel,
  traceNodeLaneY,
} from "@/lib/workflows/trace";

const TRACE_NODE_WIDTH = 230;
const TRACE_NODE_HEIGHT = 80;

// Trace data shape and the fallbacks for node types this view doesn't know
// live in @/lib/workflows/trace.

// ── Status → existing theme tokens (no invented colors) ──────────────────────

const STATUS_DOT: Record<KnownTraceStatus, string> = {
  running: "bg-status-info-05",
  completed: "bg-status-success-05",
  paused: "bg-status-warning-05",
  failed: "bg-status-error-05",
};
const STATUS_BORDER: Record<KnownTraceStatus, string> = {
  running: "border-status-info-05",
  completed: "border-status-success-05",
  paused: "border-status-warning-05",
  failed: "border-status-error-05",
};

function statusDot(status: string): string {
  return isKnownTraceStatus(status) ? STATUS_DOT[status] : "bg-background-tint-02";
}

function statusBorder(status: string): string {
  return isKnownTraceStatus(status) ? STATUS_BORDER[status] : "border-border-02";
}

// ── Custom ReactFlow node ────────────────────────────────────────────────────

interface FlowNodeData extends Record<string, unknown> {
  node: TraceNode;
}

function TraceFlowNode({ data, selected }: NodeProps) {
  const node = (data as FlowNodeData).node;
  // Node types this view doesn't know render as a generic (dashed) node.
  const generic = !isKnownTraceNodeType(node.type);
  return (
    <div
      className={`rounded-lg border-2 ${statusBorder(node.status)} ${
        generic ? "border-dashed" : ""
      } bg-background-tint-00 px-3 py-2 shadow-sm ${selected ? "ring-2" : ""}`}
      style={{
        width: TRACE_NODE_WIDTH,
        ...(selected
          ? {
              boxShadow:
                "0 0 0 2px var(--virtualai-accent, var(--theme-primary-05))",
            }
          : {}),
      }}
    >
      <Handle type="target" position={Position.Left} />
      <div className="flex items-center gap-1.5 mb-1">
        <span
          className={`inline-block h-2 w-2 rounded-full ${statusDot(node.status)}`}
        />
        <span className="text-[11px] text-text-03 uppercase tracking-wide">
          {traceNodeLabel(node.type)}
          {node.call_index ? ` · call ${node.call_index}` : ""}
        </span>
      </div>
      <div className="text-text-05 font-medium text-sm leading-tight">
        {node.name}
      </div>
      {node.scope && (
        <div className="text-[11px] text-text-03 leading-tight truncate">
          {node.scope}
        </div>
      )}
      <div className="flex flex-wrap gap-1.5 mt-1 text-[11px] text-text-03">
        {node.duration_ms != null && (
          <span>⏱ {(node.duration_ms / 1000).toFixed(1)}s</span>
        )}
        {node.tokens != null && <span>🔢 {node.tokens}</span>}
        {node.file_names?.length > 0 && (
          <span>📎 {node.file_names.length}</span>
        )}
      </div>
      <Handle type="source" position={Position.Right} />
    </div>
  );
}

const nodeTypes = { trace: TraceFlowNode };

// ── Layout: a chain in execution order; runs with containers get a grid ────────────────────

function buildFlow(trace: WorkflowTrace): { nodes: Node[]; edges: Edge[] } {
  const X = 300;
  const ROW_HEIGHT = 130;
  const grid = traceHasContainers(trace) ? traceGrid(trace) : null;
  const nodes: Node[] = trace.nodes.map((n, i) => {
    const cell = grid?.get(n.id);
    return {
      id: n.id,
      type: "trace",
      // The minimap only draws nodes it knows the size of; these are never written back.
      initialWidth: TRACE_NODE_WIDTH,
      initialHeight: TRACE_NODE_HEIGHT,
      position: cell
        ? { x: cell.column * X, y: cell.row * ROW_HEIGHT }
        : { x: i * X, y: traceNodeLaneY(n.type) },
      data: { node: n } as FlowNodeData,
    };
  });
  const edges: Edge[] = trace.edges.map((e, i) => ({
    id: `e${i}`,
    source: e.from_id,
    target: e.to_id,
    label: e.label || undefined,
    animated: e.type === "delegation",
    labelStyle: { fontSize: 10 },
    style: {
      stroke:
        e.type === "delegation"
          ? "var(--virtualai-accent, var(--theme-primary-05))"
          : "var(--border-02, #ccc)",
    },
  }));
  return { nodes, edges };
}

// ── Inspector (per-node detail) ──────────────────────────────────────────────

function Section({ title, body }: { title: string; body: string }) {
  if (!body) return null;
  return (
    <div className="mb-3">
      <div className="text-[11px] text-text-03 uppercase tracking-wide mb-1">
        {title}
      </div>
      <pre className="text-xs text-text-04 whitespace-pre-wrap break-words bg-background-tint-01 rounded-md p-2 max-h-[16rem] overflow-auto">
        {body}
      </pre>
    </div>
  );
}

function Inspector({ node }: { node: TraceNode }) {
  return (
    <div className="w-[24rem] shrink-0 border-l border-border-02 pl-3 overflow-auto">
      <div className="flex items-center gap-1.5 mb-2">
        <span
          className={`inline-block h-2.5 w-2.5 rounded-full ${statusDot(node.status)}`}
        />
        <div className="text-text-05 font-semibold">{node.name}</div>
      </div>
      <div className="text-[11px] text-text-03 mb-3">
        {traceNodeLabel(node.type)} · {node.status}
        {node.duration_ms != null
          ? ` · ${(node.duration_ms / 1000).toFixed(1)}s`
          : ""}
        {node.tokens != null ? ` · ${node.tokens} tok` : ""}
      </div>
      {node.reason ? (
        <Section title="Why (routing reason)" body={node.reason} />
      ) : null}
      <Section title="Input" body={node.input} />
      <Section title="Output" body={node.output} />
      {node.file_names?.length > 0 ? (
        <Section title="Files available" body={node.file_names.join("\n")} />
      ) : null}
    </div>
  );
}

// ── Main graph (inside the modal) ────────────────────────────────────────────

function TraceGraphBody({
  messageId,
  chatId,
  live,
}: {
  messageId?: number;
  chatId: string | null;
  live?: boolean;
}) {
  // Prefer the per-message trace (so multiple runs in one session each resolve
  // to their own graph); fall back to the latest run for the session.
  const url =
    messageId != null
      ? `/api/workflow/message/${messageId}/trace`
      : chatId
        ? `/api/workflow/chat-session/${chatId}/trace`
        : null;
  // Poll only while the run is live AND this modal is open (this hook only
  // mounts when the modal is open), and stop once the run reaches a terminal
  // status — keeps polling tightly scoped.
  const { data, error, isLoading } = useSWR<WorkflowTrace>(
    url,
    errorHandlingFetcher,
    {
      // While live, keep polling every 2s (even before the first blob exists)
      // until the run reaches a terminal status; otherwise never poll.
      refreshInterval: (latest) =>
        live && (!latest || latest.status === "running") ? 2000 : 0,
      shouldRetryOnError: live ?? false,
    }
  );
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const trace = useMemo(() => (data ? normalizeTrace(data) : null), [data]);
  const flow = useMemo(
    () => (trace ? buildFlow(trace) : { nodes: [], edges: [] }),
    [trace]
  );
  const selected = trace?.nodes.find((n) => n.id === selectedId) || null;

  if (isLoading) {
    return <div className="p-4 text-text-03">Loading execution trace…</div>;
  }
  if (error || !trace) {
    return (
      <div className="p-4 text-text-03">
        No execution trace is available for this run yet.
      </div>
    );
  }

  return (
    <div className="flex h-[70dvh] w-full">
      <div className="flex-1 min-w-0">
        <ReactFlow
          nodes={flow.nodes}
          edges={flow.edges}
          nodeTypes={nodeTypes}
          fitView
          minZoom={0.2}
          onNodeClick={(_e, n) => setSelectedId(n.id)}
          proOptions={{ hideAttribution: true }}
        >
          <Background variant={BackgroundVariant.Dots} gap={16} />
          <Controls showInteractive={false} />
          <MiniMap pannable zoomable />
        </ReactFlow>
      </div>
      {selected ? <Inspector node={selected} /> : null}
    </div>
  );
}

export default TraceGraphBody;
