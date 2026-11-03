import React from "react";
import { act, renderHook, waitFor } from "@testing-library/react";
import { SWRConfig } from "swr";

import type { WorkflowNote } from "@/lib/workflows/notes";
import type { WorkflowNode } from "../types";
import { mergeServerNotes, TEXT_SAVE_DELAY_MS, useWorkflowNotes } from "./useWorkflowNotes";

const note = (overrides: Partial<WorkflowNote> = {}): WorkflowNote => ({
  id: 1,
  workflow_id: 7,
  text: "first",
  color: "yellow",
  step_node_key: null,
  x: 100,
  y: 50,
  width: 260,
  height: 180,
  version: 1,
  created_at: "",
  updated_at: "",
  ...overrides,
});

const steps: WorkflowNode[] = [
  { id: "s1", type: "agent", position: { x: 500, y: 200 }, data: { step_name: "Intake" } } as WorkflowNode,
];

function respond(status: number, body: unknown) {
  return Promise.resolve({ ok: status < 300, status, json: async () => body } as Response);
}

const fetchMock = jest.fn();

function setup(notes: WorkflowNote[] = [note()]) {
  // The list request answers with the same notes the workflow came with
  fetchMock.mockImplementation((url: string, init?: RequestInit) =>
    !init || !init.method ? respond(200, notes) : respond(500, { detail: "unexpected" })
  );
  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <SWRConfig value={{ provider: () => new Map(), dedupingInterval: 0 }}>{children}</SWRConfig>
  );
  return renderHook(
    () => useWorkflowNotes({ workflowId: 7, initialNotes: notes, nodes: steps, savedStepKeys: new Set(["s1"]) }),
    { wrapper }
  );
}

/** Saves answer with `saved`; the list answers with the same note, as the server would. */
function answerSaves(saved: WorkflowNote) {
  fetchMock.mockImplementation((url: string, init?: RequestInit) =>
    init?.method ? respond(200, saved) : respond(200, [saved])
  );
}

function calls(method: string) {
  return fetchMock.mock.calls.filter(([, init]) => init?.method === method);
}

function body(call: unknown[]) {
  return JSON.parse((call[1] as RequestInit).body as string);
}

beforeEach(() => {
  fetchMock.mockReset();
  global.fetch = fetchMock as unknown as typeof fetch;
  jest.useFakeTimers();
});

afterEach(() => {
  jest.useRealTimers();
});

describe("mergeServerNotes", () => {
  const idle = () => false;
  it("never takes an older copy than the one already saved here", () => {
    const local = [note({ id: 1, text: "saved", version: 4 })];
    expect(mergeServerNotes(local, [note({ id: 1, text: "old", version: 3 })], idle)[0]!.text).toBe("saved");
    expect(mergeServerNotes(local, [note({ id: 1, text: "newer", version: 5 })], idle)[0]!.text).toBe("newer");
  });

  it("keeps a note with work in progress, and drops one deleted elsewhere", () => {
    const local = [note({ id: 1, text: "typing" }), note({ id: 2 }), note({ id: 3 })];
    const merged = mergeServerNotes(local, [note({ id: 1, text: "server" })], (id) => id !== 2);
    expect(merged.map((n) => [n.id, n.text])).toEqual([
      [1, "typing"],
      [3, "first"],
    ]);
  });
});

describe("useWorkflowNotes", () => {
  it("shows the notes that came with the workflow", async () => {
    const { result } = setup();
    await waitFor(() => expect(result.current.nodes).toHaveLength(1));
    expect(result.current.nodes[0]!.position).toEqual({ x: 100, y: 50 });
    expect(result.current.canAdd).toBe(true);
  });

  it("replaces notes from a cached workflow with the server's fresh list", async () => {
    const cached = [note({ text: "old", version: 1 })];
    fetchMock.mockImplementation(() => respond(200, [note({ text: "fresh", version: 3 })]));
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <SWRConfig value={{ provider: () => new Map(), dedupingInterval: 0 }}>{children}</SWRConfig>
    );
    const { result } = renderHook(
      () => useWorkflowNotes({ workflowId: 7, initialNotes: cached, nodes: steps, savedStepKeys: new Set() }),
      { wrapper }
    );
    await waitFor(() => expect((result.current.nodes[0]!.data as any).note.text).toBe("fresh"));
    expect((result.current.nodes[0]!.data as any).note.version).toBe(3);
  });

  it("saves typing once, a second after it stops", async () => {
    const { result } = setup();
    await waitFor(() => expect(result.current.nodes).toHaveLength(1));
    fetchMock.mockImplementation((url: string, init?: RequestInit) =>
      init?.method === "PATCH" ? respond(200, note({ text: "abc", version: 2 })) : respond(200, [note()])
    );

    const { actions } = result.current.nodes[0]!.data as any;
    act(() => {
      actions.changeText(1, "a");
      actions.changeText(1, "ab");
      actions.changeText(1, "abc");
    });
    expect(calls("PATCH")).toHaveLength(0);
    expect((result.current.nodes[0]!.data as any).note.text).toBe("abc");

    await act(async () => {
      jest.advanceTimersByTime(TEXT_SAVE_DELAY_MS);
    });
    expect(calls("PATCH")).toHaveLength(1);
    expect(body(calls("PATCH")[0]!)).toEqual({ expected_version: 1, text: "abc" });
  });

  it("saves straight away when the editor closes, then uses the new version", async () => {
    const { result } = setup();
    await waitFor(() => expect(result.current.nodes).toHaveLength(1));
    fetchMock.mockImplementationOnce(() => respond(200, note({ text: "x", version: 2 })));
    fetchMock.mockImplementationOnce(() => respond(200, note({ color: "pink", version: 3 })));

    const { actions } = result.current.nodes[0]!.data as any;
    act(() => actions.startEdit(1));
    expect((result.current.nodes[0]!.data as any).editing).toBe(true);
    act(() => actions.changeText(1, "x"));
    await act(async () => actions.stopEdit(1));
    expect((result.current.nodes[0]!.data as any).editing).toBe(false);
    await act(async () => actions.setColor(1, "pink"));

    const patches = calls("PATCH").map(body);
    expect(patches).toEqual([
      { expected_version: 1, text: "x" },
      { expected_version: 2, color: "pink" },
    ]);
  });

  it("reloads a note someone else changed, and says so", async () => {
    const { result } = setup();
    await waitFor(() => expect(result.current.nodes).toHaveLength(1));
    const theirs = note({ text: "their text", version: 5 });
    fetchMock.mockImplementation((url: string, init?: RequestInit) =>
      init?.method === "PATCH" ? respond(409, { detail: "This note was changed somewhere else." }) : respond(200, [theirs])
    );
    const { actions } = result.current.nodes[0]!.data as any;
    await act(async () => actions.setColor(1, "green"));
    await waitFor(() => expect(result.current.error).toBe("This note was changed somewhere else."));
    expect((result.current.nodes[0]!.data as any).note).toMatchObject({ text: "their text", version: 5 });
  });

  it("doesn't retry a failed save in a loop, and sends it with the next change", async () => {
    const { result } = setup();
    await waitFor(() => expect(result.current.nodes).toHaveLength(1));
    fetchMock.mockImplementation(() => respond(500, { detail: "Server is down" }));
    const { actions } = result.current.nodes[0]!.data as any;
    await act(async () => actions.setColor(1, "green"));
    await act(async () => {
      jest.advanceTimersByTime(5000);
    });
    expect(calls("PATCH")).toHaveLength(1);
    expect(result.current.error).toBe("Server is down");

    answerSaves(note({ version: 2 }));
    await act(async () => actions.setColor(1, "pink"));
    expect(body(calls("PATCH")[1]!)).toEqual({ expected_version: 1, color: "pink" });
  });

  it("saves where a note was dragged to, relative to its step", async () => {
    const { result } = setup([note({ step_node_key: "s1", x: 10, y: -150 })]);
    await waitFor(() => expect(result.current.nodes).toHaveLength(1));
    expect(result.current.nodes[0]!.position).toEqual({ x: 510, y: 50 });
    answerSaves(note({ version: 2 }));

    act(() =>
      result.current.onNodesChange([{ type: "position", id: "note:1", position: { x: 530, y: 60 }, dragging: true }])
    );
    expect(calls("PATCH")).toHaveLength(0);
    await act(async () =>
      result.current.onNodesChange([{ type: "position", id: "note:1", position: { x: 545, y: 75 }, dragging: false }])
    );
    expect(body(calls("PATCH")[0]!)).toEqual({ expected_version: 1, x: 45, y: -125 });
  });

  it("keeps a note in place on screen when it's linked to a step", async () => {
    const { result } = setup();
    await waitFor(() => expect(result.current.nodes).toHaveLength(1));
    answerSaves(note({ version: 2 }));
    const { actions } = result.current.nodes[0]!.data as any;
    await act(async () => actions.setLink(1, "s1"));
    expect(body(calls("PATCH")[0]!)).toEqual({ expected_version: 1, step_node_key: "s1", x: -400, y: -150 });
    expect(result.current.nodes[0]!.position).toEqual({ x: 100, y: 50 });
    expect(result.current.edges.map((e) => e.target)).toEqual(["s1"]);
  });

  it("saves a resize when it ends", async () => {
    const { result } = setup();
    await waitFor(() => expect(result.current.nodes).toHaveLength(1));
    answerSaves(note({ version: 2 }));
    act(() =>
      result.current.onNodesChange([
        { type: "dimensions", id: "note:1", dimensions: { width: 300, height: 200 }, resizing: true },
      ])
    );
    expect(calls("PATCH")).toHaveLength(0);
    await act(async () =>
      result.current.onNodesChange([
        { type: "dimensions", id: "note:1", dimensions: { width: 320.4, height: 210 }, resizing: false },
      ])
    );
    expect(body(calls("PATCH")[0]!)).toEqual({ expected_version: 1, width: 320, height: 210, x: 100, y: 50 });
  });

  it("adds a note centred where asked, ready to type", async () => {
    const { result } = setup([]);
    fetchMock.mockImplementation((url: string, init?: RequestInit) =>
      init?.method === "POST" ? respond(200, note({ id: 9, x: 70, y: 110 })) : respond(200, [])
    );
    await act(async () => result.current.addNote({ x: 200, y: 200 }));
    expect(body(calls("POST")[0]!)).toEqual({ x: 70, y: 110, width: 260, height: 180 });
    await waitFor(() => expect(result.current.nodes).toHaveLength(1));
    expect((result.current.nodes[0]!.data as any).editing).toBe(true);
  });

  it("keeps the other notes when one is added before the list has loaded", async () => {
    let answerList: (notes: WorkflowNote[]) => void = () => {};
    fetchMock.mockImplementation((url: string, init?: RequestInit) =>
      init?.method === "POST"
        ? respond(200, note({ id: 9, text: "new" }))
        : new Promise((resolve) => {
            answerList = (notes) => resolve({ ok: true, status: 200, json: async () => notes } as Response);
          })
    );
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <SWRConfig value={{ provider: () => new Map(), dedupingInterval: 0 }}>{children}</SWRConfig>
    );
    const initialNotes = [note()];
    const { result } = renderHook(
      () => useWorkflowNotes({ workflowId: 7, initialNotes, nodes: steps, savedStepKeys: new Set() }),
      { wrapper }
    );

    await act(async () => result.current.addNote({ x: 200, y: 200 }));
    // The list read before the new note existed arrives late
    await act(async () => answerList([note()]));

    await waitFor(() => expect(result.current.nodes.map((n) => n.id)).toEqual(["note:1", "note:9"]));
  });

  it("asks before deleting, and deletes on confirm", async () => {
    const { result } = setup();
    await waitFor(() => expect(result.current.nodes).toHaveLength(1));
    act(() => result.current.requestDelete(["note:1"]));
    expect((result.current.nodes[0]!.data as any).confirmingDelete).toBe(true);
    expect(calls("DELETE")).toHaveLength(0);

    fetchMock.mockImplementation((url: string, init?: RequestInit) =>
      init?.method === "DELETE" ? respond(200, {}) : respond(200, [])
    );
    const { actions } = result.current.nodes[0]!.data as any;
    await act(async () => actions.confirmDelete(1));
    await waitFor(() => expect(result.current.nodes).toHaveLength(0));
    expect(calls("DELETE")[0]![0]).toBe("/api/admin/workflow/7/notes/1");
  });

  it("undoes a change the server refuses, and the next edit still saves", async () => {
    const { result } = setup();
    await waitFor(() => expect(result.current.nodes).toHaveLength(1));
    fetchMock.mockImplementation(() => respond(422, { detail: "Too wide" }));
    await act(async () =>
      result.current.onNodesChange([
        { type: "dimensions", id: "note:1", dimensions: { width: 5000, height: 180 }, resizing: false },
      ])
    );
    expect(result.current.error).toBe("Too wide");
    expect((result.current.nodes[0]!.data as any).note.width).toBe(260);

    answerSaves(note({ color: "blue", version: 2 }));
    const { actions } = result.current.nodes[0]!.data as any;
    await act(async () => actions.setColor(1, "blue"));
    expect(body(calls("PATCH")[1]!)).toEqual({ expected_version: 1, color: "blue" });
  });

  it("removes a note that was deleted somewhere else", async () => {
    const { result } = setup();
    await waitFor(() => expect(result.current.nodes).toHaveLength(1));
    fetchMock.mockImplementation(() => respond(404, { detail: "Note not found" }));
    const { actions } = result.current.nodes[0]!.data as any;
    await act(async () => actions.setColor(1, "green"));
    expect(result.current.nodes).toHaveLength(0);
    expect(result.current.error).toBe("This note was deleted somewhere else.");
  });

  it("deletes only after a save that's still running", async () => {
    const { result } = setup();
    await waitFor(() => expect(result.current.nodes).toHaveLength(1));
    let finishSave: (r: Response) => void = () => {};
    fetchMock.mockImplementation((url: string, init?: RequestInit) =>
      init?.method === "PATCH"
        ? new Promise<Response>((resolve) => (finishSave = resolve))
        : respond(200, {})
    );
    const { actions } = result.current.nodes[0]!.data as any;
    act(() => actions.setColor(1, "green"));
    act(() => actions.confirmDelete(1));
    await act(async () => {
      await Promise.resolve();
    });
    expect(calls("DELETE")).toHaveLength(0);
    await act(async () => finishSave({ ok: true, status: 200, json: async () => note({ version: 2 }) } as Response));
    await waitFor(() => expect(calls("DELETE")).toHaveLength(1));
    await waitFor(() => expect(result.current.nodes).toHaveLength(0));
  });

  it("keeps the note on screen when a conflict can't be reloaded", async () => {
    const { result } = setup();
    await waitFor(() => expect(result.current.nodes).toHaveLength(1));
    fetchMock.mockImplementation((url: string, init?: RequestInit) =>
      init?.method === "PATCH" ? respond(409, { detail: "Changed elsewhere." }) : Promise.reject(new Error("offline"))
    );
    const { actions } = result.current.nodes[0]!.data as any;
    await act(async () => actions.setColor(1, "green"));
    await waitFor(() => expect(result.current.error).toContain("Reload the page"));
    expect(result.current.nodes).toHaveLength(1);
  });

  it("selects a new note, so its toolbar stays after typing", async () => {
    const { result } = setup([]);
    fetchMock.mockImplementation((url: string, init?: RequestInit) =>
      init?.method === "POST" ? respond(200, note({ id: 9 })) : respond(200, [])
    );
    await act(async () => result.current.addNote({ x: 0, y: 0 }));
    await waitFor(() => expect(result.current.nodes).toHaveLength(1));
    expect(result.current.nodes[0]!.selected).toBe(true);
  });

  it("won't move a note whose step is gone, so its offset isn't lost", async () => {
    const { result } = setup([note({ step_node_key: "gone", x: 30, y: -40 })]);
    await waitFor(() => expect(result.current.nodes).toHaveLength(1));
    expect(result.current.nodes[0]!.draggable).toBe(false);
    expect((result.current.nodes[0]!.data as any).linkMissing).toBe(true);
  });

  it("can't add notes before the workflow is saved", () => {
    const { result } = renderHook(() =>
      useWorkflowNotes({ workflowId: null, nodes: steps, savedStepKeys: new Set() })
    );
    expect(result.current.canAdd).toBe(false);
  });
});
