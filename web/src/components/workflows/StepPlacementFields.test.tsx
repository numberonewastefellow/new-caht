import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";
import { StepPlacementFields } from "./StepPlacementFields";
import { createEditorStep, type EditorStep } from "@/lib/workflows/editorModel";
import { CATALOG } from "@/lib/workflows/testFixtures";

const CLASSES = { section: "", label: "", select: "" };

const agent = (key: string, overrides: Partial<EditorStep> = {}) =>
  createEditorStep("agent", CATALOG, {
    node_key: key,
    agent_id: 1,
    step_name: key,
    output_key: key,
    ...overrides,
  });

const parallel = createEditorStep("parallel", CATALOG, {
  node_key: "p",
  step_name: "Fan out",
  output_key: "p",
  config: { branches: [{ label: "Flights" }, { label: "Hotels" }] },
});

function setup(step: EditorStep, steps: EditorStep[]) {
  const onMove = jest.fn();
  render(
    <StepPlacementFields
      step={step}
      steps={steps}
      catalog={CATALOG}
      classes={CLASSES}
      onMove={onMove}
    />
  );
  return onMove;
}

describe("StepPlacementFields", () => {
  it("shows nothing when there is no container to move into", () => {
    const a = agent("a");
    setup(a, [a]);
    expect(screen.queryByLabelText("Run inside")).toBeNull();
  });

  it("moves a step into a container's first branch", () => {
    const a = agent("a");
    const onMove = setup(a, [a, parallel]);
    fireEvent.change(screen.getByLabelText("Run inside"), {
      target: { value: "p" },
    });
    expect(onMove).toHaveBeenCalledWith({ parent_key: "p", branch_index: 0 });
  });

  it("offers branches only inside a container with several", () => {
    const a = agent("a");
    setup(a, [a, parallel]);
    expect(screen.queryByLabelText("Branch")).toBeNull();
  });

  it("moves a step to another branch, by its label", () => {
    const a = agent("a", { parent_key: "p", branch_index: 0 });
    const onMove = setup(a, [parallel, a]);
    const branch = screen.getByLabelText("Branch");
    expect(screen.getByRole("option", { name: "Hotels" })).toBeInTheDocument();
    fireEvent.change(branch, { target: { value: "1" } });
    expect(onMove).toHaveBeenCalledWith({ parent_key: "p", branch_index: 1 });
  });

  it("moves a step back to the top level", () => {
    const a = agent("a", { parent_key: "p", branch_index: 0 });
    const onMove = setup(a, [parallel, a]);
    fireEvent.change(screen.getByLabelText("Run inside"), {
      target: { value: "" },
    });
    expect(onMove).toHaveBeenCalledWith({ parent_key: null, branch_index: null });
  });
});
