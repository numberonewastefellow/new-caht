import { createEditorStep, type EditorStep } from "@/lib/workflows/editorModel";
import {
  laneLabels,
  moveEditorStep,
  placementChoices,
} from "@/lib/workflows/containerLanes";
import { CATALOG } from "@/lib/workflows/testFixtures";

function agent(key: string, overrides: Partial<EditorStep> = {}): EditorStep {
  return createEditorStep("agent", CATALOG, {
    node_key: key,
    agent_id: 1,
    step_name: key,
    output_key: key,
    ...overrides,
  });
}

function parallel(key: string, overrides: Partial<EditorStep> = {}): EditorStep {
  return createEditorStep("parallel", CATALOG, {
    node_key: key,
    step_name: key,
    output_key: key,
    config: { branches: [{ label: "A" }, { label: "B" }] },
    ...overrides,
  });
}

function loop(key: string, overrides: Partial<EditorStep> = {}): EditorStep {
  return createEditorStep("loop", CATALOG, {
    node_key: key,
    step_name: key,
    output_key: key,
    ...overrides,
  });
}

const parents = (step: EditorStep, steps: EditorStep[]) =>
  placementChoices(step, steps, CATALOG).map((c) => c.parent_key);

describe("laneLabels", () => {
  it("uses the configured branch labels", () => {
    expect(laneLabels(parallel("p"), [])).toEqual(["A", "B"]);
  });

  it("shows a lane for a branch beyond the labels, so its steps stay visible", () => {
    const steps = [agent("x", { parent_key: "p", branch_index: 3 })];
    expect(laneLabels(parallel("p"), steps)).toEqual([
      "A",
      "B",
      "Branch 3",
      "Branch 4",
    ]);
  });

  it("gives a parallel two lanes before it has a config", () => {
    expect(laneLabels(parallel("p", { config: null }), [])).toEqual([
      "Branch 1",
      "Branch 2",
    ]);
  });

  it("gives a loop one lane", () => {
    expect(laneLabels(loop("l"), [])).toEqual(["Each iteration"]);
  });
});

describe("placementChoices", () => {
  it("offers the top level and every container", () => {
    const a = agent("a");
    const steps = [a, parallel("p"), loop("l")];
    expect(parents(a, steps)).toEqual([null, "p", "l"]);
  });

  it("gives each container's lanes", () => {
    const a = agent("a");
    const choices = placementChoices(a, [a, parallel("p")], CATALOG);
    expect(choices[1]).toMatchObject({ label: "p", lanes: ["A", "B"] });
  });

  it("never offers a step itself or what's inside it", () => {
    const outer = loop("outer");
    const inner = loop("inner", { parent_key: "outer", branch_index: 0 });
    expect(parents(outer, [outer, inner])).toEqual([null]);
  });

  it("doesn't allow a parallel inside a parallel, even through a loop", () => {
    const moving = parallel("moving");
    const steps = [
      moving,
      parallel("other"),
      loop("l", { parent_key: "other", branch_index: 0 }),
      loop("free"),
    ];
    expect(parents(moving, steps)).toEqual([null, "free"]);
  });

  it("doesn't allow a loop holding a parallel into a parallel", () => {
    const moving = loop("moving");
    const inner = parallel("inner", { parent_key: "moving", branch_index: 0 });
    expect(parents(moving, [moving, inner, parallel("p")])).toEqual([null]);
  });

  it("respects the nesting limit", () => {
    const a = agent("a");
    const steps = [
      a,
      loop("l1"),
      loop("l2", { parent_key: "l1", branch_index: 0 }),
      loop("l3", { parent_key: "l2", branch_index: 0 }),
    ];
    expect(parents(a, steps)).toEqual([null, "l1", "l2", "l3"]);

    const box = loop("box");
    const child = agent("c", { parent_key: "box", branch_index: 0 });
    expect(parents(box, [box, child, ...steps.slice(1)])).toEqual([
      null,
      "l1",
      "l2",
    ]);
  });
});

describe("moveEditorStep", () => {
  const options = (steps: EditorStep[], key: string) => {
    const step = steps.find((s) => s.node_key === key);
    return [step?.is_terminal, step?.promote_output, step?.can_request_input];
  };
  const steps = [
    loop("box"),
    agent("a", {
      is_terminal: true,
      promote_output: true,
      can_request_input: true,
    }),
  ];

  it("turns off the options a step can't have inside a container", () => {
    const moved = moveEditorStep(steps, "a", { parent_key: "box", branch_index: 0 });
    expect(moved.find((s) => s.node_key === "a")?.parent_key).toBe("box");
    expect(options(moved, "a")).toEqual([false, false, false]);
  });

  it("keeps them when the step stays at the top level", () => {
    const moved = moveEditorStep(steps, "a", { parent_key: null, branch_index: null });
    expect(options(moved, "a")).toEqual([true, true, true]);
  });

  it("places the step at the given position", () => {
    const moved = moveEditorStep(
      [agent("x"), agent("y"), agent("z")],
      "z",
      { parent_key: null, branch_index: null },
      1
    );
    expect(moved.map((s) => s.node_key)).toEqual(["x", "z", "y"]);
  });

  it("keeps them when the move is refused", () => {
    const inside = loop("b", { parent_key: "a", branch_index: 0 });
    const moved = moveEditorStep([...steps, inside], "a", {
      parent_key: "b",
      branch_index: 0,
    });
    expect(options(moved, "a")).toEqual([true, true, true]);
  });
});
