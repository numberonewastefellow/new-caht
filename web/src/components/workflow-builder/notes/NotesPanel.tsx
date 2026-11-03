"use client";

import { Panel, useReactFlow, useStore } from "@xyflow/react";

import type { CanvasNotes } from "./useWorkflowNotes";

/** The "Add note" button, and any note error, at the top right of the canvas. */
export function NotesPanel({ notes }: { notes: CanvasNotes }) {
  const { screenToFlowPosition } = useReactFlow();
  const domNode = useStore((s) => s.domNode);

  function addAtCentre() {
    const box = domNode?.getBoundingClientRect();
    if (!box) return;
    notes.addNote(screenToFlowPosition({ x: box.left + box.width / 2, y: box.top + box.height / 2 }));
  }

  return (
    <Panel position="top-right">
      <div className="wfb-notes-panel">
        <button
          type="button"
          className="wfb-notes-add"
          onClick={addAtCentre}
          disabled={!notes.canAdd}
          title={notes.canAdd ? "Add a sticky note" : "Save the workflow first to add notes"}
        >
          <svg width="13" height="13" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2" fill="none">
            <path d="M4 4h16v11l-5 5H4z" />
            <path d="M15 20v-5h5" />
          </svg>
          Add note
        </button>
        {notes.error && (
          <div className="wfb-notes-error" role="alert">
            {notes.error}
            <button type="button" onClick={notes.clearError}>
              Dismiss
            </button>
          </div>
        )}
      </div>
    </Panel>
  );
}
