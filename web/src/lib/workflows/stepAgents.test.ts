import {
  DEFAULT_ASSISTANT_AGENT_ID,
  isSelectableStepAgent,
  selectableStepAgents,
} from "@/lib/workflows/stepAgents";

describe("step agents", () => {
  it("accepts dedicated agents", () => {
    expect(isSelectableStepAgent({ id: 7 })).toBe(true);
    expect(isSelectableStepAgent({ id: 7, workflow_id: null })).toBe(true);
  });

  it("refuses the default Assistant and workflow wrapper agents", () => {
    expect(isSelectableStepAgent({ id: DEFAULT_ASSISTANT_AGENT_ID })).toBe(false);
    expect(isSelectableStepAgent({ id: 7, workflow_id: 3 })).toBe(false);
  });

  it("filters a list and keeps the agents' own fields", () => {
    const agents = [
      { id: 0, name: "Assistant" },
      { id: 5, name: "Researcher" },
      { id: 9, name: "Some workflow", workflow_id: 3 },
    ];
    expect(selectableStepAgents(agents)).toEqual([{ id: 5, name: "Researcher" }]);
  });
});
