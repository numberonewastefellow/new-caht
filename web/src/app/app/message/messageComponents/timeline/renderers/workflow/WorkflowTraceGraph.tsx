"use client";

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

import { Button } from "@opal/components";

import Modal from "@/refresh-components/Modal";
import { errorHandlingFetcher } from "@/lib/fetcher";
import { useChatSessionStore } from "@/app/app/stores/useChatSessionStore";

// Graph/flow glyph used for the "View execution trace" trigger.
function TraceGraphIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      {...props}
    >
      <circle cx="5" cy="6" r="2" />
      <circle cx="5" cy="18" r="2" />
      <circle cx="19" cy="12" r="2" />
      <path d="M7 6h6M7 18h6M13 6c4 0 4 6 4 6M13 18c4 0 4-6 4-6" />
    </svg>
  );
}

// ── Trace data shape (mirrors backend onyx/workflows/trace_models.py) ────────

type TraceNodeType = "start" | "orchestrator" | "agent" | "pause" | "finish";
type TraceStatus = "running" | "completed" | "paused" | "failed";

interface TraceNode {
  id: string;
  type: TraceNodeType;
  name: string;
  status: TraceStatus;
  input: string;
  output: string;
  reason?: string | null;
  step_id?: number | null;
  persona_id?: number | null;
  call_index?: number | null;
  duration_ms?: number | null;
  tokens?: number | null;
  file_ids: string[];
  file_names: string[];
  started_at?: string | null;
  ended_at?: string | null;
}

interface TraceEdge {
  from_id: string;
  to_id: string;
  type: string;
  label?: string | null;
}

interface WorkflowTrace {
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

// ── Status → existing theme tokens (no invented colors) ──────────────────────

const STATUS_DOT: Record<TraceStatus, string> = {
  running: "bg-status-info-05",
  completed: "bg-status-success-05",
  paused: "bg-status-warning-05",
  failed: "bg-status-error-05",
};
const STATUS_BORDER: Record<TraceStatus, string> = {
  running: "border-status-info-05",
  completed: "border-status-success-05",
  paused: "border-status-warning-05",
  failed: "border-status-error-05",
};

const TYPE_LABEL: Record<TraceNodeType, string> = {
  start: "Input",
  orchestrator: "Orchestrator",
  agent: "Agent",
  pause: "Paused",
  finish: "Final answer",
};

// ── Custom ReactFlow node ────────────────────────────────────────────────────

interface FlowNodeData extends Record<string, unknown> {
  node: TraceNode;
}

function TraceFlowNode({ data, selected }: NodeProps) {
  const node = (data as FlowNodeData).node;
  const border = STATUS_BORDER[node.status] || "border-border-02";
  return (
    <div
      className={`rounded-lg border-2 ${border} bg-background-tint-00 px-3 py-2 shadow-sm ${
        selected ? "ring-2" : ""
      }`}
      style={{
        width: 230,
        ...(selected
          ? { boxShadow: "0 0 0 2px var(--virtualai-accent, var(--theme-primary-05))" }
          : {}),
      }}
    >
      <Handle type="target" position={Position.Left} />
      <div className="flex items-center gap-1.5 mb-1">
        <span className={`inline-block h-2 w-2 rounded-full ${STATUS_DOT[node.status] || "bg-background-tint-02"}`} />
        <span className="text-[11px] text-text-03 uppercase tracking-wide">
          {TYPE_LABEL[node.type] || node.type}
          {node.call_index ? ` · call ${node.call_index}` : ""}
        </span>
      </div>
      <div className="text-text-05 font-medium text-sm leading-tight">
        {node.name}
      </div>
      <div className="flex flex-wrap gap-1.5 mt-1 text-[11px] text-text-03">
        {node.duration_ms != null && <span>⏱ {(node.duration_ms / 1000).toFixed(1)}s</span>}
        {node.tokens != null && <span>🔢 {node.tokens}</span>}
        {node.file_names?.length > 0 && <span>📎 {node.file_names.length}</span>}
      </div>
      <Handle type="source" position={Position.Right} />
    </div>
  );
}

const nodeTypes = { trace: TraceFlowNode };

// ── Layout: simple left-to-right chain in execution order ────────────────────

function buildFlow(trace: WorkflowTrace): { nodes: Node[]; edges: Edge[] } {
  const X = 300;
  const laneY: Record<TraceNodeType, number> = {
    start: 60,
    orchestrator: 0,
    agent: 130,
    pause: 130,
    finish: 60,
  };
  const nodes: Node[] = trace.nodes.map((n, i) => ({
    id: n.id,
    type: "trace",
    position: { x: i * X, y: laneY[n.type] ?? 60 },
    data: { node: n } as FlowNodeData,
  }));
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
        <span className={`inline-block h-2.5 w-2.5 rounded-full ${STATUS_DOT[node.status] || "bg-background-tint-02"}`} />
        <div className="text-text-05 font-semibold">{node.name}</div>
      </div>
      <div className="text-[11px] text-text-03 mb-3">
        {TYPE_LABEL[node.type] || node.type} · {node.status}
        {node.duration_ms != null ? ` · ${(node.duration_ms / 1000).toFixed(1)}s` : ""}
        {node.tokens != null ? ` · ${node.tokens} tok` : ""}
      </div>
      {node.reason ? <Section title="Why (routing reason)" body={node.reason} /> : null}
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
}: {
  messageId?: number;
  chatId: string | null;
}) {
  // Prefer the per-message trace (so multiple runs in one session each resolve
  // to their own graph); fall back to the latest run for the session.
  const url =
    messageId != null
      ? `/api/workflow/message/${messageId}/trace`
      : chatId
        ? `/api/workflow/chat-session/${chatId}/trace`
        : null;
  const { data, error, isLoading } = useSWR<WorkflowTrace>(
    url,
    errorHandlingFetcher
  );
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const flow = useMemo(() => (data ? buildFlow(data) : { nodes: [], edges: [] }), [data]);
  const selected = data?.nodes.find((n) => n.id === selectedId) || null;

  if (isLoading) {
    return <div className="p-4 text-text-03">Loading execution trace…</div>;
  }
  if (error || !data) {
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

// ── Public: the "View execution trace" button ────────────────────────────────

export function WorkflowTraceButton({
  messageId,
  compact,
}: {
  messageId?: number;
  compact?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const chatId = useChatSessionStore((s) => s.currentSessionId);
  if (!chatId && messageId == null) return null;

  const trigger = compact ? (
    // Icon-only trigger that matches the timeline header's chevron buttons.
    <Button
      prominence="tertiary"
      size="md"
      icon={TraceGraphIcon}
      onClick={() => setOpen(true)}
      tooltip="View execution trace"
      aria-label="View execution trace"
    />
  ) : (
    <button
      type="button"
      onClick={() => setOpen(true)}
      className="flex items-center gap-1.5 text-[11px] text-text-03 hover:text-text-05 mt-1"
    >
      <TraceGraphIcon width={14} height={14} />
      View execution trace
    </button>
  );

  return (
    <>
      {trigger}
      <Modal open={open} onOpenChange={setOpen}>
        <Modal.Content width="lg" height="lg">
          <Modal.Header title="Workflow execution trace" onClose={() => setOpen(false)} />
          <Modal.Body>
            <TraceGraphBody
              messageId={messageId}
              chatId={chatId ? String(chatId) : null}
            />
          </Modal.Body>
        </Modal.Content>
      </Modal>
    </>
  );
}

export default WorkflowTraceButton;
