"use client";

import { SvgShield } from "@opal/icons";
import SidebarTab from "@/refresh-components/buttons/SidebarTab";
import { useUser } from "@/providers/UserProvider";
import { useSettingsContext } from "@/providers/SettingsProvider";
import { makeColorfulIcon } from "@/refresh-components/popovers/ActionsPopover/colorfulIcons";
import useNavVersion from "@/hooks/useNavVersion";
import { adminEntry } from "@/sections/sidebar/adminEntry";

const ColorfulAdmin = makeColorfulIcon(SvgShield, "sidebar_admin");

export interface AdminEntryTabProps {
  folded?: boolean;
}

/**
 * The way into the admin area, pinned in the sidebar above the user chip.
 *
 * Only rendered in nav v2 — v1 keeps the entry inside the user-avatar menu
 * (see `UserAvatarPopover`), so exactly one of the two is ever present.
 *
 * Renders nothing for non-admins — `requireAdminAuth` is still the real gate,
 * this only keeps the door out of sight for users who can't open it.
 */
export default function AdminEntryTab({ folded }: AdminEntryTabProps) {
  const { isAdmin, isCurator } = useUser();
  const settings = useSettingsContext();
  const navVersion = useNavVersion();

  const entry = adminEntry({ isAdmin, isCurator, settings });
  if (!entry || navVersion !== "v2") return null;

  return (
    <div data-testid="AppSidebar/admin">
      <SidebarTab leftIcon={ColorfulAdmin} folded={folded} href={entry.href}>
        {entry.label}
      </SidebarTab>
    </div>
  );
}
