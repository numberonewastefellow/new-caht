"use client";

/**
 * Sticky notes on the canvas: their state, and saving them on their own.
 *
 * Notes never go through the workflow's Update, so editing one can't save half-finished
 * step changes or add a workflow version. Each note saves itself: text a second after
 * typing stops (or when the editor closes), everything else straight away. One save per
 * note is in flight at a time, so versions stay in order.
 *
 * What the server last confirmed is kept in the SWR cache, so a refetch can never bring
 * back something older than what was saved, and a refused change can be undone.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import useSWR from "swr";
import type { Edge, NodeChange, XYPosition } from "@xyflow/react";

import { errorHandlingFetcher } from "@/lib/fetcher";
import {
  createNote,
  deleteNote,
  NOTE_DEFAULT_SIZE,
  NoteRequestError,
  updateNote,
  workflowNotesUrl,
  type NoteChanges,
  type NoteColor,
  type WorkflowNote,
} from "@/lib/workflows/notes";
import type { WorkflowNode } from "../types";
import {
  isNoteNodeId,
  NOTE_NODE_TYPE,
  noteCanvasPosition,
  noteIdOf,
  noteLinkEdges,
  noteNodeId,
  stepOptions,
  storedPosition,
  type NoteFlowNode,
  type StepOption,
} from "./noteLayout";

export const TEXT_SAVE_DELAY_MS = 1000;

export interface NoteActions {
  startEdit: (noteId: number) => void;
  stopEdit: (noteId: number) => void;
  changeText: (noteId: number, text: string) => void;
  setColor: (noteId: number, color: NoteColor) => void;
  setLink: (noteId: number, stepNodeKey: string | null) => void;
  askDelete: (noteId: number) => void;
  cancelDelete: () => void;
  confirmDelete: (noteId: number) => void;
}

export interface NoteNodeData {
  note: WorkflowNote;
  editing: boolean;
  confirmingDelete: boolean;
  /** The linked step's name, when it's on the canvas */
  linkedStepName: string | null;
  /** Linked to a step that's no longer in the workflow. Such a note can't be moved: its
   * position is measured from that step, which may come back. */
  linkMissing: boolean;
  stepOptions: StepOption[];
  actions: NoteActions;
  [key: string]: unknown;
}

export interface CanvasNotes {
  nodes: NoteFlowNode[];
  edges: Edge[];
  /** False until the workflow has been saved once */
  canAdd: boolean;
  error: string | null;
  clearError: () => void;
  addNote: (position: XYPosition) => void;
  onNodesChange: (changes: NodeChange[]) => void;
  /** Delete pressed with notes selected: ask first, like the note's own button. */
  requestDelete: (nodeIds: string[]) => void;
}

interface Options {
  workflowId: number | null;
  /** Notes that came with the workflow, so they show before the notes list has loaded */
  initialNotes?: WorkflowNote[] | null;
  nodes: WorkflowNode[];
  /** Steps saved on the server: only these can be linked */
  savedStepKeys: ReadonlySet<string>;
}

function describe(error: unknown): string {
  return error instanceof Error ? error.message : "The note couldn't be saved";
}

/** The server's list, except notes with local work still going on, or a newer local copy. */
export function mergeServerNotes(
  local: WorkflowNote[],
  server: WorkflowNote[],
  isBusy: (noteId: number) => boolean
): WorkflowNote[] {
  const localById = new Map(local.map((n) => [n.id, n]));
  const merged = server.map((s) => {
    const mine = localById.get(s.id);
    return mine && (isBusy(s.id) || mine.version > s.version) ? mine : s;
  });
  const onServer = new Set(server.map((s) => s.id));
  // A note being worked on stays, even if this list was read before it existed
  return [...merged, ...local.filter((n) => !onServer.has(n.id) && isBusy(n.id))];
}

export function useWorkflowNotes({
  workflowId,
  initialNotes,
  nodes,
  savedStepKeys,
}: Options): CanvasNotes {
  const { data: serverNotes, mutate } = useSWR<WorkflowNote[]>(
    workflowId ? workflowNotesUrl(workflowId) : null,
    errorHandlingFetcher,
    { fallbackData: initialNotes ?? undefined, revalidateOnFocus: false }
  );

  const [notes, setNotes] = useState<WorkflowNote[]>([]);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [confirmingId, setConfirmingId] = useState<number | null>(null);
  const [selected, setSelected] = useState<ReadonlySet<number>>(new Set());
  const [error, setError] = useState<string | null>(null);

  // Read by saves, which run outside React's render cycle
  const notesRef = useRef<WorkflowNote[]>([]);
  const nodesRef = useRef(nodes);
  nodesRef.current = nodes;
  const editingRef = useRef(editingId);
  editingRef.current = editingId;
  const pending = useRef(new Map<number, NoteChanges>());
  const timers = useRef(new Map<number, ReturnType<typeof setTimeout>>());
  const inFlight = useRef(new Map<number, Promise<void>>());

  const replaceNotes = useCallback((next: (current: WorkflowNote[]) => WorkflowNote[]) => {
    notesRef.current = next(notesRef.current);
    setNotes(notesRef.current);
  }, []);

  const initialNotesRef = useRef(initialNotes);
  initialNotesRef.current = initialNotes;
  /** Record what the server confirmed, without asking it again. Before the list has
   * loaded, start from the notes that came with the workflow: a change made then also
   * discards the list request still on its way, so an empty start would hide the rest. */
  const remember = useCallback(
    (update: (cached: WorkflowNote[]) => WorkflowNote[]) =>
      void mutate((cached) => update(cached ?? initialNotesRef.current ?? []), {
        revalidate: false,
      }),
    [mutate]
  );

  const isBusy = useCallback(
    (noteId: number) =>
      pending.current.has(noteId) || inFlight.current.has(noteId) || editingRef.current === noteId,
    []
  );

  useEffect(() => {
    if (!workflowId || !serverNotes) return;
    replaceNotes((local) => mergeServerNotes(local, serverNotes, isBusy));
  }, [workflowId, serverNotes, replaceNotes, isBusy]);

  const dropLocal = useCallback(
    (noteId: number) => {
      pending.current.delete(noteId);
      const timer = timers.current.get(noteId);
      if (timer) clearTimeout(timer);
      timers.current.delete(noteId);
      replaceNotes((current) => current.filter((n) => n.id !== noteId));
      remember((cached) => cached.filter((n) => n.id !== noteId));
    },
    [replaceNotes, remember]
  );

  const reloadAfterConflict = useCallback(
    async (noteId: number, message: string) => {
      pending.current.delete(noteId);
      let fresh: WorkflowNote[] | undefined;
      try {
        fresh = await mutate();
      } catch {
        fresh = undefined;
      }
      if (!fresh) {
        // Couldn't fetch the latest: leave the note on screen rather than hide it
        setError(`${message} Reload the page to see the latest version.`);
        return;
      }
      const latest = fresh.find((n) => n.id === noteId);
      replaceNotes((current) =>
        latest ? current.map((n) => (n.id === noteId ? latest : n)) : current.filter((n) => n.id !== noteId)
      );
      setError(message);
    },
    [mutate, replaceNotes]
  );

  const serverNotesRef = useRef(serverNotes);
  serverNotesRef.current = serverNotes;
  /** Undo a change the server refused, back to what it last confirmed. */
  const revertToSaved = useCallback(
    (noteId: number) => {
      const saved = serverNotesRef.current?.find((n) => n.id === noteId);
      if (saved) replaceNotes((current) => current.map((n) => (n.id === noteId ? saved : n)));
    },
    [replaceNotes]
  );

  const flush = useCallback(
    async (noteId: number): Promise<void> => {
      if (!workflowId) return;
      const timer = timers.current.get(noteId);
      if (timer) clearTimeout(timer);
      timers.current.delete(noteId);

      const running = inFlight.current.get(noteId);
      if (running) await running;
      const changes = pending.current.get(noteId);
      const note = notesRef.current.find((n) => n.id === noteId);
      if (!changes || !note) return;
      pending.current.delete(noteId);

      let failed = false;
      const save = updateNote(workflowId, noteId, note.version, changes)
        .then((saved) => {
          // Keep what's on screen: more typing may have happened while this was saving
          replaceNotes((current) =>
            current.map((n) =>
              n.id === noteId ? { ...n, version: saved.version, updated_at: saved.updated_at } : n
            )
          );
          remember((cached) => cached.map((n) => (n.id === noteId ? saved : n)));
        })
        .catch(async (e: unknown) => {
          failed = true;
          if (e instanceof NoteRequestError && e.isConflict) {
            await reloadAfterConflict(noteId, e.message);
          } else if (e instanceof NoteRequestError && e.status === 404) {
            dropLocal(noteId);
            setError("This note was deleted somewhere else.");
          } else if (e instanceof NoteRequestError && e.isRejected) {
            // Sending it again would fail the same way, and block every later edit
            revertToSaved(noteId);
            setError(e.message);
          } else {
            // The server or the network failed: kept, and sent with the next edit or
            // click-away. Not retried here, so a failing server isn't called in a loop.
            pending.current.set(noteId, { ...changes, ...pending.current.get(noteId) });
            setError(describe(e));
          }
        })
        .finally(() => inFlight.current.delete(noteId));
      inFlight.current.set(noteId, save);
      await save;
      // Changes made while that save was running go out now
      if (!failed && pending.current.has(noteId) && !timers.current.has(noteId)) {
        await flush(noteId);
      }
    },
    [workflowId, replaceNotes, remember, reloadAfterConflict, dropLocal, revertToSaved]
  );

  const change = useCallback(
    (noteId: number, changes: NoteChanges, when: "now" | "soon") => {
      replaceNotes((current) => current.map((n) => (n.id === noteId ? { ...n, ...changes } : n)));
      pending.current.set(noteId, { ...pending.current.get(noteId), ...changes });
      if (when === "now") {
        void flush(noteId);
        return;
      }
      const timer = timers.current.get(noteId);
      if (timer) clearTimeout(timer);
      timers.current.set(
        noteId,
        setTimeout(() => {
          timers.current.delete(noteId);
          void flush(noteId);
        }, TEXT_SAVE_DELAY_MS)
      );
    },
    [replaceNotes, flush]
  );

  // Leaving the builder saves what was typed. Closing the tab sends it with keepalive,
  // which the browser completes after the page is gone.
  useEffect(() => {
    const pendingSaves = pending.current;
    const onPageHide = () => {
      if (!workflowId) return;
      pendingSaves.forEach((changes, noteId) => {
        const note = notesRef.current.find((n) => n.id === noteId);
        if (note) void updateNote(workflowId, noteId, note.version, changes, true).catch(() => {});
      });
      pendingSaves.clear();
    };
    window.addEventListener("pagehide", onPageHide);
    return () => {
      window.removeEventListener("pagehide", onPageHide);
      Array.from(pendingSaves.keys()).forEach((id) => void flush(id));
    };
  }, [flush, workflowId]);

  const actions = useMemo<NoteActions>(
    () => ({
      startEdit: (noteId) => setEditingId(noteId),
      stopEdit: (noteId) => {
        setEditingId((current) => (current === noteId ? null : current));
        void flush(noteId);
      },
      changeText: (noteId, text) => change(noteId, { text }, "soon"),
      setColor: (noteId, color) => change(noteId, { color }, "now"),
      setLink: (noteId, stepNodeKey) => {
        const note = notesRef.current.find((n) => n.id === noteId);
        if (!note) return;
        // The note stays where it is on screen; only what it's measured from changes
        const onScreen = noteCanvasPosition(note, nodesRef.current);
        const position = storedPosition(stepNodeKey, onScreen, nodesRef.current);
        change(noteId, { step_node_key: stepNodeKey, ...position }, "now");
      },
      askDelete: (noteId) => setConfirmingId(noteId),
      cancelDelete: () => setConfirmingId(null),
      confirmDelete: (noteId) => {
        if (!workflowId) return;
        setConfirmingId(null);
        const timer = timers.current.get(noteId);
        if (timer) clearTimeout(timer);
        timers.current.delete(noteId);
        pending.current.delete(noteId);
        // A save still running would otherwise land after the delete and fail
        const running = inFlight.current.get(noteId) ?? Promise.resolve();
        running
          .then(() => deleteNote(workflowId, noteId))
          .then(() => dropLocal(noteId))
          .catch((e: unknown) => setError(describe(e)));
      },
    }),
    [workflowId, change, flush, dropLocal]
  );

  const addNote = useCallback(
    (position: XYPosition) => {
      if (!workflowId) return;
      createNote(workflowId, {
        x: Math.round(position.x - NOTE_DEFAULT_SIZE.width / 2),
        y: Math.round(position.y - NOTE_DEFAULT_SIZE.height / 2),
        ...NOTE_DEFAULT_SIZE,
      })
        .then((created) => {
          replaceNotes((current) => [...current, created]);
          remember((cached) => [...cached.filter((n) => n.id !== created.id), created]);
          // Selected too, so its toolbar stays when the editor closes
          setSelected(new Set([created.id]));
          setEditingId(created.id);
        })
        .catch((e: unknown) => setError(describe(e)));
    },
    [workflowId, replaceNotes, remember]
  );

  const onNodesChange = useCallback(
    (changes: NodeChange[]) => {
      for (const c of changes) {
        if (!("id" in c) || !isNoteNodeId(c.id)) continue;
        const noteId = noteIdOf(c.id);
        const note = notesRef.current.find((n) => n.id === noteId);
        if (!note) continue;

        if (c.type === "select") {
          setSelected((current) => {
            const next = new Set(current);
            if (c.selected) next.add(noteId);
            else next.delete(noteId);
            return next;
          });
        } else if (c.type === "position" && c.position) {
          const position = storedPosition(note.step_node_key, c.position, nodesRef.current);
          if (c.dragging === false) change(noteId, position, "now");
          else replaceNotes((current) => current.map((n) => (n.id === noteId ? { ...n, ...position } : n)));
        } else if (c.type === "dimensions" && c.dimensions && c.resizing !== undefined) {
          const size = { width: Math.round(c.dimensions.width), height: Math.round(c.dimensions.height) };
          if (c.resizing) {
            replaceNotes((current) => current.map((n) => (n.id === noteId ? { ...n, ...size } : n)));
          } else {
            // A resize from the top or left edge also moved the note
            const latest = notesRef.current.find((n) => n.id === noteId) ?? note;
            change(noteId, { ...size, x: latest.x, y: latest.y }, "now");
          }
        }
      }
    },
    [change, replaceNotes]
  );

  const requestDelete = useCallback((nodeIds: string[]) => {
    const first = nodeIds.find(isNoteNodeId);
    if (first) setConfirmingId(noteIdOf(first));
  }, []);

  const options = useMemo(() => stepOptions(nodes, savedStepKeys), [nodes, savedStepKeys]);

  const noteNodes = useMemo<NoteFlowNode[]>(() => {
    const onCanvas = new Map(options.map((o) => [o.key, o.name]));
    return notes.map((note) => {
      const linkedName = note.step_node_key ? onCanvas.get(note.step_node_key) ?? null : null;
      const linkMissing = !!note.step_node_key && linkedName === null;
      const data: NoteNodeData = {
        note,
        editing: editingId === note.id,
        confirmingDelete: confirmingId === note.id,
        linkedStepName: linkedName,
        linkMissing,
        stepOptions: options,
        actions,
      };
      return {
        id: noteNodeId(note.id),
        type: NOTE_NODE_TYPE,
        position: noteCanvasPosition(note, nodes),
        width: note.width,
        height: note.height,
        selected: selected.has(note.id),
        // Not while typing (selecting text would drag it), nor while its step is missing
        draggable: editingId !== note.id && !linkMissing,
        data,
      };
    });
  }, [notes, nodes, options, editingId, confirmingId, selected, actions]);

  const edges = useMemo(() => noteLinkEdges(notes, nodes), [notes, nodes]);

  return {
    nodes: noteNodes,
    edges,
    canAdd: !!workflowId,
    error,
    clearError: () => setError(null),
    addNote,
    onNodesChange,
    requestDelete,
  };
}
