"use client";

import { useState } from "react";
import { usePathname } from "next/navigation";
import { useSettingsContext } from "@/providers/SettingsProvider";
import { useUser } from "@/providers/UserProvider";
import { UserRole } from "@/lib/types";
import { usePaidEnterpriseFeaturesEnabled } from "@/components/settings/usePaidEnterpriseFeaturesEnabled";
import { useIsKGExposed } from "@/app/admin/kg/utils";
import { useCustomAnalyticsEnabled } from "@/lib/hooks/useCustomAnalyticsEnabled";
import {
  useBillingInformation,
  useLicense,
  hasActiveSubscription,
} from "@/lib/billing";
import { ApplicationStatus } from "@/app/admin/settings/interfaces";
import Button from "@/refresh-components/buttons/Button";
import AdminTopBar from "./AdminTopBar";
import AdminCommandPalette from "./AdminCommandPalette";
import { getAdminNavGroups } from "./adminNavItems";

export interface ClientLayoutProps {
  children: React.ReactNode;
  enableEnterprise: boolean;
  enableCloud: boolean;
}

export function ClientLayout({
  children,
  enableEnterprise: enableEnterpriseSS,
  enableCloud,
}: ClientLayoutProps) {
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);
  const pathname = usePathname();
  const settings = useSettingsContext();
  const { user } = useUser();
  const { kgExposed } = useIsKGExposed();
  const { customAnalyticsEnabled } = useCustomAnalyticsEnabled();
  const { data: billingData } = useBillingInformation();
  const { data: licenseData } = useLicense();

  // Use runtime license check for enterprise features
  const enableEnterprise = usePaidEnterpriseFeaturesEnabled();

  const isCurator =
    user?.role === UserRole.CURATOR || user?.role === UserRole.GLOBAL_CURATOR;

  const hasSubscription = Boolean(
    (billingData && hasActiveSubscription(billingData)) ||
      licenseData?.has_license
  );

  const groups = getAdminNavGroups({
    isCurator,
    enableCloud,
    enableEnterprise,
    settings,
    kgExposed,
    customAnalyticsEnabled,
    hasSubscription,
  });

  // Pages with custom sidebar still get the top bar, but their content area is unstyled
  const hasCustomSidebar =
    pathname.startsWith("/admin/connectors") ||
    pathname.startsWith("/admin/embeddings");

  return (
    <div className="h-screen w-screen flex flex-col overflow-hidden">
      {/* Payment reminder banner */}
      {settings.settings.application_status ===
        ApplicationStatus.PAYMENT_REMINDER && (
        <div className="fixed top-16 left-1/2 transform -translate-x-1/2 bg-amber-400 dark:bg-amber-500 text-gray-900 dark:text-gray-100 p-4 rounded-lg shadow-lg z-50 max-w-md text-center">
          <strong className="font-bold">Warning:</strong> Your trial ends in
          less than 5 days and no payment method has been added.
          <div className="mt-2">
            <Button className="w-full" href="/admin/billing">
              Update Billing Information
            </Button>
          </div>
        </div>
      )}

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
        <div className="flex-1 min-w-0 min-h-0 overflow-y-auto pt-6 px-4 md:px-12 pb-12">
          <div className="max-w-6xl mx-auto w-full">{children}</div>
        </div>
      )}
    </div>
  );
}
