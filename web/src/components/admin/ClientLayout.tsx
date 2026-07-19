"use client";

import { useState } from "react";
import { usePathname } from "next/navigation";
import { useSettingsContext } from "@/providers/SettingsProvider";
import { useUser } from "@/providers/UserProvider";
import { UserRole } from "@/lib/types";
import { useIsKGExposed } from "@/app/admin/kg/utils";
import { useCustomAnalyticsEnabled } from "@/lib/hooks/useCustomAnalyticsEnabled";
import AdminTopBar from "./AdminTopBar";
import AdminCommandPalette from "./AdminCommandPalette";
import { getAdminNavGroups } from "./adminNavItems";

export interface ClientLayoutProps {
  children: React.ReactNode;
  enableCloud: boolean;
}

export function ClientLayout({
  children,
  enableCloud,
}: ClientLayoutProps) {
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);
  const pathname = usePathname();
  const settings = useSettingsContext();
  const { user } = useUser();
  const { kgExposed } = useIsKGExposed();
  const { customAnalyticsEnabled } = useCustomAnalyticsEnabled();

  const isCurator =
    user?.role === UserRole.CURATOR || user?.role === UserRole.GLOBAL_CURATOR;

  const groups = getAdminNavGroups({
    isCurator,
    enableCloud,
    settings,
    kgExposed,
    customAnalyticsEnabled,
  });

  // Pages with custom sidebar still get the top bar, but their content area is unstyled
  const hasCustomSidebar =
    pathname.startsWith("/admin/connectors") ||
    pathname.startsWith("/admin/embeddings") ||
    pathname.startsWith("/admin/workflows/visual");

  return (
    <div className="h-screen w-screen flex flex-col overflow-hidden bg-background-tint-00">
      {/* Top navigation bar */}
      <AdminTopBar
        groups={groups}
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
              background: "radial-gradient(ellipse 80% 50% at 50% 0%, color-mix(in srgb, var(--virtualai-accent, var(--theme-primary-05)) 3%, transparent), transparent)",
            }}
          />
          <div className="relative max-w-6xl mx-auto w-full pt-8 px-6 md:px-12 pb-16">
            {children}
          </div>
        </div>
      )}
    </div>
  );
}
