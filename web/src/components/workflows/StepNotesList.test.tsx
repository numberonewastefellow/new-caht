import React from "react";
import { render, renderHook, screen, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom";
import { SWRConfig } from "swr";

import type { WorkflowNote } from "@/lib/workflows/notes";
import StepNotesList, { useStepNotes } from "./StepNotesList";

const note = (overrides: Partial<WorkflowNote>): WorkflowNote => ({
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

describe("StepNotesList", () => {
  it("shows a step's notes as markdown, with a way to edit them", () => {
    render(<StepNotesList workflowId={7} notes={[note({ text: "**Check** sections" }), note({ id: 2, color: "pink" })]} />);
    expect(screen.getByText("Notes (2)")).toBeInTheDocument();
    expect(screen.getByText("Check").tagName).toBe("STRONG");
    expect(screen.getByText("Empty note")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Edit in visual builder" })).toHaveAttribute("href", "/admin/workflows/visual/7");
  });

  it("shows nothing for a step without notes", () => {
    const { container } = render(<StepNotesList workflowId={7} notes={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("fetches the notes and groups them by step, ignoring unlinked ones", async () => {
    const notes = [note({ id: 1, step_node_key: "a" }), note({ id: 2, step_node_key: "a" }), note({ id: 3 })];
    global.fetch = jest.fn(() =>
      Promise.resolve({ ok: true, status: 200, json: async () => notes } as Response)
    ) as unknown as typeof fetch;
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <SWRConfig value={{ provider: () => new Map() }}>{children}</SWRConfig>
    );
    const { result } = renderHook(() => useStepNotes(7), { wrapper });
    await waitFor(() => expect(result.current("a")?.items.map((n) => n.id)).toEqual([1, 2]));
    expect(global.fetch).toHaveBeenCalledWith("/api/workflow/7/notes");
    expect(result.current("b")).toBeUndefined();
    const none = renderHook(() => useStepNotes(undefined), { wrapper });
    expect(none.result.current("a")).toBeUndefined();
  });
});
