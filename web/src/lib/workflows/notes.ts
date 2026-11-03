/**
 * Sticky notes on the workflow canvas. Notes are documentation: they're saved on their
 * own, never through the workflow's Update, and never create a workflow version.
 */

import type { WorkflowSnapshot } from "@/lib/workflows/interfaces";

export const NOTE_COLORS = ["yellow", "blue", "green", "pink", "purple", "gray"] as const;
export type NoteColor = (typeof NOTE_COLORS)[number];

export const NOTE_TEXT_MAX_CHARS = 20000;
export const NOTE_DEFAULT_SIZE = { width: 260, height: 180 };
export const NOTE_MIN_SIZE = { width: 120, height: 60 };
/** The server refuses anything bigger */
export const NOTE_MAX_SIZE = { width: 1600, height: 1600 };

export interface WorkflowNote {
  id: number;
  workflow_id: number;
  text: string;
  color: NoteColor;
  /** The linked step's node_key. When set, x and y are relative to that step. */
  step_node_key: string | null;
  x: number;
  y: number;
  width: number;
  height: number;
  version: number;
  created_at: string;
  updated_at: string;
}

export type NoteChanges = Partial<
  Pick<WorkflowNote, "text" | "color" | "step_node_key" | "x" | "y" | "width" | "height">
>;

/** `GET /api/workflow/{id}` includes the workflow's notes. */
export type WorkflowWithNotes = WorkflowSnapshot & { notes?: WorkflowNote[] | null };

export const workflowNotesUrl = (workflowId: number) => `/api/workflow/${workflowId}/notes`;
const adminNotesUrl = (workflowId: number) => `/api/admin/workflow/${workflowId}/notes`;

/** The server answered with an error. */
export class NoteRequestError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    // Keep `instanceof` working when compiled to ES5.
    Object.setPrototypeOf(this, new.target.prototype);
    this.name = "NoteRequestError";
    this.status = status;
  }

  /** The note changed somewhere else since it was loaded. */
  get isConflict(): boolean {
    return this.status === 409;
  }

  /** Sending the same change again would fail the same way. */
  get isRejected(): boolean {
    return this.status >= 400 && this.status < 500;
  }
}

async function parse<T>(response: Response): Promise<T> {
  if (response.ok) return (await response.json()) as T;
  let detail = `Request failed (${response.status})`;
  try {
    const body = await response.json();
    if (typeof body?.detail === "string") detail = body.detail;
  } catch {
    // keep the status message
  }
  throw new NoteRequestError(detail, response.status);
}

export async function createNote(
  workflowId: number,
  note: NoteChanges & { x: number; y: number }
): Promise<WorkflowNote> {
  return parse(
    await fetch(adminNotesUrl(workflowId), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(note),
    })
  );
}

export async function updateNote(
  workflowId: number,
  noteId: number,
  expectedVersion: number,
  changes: NoteChanges,
  /** For a save sent while the page closes: the browser finishes it after the page is gone */
  keepalive = false
): Promise<WorkflowNote> {
  return parse(
    await fetch(`${adminNotesUrl(workflowId)}/${noteId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ expected_version: expectedVersion, ...changes }),
      keepalive,
    })
  );
}

export async function deleteNote(workflowId: number, noteId: number): Promise<void> {
  const response = await fetch(`${adminNotesUrl(workflowId)}/${noteId}`, { method: "DELETE" });
  // Already gone is what the caller wanted
  if (!response.ok && response.status !== 404) await parse(response);
}
