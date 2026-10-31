import { createEditorStep, type EditorStep } from "@/lib/workflows/editorModel";
import { validateSteps } from "@/lib/workflows/validation";
import { CATALOG } from "@/lib/workflows/testFixtures";

const THREE_LABELS = [{ label: "A" }, { label: "B" }, { label: "C" }];

function agent(key: string, overrides: Partial<EditorStep> = {}): EditorStep {
  return createEditorStep("agent", CATALOG, {
    node_key: key,
    agent_id: 1,
    step_name: key,
    output_key: `out_${key}`,
    ...overrides,
  });
}

function parallel(key = "p", overrides: Partial<EditorStep> = {}): EditorStep {
  return createEditorStep("parallel", CATALOG, {
    node_key: key,
    step_name: key,
    output_key: `out_${key}`,
    config: { branches: [{ label: "A" }, { label: "B" }] },
    ...overrides,
  });
}

function loop(key = "l", overrides: Partial<EditorStep> = {}): EditorStep {
  return createEditorStep("loop", CATALOG, {
    node_key: key,
    step_name: key,
    output_key: `out_${key}`,
    config: { mode: "for_each", items: "$a.output", max_iterations: 5 },
    ...overrides,
  });
}

function code(config: Record<string, unknown>): EditorStep {
  return createEditorStep("code", CATALOG, {
    node_key: "c",
    step_name: "c",
    output_key: "out_c",
    config: {
      source: "x",
      code: "def main(inputs):\n    return {}\n",
      ...config,
    },
  });
}

const child = (key: string, parent: string, branch = 0) =>
  agent(key, { parent_key: parent, branch_index: branch });

const messages = (steps: EditorStep[]) =>
  validateSteps(steps, "sequential", CATALOG).map((e) => e.message);

describe("container structure", () => {
  it("accepts a parallel with both branches filled and a loop with a body", () => {
    expect(
      messages([
        parallel(),
        child("a", "p", 0),
        child("b", "p", 1),
        loop(),
        child("c", "l"),
      ])
    ).toEqual([]);
  });

  it("accepts a loop inside a parallel branch", () => {
    expect(
      messages([
        parallel(),
        loop("l", { parent_key: "p", branch_index: 0 }),
        child("a", "l"),
        child("b", "p", 1),
      ])
    ).toEqual([]);
  });

  it("rejects a branch without a container", () => {
    expect(messages([agent("a", { branch_index: 0 })])).toContain(
      '"a" has a branch but no container'
    );
  });

  it("rejects a parent that can't hold steps", () => {
    expect(messages([agent("a"), child("b", "a")])).toContain(
      '"b" is inside "Agent", which can\'t contain steps'
    );
  });

  it("rejects a child without a branch", () => {
    const steps = [
      parallel(),
      agent("a", { parent_key: "p", branch_index: null }),
    ];
    expect(messages(steps)).toContain('"a" needs a branch');
  });

  it("rejects a child placed before its container", () => {
    expect(messages([child("a", "p", 0), parallel()])).toContain(
      '"a" must come after its container'
    );
  });

  it("rejects nesting deeper than three containers", () => {
    const steps = [
      loop("l1"),
      loop("l2", { parent_key: "l1", branch_index: 0 }),
      loop("l3", { parent_key: "l2", branch_index: 0 }),
      loop("l4", { parent_key: "l3", branch_index: 0 }),
      child("a", "l4"),
    ];
    expect(messages(steps)).toContain(
      "Containers can be nested at most 3 levels deep"
    );
  });

  it.each([
    ["can_request_input"],
    ["promote_output"],
    ["is_terminal"],
  ] as const)("rejects %s on a child", (flag) => {
    const steps = [
      loop(),
      agent("a", { parent_key: "l", branch_index: 0, [flag]: true }),
    ];
    expect(messages(steps)).toContain(
      '"a" is inside a container, so it can\'t ask for input, promote its output, or end the workflow'
    );
  });

  it("rejects more than 100 steps", () => {
    const steps = Array.from({ length: 101 }, (_, i) => agent(`s${i}`));
    expect(messages(steps)).toContain("A workflow can have at most 100 steps");
  });
});

describe("parallel config", () => {
  it("needs 2 to 8 branches", () => {
    expect(
      messages([parallel("p", { config: { branches: [{ label: "A" }] } })])
    ).toContain('Parallel step "p" needs 2 to 8 branches');
  });

  it("names branches without steps", () => {
    expect(messages([parallel(), child("a", "p", 0)])).toContain(
      'Parallel step "p": branches without steps: B'
    );
  });

  it("rejects steps in a branch that doesn't exist", () => {
    const steps = [
      parallel(),
      child("a", "p", 0),
      child("b", "p", 1),
      child("c", "p", 2),
    ];
    expect(messages(steps)).toContain(
      'Parallel step "p" has steps in a branch that doesn\'t exist'
    );
  });

  it("accepts every branch filled", () => {
    const steps = [
      parallel("p", { config: { branches: THREE_LABELS } }),
      child("a", "p", 0),
      child("b", "p", 1),
      child("c", "p", 2),
    ];
    expect(messages(steps)).toEqual([]);
  });

  it("rejects a parallel inside a parallel, even through a loop", () => {
    const steps = [
      parallel("outer"),
      loop("l", { parent_key: "outer", branch_index: 0 }),
      parallel("inner", { parent_key: "l", branch_index: 0 }),
      child("a", "inner", 0),
      child("b", "inner", 1),
      child("c", "outer", 1),
    ];
    expect(messages(steps)).toContain(
      'Parallel step "inner" can\'t be inside another parallel step'
    );
  });

  it("needs unique, non-empty branch names", () => {
    const named = (labels: string[]) => [
      parallel("p", { config: { branches: labels.map((label) => ({ label })) } }),
      child("a", "p", 0),
      child("b", "p", 1),
    ];
    expect(messages(named(["Same", "Same"]))).toContain(
      'Parallel step "p": branch names must be unique'
    );
    expect(messages(named(["A", " "]))).toContain(
      'Parallel step "p": every branch needs a name'
    );
  });

  it("limits concurrency", () => {
    const steps = [
      parallel("p", {
        config: {
          branches: [{ label: "A" }, { label: "B" }],
          max_concurrency: 9,
        },
      }),
      child("a", "p", 0),
      child("b", "p", 1),
    ];
    expect(messages(steps)).toContain(
      'Parallel step "p" can run 1 to 8 branches at once'
    );
  });
});

describe("loop config", () => {
  it("needs a body", () => {
    expect(messages([loop()])).toContain(
      'Loop step "l" has no steps to repeat'
    );
  });

  it("needs items in for_each mode", () => {
    const steps = [
      loop("l", { config: { mode: "for_each", items: " " } }),
      child("a", "l"),
    ];
    expect(messages(steps)).toContain(
      'Loop step "l" needs items (a $reference to a list)'
    );
  });

  it("needs a condition in while mode", () => {
    const steps = [
      loop("l", { config: { mode: "while", condition_field: "" } }),
      child("a", "l"),
    ];
    expect(messages(steps)).toContain('Loop step "l" needs a condition');
  });

  it("limits iterations", () => {
    const steps = [
      loop("l", {
        config: { mode: "for_each", items: "$a", max_iterations: 51 },
      }),
      child("a", "l"),
    ];
    expect(messages(steps)).toContain('Loop step "l" can repeat 1 to 50 times');
  });
});

describe("code config", () => {
  it("accepts a valid step", () => {
    expect(
      messages([
        code({
          inputs: { text: "$user_input" },
          outputs: [{ name: "result" }],
        }),
      ])
    ).toEqual([]);
  });

  it("needs unique, named outputs", () => {
    expect(messages([code({ outputs: [{ name: "a" }, { name: "a" }] })])).toContain(
      'Code step "c": output names must be unique'
    );
    expect(messages([code({ outputs: [] })])).toContain(
      'Code step "c" needs at least one output'
    );
    expect(messages([code({ outputs: [{ name: "" }] })])).toContain(
      'Code step "c": every output needs a name'
    );
  });

  it("needs input names that are Python identifiers", () => {
    expect(messages([code({ inputs: { "not valid": "x", ok_1: "y" } })])).toContain(
      'Code step "c": invalid input names: not valid'
    );
  });

  it("needs a main function", () => {
    expect(messages([code({ code: "print(1)" })])).toContain(
      'Code step "c": define a function main(inputs) that returns a dict'
    );
  });

  it("limits the timeout", () => {
    expect(messages([code({ timeout_seconds: 31 })])).toContain(
      'Code step "c" can run for 1 to 30 seconds'
    );
  });
});
