/**
 * Visual Builder graph <-> payload conversion. Pure logic; named .tsx only
 * so the jest "integration" project (src/components/**) picks it up.
 */
import {
  graphFromSteps,
  graphToPayload,
  graphToSteps,
  graphToUpdatePayload,
  laneAt,
  snapshotToGraph,
  validateGraph,
} from "@/components/workflow-builder/graphUtils";
import { moveStep, removeStep } from "@/lib/workflows/stepTree";
import type {
  StepFlowNode,
  WorkflowEdge,
  WorkflowNode,
} from "@/components/workflow-builder/types";
import {
  FINISH_NODE_ID,
  ORCHESTRATOR_NODE_ID,
  isStepNode,
} from "@/components/workflow-builder/types";
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

describe("saved order", () => {
  it("doesn't reorder steps after a router's branch (loading then saving)", () => {
    // R -> x, x -> x2, R -> y: BFS used to save [R, x, y, x2].
    const workflow = makeWorkflow([
      makeStep({ id: 1, step_order: 0 }),
      makeStep({
        id: 2,
        step_order: 1,
        step_type: "conditional_router",
        agent_id: null,
        step_name: "Route",
        config: {
          condition_field: "$a.output",
          operator: "contains",
          match_value: "x",
          case_sensitive: false,
          true_node_keys: ["s3"],
          false_node_keys: ["s5"],
        },
      }),
      makeStep({ id: 3, step_order: 2 }),
      makeStep({ id: 4, step_order: 3 }),
      makeStep({ id: 5, step_order: 4 }),
    ]);
    const { nodes, edges } = snapshotToGraph(workflow, CATALOG);
    const payload = graphToPayload(nodes, edges, snapshotToMeta(workflow));
    expect(payload.steps.map((s) => s.node_key)).toEqual([
      "s1",
      "s2",
      "s3",
      "s4",
      "s5",
    ]);
  });

  it("re-wiring within a block changes the order", () => {
    const workflow = makeWorkflow([
      makeStep({ id: 1, step_order: 0 }),
      makeStep({ id: 2, step_order: 1 }),
      makeStep({ id: 3, step_order: 2 }),
    ]);
    const { nodes } = snapshotToGraph(workflow, CATALOG);
    const edge = (source: string, target: string) => ({
      id: `edge-${source}-${target}`,
      source,
      target,
      type: "step" as const,
    });
    const rewired = [
      edge(ORCHESTRATOR_NODE_ID, "s1"),
      edge("s1", "s3"),
      edge("s3", "s2"),
    ];
    const payload = graphToPayload(nodes, rewired, snapshotToMeta(workflow));
    expect(payload.steps.map((s) => s.node_key)).toEqual(["s1", "s3", "s2"]);
  });
});

describe("workflows without containers", () => {
  it("keep the existing grid layout", () => {
    const workflow = makeWorkflow([
      makeStep({ id: 1, step_order: 0 }),
      makeStep({ id: 2, step_order: 1 }),
      makeStep({ id: 3, step_order: 2 }),
      makeStep({ id: 4, step_order: 3 }),
    ]);
    const { nodes } = snapshotToGraph(workflow, CATALOG);
    const row = (id: string) => stepNode(nodes, id).position.y;
    expect(row("s1")).toBe(row("s3"));
    expect(row("s4")).toBeGreaterThan(row("s1"));
    expect(stepNode(nodes, "s1").parentId).toBeUndefined();
  });
});

describe("the demo: code + parallel + loop", () => {
  const code = (id: number, order: number, name: string) =>
    makeStep({
      id,
      step_order: order,
      step_type: "code",
      agent_id: null,
      step_name: name,
      node_key: name,
      output_key: name,
      config: { code: "def main(inputs):\n    return {}\n" },
    });
  const agent = (id: number, order: number, name: string, parent: string, branch: number) =>
    makeStep({
      id,
      step_order: order,
      node_key: name,
      output_key: name,
      step_name: name,
      parent_key: parent,
      branch_index: branch,
    });
  const demo = makeWorkflow([
    code(1, 0, "intake"),
    makeStep({
      id: 2,
      step_order: 1,
      node_key: "research",
      output_key: "research",
      step_type: "parallel",
      agent_id: null,
      step_name: "research",
      config: { branches: [{ label: "Getting there" }, { label: "Where to stay" }] },
    }),
    agent(3, 2, "travel", "research", 0),
    agent(4, 3, "stay", "research", 1),
    makeStep({
      id: 5,
      step_order: 4,
      node_key: "days",
      output_key: "days",
      step_type: "loop",
      agent_id: null,
      step_name: "days",
      config: { mode: "for_each", items: "$intake.output.days", max_iterations: 5 },
    }),
    agent(6, 5, "day", "days", 0),
    code(7, 6, "wrap"),
  ]);

  const graph = () => snapshotToGraph(demo, CATALOG);
  const links = (edges: ReturnType<typeof graph>["edges"]) =>
    edges.map((e) => `${e.source}>${e.target}`);

  it("saves exactly what was loaded", () => {
    const { nodes, edges } = graph();
    const payload = graphToPayload(nodes, edges, snapshotToMeta(demo));
    expect(
      payload.steps.map((s) => [s.node_key, s.step_order, s.parent_key, s.branch_index])
    ).toEqual([
      ["intake", 0, null, null],
      ["research", 1, null, null],
      ["travel", 2, "research", 0],
      ["stay", 3, "research", 1],
      ["days", 4, null, null],
      ["day", 5, "days", 0],
      ["wrap", 6, null, null],
    ]);
  });

  it("chains only within a block: branches aren't drawn as one after the other", () => {
    expect(links(graph().edges)).toEqual([
      `${ORCHESTRATOR_NODE_ID}>intake`,
      "intake>research",
      "research>days",
      "days>wrap",
      `wrap>${FINISH_NODE_ID}`,
    ]);
  });

  it("is valid: a branch's first step needs no incoming line", () => {
    const { nodes, edges } = graph();
    expect(validateGraph(nodes, edges, snapshotToMeta(demo), CATALOG)).toEqual([]);
  });

  describe("editing the structure", () => {
    const apply = (edit: (steps: ReturnType<typeof graphToSteps>) => ReturnType<typeof graphToSteps>) => {
      const { nodes, edges } = graph();
      return graphFromSteps(nodes, edit(graphToSteps(nodes, edges)), "sequential");
    };
    const saved = (g: ReturnType<typeof apply>) =>
      graphToPayload(g.nodes, g.edges, snapshotToMeta(demo)).steps;

    it("moving a step out of a box redraws the chain and saves it", () => {
      const g = apply((steps) =>
        moveStep(steps, "travel", { parent_key: null, branch_index: null }, 1)
      );
      expect(stepNode(g.nodes, "travel").parentId).toBeUndefined();
      expect(links(g.edges)).toContain("intake>travel");
      expect(links(g.edges)).toContain("travel>research");
      expect(saved(g).map((s) => s.node_key)).toEqual([
        "intake",
        "travel",
        "research",
        "stay",
        "days",
        "day",
        "wrap",
      ]);
    });

    it("moving a step into a lane puts it in the box and chains it there", () => {
      const g = apply((steps) =>
        moveStep(steps, "wrap", { parent_key: "days", branch_index: 0 })
      );
      expect(stepNode(g.nodes, "wrap").parentId).toBe("days");
      expect(links(g.edges)).toContain("day>wrap");
      expect(links(g.edges)).toContain(`days>${FINISH_NODE_ID}`);
    });

    it("removing a container takes its steps and heals the chain", () => {
      const g = apply((steps) => removeStep(steps, "research"));
      expect(g.nodes.map((n) => n.id)).not.toContain("travel");
      expect(links(g.edges)).toContain("intake>days");
    });

    it("removing a container can keep its steps, in its place", () => {
      const g = apply((steps) =>
        removeStep(steps, "research", { keepChildren: true })
      );
      expect(stepNode(g.nodes, "travel").parentId).toBeUndefined();
      expect(links(g.edges)).toEqual(
        expect.arrayContaining(["intake>travel", "travel>stay", "stay>days"])
      );
    });

    it("drops to the normal grid once the last container is gone", () => {
      const g = apply((steps) =>
        removeStep(removeStep(steps, "research"), "days")
      );
      expect(g.nodes.filter(isStepNode).every((n) => !n.parentId)).toBe(true);
    });

    it("the result stays valid and saves after a move", () => {
      const g = apply((steps) =>
        moveStep(steps, "stay", { parent_key: "research", branch_index: 0 })
      );
      expect(g.nodes.find((n) => n.id === "stay")).toBeDefined();
      expect(saved(g).filter((s) => s.parent_key === "research")).toHaveLength(2);
    });
  });

  describe("laneAt", () => {
    const boxOf = (id: string) => {
      const { nodes } = graph();
      const box = stepNode(nodes, id);
      return { nodes, box, lanes: box.data.lanes! };
    };

    it("finds the lane under a point", () => {
      const { nodes, box, lanes } = boxOf("research");
      const point = (lane: number) => ({
        x: box.position.x + 40,
        y: box.position.y + lanes[lane]!.y + 10,
      });
      expect(laneAt(nodes, point(0))).toEqual({ parent_key: "research", branch_index: 0 });
      expect(laneAt(nodes, point(1))).toEqual({ parent_key: "research", branch_index: 1 });
    });

    it("is null outside every box and on a box's header", () => {
      const { nodes, box } = boxOf("research");
      expect(laneAt(nodes, { x: -5000, y: -5000 })).toBeNull();
      expect(laneAt(nodes, { x: box.position.x + 40, y: box.position.y + 5 })).toBeNull();
    });

    it("ignores excluded boxes", () => {
      const { nodes, box, lanes } = boxOf("research");
      const point = { x: box.position.x + 40, y: box.position.y + lanes[0]!.y + 10 };
      expect(laneAt(nodes, point, new Set(["research"]))).toBeNull();
    });
  });
});

describe("containers", () => {
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

  it("draws the container as a box holding its children", () => {
    const { nodes } = snapshotToGraph(withParallel, CATALOG);
    const box = stepNode(nodes, "s2");
    expect(box.type).toBe("container");
    expect(box.style?.width).toBeGreaterThan(0);
    expect(box.data.lanes).toHaveLength(2);
    expect(stepNode(nodes, "s3").parentId).toBe("s2");
    expect(stepNode(nodes, "s4").parentId).toBe("s2");
    expect(stepNode(nodes, "s1").parentId).toBeUndefined();
  });

  it("puts containers before their children, as React Flow requires", () => {
    const { nodes } = snapshotToGraph(withParallel, CATALOG);
    const ids = nodes.map((n) => n.id);
    expect(ids.indexOf("s2")).toBeLessThan(ids.indexOf("s3"));
    expect(ids.indexOf("s2")).toBeLessThan(ids.indexOf("s4"));
  });

  it("doesn't save the layout: positions and lanes stay out of the payload", () => {
    const { nodes, edges } = snapshotToGraph(withParallel, CATALOG);
    const saved = JSON.stringify(
      graphToPayload(nodes, edges, snapshotToMeta(withParallel))
    );
    expect(saved).not.toContain("lanes");
    expect(saved).not.toContain("parentId");
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
