import type { WorkflowNote } from "@/lib/workflows/notes";
import type { WorkflowNode } from "../types";
import {
  absolutePosition,
  noteCanvasPosition,
  noteLinkEdges,
  stepOptions,
  storedPosition,
} from "./noteLayout";

const step = (id: string, x: number, y: number, extra: Partial<WorkflowNode> = {}) =>
  ({ id, type: "agent", position: { x, y }, data: { step_name: id.toUpperCase() }, ...extra }) as WorkflowNode;

const note = (overrides: Partial<WorkflowNote> = {}): WorkflowNote => ({
  id: 1,
  workflow_id: 7,
  text: "",
  color: "yellow",
  step_node_key: null,
  x: 0,
  y: 0,
  width: 260,
  height: 180,
  version: 1,
  created_at: "",
  updated_at: "",
  ...overrides,
});

const nodes: WorkflowNode[] = [
  { id: "__orchestrator__", type: "orchestrator", position: { x: 0, y: 0 }, data: { label: "Start", orchestration_mode: "sequential" } } as WorkflowNode,
  step("box", 400, 100),
  step("inner", 30, 50, { parentId: "box" }),
  step("solo", 900, 300),
];

describe("noteLayout", () => {
  it("adds up container offsets for a step inside a box", () => {
    expect(absolutePosition("inner", nodes)).toEqual({ x: 430, y: 150 });
    expect(absolutePosition("missing", nodes)).toBeNull();
  });

  it("draws a linked note relative to its step, so it follows the step", () => {
    const linked = note({ step_node_key: "solo", x: -20, y: -200 });
    expect(noteCanvasPosition(linked, nodes)).toEqual({ x: 880, y: 100 });
    const moved = nodes.map((n) => (n.id === "solo" ? { ...n, position: { x: 1000, y: 300 } } : n));
    expect(noteCanvasPosition(linked, moved)).toEqual({ x: 980, y: 100 });
  });

  it("keeps a note whose step is gone where its numbers say", () => {
    expect(noteCanvasPosition(note({ step_node_key: "gone", x: 5, y: 6 }), nodes)).toEqual({ x: 5, y: 6 });
  });

  it("stores a position relative to the step when linked, and as is otherwise", () => {
    expect(storedPosition("inner", { x: 500, y: 100 }, nodes)).toEqual({ x: 70, y: -50 });
    expect(storedPosition(null, { x: 12.4, y: 7.6 }, nodes)).toEqual({ x: 12, y: 8 });
  });

  it("offers only steps, and marks the unsaved ones", () => {
    const options = stepOptions(nodes, new Set(["box", "solo"]));
    expect(options.map((o) => [o.key, o.name, o.saved])).toEqual([
      ["box", "BOX", true],
      ["inner", "INNER", false],
      ["solo", "SOLO", true],
    ]);
  });

  it("draws a link line only to a step that's on the canvas", () => {
    const edges = noteLinkEdges(
      [note({ id: 1, step_node_key: "solo" }), note({ id: 2, step_node_key: "gone" }), note({ id: 3 })],
      nodes
    );
    expect(edges.map((e) => [e.source, e.target])).toEqual([["note:1", "solo"]]);
    expect(edges[0]!.deletable).toBe(false);
  });
});
