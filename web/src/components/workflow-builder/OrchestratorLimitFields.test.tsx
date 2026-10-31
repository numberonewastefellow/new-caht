import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";
import { OrchestratorLimitFields } from "./OrchestratorLimitFields";
import type { WorkflowMeta } from "./types";

function setup(mode: WorkflowMeta["orchestration_mode"]) {
  const onUpdateMeta = jest.fn();
  const meta = {
    orchestration_mode: mode,
    max_steps: 10,
    max_calls_per_agent: 2,
  } as WorkflowMeta;
  render(<OrchestratorLimitFields meta={meta} onUpdateMeta={onUpdateMeta} />);
  return onUpdateMeta;
}

describe("OrchestratorLimitFields", () => {
  it("is hidden for Sequential workflows, which have no orchestrator", () => {
    setup("sequential");
    expect(screen.queryByText("Max Total Steps")).toBeNull();
    expect(screen.queryByText("Max Calls per Agent")).toBeNull();
  });

  it("shows both limits for LLM Decision workflows", () => {
    setup("llm_decision");
    expect(screen.getByText("Max Total Steps")).toBeInTheDocument();
    expect(screen.getByText("Max Calls per Agent")).toBeInTheDocument();
  });

  it("allows up to the shared limit and reports changes", () => {
    const onUpdateMeta = setup("llm_decision");
    const [, maxCalls] = screen.getAllByRole("spinbutton");
    expect(maxCalls).toHaveAttribute("max", "20");
    fireEvent.change(maxCalls!, { target: { value: "20" } });
    expect(onUpdateMeta).toHaveBeenCalledWith({ max_calls_per_agent: 20 });
  });
});
