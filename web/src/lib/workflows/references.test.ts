import { createEditorStep, type EditorStep } from "@/lib/workflows/editorModel";
import { availableReferences } from "@/lib/workflows/references";
import { CATALOG } from "@/lib/workflows/testFixtures";

const agent = (key: string, overrides: Partial<EditorStep> = {}) =>
  createEditorStep("agent", CATALOG, {
    node_key: key,
    agent_id: 1,
    step_name: key,
    output_key: key,
    ...overrides,
  });

const container = (
  type: "parallel" | "loop",
  key: string,
  overrides: Partial<EditorStep> = {}
) =>
  createEditorStep(type, CATALOG, {
    node_key: key,
    step_name: key,
    output_key: key,
    ...overrides,
  });

describe("availableReferences", () => {
  it("offers the user's input and earlier steps, not later ones", () => {
    const [a, b, c] = [agent("a"), agent("b"), agent("c")];
    expect(availableReferences(b!, [a!, b!, c!])).toEqual([
      "$user_input",
      "$a.output",
    ]);
  });

  it("names a code step's declared outputs", () => {
    const code = createEditorStep("code", CATALOG, {
      node_key: "plan",
      step_name: "plan",
      output_key: "plan",
      config: { outputs: [{ name: "days" }, { name: "city" }] },
    });
    const a = agent("a");
    expect(availableReferences(a, [code, a])).toEqual([
      "$user_input",
      "$plan.output",
      "$plan.output.days",
      "$plan.output.city",
    ]);
  });

  it("offers loop variables only inside a loop, not to the loop itself", () => {
    const loop = container("loop", "l");
    const body = agent("x", { parent_key: "l", branch_index: 0 });
    const refs = availableReferences(body, [loop, body]);
    expect(refs).toContain("$loop.item");
    expect(refs).toContain("$loop.previous");
    expect(availableReferences(loop, [loop, body])).not.toContain("$loop.item");
  });

  it("keeps a sibling branch out, because it runs at the same time", () => {
    const start = agent("start");
    const par = container("parallel", "p");
    const flights = agent("flights", { parent_key: "p", branch_index: 0 });
    const hotels = agent("hotels", { parent_key: "p", branch_index: 1 });
    const steps = [start, par, flights, hotels];
    expect(availableReferences(hotels, steps)).toEqual([
      "$user_input",
      "$start.output",
    ]);
  });

  it("offers earlier steps in the same branch", () => {
    const par = container("parallel", "p");
    const first = agent("first", { parent_key: "p", branch_index: 0 });
    const second = agent("second", { parent_key: "p", branch_index: 0 });
    expect(availableReferences(second, [par, first, second])).toContain(
      "$first.output"
    );
  });

  it("lets a later step read a container and its direct children", () => {
    const par = container("parallel", "p");
    const child = agent("c", { parent_key: "p", branch_index: 0 });
    const after = agent("after");
    expect(availableReferences(after, [par, child, after])).toEqual([
      "$user_input",
      "$p.output",
      "$c.output",
    ]);
  });
});
