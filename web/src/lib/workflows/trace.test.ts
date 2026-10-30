import {
  GENERIC_LANE_Y,
  normalizeTrace,
  traceNodeLabel,
  traceNodeLaneY,
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
