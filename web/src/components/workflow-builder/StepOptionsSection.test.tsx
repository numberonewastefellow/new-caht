import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";
import { StepOptionsSection } from "./StepOptionsSection";
import type { StepNodeData } from "./types";

function setup(overrides: Partial<StepNodeData>, canPause = true) {
  const onUpdate = jest.fn();
  const data = {
    is_terminal: false,
    can_request_input: false,
    promote_output: false,
    parent_key: null,
    ...overrides,
  } as StepNodeData;
  render(
    <StepOptionsSection
      nodeId="n1"
      data={data}
      canPause={canPause}
      onUpdate={onUpdate}
    />
  );
  return onUpdate;
}

describe("StepOptionsSection", () => {
  it("offers the three options for a step that can pause", () => {
    setup({});
    expect(screen.getByText("Terminal Step")).toBeInTheDocument();
    expect(screen.getByText("Can Request Input (HITL)")).toBeInTheDocument();
    expect(screen.getByText("Show as Message")).toBeInTheDocument();
  });

  it("hides Can Request Input when the node type can't pause", () => {
    setup({}, false);
    expect(screen.getByText("Terminal Step")).toBeInTheDocument();
    expect(screen.queryByText("Can Request Input (HITL)")).toBeNull();
  });

  it("shows nothing inside a container, where the server refuses these options", () => {
    setup({ parent_key: "p" });
    expect(screen.queryByText("Terminal Step")).toBeNull();
    expect(screen.queryByText("Show as Message")).toBeNull();
  });

  it("reports a change to the node", () => {
    const onUpdate = setup({});
    const [terminal] = screen.getAllByRole("switch");
    fireEvent.click(terminal!);
    expect(onUpdate).toHaveBeenCalledWith("n1", { is_terminal: true });
  });
});
