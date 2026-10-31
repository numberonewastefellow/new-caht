import type { EditorStep } from "./editorModel";
import { configProblems, stepOutputSchema } from "./nodeConfigRules";

describe("agent steps with an expected output", () => {
  const step = (config: Record<string, unknown> | null, canRequestInput = false) =>
    ({
      node_key: "a",
      step_type: "agent",
      config,
      can_request_input: canRequestInput,
    }) as unknown as EditorStep;
  const problems = (config: Record<string, unknown> | null, canRequestInput = false) => {
    const s = step(config, canRequestInput);
    return configProblems(s, "A", [s], new Map([["a", s]]));
  };
  const SCHEMA = { type: "object", properties: { days: { type: "array" } } };

  it("reads the schema", () => {
    expect(stepOutputSchema(step(null))).toBeNull();
    expect(stepOutputSchema(step({ output_schema: null }))).toBeNull();
    expect(stepOutputSchema(step({ output_schema: SCHEMA }))).toEqual(SCHEMA);
  });

  it("has nothing to say about a free-text step", () => {
    expect(problems(null)).toEqual([]);
    expect(problems({ output_schema: null })).toEqual([]);
  });

  it("accepts an object with properties", () => {
    expect(problems({ output_schema: SCHEMA })).toEqual([]);
  });

  it("refuses other shapes", () => {
    expect(problems({ output_schema: { type: "array" } })[0]).toContain(
      "object with properties"
    );
    expect(problems({ output_schema: { type: "object" } })[0]).toContain(
      "object with properties"
    );
  });

  it("refuses it on a step that can ask questions", () => {
    expect(problems({ output_schema: SCHEMA }, true)[0]).toContain("ask the user");
  });
});
