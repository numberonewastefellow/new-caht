import { workflowStepLabel } from "./WorkflowStepRenderer";
import type { WorkflowStepStart } from "@/app/app/services/streamingModels";

const start = (overrides: Partial<WorkflowStepStart>) =>
  ({
    type: "workflow_step_start",
    step_name: "Read the request",
    agent_name: null,
    step_order: 0,
    ...overrides,
  }) as WorkflowStepStart;

describe("workflowStepLabel", () => {
  it("names the agent of an agent step", () => {
    expect(workflowStepLabel(start({ agent_name: "Researcher" }))).toBe("Researcher");
  });

  it("gives other steps their type", () => {
    expect(workflowStepLabel(start({ step_type: "code" }))).toBe("Code: Read the request");
  });

  it("shows where a step inside a container runs", () => {
    expect(
      workflowStepLabel(
        start({ agent_name: "Researcher", scope: "Research · Flights", depth: 1 })
      )
    ).toBe("↳ Researcher (Research · Flights)");
  });

  it("leaves top-level steps unmarked", () => {
    expect(workflowStepLabel(start({ agent_name: "Researcher", scope: null }))).toBe(
      "Researcher"
    );
  });
});
