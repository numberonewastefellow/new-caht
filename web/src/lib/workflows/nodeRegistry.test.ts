import {
  editorKindFor,
  humanizeNodeType,
  isAllowedInMode,
  isContainer,
  labelFor,
  latestVersion,
  paletteTypes,
  resolveVersion,
} from "@/lib/workflows/nodeRegistry";
import { CATALOG } from "@/lib/workflows/testFixtures";

describe("version lookups", () => {
  it("finds the latest and pinned versions", () => {
    expect(latestVersion(CATALOG, "conditional_router")?.version).toBe(2);
    expect(resolveVersion(CATALOG, "conditional_router", 1)?.deprecated).toBe(
      true
    );
    expect(resolveVersion(CATALOG, "conditional_router", null)?.version).toBe(
      2
    );
    expect(latestVersion(CATALOG, "teleport")).toBeUndefined();
    expect(resolveVersion(CATALOG, "agent", 9)).toBeUndefined();
  });
});

describe("paletteTypes", () => {
  it("excludes types not allowed in the mode", () => {
    expect(paletteTypes(CATALOG, "llm_decision").map((t) => t.type)).toEqual([
      "agent",
    ]);
    expect(paletteTypes(CATALOG, "sequential").map((t) => t.type)).toEqual([
      "agent",
      "conditional_router",
      "code",
      "parallel",
      "loop",
      "transform",
    ]);
  });

  it("excludes types whose latest version is deprecated", () => {
    const catalog = CATALOG.map((t) =>
      t.type === "code"
        ? {
            ...t,
            versions: t.versions.map((v) => ({ ...v, deprecated: true })),
          }
        : t
    );
    expect(
      paletteTypes(catalog, "sequential").map((t) => t.type)
    ).not.toContain("code");
  });
});

describe("capabilities", () => {
  it("checks modes per version and is lenient for unknown types", () => {
    expect(
      isAllowedInMode(CATALOG, "conditional_router", 2, "llm_decision")
    ).toBe(false);
    expect(isAllowedInMode(CATALOG, "agent", 1, "llm_decision")).toBe(true);
    expect(isAllowedInMode(CATALOG, "teleport", 1, "llm_decision")).toBe(true);
    expect(isAllowedInMode([], "conditional_router", 2, "llm_decision")).toBe(
      true
    );
  });

  it("reports containers", () => {
    expect(isContainer(CATALOG, "agent")).toBe(false);
    expect(isContainer(CATALOG, "parallel")).toBe(true);
    const withLoop = [
      ...CATALOG,
      {
        type: "loop",
        latest_version: 1,
        versions: [{ ...CATALOG[0]!.versions[0]!, is_container: true }],
      },
    ];
    expect(isContainer(withLoop, "loop")).toBe(true);
  });
});

describe("presentation", () => {
  it("labels known types from the catalog and humanizes unknown ones", () => {
    expect(labelFor(CATALOG, "conditional_router")).toBe("Condition");
    expect(labelFor(CATALOG, "web_hook_trigger")).toBe("Web hook trigger");
    expect(humanizeNodeType("")).toBe("Step");
  });

  it("picks the editor kind", () => {
    expect(editorKindFor(CATALOG, "agent")).toBe("agent");
    expect(editorKindFor(CATALOG, "conditional_router")).toBe("router");
    expect(editorKindFor(CATALOG, "code")).toBe("schema");
    expect(editorKindFor(CATALOG, "teleport")).toBe("unsupported");
    // Built-in types keep their UI even before the catalog loads.
    expect(editorKindFor([], "agent")).toBe("agent");
  });
});
