"use client";

import { useState } from "react";
import type { Route } from "next";
import { ANONYMOUS_USER_NAME, LOGOUT_DISABLED } from "@/lib/constants";
import { Notification } from "@/app/admin/settings/interfaces";
import useSWR, { preload } from "swr";
import { errorHandlingFetcher } from "@/lib/fetcher";
import { checkUserIsNoAuthUser, logout } from "@/lib/user";
import { useUser } from "@/providers/UserProvider";
import { useSettingsContext } from "@/providers/SettingsProvider";
import InputAvatar from "@/refresh-components/inputs/InputAvatar";
import Text from "@/refresh-components/texts/Text";
import LineItem from "@/refresh-components/buttons/LineItem";
import Popover, { PopoverMenu } from "@/refresh-components/Popover";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { cn } from "@/lib/utils";
import NotificationsPopover from "@/sections/sidebar/NotificationsPopover";
import {
  SvgBell,
  SvgExternalLink,
  SvgLogOut,
  SvgSettings,
  SvgShield,
  SvgUser,
} from "@opal/icons";
import { toast } from "@/hooks/useToast";
import useAppFocus from "@/hooks/useAppFocus";

function getDisplayName(email?: string, personalName?: string): string {
  // Prioritize custom personal name if set
  if (personalName && personalName.trim()) {
    return personalName.trim();
  }

  // Fallback to email-derived username
  if (!email) return ANONYMOUS_USER_NAME;
  const atIndex = email.indexOf("@");
  if (atIndex <= 0) return ANONYMOUS_USER_NAME;

  return email.substring(0, atIndex);
}

interface SettingsPopoverProps {
  onUserSettingsClick: () => void;
  onOpenNotifications: () => void;
  showAdminPanel: boolean;
  adminLabel: string;
  onAdminPanelClick: () => void;
}

function SettingsPopover({
  onUserSettingsClick,
  onOpenNotifications,
  showAdminPanel,
  adminLabel,
  onAdminPanelClick,
}: SettingsPopoverProps) {
  const { user } = useUser();
  const { data: notifications } = useSWR<Notification[]>(
    "/api/signals",
    errorHandlingFetcher,
    { revalidateOnFocus: false }
  );
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const undismissedCount =
    notifications?.filter((n) => !n.dismissed).length ?? 0;
  const isAnonymousUser =
    user?.is_anonymous_user || checkUserIsNoAuthUser(user?.id ?? "");
  const showLogout = user && !isAnonymousUser && !LOGOUT_DISABLED;
  const showLogin = isAnonymousUser;

  const handleLogin = () => {
    const currentUrl = `${pathname}${
      searchParams?.toString() ? `?${searchParams.toString()}` : ""
    }`;
    const encodedRedirect = encodeURIComponent(currentUrl);
    router.push(`/auth/login?next=${encodedRedirect}`);
  };

  const handleLogout = () => {
    logout()
      .then((response) => {
        if (!response?.ok) {
          alert("Failed to logout");
          return;
        }

        const currentUrl = `${pathname}${
          searchParams?.toString() ? `?${searchParams.toString()}` : ""
        }`;

        const encodedRedirect = encodeURIComponent(currentUrl);

        router.push(
          `/auth/login?disableAutoRedirect=true&next=${encodedRedirect}`
        );
      })

      .catch(() => {
        toast.error("Failed to logout");
      });
  };

  return (
    <>
      <PopoverMenu>
        {[
          <div key="user-settings" data-testid="Settings/user-settings">
            <LineItem icon={SvgUser} onClick={onUserSettingsClick}>
              User Settings
            </LineItem>
          </div>,
          // Admin/Curator Panel — unified into this menu, shown only to
          // admins/curators (same gating as the previous standalone footer tab).
          showAdminPanel && (
            <LineItem
              key="admin-panel"
              icon={SvgShield}
              onClick={onAdminPanelClick}
            >
              {adminLabel}
            </LineItem>
          ),
          <LineItem
            key="notifications"
            icon={SvgBell}
            onClick={onOpenNotifications}
          >
            {`Notifications${
              undismissedCount > 0 ? ` (${undismissedCount})` : ""
            }`}
          </LineItem>,
          <LineItem
            key="help-faq"
            icon={SvgExternalLink}
            onClick={() =>
              window.open(
                "https://docs.vertualai.com",
                "_blank",
                "noopener,noreferrer"
              )
            }
          >
            Help & FAQ
          </LineItem>,
          null,
          showLogin && (
            <LineItem key="log-in" icon={SvgUser} onClick={handleLogin}>
              Log in
            </LineItem>
          ),
          showLogout && (
            <LineItem
              key="log-out"
              icon={SvgLogOut}
              danger
              onClick={handleLogout}
            >
              Log out
            </LineItem>
          ),
        ]}
      </PopoverMenu>
    </>
  );
}

export interface SettingsProps {
  folded?: boolean;
  onShowBuildIntro?: () => void;
}

export default function UserAvatarPopover({
  folded,
  onShowBuildIntro,
}: SettingsProps) {
  const [popupState, setPopupState] = useState<
    "Settings" | "Notifications" | undefined
  >(undefined);
  const { user, isAdmin, isCurator } = useUser();
  const settings = useSettingsContext();
  const router = useRouter();
  const appFocus = useAppFocus();

  // Fetch notifications for display
  // The GET endpoint also triggers a refresh if release notes are stale
  const { data: notifications } = useSWR<Notification[]>(
    "/api/signals",
    errorHandlingFetcher
  );

  const displayName = getDisplayName(user?.email, user?.personalization?.name);
  const undismissedCount =
    notifications?.filter((n) => !n.dismissed).length ?? 0;
  const hasNotifications = undismissedCount > 0;

  // Admin entry (moved out of the sidebar footer into this unified menu).
  const vectorDbEnabled = settings?.settings?.vector_db_enabled !== false;
  const adminDefaultHref = (
    vectorDbEnabled ? "/admin/workflows" : "/admin/assistants"
  ) as Route;
  const showAdminPanel = isAdmin || isCurator;
  const adminLabel = isAdmin ? "Admin Panel" : "Curator Panel";
  const roleLabel = isAdmin ? "Admin" : isCurator ? "Curator" : "Member";

  const handlePopoverOpen = (state: boolean) => {
    if (state) {
      // Prefetch user settings data when popover opens for instant modal display
      preload("/api/user/pats", errorHandlingFetcher);
      preload("/api/bridges/oauth-status", errorHandlingFetcher);
      preload("/api/nexus/connector-status", errorHandlingFetcher);
      preload("/api/llm/provider", errorHandlingFetcher);
      setPopupState("Settings");
    } else {
      setPopupState(undefined);
    }
  };

  const isActive = !!popupState || appFocus.isUserSettings();

  return (
    <Popover open={!!popupState} onOpenChange={handlePopoverOpen}>
      <Popover.Trigger asChild>
        <button
          id="onyx-user-dropdown"
          type="button"
          title={folded ? displayName : undefined}
          className={cn(
            "group relative w-full flex items-center rounded-08 cursor-pointer select-none transition-colors",
            "hover:bg-background-tint-02",
            isActive && "bg-background-tint-02",
            folded ? "justify-center p-1.5" : "gap-2 p-1.5"
          )}
        >
          {/* Avatar (with notification dot when folded) */}
          <div className="relative shrink-0">
            <InputAvatar
              className="w-7 h-7 border-0 flex items-center justify-center"
              style={{
                backgroundColor:
                  "var(--virtualai-accent, var(--theme-primary-05))",
              }}
            >
              <Text as="p" inverted secondaryBody>
                {displayName[0]?.toUpperCase()}
              </Text>
            </InputAvatar>
            {folded && hasNotifications && (
              <span
                className="absolute -top-0.5 -right-0.5 h-2 w-2 rounded-full"
                style={{
                  backgroundColor:
                    "var(--virtualai-accent, var(--theme-primary-05))",
                }}
              />
            )}
          </div>

          {/* Name + role + gear (expanded only) */}
          {!folded && (
            <>
              <div className="flex flex-col min-w-0 flex-1 text-left">
                <span className="truncate text-[13px] font-medium text-text-05">
                  {displayName}
                </span>
                <span className="truncate text-[11px] text-text-03">
                  {roleLabel}
                </span>
              </div>
              <div className="relative flex items-center justify-center shrink-0">
                <SvgSettings className="h-4 w-4 stroke-text-03 group-hover:stroke-text-05 transition-colors" />
                {hasNotifications && (
                  <span
                    className="absolute -top-0.5 -right-0.5 h-2 w-2 rounded-full"
                    style={{
                      backgroundColor:
                        "var(--virtualai-accent, var(--theme-primary-05))",
                    }}
                  />
                )}
              </div>
            </>
          )}
        </button>
      </Popover.Trigger>

      <Popover.Content
        align="end"
        side="right"
        width={popupState === "Notifications" ? "xl" : "md"}
      >
        {popupState === "Settings" && (
          <SettingsPopover
            onUserSettingsClick={() => {
              setPopupState(undefined);
              router.push("/app/settings");
            }}
            onOpenNotifications={() => setPopupState("Notifications")}
            showAdminPanel={showAdminPanel}
            adminLabel={adminLabel}
            onAdminPanelClick={() => {
              setPopupState(undefined);
              router.push(adminDefaultHref);
            }}
          />
        )}
        {popupState === "Notifications" && (
          <NotificationsPopover
            onClose={() => setPopupState("Settings")}
            onNavigate={() => setPopupState(undefined)}
            onShowBuildIntro={onShowBuildIntro}
          />
        )}
      </Popover.Content>
    </Popover>
  );
}
