"use client";

import { memo, useEffect, useRef } from "react";
import { Handle, NodeResizer, Position, type NodeProps } from "@xyflow/react";

import MinimalMarkdown from "@/components/chat/MinimalMarkdown";
import { NOTE_COLORS, NOTE_MAX_SIZE, NOTE_MIN_SIZE, NOTE_TEXT_MAX_CHARS } from "@/lib/workflows/notes";
import type { NoteFlowNode } from "./noteLayout";
import type { NoteNodeData } from "./useWorkflowNotes";
import "./StickyNote.css";

function NoteToolbar({ data }: { data: NoteNodeData }) {
  const { note, actions, stepOptions } = data;
  return (
    <div
      className="wfb-note-toolbar nodrag"
      data-testid="note-toolbar"
      // Buttons keep the editor's focus, so a click here doesn't close the editor first
      onMouseDown={(e) => {
        if ((e.target as HTMLElement).closest("button")) e.preventDefault();
      }}
    >
      <div className="wfb-note-colors" role="radiogroup" aria-label="Note colour">
        {NOTE_COLORS.map((color) => (
          <button
            key={color}
            type="button"
            role="radio"
            aria-checked={note.color === color}
            aria-label={color}
            title={color}
            className="wfb-note-swatch"
            data-color={color}
            onClick={() => actions.setColor(note.id, color)}
          />
        ))}
      </div>
      <select
        className="wfb-note-link-select"
        aria-label="Link to step"
        value={note.step_node_key ?? ""}
        onChange={(e) => actions.setLink(note.id, e.target.value || null)}
      >
        <option value="">Not linked</option>
        {data.linkMissing && note.step_node_key && (
          <option value={note.step_node_key}>Removed step</option>
        )}
        {stepOptions.map((step) => (
          <option key={step.key} value={step.key} disabled={!step.saved}>
            {step.saved ? step.name : `${step.name} (save the workflow first)`}
          </option>
        ))}
      </select>
      <button
        type="button"
        className="wfb-note-delete"
        aria-label="Delete note"
        title="Delete note"
        onClick={() => actions.askDelete(note.id)}
      >
        <svg width="12" height="12" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2" fill="none">
          <path d="M3 6h18M8 6V4h8v2M6 6l1 14h10l1-14" />
        </svg>
      </button>
    </div>
  );
}

function NoteEditor({ data }: { data: NoteNodeData }) {
  const { note, actions } = data;
  const ref = useRef<HTMLTextAreaElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.focus();
    el.setSelectionRange(el.value.length, el.value.length);
  }, []);
  return (
    <textarea
      ref={ref}
      className="wfb-note-editor nodrag nowheel"
      aria-label="Note text"
      value={note.text}
      maxLength={NOTE_TEXT_MAX_CHARS}
      placeholder="Write a note. Markdown works: **bold**, lists, links."
      onChange={(e) => actions.changeText(note.id, e.target.value)}
      onBlur={() => actions.stopEdit(note.id)}
      onKeyDown={(e) => {
        if (e.key === "Escape") e.currentTarget.blur();
      }}
    />
  );
}

function StickyNoteNodeComponent({ data, selected }: NodeProps<NoteFlowNode>) {
  const noteData = data as NoteNodeData;
  const { note, actions, editing } = noteData;
  return (
    <div
      className="wfb-note"
      data-color={note.color}
      data-testid="sticky-note"
      onDoubleClick={() => !editing && actions.startEdit(note.id)}
    >
      <NodeResizer
        isVisible={selected && !noteData.linkMissing}
        minWidth={NOTE_MIN_SIZE.width}
        minHeight={NOTE_MIN_SIZE.height}
        maxWidth={NOTE_MAX_SIZE.width}
        maxHeight={NOTE_MAX_SIZE.height}
        lineClassName="wfb-note-resize-line"
        handleClassName="wfb-note-resize-handle"
      />
      {(selected || editing) && <NoteToolbar data={noteData} />}
      {editing ? (
        <NoteEditor data={noteData} />
      ) : (
        <div className="wfb-note-body nowheel" title="Double-click to edit">
          {note.text.trim() ? (
            <MinimalMarkdown content={note.text} />
          ) : (
            <span className="wfb-note-placeholder">Double-click to write a note</span>
          )}
        </div>
      )}
      {noteData.linkMissing ? (
        <div className="wfb-note-footer wfb-note-footer-warning" title="Unlink it to move or resize the note">
          Linked step was removed
        </div>
      ) : (
        noteData.linkedStepName && (
          <div className="wfb-note-footer">For: {noteData.linkedStepName}</div>
        )
      )}
      {noteData.confirmingDelete && (
        <div className="wfb-note-confirm nodrag" role="alertdialog" aria-label="Delete this note?">
          <span>Delete this note?</span>
          <div className="wfb-note-confirm-actions">
            <button type="button" className="wfb-note-confirm-delete" onClick={() => actions.confirmDelete(note.id)}>
              Delete
            </button>
            <button type="button" onClick={actions.cancelDelete}>
              Cancel
            </button>
          </div>
        </div>
      )}
      {/* Where the dashed line to a linked step starts. Not something to drag a connection from. */}
      <Handle type="source" position={Position.Right} isConnectable={false} className="wfb-note-handle" />
    </div>
  );
}

export const StickyNoteNode = memo(StickyNoteNodeComponent);
