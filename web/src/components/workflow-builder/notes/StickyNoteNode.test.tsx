import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";

import type { WorkflowNote } from "@/lib/workflows/notes";
import { StickyNoteNode } from "./StickyNoteNode";
import type { NoteActions, NoteNodeData } from "./useWorkflowNotes";

jest.mock("@xyflow/react", () => ({
  Handle: () => null,
  NodeResizer: () => null,
  Position: { Right: "right" },
}));

const note: WorkflowNote = {
  id: 4,
  workflow_id: 7,
  text: "## Intake\n**Reads** the FIR",
  color: "blue",
  step_node_key: null,
  x: 0,
  y: 0,
  width: 260,
  height: 180,
  version: 1,
  created_at: "",
  updated_at: "",
};

function setup(overrides: Partial<NoteNodeData> = {}, selected = false) {
  const actions: NoteActions = {
    startEdit: jest.fn(),
    stopEdit: jest.fn(),
    changeText: jest.fn(),
    setColor: jest.fn(),
    setLink: jest.fn(),
    askDelete: jest.fn(),
    cancelDelete: jest.fn(),
    confirmDelete: jest.fn(),
  };
  const data: NoteNodeData = {
    note,
    editing: false,
    confirmingDelete: false,
    linkedStepName: null,
    linkMissing: false,
    stepOptions: [
      { key: "a", name: "Intake", saved: true },
      { key: "b", name: "Draft", saved: false },
    ],
    actions,
    ...overrides,
  };
  const props = { id: "note:4", data, selected } as unknown as React.ComponentProps<typeof StickyNoteNode>;
  render(<StickyNoteNode {...props} />);
  return actions;
}

describe("StickyNoteNode", () => {
  it("shows the text as markdown, in its colour", () => {
    setup();
    expect(screen.getByRole("heading", { name: "Intake" })).toBeInTheDocument();
    expect(screen.getByText("Reads").tagName).toBe("STRONG");
    expect(screen.getByTestId("sticky-note")).toHaveAttribute("data-color", "blue");
  });

  it("starts editing on double-click", () => {
    const actions = setup();
    fireEvent.doubleClick(screen.getByTestId("sticky-note"));
    expect(actions.startEdit).toHaveBeenCalledWith(4);
  });

  it("sends typing on, and saves when you click away", () => {
    const actions = setup({ editing: true });
    const box = screen.getByLabelText("Note text");
    expect(box).toHaveFocus();
    fireEvent.change(box, { target: { value: "new text" } });
    expect(actions.changeText).toHaveBeenCalledWith(4, "new text");
    fireEvent.blur(box);
    expect(actions.stopEdit).toHaveBeenCalledWith(4);
  });

  it("shows the toolbar only when selected", () => {
    setup();
    expect(screen.queryByTestId("note-toolbar")).toBeNull();
  });

  it("changes colour from the toolbar", () => {
    const actions = setup({}, true);
    expect(screen.getByRole("radio", { name: "blue" })).toHaveAttribute("aria-checked", "true");
    fireEvent.click(screen.getByRole("radio", { name: "pink" }));
    expect(actions.setColor).toHaveBeenCalledWith(4, "pink");
  });

  it("links only to saved steps, and can unlink", () => {
    const actions = setup({}, true);
    const select = screen.getByLabelText("Link to step");
    expect(screen.getByRole("option", { name: "Draft (save the workflow first)" })).toBeDisabled();
    fireEvent.change(select, { target: { value: "a" } });
    expect(actions.setLink).toHaveBeenCalledWith(4, "a");
    fireEvent.change(select, { target: { value: "" } });
    expect(actions.setLink).toHaveBeenLastCalledWith(4, null);
  });

  it("asks before deleting", () => {
    const actions = setup({}, true);
    fireEvent.click(screen.getByRole("button", { name: "Delete note" }));
    expect(actions.askDelete).toHaveBeenCalledWith(4);
    expect(actions.confirmDelete).not.toHaveBeenCalled();
  });

  it("deletes or cancels from the confirmation", () => {
    const actions = setup({ confirmingDelete: true });
    fireEvent.click(screen.getByRole("button", { name: "Delete" }));
    expect(actions.confirmDelete).toHaveBeenCalledWith(4);
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(actions.cancelDelete).toHaveBeenCalled();
  });

  it("says which step it's for, or that the step was removed", () => {
    setup({ linkedStepName: "Intake" });
    expect(screen.getByText("For: Intake")).toBeInTheDocument();
  });

  it("says when its step was removed", () => {
    setup({ linkMissing: true, note: { ...note, step_node_key: "gone" } });
    expect(screen.getByText("Linked step was removed")).toBeInTheDocument();
  });

  it("invites writing when empty", () => {
    setup({ note: { ...note, text: "  " } });
    expect(screen.getByText("Double-click to write a note")).toBeInTheDocument();
  });
});
