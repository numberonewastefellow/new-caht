import type { EditorStep } from "./editorModel";
import { hidesFinalAnswer, lastRunningStep } from "./finalAnswer";

function step(key: string, fields: Partial<EditorStep> = {}): EditorStep {
  return {
    node_key: key,
    parent_key: null,
    disabled: false,
    promote_output: false,
    ...fields,
  } as EditorStep;
}

describe("lastRunningStep", () => {
  it("is the last top-level step that runs", () => {
    const steps = [
      step("a"),
      step("box"),
      step("inner", { parent_key: "box" }),
      step("c", { disabled: true }),
    ];
    expect(lastRunningStep(steps)?.node_key).toBe("box");
  });

  it("is nothing when no step runs", () => {
    expect(lastRunningStep([step("a", { disabled: true })])).toBeUndefined();
  });
});

describe("hidesFinalAnswer", () => {
  it("is true for an earlier step shown as a message", () => {
    const steps = [step("a", { promote_output: true }), step("b")];
    expect(hidesFinalAnswer(steps[0]!, steps)).toBe(true);
  });

  it("is false when the last step is shown too", () => {
    const steps = [step("a", { promote_output: true }), step("b", { promote_output: true })];
    expect(hidesFinalAnswer(steps[0]!, steps)).toBe(false);
  });

  it("is false for the last step itself", () => {
    const steps = [step("a"), step("b", { promote_output: true })];
    expect(hidesFinalAnswer(steps[1]!, steps)).toBe(false);
  });

  it("is false for a skipped step, which never shows anything", () => {
    const steps = [step("a"), step("b", { promote_output: true, disabled: true })];
    expect(hidesFinalAnswer(steps[1]!, steps)).toBe(false);
  });

  it("counts only the steps that run when finding the last one", () => {
    const steps = [step("a", { promote_output: true }), step("b", { disabled: true })];
    expect(hidesFinalAnswer(steps[0]!, steps)).toBe(false);
  });
});
