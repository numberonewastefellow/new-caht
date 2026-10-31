import {
  GENERIC_LANE_Y,
  normalizeTrace,
  traceGrid,
  traceHasContainers,
  traceNodeLabel,
  traceNodeLaneY,
  type TraceNode,
  type WorkflowTrace,
} from "@/lib/workflows/trace";

describe("trace node fallbacks", () => {
  it("labels and places known and unknown node types", () => {
    expect(traceNodeLabel("router")).toBe("Decision");
    expect(traceNodeLabel("parallel_group")).toBe("Parallel group");
    expect(traceNodeLaneY("orchestrator")).toBe(0);
    expect(traceNodeLaneY("code")).toBe(GENERIC_LANE_Y);
  });

  it("fills missing fields of new or partial nodes", () => {
    const trace = normalizeTrace({
      execution_id: 1,
      workflow_id: 1,
      workflow_name: "w",
      mode: "sequential",
      status: "completed",
      total_tokens: 0,
      total_duration_ms: 0,
      nodes: [{ id: "n1", type: "loop" } as never],
      edges: [{ from_id: "n1", to_id: "n2", type: "flow" }, {} as never],
    } as WorkflowTrace);
    expect(trace.nodes[0]).toMatchObject({
      id: "n1",
      type: "loop",
      name: "Loop",
      status: "completed",
      input: "",
      output: "",
      file_ids: [],
      file_names: [],
    });
    expect(trace.edges).toHaveLength(1);
  });
});

describe("traceGrid", () => {
  const node = (id: string, depth: number | null = null): TraceNode => ({
    id,
    type: "agent",
    name: id,
    status: "completed",
    input: "",
    output: "",
    file_ids: [],
    file_names: [],
    depth,
  });
  const edge = (from_id: string, to_id: string) => ({
    from_id,
    to_id,
    type: "sequence",
  });
  const trace = (nodes: TraceNode[], edges: ReturnType<typeof edge>[]) =>
    ({ nodes, edges }) as unknown as WorkflowTrace;

  it("stacks parallel branches in one column and joins after them", () => {
    const grid = traceGrid(
      trace(
        [node("start"), node("par"), node("a", 1), node("b", 1), node("after")],
        [
          edge("start", "par"),
          edge("par", "a"),
          edge("par", "b"),
          edge("a", "after"),
          edge("b", "after"),
        ]
      )
    );
    expect(grid.get("a")!.column).toBe(grid.get("b")!.column);
    expect(grid.get("a")!.row).not.toBe(grid.get("b")!.row);
    expect(grid.get("after")!.column).toBe(grid.get("a")!.column + 1);
  });

  it("places what follows branches of different lengths after the longest", () => {
    const grid = traceGrid(
      trace(
        [node("par"), node("a1", 1), node("a2", 1), node("b", 1), node("after")],
        [
          edge("par", "a1"),
          edge("a1", "a2"),
          edge("par", "b"),
          edge("a2", "after"),
          edge("b", "after"),
        ]
      )
    );
    expect(grid.get("after")!.column).toBe(grid.get("a2")!.column + 1);
  });

  it("ignores edges going back (an orchestrator's returns)", () => {
    const grid = traceGrid(
      trace([node("orch"), node("agent")], [edge("orch", "agent"), edge("agent", "orch")])
    );
    expect(grid.get("orch")!.column).toBe(0);
    expect(grid.get("agent")!.column).toBe(1);
  });

  it("knows when a run has containers", () => {
    expect(traceHasContainers(trace([node("a")], []))).toBe(false);
    expect(traceHasContainers(trace([node("a"), node("b", 1)], []))).toBe(true);
  });
});
