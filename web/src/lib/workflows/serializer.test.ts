import type { WorkflowStepSnapshot } from "@/lib/workflows/interfaces";
import {
  buildWorkflowCreate,
  buildWorkflowUpdate,
  editorStepsToPayload,
  snapshotToEditorSteps,
  snapshotToMeta,
  stepOrderToNodeKey,
} from "@/lib/workflows/serializer";
import { createEditorStep, newNodeKey } from "@/lib/workflows/editorModel";
import { CATALOG, makeStep, makeWorkflow } from "@/lib/workflows/testFixtures";

/** Snapshot fields the server computes; they are never sent back. */
const RESPONSE_ONLY_FIELDS = new Set<keyof WorkflowStepSnapshot>([
  "id",
  "workflow_id",
  "agent_name",
  "latest_type_version",
  "upgrade_available",
]);

const agentStep = makeStep({
  id: 1,
  step_order: 0,
  node_key: "s1",
  step_description: "Collects details",
  input_mapping: { query: "$user_input", extra: { nested: [1, 2] } },
  condition: { legacy: "kept" },
  is_terminal: true,
  can_request_input: true,
  promote_output: true,
  llm_provider_override: "openai",
  llm_model_override: "gpt-4.1",
  max_output_tokens_override: 2048,
  system_prompt_override: "Be brief.",
  task_prompt_override: "Summarize $user_input",
  tool_ids_override: [3, 4],
  document_set_ids_override: [],
  replace_base_system_prompt_override: true,
});

const routerStep = makeStep({
  id: 2,
  step_order: 1,
  node_key: "s2",
  step_type: "conditional_router",
  type_version: 2,
  latest_type_version: 2,
  agent_id: null,
  agent_name: null,
  config: {
    condition_field: "$out_1.output",
    operator: "contains",
    match_value: "error",
    case_sensitive: true,
    true_node_keys: ["s3"],
    false_node_keys: ["n_abcdef01"],
  },
  // The server mirrors v2 configs into the legacy column; it is not sent back.
  condition: { true_steps: [2], false_steps: [3] },
});

const codeStep = makeStep({
  id: 3,
  step_order: 2,
  node_key: "s3",
  step_type: "code",
  agent_id: null,
  agent_name: null,
  config: { source: "print(1)", timeout_seconds: 5 },
});

const lastStep = makeStep({ id: 4, step_order: 3, node_key: "n_abcdef01" });

// A parallel container and a step in its second branch.
const parallelStep = makeStep({
  id: 5,
  step_order: 4,
  node_key: "s5",
  step_type: "parallel",
  agent_id: null,
  agent_name: null,
  config: {
    branches: [{ label: "Flights" }, { label: "Hotels" }],
    join: "wait_all",
    on_branch_error: "continue",
    max_concurrency: 2,
  },
});
const childStep = makeStep({
  id: 6,
  step_order: 5,
  node_key: "s6",
  parent_key: "s5",
  branch_index: 1,
});

const workflow = makeWorkflow([
  lastStep,
  codeStep,
  agentStep,
  routerStep,
  childStep,
  parallelStep,
]);

describe("round trip", () => {
  const steps = snapshotToEditorSteps(workflow);
  const payload = buildWorkflowUpdate(snapshotToMeta(workflow), steps, 7);

  it("orders steps by step_order", () => {
    expect(steps.map((s) => s.node_key)).toEqual([
      "s1",
      "s2",
      "s3",
      "n_abcdef01",
      "s5",
      "s6",
    ]);
    expect(payload.steps!.map((s) => s.step_order)).toEqual([0, 1, 2, 3, 4, 5]);
  });

  it.each([
    ["agent", agentStep, 0],
    ["code", codeStep, 2],
    ["container", parallelStep, 4],
    ["container child", childStep, 5],
  ])("carries every %s step field", (_label, snapshot, index) => {
    const sent = payload.steps![index]! as unknown as Record<string, unknown>;
    for (const [field, value] of Object.entries(snapshot)) {
      if (RESPONSE_ONLY_FIELDS.has(field as keyof WorkflowStepSnapshot))
        continue;
      expect([field, sent[field]]).toEqual([field, value]);
    }
  });

  it("sends routers as v2 configs keyed by node", () => {
    const sent = payload.steps![1]!;
    expect(sent).toMatchObject({
      node_key: "s2",
      step_type: "conditional_router",
      type_version: 2,
      condition: null,
      config: routerStep.config,
    });
  });

  it("carries workflow settings, including icon_name and the expected version", () => {
    expect(payload).toMatchObject({
      name: "Fixture workflow",
      description: "A workflow for tests",
      orchestration_mode: "sequential",
      icon_name: "rocket",
      max_steps: 10,
      timeout_seconds: 1800,
      expected_version: 7,
    });
    expect(
      buildWorkflowCreate(snapshotToMeta(workflow), steps)
    ).not.toHaveProperty("expected_version");
  });

  it("is stable when serialized twice", () => {
    const again = snapshotToEditorSteps(
      makeWorkflow(
        payload.steps!.map((s, i) =>
          makeStep({
            ...(s as Partial<WorkflowStepSnapshot>),
            id: i + 1,
            step_order: s.step_order,
          })
        )
      )
    );
    expect(editorStepsToPayload(again)).toEqual(payload.steps);
  });
});

describe("router targets", () => {
  it("survive re-ordering because they are node keys", () => {
    const [a, router, c, d] = snapshotToEditorSteps(workflow);
    // Move the false-branch target before the true-branch target.
    const reordered = editorStepsToPayload([a!, router!, d!, c!]);
    expect(reordered[1]!.config).toMatchObject({
      true_node_keys: ["s3"],
      false_node_keys: ["n_abcdef01"],
    });
    expect(reordered.map((s) => s.node_key)).toEqual([
      "s1",
      "s2",
      "n_abcdef01",
      "s3",
    ]);
  });

  it("drop targets whose step was deleted", () => {
    const [a, router, c] = snapshotToEditorSteps(workflow);
    const sent = editorStepsToPayload([a!, router!, c!]);
    expect(sent[1]!.config).toMatchObject({
      true_node_keys: ["s3"],
      false_node_keys: [],
    });
  });

  it("load legacy v1 routers (true_steps/false_steps) into node-key form", () => {
    const legacy = makeWorkflow([
      makeStep({ id: 10, step_order: 0 }),
      makeStep({
        id: 11,
        step_order: 1,
        step_type: "conditional_router",
        type_version: 1,
        latest_type_version: 2,
        upgrade_available: true,
        agent_id: null,
        config: null,
        condition: {
          condition_field: "$out_10.output",
          operator: "equals",
          match_value: "yes",
          case_sensitive: false,
          true_steps: [2],
          false_steps: [3, 99],
        },
      }),
      makeStep({ id: 12, step_order: 2 }),
      makeStep({ id: 13, step_order: 3 }),
    ]);
    const router = snapshotToEditorSteps(legacy)[1]!;
    expect(router).toMatchObject({
      type_version: 2,
      upgrade_available: false,
      condition: null,
      config: {
        condition_field: "$out_10.output",
        operator: "equals",
        match_value: "yes",
        case_sensitive: false,
        // Order 99 matches no step and is dropped, as on the server.
        true_node_keys: ["s12"],
        false_node_keys: ["s13"],
      },
    });
    expect(router.config).not.toHaveProperty("true_steps");
  });
});

describe("new steps", () => {
  it("get a fresh node key and are pinned to the latest version", () => {
    const key = newNodeKey(["n_00000000"]);
    expect(key).toMatch(/^n_[0-9a-f]{8}$/);

    const code = createEditorStep("code", CATALOG, { node_key: key });
    expect(code).toMatchObject({
      type_version: 1,
      parent_key: null,
      branch_index: null,
      config: { code: "def main(inputs):\n    return {}", timeout_seconds: 5 },
    });

    const router = createEditorStep("conditional_router", CATALOG, {
      node_key: "n_1",
    });
    expect(router.type_version).toBe(2);
    expect(router.config).toMatchObject({
      true_node_keys: [],
      false_node_keys: [],
    });
  });

  it("omit type_version when it is unknown, so the server picks the latest", () => {
    const step = createEditorStep("agent", [], {
      node_key: "n_2",
      agent_id: 5,
    });
    expect(editorStepsToPayload([step])[0]).not.toHaveProperty("type_version");
  });

  it("map empty override strings to null (inherit)", () => {
    const step = createEditorStep("agent", CATALOG, {
      node_key: "n_3",
      agent_id: 5,
      llm_model_override: "",
    });
    expect(editorStepsToPayload([step])[0]!.llm_model_override).toBeNull();
  });
});

describe("stepOrderToNodeKey", () => {
  it("maps positions to keys", () => {
    expect(stepOrderToNodeKey(snapshotToEditorSteps(workflow))).toEqual({
      0: "s1",
      1: "s2",
      2: "s3",
      3: "n_abcdef01",
      4: "s5",
      5: "s6",
    });
  });
});
