import fs from "fs";
import path from "path";
import {
  DEFAULT_NAV_VERSION,
  NAV_V2_FLAG,
  isNavVersion,
  parseNavVersionEnv,
  resolveNavVersion,
} from "@/lib/navVersion";
import { adminEntry } from "@/sections/sidebar/adminEntry";
import { getAppNavItems } from "@/sections/sidebar/appNavItems";
import type { CombinedSettings } from "@/app/admin/settings/interfaces";

const SRC = path.join(__dirname, "..", "..");

function settingsWith(
  overrides: Record<string, unknown> = {}
): CombinedSettings {
  return { settings: overrides } as unknown as CombinedSettings;
}

describe("nav version resolution", () => {
  it("defaults to v1 — a client keeps the classic view until they opt in", () => {
    expect(DEFAULT_NAV_VERSION).toBe("v1");
    expect(resolveNavVersion({})).toBe("v1");
  });

  it("lets the tenant's flag beat the deployment default, both ways", () => {
    expect(resolveNavVersion({ flagEnabled: true, envDefault: "v1" })).toBe(
      "v2"
    );
    expect(resolveNavVersion({ flagEnabled: false, envDefault: "v2" })).toBe(
      "v1"
    );
  });

  it("falls back to the deployment default when the tenant has not chosen", () => {
    expect(resolveNavVersion({ envDefault: "v2" })).toBe("v2");
    expect(resolveNavVersion({ envDefault: "v1" })).toBe("v1");
    // An unset flag must not be mistaken for "false".
    expect(resolveNavVersion({ flagEnabled: undefined, envDefault: "v2" })).toBe(
      "v2"
    );
  });

  it("reads the env var defensively", () => {
    expect(parseNavVersionEnv("v2")).toBe("v2");
    expect(parseNavVersionEnv("V2")).toBe("v2");
    expect(parseNavVersionEnv("v1")).toBe("v1");
    for (const junk of [undefined, "", "legacy", "new", "nonsense"]) {
      expect(parseNavVersionEnv(junk)).toBe("v1");
    }
  });

  it("validates version strings", () => {
    expect(isNavVersion("v1")).toBe(true);
    expect(isNavVersion("v2")).toBe(true);
    for (const junk of ["V1", "new", "", null, undefined, 2]) {
      expect(isNavVersion(junk)).toBe(false);
    }
  });

  it("keeps the flag key stable — it is persisted per tenant", () => {
    // Changing this silently resets every client to the classic view.
    expect(NAV_V2_FLAG).toBe("nav_v2");
  });
});

describe("admin entry", () => {
  it("is hidden from users with no admin area", () => {
    expect(
      adminEntry({ isAdmin: false, isCurator: false, settings: settingsWith() })
    ).toBeNull();
  });

  it("labels admins and curators differently", () => {
    expect(
      adminEntry({ isAdmin: true, isCurator: false, settings: settingsWith() })
        ?.label
    ).toBe("Admin Panel");
    expect(
      adminEntry({ isAdmin: false, isCurator: true, settings: settingsWith() })
        ?.label
    ).toBe("Curator Panel");
  });

  it("avoids the data-sources landing page when there is no vector DB", () => {
    const withDb = adminEntry({
      isAdmin: true,
      isCurator: false,
      settings: settingsWith({ vector_db_enabled: true }),
    });
    const withoutDb = adminEntry({
      isAdmin: true,
      isCurator: false,
      settings: settingsWith({ vector_db_enabled: false }),
    });
    expect(withDb?.href).toBe("/admin/workflows");
    expect(withoutDb?.href).toBe("/admin/assistants");
  });
});

describe("app sidebar catalog", () => {
  const base = getAppNavItems({ settings: settingsWith() });

  it("keeps every destination the classic sidebar had", () => {
    expect(base.map((i) => i.id)).toEqual([
      "new-session",
      "search-chats",
      "workspaces",
      "new-workspace",
      "workflows",
      "schedules",
    ]);
  });

  it("gates Craft on an explicit opt-in", () => {
    const ids = (settings: CombinedSettings) =>
      getAppNavItems({ settings }).map((i) => i.id);

    expect(ids(settingsWith({ om_craft_enabled: true }))).toContain("craft");
    expect(ids(settingsWith({ om_craft_enabled: false }))).not.toContain(
      "craft"
    );
    expect(ids(settingsWith())).not.toContain("craft");
  });

  it("pins new chats to the current agent only when the default is disabled", () => {
    const hrefFor = (settings: CombinedSettings, currentAgentId?: number) =>
      getAppNavItems({ settings, currentAgentId }).find(
        (i) => i.id === "new-session"
      )?.href;

    expect(hrefFor(settingsWith(), 7)).toBe("/app");
    expect(
      hrefFor(settingsWith({ disable_default_assistant: true }), 7)
    ).toBe("/app?assistantId=7");
    // No agent to pin to → plain new chat rather than a broken query string.
    expect(hrefFor(settingsWith({ disable_default_assistant: true }))).toBe(
      "/app"
    );
  });

  it("gives every row a label, an icon and a group", () => {
    for (const item of getAppNavItems({
      settings: settingsWith({ om_craft_enabled: true }),
    })) {
      expect(item.label).toBeTruthy();
      expect(item.icon).toBeTruthy();
      expect(["primary", "library"]).toContain(item.group);
      // Plain links must actually go somewhere.
      if (item.behavior === "link") expect(item.href).toBeTruthy();
    }
  });

  it("never repeats an id", () => {
    const ids = getAppNavItems({
      settings: settingsWith({ om_craft_enabled: true }),
    }).map((i) => i.id);
    expect(ids).toEqual(Array.from(new Set(ids)));
  });
});

/**
 * The property that makes two permanent nav versions affordable: each surface
 * has ONE catalog, and the renderers only lay it out. If a renderer ever grows
 * its own item list, adding a menu entry starts costing two edits and the
 * versions drift — which is exactly what this guards against.
 */
describe("single source of truth", () => {
  const read = (rel: string) => fs.readFileSync(path.join(SRC, rel), "utf8");

  it("has both admin renderers consume the shared catalog", () => {
    for (const renderer of [
      "components/admin/AdminSidebar.tsx", // v2
      "components/admin/AdminNavTab.tsx", // v1
      "components/admin/AdminMobileMenu.tsx",
      "components/admin/AdminCommandPalette.tsx",
    ]) {
      const source = read(renderer);
      expect(source).toMatch(/from "\.\/adminNavItems"/);
      // A renderer must not hardcode admin routes of its own.
      expect(source).not.toMatch(/link:\s*"\/admin/);
      expect(source.match(/href="\/admin\/[a-z]/g) ?? []).toEqual([]);
    }
  });

  it("builds the admin menu in exactly one place", () => {
    const callers = [
      "components/admin/ClientLayout.tsx",
      "components/admin/AdminSidebar.tsx",
      "components/admin/AdminNavTab.tsx",
      "components/admin/AdminTopBar.tsx",
    ]
      .filter((f) => read(f).includes("getAdminNavGroups("))
      .sort();

    expect(callers).toEqual(["components/admin/ClientLayout.tsx"]);
  });

  it("keeps the nav version out of the catalogs", () => {
    // The moment a catalog branches on version, the two views can diverge and
    // adminNav.test.tsx stops covering what ships.
    for (const catalog of [
      "components/admin/adminNavItems.ts",
      "sections/sidebar/appNavItems.ts",
    ]) {
      const source = read(catalog);
      expect(source).not.toMatch(/navVersion|useNavVersion|NavVersion/);
    }
  });

  it("offers the admin entry in exactly one place per version", () => {
    // v2 pins it in the sidebar, v1 puts it in the user menu; both derive the
    // href and label from the same helper so they cannot drift.
    expect(read("sections/sidebar/AdminEntryTab.tsx")).toContain("adminEntry");
    expect(read("sections/sidebar/UserAvatarPopover.tsx")).toContain(
      "adminEntry"
    );
    expect(read("sections/sidebar/AdminEntryTab.tsx")).toMatch(
      /navVersion !== "v2"/
    );
    expect(read("sections/sidebar/UserAvatarPopover.tsx")).toMatch(
      /navVersion === "v1"/
    );
  });
});
