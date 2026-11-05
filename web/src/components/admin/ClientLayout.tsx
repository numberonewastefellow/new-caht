"use client";

import { useState } from "react";
import { usePathname } from "next/navigation";
import { useSettingsContext } from "@/providers/SettingsProvider";
import { useUser } from "@/providers/UserProvider";
import { UserRole } from "@/lib/types";
import { useIsKGExposed } from "@/app/admin/kg/utils";
import AdminTopBar from "./AdminTopBar";
import AdminSidebar from "./AdminSidebar";
import useNavVersion from "@/hooks/useNavVersion";
import AdminCommandPalette from "./AdminCommandPalette";
import { getAdminNavGroups } from "./adminNavItems";

export interface ClientLayoutProps {
  children: React.ReactNode;
  enableCloud: boolean;
}

export function ClientLayout({ children, enableCloud }: ClientLayoutProps) {
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);
  const pathname = usePathname();
  const settings = useSettingsContext();
  const { user } = useUser();
  const { kgExposed } = useIsKGExposed();

  const navVersion = useNavVersion();

  const isCurator =
    user?.role === UserRole.CURATOR || user?.role === UserRole.GLOBAL_CURATOR;

  const groups = getAdminNavGroups({
    isCurator,
    enableCloud,
    settings,
    kgExposed,
  });

  // Wizard-style sub-flows bring their own left sidebar, so the admin rail
  // steps aside for them rather than stacking two sidebars.
  const hasCustomSidebar =
    pathname.startsWith("/admin/connectors") ||
    pathname.startsWith("/admin/embeddings") ||
    pathname.startsWith("/admin/workflows/visual");

  // v1 renders the classic dropdown bar; v2 the left rail. Both are fed the
  // identical `groups` above — the version never reaches the catalog.
  const showRail = navVersion === "v2" && !hasCustomSidebar;

  return (
    <div className="h-screen w-screen flex flex-row overflow-hidden bg-background-tint-00">
      {/* Primary navigation rail */}
      {showRail && (
        <AdminSidebar
          groups={groups}
          onOpenCommandPalette={() => setCommandPaletteOpen(true)}
        />
      )}

      <div className="flex-1 min-w-0 flex flex-col overflow-hidden">
        <AdminTopBar
          groups={groups}
          variant={navVersion === "v2" ? "slim" : "tabs"}
          showBrand={!showRail}
          onOpenCommandPalette={() => setCommandPaletteOpen(true)}
        />

        {/* Command palette overlay */}
        <AdminCommandPalette
          open={commandPaletteOpen}
          onOpenChange={setCommandPaletteOpen}
          groups={groups}
        />

        {/* Main content area — fills remaining space below top bar */}
        {hasCustomSidebar ? (
          <div className="flex-1 min-w-0 min-h-0 overflow-hidden">
            {children}
          </div>
        ) : (
          <div className="flex-1 min-w-0 min-h-0 overflow-y-auto relative">
            {/* Subtle accent gradient at top of content area */}
            <div
              className="absolute top-0 left-0 right-0 h-64 pointer-events-none"
              style={{
                background:
                  "radial-gradient(ellipse 80% 50% at 50% 0%, color-mix(in srgb, var(--virtualai-accent, var(--theme-primary-05)) 3%, transparent), transparent)",
              }}
            />
            <div className="relative max-w-6xl mx-auto w-full pt-8 px-6 md:px-12 pb-16">
              {children}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
