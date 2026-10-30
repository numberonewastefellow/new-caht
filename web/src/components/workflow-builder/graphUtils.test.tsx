/**
 * Visual Builder graph <-> payload conversion. Pure logic; named .tsx only
 * so the jest "integration" project (src/components/**) picks it up.
 */
import {
  graphToPayload,
  graphToSteps,
  graphToUpdatePayload,
  snapshotToGraph,
  validateGraph,
} from "@/components/workflow-builder/graphUtils";
import type {
  StepFlowNode,
  WorkflowEdge,
  WorkflowNode,
} from "@/components/workflow-builder/types";
import { isStepNode } from "@/components/workflow-builder/types";
import {
  buildWorkflowCreate,
  snapshotToEditorSteps,
  snapshotToMeta,
} from "@/lib/workflows/serializer";
import { CATALOG, makeStep, makeWorkflow } from "@/lib/workflows/testFixtures";

const ROUTER = makeStep({
  id: 2,
  step_order: 1,
  step_type: "conditional_router",
  type_version: 2,
  latest_type_version: 2,
  agent_id: null,
  config: {
    condition_field: "$out_1.output",
    operator: "contains",
    match_value: "error",
    case_sensitive: false,
    true_node_keys: ["s3"],
    false_node_keys: ["s4"],
  },
});

const workflow = makeWorkflow([
  makeStep({
    id: 1,
    step_order: 0,
    tool_ids_override: [7],
    input_mapping: { a: 1 },
  }),
  ROUTER,
  makeStep({ id: 3, step_order: 2 }),
  makeStep({ id: 4, step_order: 3 }),
  makeStep({
    id: 5,
    step_order: 4,
    step_type: "teleport",
    agent_id: null,
    config: { to: "mars" },
  }),
]);

function stepNode(nodes: WorkflowNode[], id: string): StepFlowNode {
  const node = nodes.find((n) => n.id === id);
  if (!node || !isStepNode(node)) throw new Error(`no step node ${id}`);
  return node;
}

describe("snapshotToGraph", () => {
  const { nodes, edges } = snapshotToGraph(workflow, CATALOG);

  it("uses node keys as node ids and editor kinds as node types", () => {
    expect(nodes.filter(isStepNode).map((n) => [n.id, n.type])).toEqual([
      ["s1", "agent"],
      ["s2", "router"],
      ["s3", "agent"],
      ["s4", "agent"],
      ["s5", "unsupported"],
    ]);
  });

  it("draws router branches from the True/False handles", () => {
    const branches = edges
      .filter((e) => e.source === "s2")
      .map((e) => [e.sourceHandle, e.target]);
    expect(branches).toEqual([
      ["true", "s3"],
      ["false", "s4"],
    ]);
  });

  it("saves the same payload the Wizard serializer produces", () => {
    const meta = snapshotToMeta(workflow);
    expect(graphToPayload(nodes, edges, meta)).toEqual(
      buildWorkflowCreate(meta, snapshotToEditorSteps(workflow))
    );
  });

  it("keeps unknown node types unchanged", () => {
    const payload = graphToPayload(nodes, edges, snapshotToMeta(workflow));
    expect(payload.steps[4]).toMatchObject({
      node_key: "s5",
      step_type: "teleport",
      config: { to: "mars" },
    });
  });
});

describe("router branches come from edges (bug 1)", () => {
  const { nodes, edges } = snapshotToGraph(workflow, CATALOG);

  it("re-wiring the canvas changes the saved targets", () => {
    // Stale branch data on the node must not matter.
    const staleNodes = nodes.map((n) =>
      n.id === "s2" && isStepNode(n)
        ? {
            ...n,
            data: {
              ...n.data,
              config: { ...n.data.config, true_node_keys: ["s1"] },
            },
          }
        : n
    );
    const rewired: WorkflowEdge[] = edges
      .filter((e) => e.source !== "s2")
      .concat([
        { id: "t", source: "s2", sourceHandle: "true", target: "s4" },
        { id: "f1", source: "s2", sourceHandle: "false", target: "s3" },
        { id: "f2", source: "s2", sourceHandle: "false", target: "s5" },
      ]);
    const router = graphToSteps(staleNodes, rewired).find(
      (s) => s.node_key === "s2"
    )!;
    expect(router.config).toMatchObject({
      true_node_keys: ["s4"],
      false_node_keys: ["s3", "s5"],
    });
  });

  it("keeps targets when the canvas order changes", () => {
    // Move s4 to the left of s3 so BFS orders it first.
    const moved = nodes.map((n) =>
      n.id === "s4" ? { ...n, position: { x: -1000, y: n.position.y } } : n
    );
    const payload = graphToUpdatePayload(
      moved,
      edges,
      snapshotToMeta(workflow),
      7
    );
    const routerStep = payload.steps!.find((s) => s.node_key === "s2")!;
    expect(routerStep.config).toMatchObject({
      true_node_keys: ["s3"],
      false_node_keys: ["s4"],
    });
    expect(payload.expected_version).toBe(7);
  });
});

describe("validateGraph", () => {
  it("flags routers in LLM Decision mode", () => {
    const llm = makeWorkflow(workflow.steps.slice(0, 4), {
      orchestration_mode: "llm_decision",
    });
    const { nodes, edges } = snapshotToGraph(llm, CATALOG);
    expect(stepNode(nodes, "s2").data.modeConflict).toBe(true);
    const messages = validateGraph(
      nodes,
      edges,
      snapshotToMeta(llm),
      CATALOG
    ).map((e) => e.message);
    expect(messages).toContain(
      '"Step 2" is a Condition step, which can\'t be used in LLM Decision mode'
    );
  });

  it("accepts a valid sequential graph", () => {
    const valid = makeWorkflow(workflow.steps.slice(0, 4));
    const { nodes, edges } = snapshotToGraph(valid, CATALOG);
    expect(validateGraph(nodes, edges, snapshotToMeta(valid), CATALOG)).toEqual(
      []
    );
  });
});

describe("containers (no group-node UI yet)", () => {
  const withParallel = makeWorkflow([
    makeStep({ id: 1, step_order: 0 }),
    makeStep({
      id: 2,
      step_order: 1,
      step_type: "parallel",
      agent_id: null,
      step_name: "Fan out",
      config: { join: "wait_all" },
    }),
    makeStep({ id: 3, step_order: 2, parent_key: "s2", branch_index: 0 }),
    makeStep({ id: 4, step_order: 3, parent_key: "s2", branch_index: 1 }),
  ]);

  it("shows containers and children as normal nodes with badges", () => {
    const { nodes } = snapshotToGraph(withParallel, CATALOG);
    expect(stepNode(nodes, "s2")).toMatchObject({
      type: "schema",
      data: { childCount: 2, containerName: null },
    });
    expect(stepNode(nodes, "s4").data).toMatchObject({
      containerName: "Fan out",
      branch_index: 1,
    });
  });

  it("keeps parent_key and branch_index on save", () => {
    const { nodes, edges } = snapshotToGraph(withParallel, CATALOG);
    const payload = graphToPayload(nodes, edges, snapshotToMeta(withParallel));
    expect(
      payload.steps.map((s) => [s.node_key, s.parent_key, s.branch_index])
    ).toEqual([
      ["s1", null, null],
      ["s2", null, null],
      ["s3", "s2", 0],
      ["s4", "s2", 1],
    ]);
  });
});
