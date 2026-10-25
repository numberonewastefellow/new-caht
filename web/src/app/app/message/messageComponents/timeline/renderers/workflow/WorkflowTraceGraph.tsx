"use client";

import React, { useState } from "react";
import dynamic from "next/dynamic";

import { Button } from "@opal/components";

import Modal from "@/refresh-components/Modal";
import { useChatSessionStore } from "@/app/app/stores/useChatSessionStore";

// Loaded on demand so @xyflow isn't part of the chat page bundle.
const TraceGraphBody = dynamic(() => import("./WorkflowTraceGraphBody"), {
  ssr: false,
  loading: () => (
    <div className="p-4 text-text-03">Loading execution trace…</div>
  ),
});

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

// ── Public: the "View execution trace" button ────────────────────────────────

export function WorkflowTraceButton({
  messageId,
  compact,
  live,
}: {
  messageId?: number;
  compact?: boolean;
  live?: boolean;
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
          <Modal.Header
            title="Workflow execution trace"
            onClose={() => setOpen(false)}
          />
          <Modal.Body>
            <TraceGraphBody
              messageId={messageId}
              chatId={chatId ? String(chatId) : null}
              live={live}
            />
          </Modal.Body>
        </Modal.Content>
      </Modal>
    </>
  );
}

export default WorkflowTraceButton;
