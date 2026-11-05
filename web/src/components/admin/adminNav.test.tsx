import fs from "fs";
import path from "path";
import {
  getAdminNavGroups,
  type AdminNavGroup,
  type AdminNavItem,
} from "./adminNavItems";
import { NAV_GROUP_COLORS } from "./navGroupColors";
import type { CombinedSettings } from "@/app/admin/settings/interfaces";

const ADMIN_APP_DIR = path.join(__dirname, "..", "..", "app", "admin");

/**
 * Admin pages that deliberately have no nav entry, each with the reason.
 * Adding a new page under app/admin/ without a nav item will fail the
 * "every admin page is reachable" test until it is listed here or linked.
 */
const INTENTIONALLY_UNLINKED: Record<string, string> = {
  "/admin": "redirect stub → /admin/workflows",
  "/admin/actions": "client redirect → /admin/actions/mcp",
  "/admin/configuration": "redirect stub → /admin/configuration/default-assistant",
  "/admin/documents": "redirect stub → /admin/documents/sets",
  "/admin/indexing": "redirect stub → /admin/indexing/status",
  "/admin/embeddings": "wizard, entered from Retrieval Tuning",
  "/admin/workflows/visual": "visual builder, entered from the workflows list",
  "/admin/app-settings": "duplicates General + Branding; kept out of the nav on purpose",
};

/** Detail pages and create/edit sub-flows are reached from their list page. */
function isSubRoute(route: string): boolean {
  return (
    route.includes("[") || /\/(new|create|edit-mcp)$/.test(route)
  );
}

function makeSettings(overrides: {
  vectorDb?: boolean;
  opensearch?: boolean;
  queryHistory?: string;
  needsReindexing?: boolean;
}): CombinedSettings {
  return {
    settings: {
      vector_db_enabled: overrides.vectorDb ?? true,
      opensearch_indexing_enabled: overrides.opensearch ?? false,
      query_history_type: overrides.queryHistory ?? "normal",
      needs_reindexing: overrides.needsReindexing ?? false,
    },
  } as unknown as CombinedSettings;
}

/** Every combination of the flags that gate nav items. */
function allGatePermutations(): AdminNavGroup[][] {
  const results: AdminNavGroup[][] = [];
  for (const isCurator of [false, true]) {
    for (const enableCloud of [false, true]) {
      for (const vectorDb of [false, true]) {
        for (const kgExposed of [false, true]) {
          for (const opensearch of [false, true]) {
            for (const queryHistory of ["normal", "disabled"]) {
              results.push(
                getAdminNavGroups({
                  isCurator,
                  enableCloud,
                  kgExposed,
                  settings: makeSettings({
                    vectorDb,
                    opensearch,
                    queryHistory,
                  }),
                })
              );
            }
          }
        }
      }
    }
  }
  return results;
}

const ALL_PERMUTATIONS = allGatePermutations();

function everyItemEverRendered(): AdminNavItem[] {
  const seen = new Map<string, AdminNavItem>();
  for (const groups of ALL_PERMUTATIONS) {
    for (const group of groups) {
      for (const item of group.items) {
        if (!seen.has(item.link)) seen.set(item.link, item);
      }
    }
  }
  return Array.from(seen.values());
}

/** Walk app/admin/ and collect every route that has a page.tsx. */
function listAdminRoutes(): string[] {
  const routes: string[] = [];

  function walk(dir: string, route: string) {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      if (!entry.isDirectory()) continue;
      const childDir = path.join(dir, entry.name);
      const childRoute = `${route}/${entry.name}`;
      if (fs.existsSync(path.join(childDir, "page.tsx"))) {
        routes.push(childRoute);
      }
      walk(childDir, childRoute);
    }
  }

  if (fs.existsSync(path.join(ADMIN_APP_DIR, "page.tsx"))) {
    routes.push("/admin");
  }
  walk(ADMIN_APP_DIR, "/admin");
  return routes.sort();
}

describe("admin navigation", () => {
  const items = everyItemEverRendered();

  it("surfaces a non-trivial number of destinations", () => {
    expect(items.length).toBeGreaterThan(30);
    expect(ALL_PERMUTATIONS.length).toBe(2 * 2 * 2 * 2 * 2 * 2);
  });

  it("points every nav link at a page that exists", () => {
    const broken = items
      .filter((item) => !item.external)
      .filter((item) => {
        const rel = item.link.replace(/^\/admin\/?/, "");
        const pageFile = path.join(ADMIN_APP_DIR, rel, "page.tsx");
        return !fs.existsSync(pageFile);
      })
      .map((item) => `${item.name} → ${item.link}`);

    expect(broken).toEqual([]);
  });

  it("marks links outside the Next router as external", () => {
    for (const item of items) {
      const isNextRoute = item.link.startsWith("/admin");
      expect(item.external ?? false).toBe(!isNextRoute);
    }
  });

  it("leaves no admin page unreachable", () => {
    const linked = new Set(items.map((i) => i.link));

    const unreachable = listAdminRoutes().filter(
      (route) =>
        !linked.has(route) &&
        !isSubRoute(route) &&
        !(route in INTENTIONALLY_UNLINKED)
    );

    expect(unreachable).toEqual([]);
  });

  it("keeps the unlinked-page allowlist honest", () => {
    const existing = new Set(listAdminRoutes());
    const stale = Object.keys(INTENTIONALLY_UNLINKED).filter(
      (route) => !existing.has(route)
    );
    expect(stale).toEqual([]);
  });

  it("never lists the same destination twice in one menu", () => {
    for (const groups of ALL_PERMUTATIONS) {
      const links = groups.flatMap((g) => g.items.map((i) => i.link));
      expect(links).toEqual(Array.from(new Set(links)));
    }
  });

  it("never renders an empty group, and labels every group and item", () => {
    for (const groups of ALL_PERMUTATIONS) {
      for (const group of groups) {
        expect(group.items.length).toBeGreaterThan(0);
        expect(group.name).toBeTruthy();
        expect(group.icon).toBeTruthy();
        for (const item of group.items) {
          expect(item.name).toBeTruthy();
          expect(item.icon).toBeTruthy();
        }
      }
    }
  });

  it("has styling for every group color it uses", () => {
    for (const groups of ALL_PERMUTATIONS) {
      for (const group of groups) {
        expect(NAV_GROUP_COLORS[group.color]).toBeDefined();
      }
    }
  });

  it("hides admin-only sections from curators", () => {
    const curatorGroups = getAdminNavGroups({
      isCurator: true,
      enableCloud: false,
      kgExposed: true,
      settings: makeSettings({}),
    });
    const curatorLinks = curatorGroups.flatMap((g) =>
      g.items.map((i) => i.link)
    );

    for (const adminOnly of [
      "/admin/users",
      "/admin/settings",
      "/admin/theme",
      "/admin/configuration/llm",
      "/admin/bots",
      "/admin/discord-bot",
      "/admin/performance/analytics",
      "/admin/scim",
    ]) {
      expect(curatorLinks).not.toContain(adminOnly);
    }

    expect(curatorLinks).toContain("/admin/teams");
  });

  it("drops the knowledge section when the vector DB is off", () => {
    const groups = getAdminNavGroups({
      isCurator: false,
      enableCloud: false,
      kgExposed: true,
      settings: makeSettings({ vectorDb: false }),
    });
    expect(groups.map((g) => g.id)).not.toContain("knowledge");
    // ...but the rest of the admin area still works.
    expect(groups.map((g) => g.id)).toContain("agents");
  });

  it("only offers Tenants in cloud mode", () => {
    const linksFor = (enableCloud: boolean) =>
      getAdminNavGroups({
        isCurator: false,
        enableCloud,
        kgExposed: false,
        settings: makeSettings({}),
      }).flatMap((g) => g.items.map((i) => i.link));

    expect(linksFor(true)).toContain("/admin/tenants");
    expect(linksFor(false)).not.toContain("/admin/tenants");
  });
});
