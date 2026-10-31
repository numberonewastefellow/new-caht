import {
  blockKey,
  depthFirst,
  descendantKeys,
  groupByBlock,
  isTopLevel,
  moveStep,
  removeStep,
  reorderInBlock,
  type BlockStep,
} from "@/lib/workflows/stepTree";

const step = (
  node_key: string,
  parent_key: string | null = null,
  branch_index: number | null = null
): BlockStep => ({ node_key, parent_key, branch_index });

const keys = (steps: BlockStep[]) => steps.map((s) => s.node_key);

describe("blocks", () => {
  it("tells apart the top level and each branch", () => {
    expect(isTopLevel(step("a"))).toBe(true);
    expect(isTopLevel(step("b", "p", 0))).toBe(false);
    expect(blockKey(step("b", "p", 0))).not.toBe(blockKey(step("c", "p", 1)));
    expect(blockKey(step("b", "p", 0))).toBe(blockKey(step("c", "p", 0)));
  });

  it("groups steps and keeps their order", () => {
    const blocks = groupByBlock([
      step("a"),
      step("x", "p", 0),
      step("b"),
      step("y", "p", 0),
    ]);
    expect(keys(blocks.get(blockKey(step("a")))!)).toEqual(["a", "b"]);
    expect(keys(blocks.get(blockKey(step("x", "p", 0)))!)).toEqual(["x", "y"]);
  });
});

describe("depthFirst", () => {
  it("leaves a flat workflow alone", () => {
    expect(keys(depthFirst([step("a"), step("b"), step("c")]))).toEqual([
      "a",
      "b",
      "c",
    ]);
  });

  it("puts each container's branches right after it, lowest branch first", () => {
    const steps = [
      step("start"),
      step("par"),
      step("hotels", "par", 1),
      step("flights", "par", 0),
      step("end"),
    ];
    expect(keys(depthFirst(steps))).toEqual([
      "start",
      "par",
      "flights",
      "hotels",
      "end",
    ]);
  });

  it("keeps the order within a branch", () => {
    const steps = [
      step("par"),
      step("a2", "par", 0),
      step("b", "par", 1),
      step("a1", "par", 0),
    ];
    expect(keys(depthFirst(steps))).toEqual(["par", "a2", "a1", "b"]);
  });

  it("walks nested containers", () => {
    const steps = [
      step("par"),
      step("inner", "par", 0),
      step("after", "par", 1),
      step("deep", "inner", 0),
    ];
    expect(keys(depthFirst(steps))).toEqual(["par", "inner", "deep", "after"]);
  });

  it("moves a child placed before its container to after it", () => {
    expect(keys(depthFirst([step("c", "par", 0), step("par")]))).toEqual([
      "par",
      "c",
    ]);
  });

  it("keeps steps with a missing container, last", () => {
    expect(keys(depthFirst([step("c", "gone", 0), step("a")]))).toEqual([
      "a",
      "c",
    ]);
  });

  it("keeps every step when parents form a cycle", () => {
    const steps = [step("a", "b", 0), step("b", "a", 0)];
    expect(keys(depthFirst(steps)).sort()).toEqual(["a", "b"]);
  });
});

describe("editing the tree", () => {
  const demo = [
    step("intake"),
    step("par"),
    step("travel", "par", 0),
    step("stay", "par", 1),
    step("wrap"),
  ];
  const places = (steps: BlockStep[]) =>
    steps.map((s) => `${s.node_key}:${s.parent_key ?? "-"}:${s.branch_index ?? "-"}`);

  describe("descendantKeys", () => {
    it("finds steps at any depth", () => {
      const steps = [
        step("a"),
        step("b", "a", 0),
        step("c", "b", 0),
        step("d"),
      ];
      expect(Array.from(descendantKeys(steps, "a")).sort()).toEqual(["b", "c"]);
    });
  });

  describe("moveStep", () => {
    it("moves a top-level step into a lane, last by default", () => {
      expect(
        places(moveStep(demo, "intake", { parent_key: "par", branch_index: 0 }))
      ).toEqual([
        "par:-:-",
        "travel:par:0",
        "intake:par:0",
        "stay:par:1",
        "wrap:-:-",
      ]);
    });

    it("moves a step to a position in the block", () => {
      expect(
        keys(moveStep(demo, "intake", { parent_key: "par", branch_index: 0 }, 0))
      ).toEqual(["par", "intake", "travel", "stay", "wrap"]);
    });

    it("moves a step between lanes", () => {
      expect(
        places(moveStep(demo, "travel", { parent_key: "par", branch_index: 1 }))
      ).toEqual([
        "intake:-:-",
        "par:-:-",
        "stay:par:1",
        "travel:par:1",
        "wrap:-:-",
      ]);
    });

    it("moves a step out to the top level", () => {
      expect(
        places(moveStep(demo, "travel", { parent_key: null, branch_index: null }))
      ).toEqual([
        "intake:-:-",
        "par:-:-",
        "stay:par:1",
        "wrap:-:-",
        "travel:-:-",
      ]);
    });

    it("moves a container with what's inside it", () => {
      const steps = [...demo, step("loop"), step("day", "loop", 0)];
      const moved = moveStep(steps, "loop", { parent_key: "par", branch_index: 1 }, 0);
      expect(places(moved).slice(2, 6)).toEqual([
        "travel:par:0",
        "loop:par:1",
        "day:loop:0",
        "stay:par:1",
      ]);
    });

    it("refuses to move a container into itself", () => {
      const steps = [step("a"), step("b", "a", 0)];
      expect(moveStep(steps, "a", { parent_key: "a", branch_index: 0 })).toEqual(steps);
      expect(moveStep(steps, "a", { parent_key: "b", branch_index: 0 })).toEqual(steps);
    });

    it("moves into an empty lane", () => {
      const steps = [step("a"), step("p")];
      expect(places(moveStep(steps, "a", { parent_key: "p", branch_index: 1 }))).toEqual([
        "p:-:-",
        "a:p:1",
      ]);
    });

    it("ignores an unknown step", () => {
      expect(moveStep(demo, "nope", { parent_key: null, branch_index: null })).toEqual(demo);
    });
  });

  describe("removeStep", () => {
    it("removes a plain step", () => {
      expect(keys(removeStep(demo, "intake"))).toEqual(["par", "travel", "stay", "wrap"]);
    });

    it("removes a container with what's inside it by default", () => {
      expect(keys(removeStep(demo, "par"))).toEqual(["intake", "wrap"]);
    });

    it("can keep a container's steps, in its place", () => {
      expect(places(removeStep(demo, "par", { keepChildren: true }))).toEqual([
        "intake:-:-",
        "travel:-:-",
        "stay:-:-",
        "wrap:-:-",
      ]);
    });

    it("keeps steps inside the block around a nested container", () => {
      const steps = [step("outer"), step("inner", "outer", 0), step("x", "inner", 0)];
      expect(places(removeStep(steps, "inner", { keepChildren: true }))).toEqual([
        "outer:-:-",
        "x:outer:0",
      ]);
    });
  });

  describe("reorderInBlock", () => {
    it("swaps with the neighbour in the same block, skipping what's inside a container", () => {
      expect(keys(reorderInBlock(demo, "wrap", -1))).toEqual([
        "intake",
        "wrap",
        "par",
        "travel",
        "stay",
      ]);
    });

    it("keeps children with their container", () => {
      expect(keys(reorderInBlock(demo, "par", -1))).toEqual([
        "par",
        "travel",
        "stay",
        "intake",
        "wrap",
      ]);
    });

    it("stays in its block at the edges", () => {
      const steps = [step("p"), step("a", "p", 0), step("b", "p", 0), step("c", "p", 1)];
      expect(keys(reorderInBlock(steps, "a", -1))).toEqual(["p", "a", "b", "c"]);
      expect(keys(reorderInBlock(steps, "b", 1))).toEqual(["p", "a", "b", "c"]);
      expect(keys(reorderInBlock(steps, "b", -1))).toEqual(["p", "b", "a", "c"]);
    });
  });
});
