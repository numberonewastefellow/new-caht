import { createEditorStep, type EditorStep } from "@/lib/workflows/editorModel";
import {
  stepsNotAllowedInMode,
  validateSteps,
} from "@/lib/workflows/validation";
import { CATALOG } from "@/lib/workflows/testFixtures";

function agent(key: string, overrides: Partial<EditorStep> = {}): EditorStep {
  return createEditorStep("agent", CATALOG, {
    node_key: key,
    agent_id: 1,
    step_name: key,
    output_key: `out_${key}`,
    ...overrides,
  });
}

function router(key: string, trueKeys: string[], falseKeys: string[] = []) {
  return createEditorStep("conditional_router", CATALOG, {
    node_key: key,
    step_name: key,
    output_key: `out_${key}`,
    config: {
      condition_field: "$a.output",
      operator: "contains",
      match_value: "x",
      case_sensitive: false,
      true_node_keys: trueKeys,
      false_node_keys: falseKeys,
    },
  });
}

const messages = (
  steps: EditorStep[],
  mode: "sequential" | "llm_decision" = "sequential"
) => validateSteps(steps, mode, CATALOG).map((e) => e.message);

describe("validateSteps", () => {
  it("accepts a valid workflow", () => {
    expect(
      messages([agent("a"), router("r", ["b"], ["c"]), agent("b"), agent("c")])
    ).toEqual([]);
  });

  it("requires steps, names, agents and unique output keys", () => {
    expect(messages([])).toEqual(["Add at least one step to the workflow"]);
    expect(
      messages([
        agent("a", { step_name: "", agent_id: null }),
        agent("b", { output_key: "out_a" }),
      ])
    ).toEqual([
      "Step 1 needs a step name",
      '"Step 1" needs an agent',
      'Duplicate output key "out_a" (also used by "Step 1")',
    ]);
  });

  it("requires router branches that come after the router", () => {
    expect(messages([agent("a"), router("r", [])])).toContain(
      'Condition "r" needs at least one step in its True or False branch'
    );
    expect(messages([agent("a"), router("r", ["a"])])).toContain(
      'Condition "r" can only branch to steps that come after it'
    );
  });

  it("rejects step types the mode does not allow", () => {
    const steps = [agent("a"), router("r", ["b"]), agent("b")];
    expect(messages(steps, "llm_decision")).toContain(
      '"r" is a Condition step, which can\'t be used in LLM Decision mode'
    );
    expect(
      stepsNotAllowedInMode(steps, "llm_decision", CATALOG).map(
        (s) => s.node_key
      )
    ).toEqual(["r"]);
  });

  it("checks required config fields of schema-driven types", () => {
    const code = createEditorStep("transform", CATALOG, {
      node_key: "c",
      step_name: "Code",
      output_key: "code_out",
    });
    expect(messages([code])).toEqual(['"Code" needs a value for Source']);
    expect(messages([{ ...code, config: { source: "print(1)" } }])).toEqual([]);
  });
});

describe("containers", () => {
  const parallel = createEditorStep("parallel", CATALOG, {
    node_key: "p",
    step_name: "Fan out",
    output_key: "fan",
  });
  const inBranch = (key: string, branch: number) =>
    agent(key, { parent_key: "p", branch_index: branch });

  it("accepts routers targeting steps of their own branch", () => {
    const steps = [
      parallel,
      { ...router("r", ["b"]), parent_key: "p", branch_index: 0 },
      inBranch("b", 0),
    ];
    expect(messages(steps)).toEqual([]);
  });

  it("rejects router targets in another block", () => {
    const steps = [parallel, router("r", ["b"]), inBranch("b", 1)];
    expect(messages(steps)).toContain(
      'Condition "r" can only branch to steps in the same container branch'
    );
  });

  it("flags steps whose container was removed", () => {
    expect(messages([agent("a"), inBranch("b", 0)])).toContain(
      '"b" belongs to a container that was removed; remove it too'
    );
  });
});

describe("validateSteps options", () => {
  it("can skip the mode check (the Wizard picks the mode after the steps)", () => {
    const steps = [agent("a"), router("r", ["b"]), agent("b")];
    expect(
      validateSteps(steps, "llm_decision", CATALOG, { checkModes: false })
    ).toEqual([]);
  });
});
