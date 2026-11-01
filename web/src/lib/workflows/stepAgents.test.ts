import {
  DEFAULT_ASSISTANT_AGENT_ID,
  isSelectableStepAgent,
  selectableStepAgents, OVERRIDES_CLEARED_ON_AGENT_CHANGE } from "@/lib/workflows/stepAgents";

describe("step agents", () => {
  it("accepts dedicated agents", () => {
    expect(isSelectableStepAgent({ id: 7 })).toBe(true);
    expect(isSelectableStepAgent({ id: 7, workflow_id: null })).toBe(true);
  });

  it("refuses the default Assistant and workflow wrapper agents", () => {
    expect(isSelectableStepAgent({ id: DEFAULT_ASSISTANT_AGENT_ID })).toBe(false);
    expect(isSelectableStepAgent({ id: 7, workflow_id: 3 })).toBe(false);
  });

  it("clears every override a step can have when its agent changes", () => {
    expect(Object.keys(OVERRIDES_CLEARED_ON_AGENT_CHANGE).sort()).toEqual([
      "document_set_ids_override",
      "llm_model_override",
      "llm_provider_override",
      "max_output_tokens_override",
      "replace_base_system_prompt_override",
      "system_prompt_override",
      "task_prompt_override",
      "tool_ids_override",
    ]);
    expect(new Set(Object.values(OVERRIDES_CLEARED_ON_AGENT_CHANGE))).toEqual(new Set([null]));
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
