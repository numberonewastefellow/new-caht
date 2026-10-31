import {
  layoutWorkflow,
  type LayoutStep,
} from "@/components/workflow-builder/containerLayout";

const SIZE = { width: 200, height: 100 };

function step(
  node_key: string,
  parent_key: string | null = null,
  branch_index: number | null = null
): LayoutStep {
  return { node_key, parent_key, branch_index, size: SIZE, lanes: null };
}

function box(
  node_key: string,
  lanes: string[],
  parent_key: string | null = null,
  branch_index: number | null = null
): LayoutStep {
  return { node_key, parent_key, branch_index, size: SIZE, lanes };
}

describe("layoutWorkflow", () => {
  it("lays a flat workflow out as one row, left to right", () => {
    const { placements } = layoutWorkflow([step("a"), step("b"), step("c")]);
    const [a, b, c] = ["a", "b", "c"].map((k) => placements.get(k)!);
    expect(a!.x).toBeLessThan(b!.x);
    expect(b!.x).toBeLessThan(c!.x);
    expect(new Set([a!.y, b!.y, c!.y]).size).toBe(1);
    expect(b!.x).toBeGreaterThanOrEqual(a!.x + SIZE.width);
  });

  it("gives a parallel one lane per branch, each holding its steps", () => {
    const { placements } = layoutWorkflow([
      box("par", ["Flights", "Hotels"]),
      step("f", "par", 0),
      step("h", "par", 1),
    ]);
    const par = placements.get("par")!;
    const [flights, hotels] = par.lanes!;
    expect(flights!.label).toBe("Flights");
    expect(hotels!.label).toBe("Hotels");
    expect(hotels!.y).toBeGreaterThanOrEqual(flights!.y + flights!.height);

    const f = placements.get("f")!;
    const h = placements.get("h")!;
    expect(f.parentId).toBe("par");
    // Children sit inside their own lane, relative to the box.
    expect(f.y).toBeGreaterThanOrEqual(flights!.y);
    expect(f.y + SIZE.height).toBeLessThanOrEqual(flights!.y + flights!.height);
    expect(h.y).toBeGreaterThanOrEqual(hotels!.y);
    expect(h.y + SIZE.height).toBeLessThanOrEqual(hotels!.y + hotels!.height);
  });

  it("sizes a box to hold its children", () => {
    const { placements } = layoutWorkflow([
      box("loop", ["Each"]),
      step("a", "loop", 0),
      step("b", "loop", 0),
    ]);
    const loop = placements.get("loop")!;
    const b = placements.get("b")!;
    expect(b.x).toBeGreaterThan(placements.get("a")!.x);
    expect(b.x + SIZE.width).toBeLessThanOrEqual(loop.size.width);
    expect(b.y + SIZE.height).toBeLessThanOrEqual(loop.size.height);
  });

  it("nests boxes", () => {
    const { placements } = layoutWorkflow([
      box("par", ["A", "B"]),
      box("loop", ["Each"], "par", 0),
      step("inner", "loop", 0),
      step("other", "par", 1),
    ]);
    const par = placements.get("par")!;
    const loop = placements.get("loop")!;
    expect(loop.parentId).toBe("par");
    expect(placements.get("inner")!.parentId).toBe("loop");
    expect(loop.x + loop.size.width).toBeLessThanOrEqual(par.size.width);
    expect(loop.y + loop.size.height).toBeLessThanOrEqual(par.size.height);
  });

  it("keeps a box after it in the row clear of the box", () => {
    const { placements } = layoutWorkflow([
      box("par", ["A", "B"]),
      step("a", "par", 0),
      step("b", "par", 1),
      step("after"),
    ]);
    const par = placements.get("par")!;
    expect(placements.get("after")!.x).toBeGreaterThan(par.x + par.size.width);
  });

  it("keeps lanes that have no steps yet", () => {
    const { placements } = layoutWorkflow([box("par", ["A", "B"])]);
    expect(placements.get("par")!.lanes).toHaveLength(2);
  });
});
