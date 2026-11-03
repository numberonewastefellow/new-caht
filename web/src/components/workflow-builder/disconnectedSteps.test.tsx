/**
 * A top-level step no line from Start reaches is kept but doesn't run. Named .tsx
 * so the jest "integration" project (src/components/**) picks it up.
 */
import { fireEvent, render, screen } from "@testing-library/react";
import {
  disconnectedStepIds,
  DISCONNECTED_NODE_CLASS,
  graphToSteps,
  snapshotToGraph,
  validateGraph,
  withDisconnectedMarks,
} from "@/components/workflow-builder/graphUtils";
import { StepOptionsSection } from "@/components/workflow-builder/StepOptionsSection";
import type { StepNodeData, WorkflowEdge, WorkflowNode } from "@/components/workflow-builder/types";
import { FINISH_NODE_ID, ORCHESTRATOR_NODE_ID } from "@/components/workflow-builder/types";
import { editorStepsToPayload, snapshotToEditorSteps, snapshotToMeta } from "@/lib/workflows/serializer";
import { CATALOG, makeStep, makeWorkflow } from "@/lib/workflows/testFixtures";
import type { WorkflowSnapshot } from "@/lib/workflows/interfaces";

// FIR Correction Helper -> Parallel 5 -> Charge Sheet Builder, as in workflow 79
const FIR = makeWorkflow([
  makeStep({ id: 1, step_order: 0, step_name: "FIR Correction Helper" }),
  makeStep({ id: 2, step_order: 1, step_name: "Parallel 5" }),
  makeStep({ id: 3, step_order: 2, step_name: "Charge Sheet Builder" }),
]);

const isLine = (edge: WorkflowEdge, from: string, to: string) =>
  edge.source === from && edge.target === to;

function cut(edges: WorkflowEdge[], from: string, to: string): WorkflowEdge[] {
  const kept = edges.filter((e) => !isLine(e, from, to));
  expect(kept).toHaveLength(edges.length - 1);
  return kept;
}

/** Save the canvas, then load what was saved, as the editor does. */
function saveAndReload(nodes: WorkflowNode[], edges: WorkflowEdge[], source: WorkflowSnapshot) {
  const saved = editorStepsToPayload(graphToSteps(nodes, edges));
  const reloaded = makeWorkflow(
    saved.map((step, i) =>
      makeStep({
        id: i + 1,
        node_key: step.node_key,
        step_order: step.step_order,
        step_name: step.step_name,
        disabled: step.disabled,
      })
    ),
    { orchestration_mode: source.orchestration_mode }
  );
  return { saved, ...snapshotToGraph(reloaded, CATALOG) };
}

describe("connected workflow (nothing cut)", () => {
  it("runs every step and saves none as disconnected", () => {
    const { nodes, edges } = snapshotToGraph(FIR, CATALOG);
    expect(disconnectedStepIds(nodes, edges).size).toBe(0);
    expect(graphToSteps(nodes, edges).map((s) => s.disabled)).toEqual([false, false, false]);
    expect(validateGraph(nodes, edges, snapshotToMeta(FIR), CATALOG)).toEqual([]);
  });

  it("draws exactly the lines it drew before this change", () => {
    const { edges } = snapshotToGraph(FIR, CATALOG);
    expect(edges.map((e) => `${e.source}->${e.target}`)).toEqual([
      `${ORCHESTRATOR_NODE_ID}->s1`,
      "s1->s2",
      "s2->s3",
      `s3->${FINISH_NODE_ID}`,
    ]);
  });

  it("leaves the drawn nodes untouched", () => {
    const { nodes, edges } = snapshotToGraph(FIR, CATALOG);
    expect(withDisconnectedMarks(nodes, edges)).toEqual(nodes);
  });
});

describe("cutting a line", () => {
  it("skips everything after the cut, and saving is allowed", () => {
    const graph = snapshotToGraph(FIR, CATALOG);
    const edges = cut(graph.edges, "s1", "s2");
    expect(disconnectedStepIds(graph.nodes, edges)).toEqual(new Set(["s2", "s3"]));
    const steps = graphToSteps(graph.nodes, edges);
    expect(steps.map((s) => [s.step_name, s.disabled])).toEqual([
      ["FIR Correction Helper", false],
      ["Parallel 5", true],
      ["Charge Sheet Builder", true],
    ]);
    expect(validateGraph(graph.nodes, edges, snapshotToMeta(FIR), CATALOG)).toEqual([]);
  });

  it("comes back the same after saving and reloading", () => {
    const graph = snapshotToGraph(FIR, CATALOG);
    const { saved, nodes, edges } = saveAndReload(graph.nodes, cut(graph.edges, "s1", "s2"), FIR);
    expect(saved.map((s) => s.disabled)).toEqual([false, true, true]);
    const lines = edges.map((e) => `${e.source}->${e.target}`);
    expect(lines).toContain(`${ORCHESTRATOR_NODE_ID}->s1`);
    expect(lines).toContain(`s1->${FINISH_NODE_ID}`);
    // The cut-off part keeps its own line, and nothing links it to Start
    expect(lines).toContain("s2->s3");
    expect(lines).not.toContain("s1->s2");
    expect(disconnectedStepIds(nodes, edges)).toEqual(new Set(["s2", "s3"]));
  });

  it("reconnecting runs them all again", () => {
    const graph = snapshotToGraph(FIR, CATALOG);
    const reconnected = [
      ...cut(graph.edges, "s1", "s2"),
      { id: "e-new", source: "s1", target: "s2", type: "step" } as WorkflowEdge,
    ];
    expect(graphToSteps(graph.nodes, reconnected).map((s) => s.disabled)).toEqual([
      false,
      false,
      false,
    ]);
  });

  it("a middle step cut out and bridged over is the only one skipped", () => {
    const graph = snapshotToGraph(FIR, CATALOG);
    const edges = [
      ...cut(cut(graph.edges, "s1", "s2"), "s2", "s3"),
      { id: "e-bridge", source: "s1", target: "s3", type: "step" } as WorkflowEdge,
    ];
    const steps = graphToSteps(graph.nodes, edges);
    expect(steps.filter((s) => s.disabled).map((s) => s.step_name)).toEqual(["Parallel 5"]);
    const reloaded = saveAndReload(graph.nodes, edges, FIR);
    const lines = reloaded.edges.map((e) => `${e.source}->${e.target}`);
    expect(lines).toContain("s1->s3");
    expect(lines).toContain(`s3->${FINISH_NODE_ID}`);
  });

  it("refuses to save when nothing is connected", () => {
    const graph = snapshotToGraph(FIR, CATALOG);
    const edges = cut(graph.edges, ORCHESTRATOR_NODE_ID, "s1");
    const messages = validateGraph(graph.nodes, edges, snapshotToMeta(FIR), CATALOG).map(
      (e) => e.message
    );
    expect(messages).toEqual([
      "Every step is disconnected, so this workflow has nothing to run. Connect at least one step.",
    ]);
  });

  it("greys and badges the disconnected steps on the canvas only", () => {
    const graph = snapshotToGraph(FIR, CATALOG);
    const edges = cut(graph.edges, "s1", "s2");
    const shown = withDisconnectedMarks(graph.nodes, edges);
    const marked = shown.filter((n) => n.className?.includes(DISCONNECTED_NODE_CLASS));
    expect(marked.map((n) => n.id)).toEqual(["s2", "s3"]);
    expect((marked[0]!.data as StepNodeData).disconnected).toBe(true);
    // The display mark never reaches the saved step
    expect(editorStepsToPayload(graphToSteps(shown, edges))[1]).not.toHaveProperty("disconnected");
  });
});

describe("LLM Decision mode", () => {
  const llm = makeWorkflow(FIR.steps, { orchestration_mode: "llm_decision" });

  it("a step without a line from the orchestrator is skipped", () => {
    const graph = snapshotToGraph(llm, CATALOG);
    const edges = cut(graph.edges, ORCHESTRATOR_NODE_ID, "s3");
    expect(graphToSteps(graph.nodes, edges).map((s) => s.disabled)).toEqual([false, false, true]);
    const reloaded = saveAndReload(graph.nodes, edges, llm);
    expect(reloaded.edges.some((e) => e.target === "s3")).toBe(false);
  });
});

describe("loading a saved workflow", () => {
  it("keeps the disabled flag from the server", () => {
    const steps = snapshotToEditorSteps(
      makeWorkflow([
        makeStep({ id: 1, step_order: 0 }),
        makeStep({ id: 2, step_order: 1, disabled: true }),
      ])
    );
    expect(steps.map((s) => s.disabled)).toEqual([false, true]);
  });

  it("treats steps saved before the flag existed as connected", () => {
    const old = makeStep({ id: 1, step_order: 0 });
    delete (old as Partial<typeof old>).disabled;
    expect(snapshotToEditorSteps(makeWorkflow([old]))[0]!.disabled).toBe(false);
  });
});

describe("Show as Message note", () => {
  function renderOptions(cutLine: boolean, promoted: string[]) {
    const graph = snapshotToGraph(FIR, CATALOG);
    const edges = cutLine ? cut(graph.edges, "s1", "s2") : graph.edges;
    const steps = graphToSteps(graph.nodes, edges).map((s) => ({
      ...s,
      promote_output: promoted.includes(s.node_key),
    }));
    const data = { ...steps[0]!, promote_output: promoted.includes("s1") } as StepNodeData;
    render(
      <StepOptionsSection nodeId="s1" data={data} canPause onUpdate={jest.fn()} steps={steps} />
    );
  }

  it("warns when an earlier step's message replaces the last answer", () => {
    renderOptions(false, ["s1"]);
    expect(screen.getByRole("note")).toHaveTextContent("won't appear in the chat");
  });

  it("says nothing when the last step shows its answer too", () => {
    renderOptions(false, ["s1", "s3"]);
    expect(screen.queryByRole("note")).toBeNull();
  });

  it("says nothing when this step is the last one that runs", () => {
    renderOptions(true, ["s1"]);
    expect(screen.queryByRole("note")).toBeNull();
  });

  it("says nothing when the option is off", () => {
    renderOptions(false, []);
    expect(screen.queryByRole("note")).toBeNull();
  });

  it("toggling still reports the change", () => {
    const onUpdate = jest.fn();
    const graph = snapshotToGraph(FIR, CATALOG);
    const steps = graphToSteps(graph.nodes, graph.edges);
    render(
      <StepOptionsSection
        nodeId="s1"
        data={steps[0] as StepNodeData}
        canPause
        onUpdate={onUpdate}
        steps={steps}
      />
    );
    const showAsMessage = screen.getAllByRole("switch")[2]!;
    fireEvent.click(showAsMessage);
    expect(onUpdate).toHaveBeenCalledWith("s1", { promote_output: true });
  });
});
