/**
 * Where notes go on the canvas. A linked note is stored relative to its step, so when
 * auto-layout moves the step the note moves with it. Pure functions, so they're tested
 * on their own.
 */

import type { Edge, Node, XYPosition } from "@xyflow/react";

import type { WorkflowNote } from "@/lib/workflows/notes";
import type { WorkflowNode } from "../types";
import { isStepNode } from "../types";

export const NOTE_NODE_TYPE = "stickyNote";
const NOTE_ID_PREFIX = "note:";
const LINK_EDGE_PREFIX = "note-link:";

export const noteNodeId = (noteId: number) => `${NOTE_ID_PREFIX}${noteId}`;
export const isNoteNodeId = (id: string) => id.startsWith(NOTE_ID_PREFIX);
export const isNoteEdgeId = (id: string) => id.startsWith(LINK_EDGE_PREFIX);
export const noteIdOf = (nodeId: string) => Number(nodeId.slice(NOTE_ID_PREFIX.length));

/** Canvas position of a node: steps inside a container are placed relative to it. */
export function absolutePosition(nodeId: string, nodes: WorkflowNode[]): XYPosition | null {
  const byId = new Map(nodes.map((n) => [n.id, n]));
  let node = byId.get(nodeId);
  if (!node) return null;
  let x = 0;
  let y = 0;
  const seen = new Set<string>();
  while (node && !seen.has(node.id)) {
    seen.add(node.id);
    x += node.position.x;
    y += node.position.y;
    node = node.parentId ? byId.get(node.parentId) : undefined;
  }
  return { x, y };
}

/** Where the note is drawn. A note whose step is gone keeps its offset as a canvas position. */
export function noteCanvasPosition(note: WorkflowNote, nodes: WorkflowNode[]): XYPosition {
  const anchor = note.step_node_key ? absolutePosition(note.step_node_key, nodes) : null;
  return anchor ? { x: anchor.x + note.x, y: anchor.y + note.y } : { x: note.x, y: note.y };
}

/** What to store for a note drawn at `position`: relative to its step if it has one on the canvas. */
export function storedPosition(
  stepNodeKey: string | null,
  position: XYPosition,
  nodes: WorkflowNode[]
): { x: number; y: number } {
  const anchor = stepNodeKey ? absolutePosition(stepNodeKey, nodes) : null;
  const x = anchor ? position.x - anchor.x : position.x;
  const y = anchor ? position.y - anchor.y : position.y;
  return { x: Math.round(x), y: Math.round(y) };
}

export interface StepOption {
  key: string;
  name: string;
  /** Only saved steps can be linked: the server checks the link against saved steps. */
  saved: boolean;
}

export function stepOptions(nodes: WorkflowNode[], savedStepKeys: ReadonlySet<string>): StepOption[] {
  return nodes.filter(isStepNode).map((n) => ({
    key: n.id,
    name: String(n.data.step_name || "Untitled step"),
    saved: savedStepKeys.has(n.id),
  }));
}

/** The dashed line from a linked note to its step, when the step is on the canvas. */
export function noteLinkEdges(notes: WorkflowNote[], nodes: WorkflowNode[]): Edge[] {
  const onCanvas = new Set(nodes.map((n) => n.id));
  return notes
    .filter((n) => n.step_node_key && onCanvas.has(n.step_node_key))
    .map((n) => ({
      id: `${LINK_EDGE_PREFIX}${n.id}`,
      source: noteNodeId(n.id),
      target: n.step_node_key as string,
      type: "straight",
      className: "wfb-note-link",
      selectable: false,
      focusable: false,
      deletable: false,
    }));
}

export type NoteFlowNode = Node<Record<string, unknown>, typeof NOTE_NODE_TYPE>;
