/**
 * Migration-safety: runtime dynamic-import resolution.
 *
 * Static imports are verified by tsc/next build. Dynamic `import("...")` paths are
 * resolved lazily at runtime and can silently break after a move/refactor. The web
 * app has a very small dynamic surface; the only app-source dynamic import that
 * points at a first-party module is StatsOverlayLoader -> @/components/dev/StatsOverlay.
 * (The others target npm packages: stats.js, react-icons/fa, sentry configs.)
 */

describe("dynamic import resolution", () => {
  it("resolves the StatsOverlay lazy import", async () => {
    const mod = await import("@/components/dev/StatsOverlay");
    expect(mod).toBeDefined();
    expect(Object.keys(mod).length).toBeGreaterThan(0);
  });

  it("resolves the StatsOverlayLoader wrapper module", async () => {
    const loader = await import("@/components/dev/StatsOverlayLoader");
    expect(loader).toBeDefined();
    expect(Object.keys(loader).length).toBeGreaterThan(0);
  });
});
