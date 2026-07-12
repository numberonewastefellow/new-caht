/**
 * Migration-safety: EE-move import smoke test.
 *
 * EE removal moved `web/src/ee/*` into the main tree and deleted the `src/ee` directory
 * (there is one edition now). Static import breakage is caught by `tsc --noEmit` /
 * `next build`, but this test gives a fast runtime confirmation that each module still
 * resolves and evaluates at its NEW location.
 *
 * The paths below are the post-move homes:
 *   src/ee/providers/AppModeProvider       -> folded into src/providers/AppModeProvider
 *   src/ee/providers/QueryControllerProvider -> folded into src/providers/QueryControllerProvider
 *   src/ee/sections/{SearchUI,SearchCard}  -> src/sections/
 *   src/ee/lib/search/svc                  -> src/lib/search/svc
 *
 * The providers were FOLDED IN rather than moved: the main-tree files already owned the
 * context + hook and the ee/ files owned the impl (they imported each other by design).
 * So the assertions check the merged module exposes BOTH halves -- the provider and the
 * hook -- which is what proves the fold actually landed rather than dropping one side.
 */

describe("EE-move import smoke", () => {
  it("imports the merged provider modules, with both the provider and its hook", async () => {
    const appMode = await import("@/providers/AppModeProvider");
    const queryController = await import("@/providers/QueryControllerProvider");

    expect(appMode.AppModeProvider).toBeDefined();
    expect(appMode.useAppMode).toBeDefined();
    expect(queryController.QueryControllerProvider).toBeDefined();
    expect(queryController.useQueryController).toBeDefined();
  });

  it("imports the moved section modules", async () => {
    const searchUI = await import("@/sections/SearchUI");
    const searchCard = await import("@/sections/SearchCard");
    expect(searchUI.default).toBeDefined();
    expect(searchCard.default).toBeDefined();
  });

  it("imports the moved search service", async () => {
    const svc = await import("@/lib/search/svc");
    expect(svc.classifyQuery).toBeDefined();
    expect(svc.searchDocuments).toBeDefined();
  });

  it("has no `ee` / `ce` edition-split directories left on disk", () => {
    // The EE/CE split is gone. Checked on the filesystem rather than with
    // `expect(import("@/ce")).rejects` -- a static import specifier for a module that
    // does not exist is a COMPILE error (tsc TS2307), so the test file itself would
    // stop building. Reintroducing either path should fail this test, not the build.
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const fs = require("fs");
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const path = require("path");
    const src = path.join(process.cwd(), "src");
    expect(fs.existsSync(path.join(src, "ee"))).toBe(false);
    expect(fs.existsSync(path.join(src, "ce.tsx"))).toBe(false);
    expect(fs.existsSync(path.join(src, "app", "ee"))).toBe(false);
  });
});
