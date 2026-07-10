/**
 * Migration-safety: EE-move import smoke test.
 *
 * The EE-removal step moves `web/src/ee/*` into the main tree. Static import
 * breakage is caught by `tsc --noEmit` / `next build`, but this test gives a fast,
 * runtime confirmation that each moved module still resolves + evaluates.
 *
 * Before/after usage: run on the current tree for a green baseline; after the move,
 * update the import paths below to the new locations and it re-confirms resolution.
 * If a module fails to import (bad path, broken transitive import), the test fails.
 */

describe("EE-move import smoke", () => {
  it("imports the moved EE provider modules", async () => {
    const appMode = await import("@/ee/providers/AppModeProvider");
    const queryController = await import("@/ee/providers/QueryControllerProvider");
    expect(appMode).toBeDefined();
    expect(queryController).toBeDefined();
    // Each module must export at least one binding (default or named).
    expect(Object.keys(appMode).length).toBeGreaterThan(0);
    expect(Object.keys(queryController).length).toBeGreaterThan(0);
  });

  it("imports the moved EE section modules", async () => {
    const searchUI = await import("@/ee/sections/SearchUI");
    const searchCard = await import("@/ee/sections/SearchCard");
    expect(Object.keys(searchUI).length).toBeGreaterThan(0);
    expect(Object.keys(searchCard).length).toBeGreaterThan(0);
  });

  it("imports the moved EE search service", async () => {
    const svc = await import("@/ee/lib/search/svc");
    expect(Object.keys(svc).length).toBeGreaterThan(0);
  });
});
