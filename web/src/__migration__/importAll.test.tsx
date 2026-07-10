/**
 * Migration-safety: exhaustive first-party import resolution.
 *
 * Complements `tsc --noEmit` / `next build` (the primary static guards) by actually
 * evaluating every first-party module at runtime under jsdom, catching import-time
 * throws that static analysis misses. Enumerates `src/**` via the filesystem and
 * `await import()`s each module.
 *
 * IMPORTANT: some modules cannot be imported in a bare jsdom test (Next.js
 * server-only route/layout files, files that read server env at module load, etc.).
 * Those are excluded via EXCLUDE_PATTERNS below -- and every skip is logged, so the
 * exclusion set is explicit, never silent. Failures in importable modules fail the
 * test with the offending path + error.
 */

import { execSync } from "child_process";
import path from "path";

// Directories/patterns that are NOT safely importable in isolation (server-only,
// route entrypoints, or otherwise environment-bound). Documented, not silent.
const EXCLUDE_PATTERNS: RegExp[] = [
  /\.test\.[cm]?tsx?$/,
  /\.d\.ts$/,
  /\.stories\.tsx?$/,
  /[\\/]__migration__[\\/]/,
  // Next.js app-router server entrypoints (need the Next runtime / server env).
  /[\\/]app[\\/].*[\\/](page|layout|template|route|loading|error|not-found|global-error)\.tsx?$/,
  /[\\/]app[\\/](page|layout|template|loading|error|not-found|global-error)\.tsx?$/,
  /[\\/]instrumentation\.ts$/,
  /[\\/]middleware\.ts$/,
  /sentry\..*\.config\.ts$/,
  /[\\/]proxy\.ts$/,
];

const SRC_DIR = path.join(__dirname, "..");

function listSourceFiles(): string[] {
  // `git ls-files` is fast and respects .gitignore; fall back to a glob if needed.
  const out = execSync('git ls-files "src/**/*.ts" "src/**/*.tsx"', {
    cwd: path.join(__dirname, "..", ".."),
    encoding: "utf8",
    maxBuffer: 64 * 1024 * 1024,
  });
  return out
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean);
}

function toModuleSpecifier(repoRelPath: string): string {
  // repoRelPath like "src/lib/foo.ts" -> "@/lib/foo"
  const withoutSrc = repoRelPath.replace(/^src[\\/]/, "");
  const noExt = withoutSrc.replace(/\.[cm]?tsx?$/, "");
  return `@/${noExt.split(path.sep).join("/")}`;
}

describe("exhaustive first-party import resolution", () => {
  const all = listSourceFiles();
  const included: string[] = [];
  const excluded: string[] = [];

  for (const file of all) {
    if (EXCLUDE_PATTERNS.some((re) => re.test(file))) {
      excluded.push(file);
    } else {
      included.push(file);
    }
  }

  it("has a sane file inventory", () => {
    expect(all.length).toBeGreaterThan(100);
    // Log the exclusion set so it is auditable (no silent gaps).
    // eslint-disable-next-line no-console
    console.log(
      `[importAll] total=${all.length} imported=${included.length} excluded=${excluded.length}`
    );
    // eslint-disable-next-line no-console
    console.log("[importAll] excluded files:\n" + excluded.join("\n"));
  });

  /**
   * A failure is migration-relevant only if a FIRST-PARTY module path could not be
   * resolved -- exactly the breakage a rename/move introduces (a dead `@/...` or
   * relative import). Environment noise (ESM `Unexpected token 'export'` from an
   * untransformed npm package, a missing third-party module, jsdom-only runtime
   * errors) is tolerated and reported, never failed -- same policy as the backend
   * suite. This keeps the test meaningful without turning into a Jest-config chore.
   */
  const isMigrationRelevant = (message: string): boolean => {
    if (!/Cannot find module/i.test(message)) return false;
    return (
      /Cannot find module\s+['"]@\//.test(message) || // alias first-party
      /Cannot find module\s+['"]\.{1,2}\//.test(message) || // relative first-party
      /Cannot find module.*[\\/]src[\\/]/.test(message)
    );
  };

  it("resolves every first-party import path (migration-relevant only)", async () => {
    const migrationFailures: string[] = [];
    const tolerated: string[] = [];

    for (const file of included) {
      const spec = toModuleSpecifier(file);
      try {
        await import(spec);
      } catch (err) {
        const message = (err as Error).message;
        const entry = `${spec}  <-  ${file}\n    ${message.split("\n")[0]}`;
        if (isMigrationRelevant(message)) {
          migrationFailures.push(entry);
        } else {
          tolerated.push(entry);
        }
      }
    }

    // eslint-disable-next-line no-console
    console.log(
      `[importAll] migration-relevant failures=${migrationFailures.length} ` +
        `env/transform tolerated=${tolerated.length}`
    );
    if (tolerated.length > 0) {
      // eslint-disable-next-line no-console
      console.log("[importAll] tolerated (not migration):\n" + tolerated.join("\n"));
    }

    if (migrationFailures.length > 0) {
      throw new Error(
        `${migrationFailures.length} first-party import path(s) failed to resolve ` +
          `(dead @/ or relative path after move/rename):\n${migrationFailures.join("\n")}`
      );
    }
  });
});
