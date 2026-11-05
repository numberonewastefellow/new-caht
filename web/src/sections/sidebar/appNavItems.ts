import {
  SvgClock,
  SvgDashboard,
  SvgDevKit,
  SvgEditBig,
  SvgFolderPlus,
  SvgSearchMenu,
  SvgSparkle,
} from "@opal/icons";
import {
  makeAccentColorfulIcon,
  makeColorfulIcon,
} from "@/refresh-components/popovers/ActionsPopover/colorfulIcons";
import { CRAFT_PATH } from "@/app/craft/v1/constants";
import type { CombinedSettings } from "@/app/admin/settings/interfaces";
import type { IconProps } from "@opal/types";

// Colorful sidebar icons — colored rounded squares with white icons.
const ColorfulNewSession = makeColorfulIcon(SvgEditBig, "sidebar_new_session");
const ColorfulSearchChats = makeColorfulIcon(SvgSearchMenu, "sidebar_search");
const ColorfulCraft = makeColorfulIcon(SvgDevKit, "sidebar_craft");
const ColorfulNewWorkspace = makeColorfulIcon(
  SvgFolderPlus,
  "sidebar_workspaces"
);
const ColorfulWorkspaces = makeColorfulIcon(SvgDashboard, "sidebar_workspaces");
const ColorfulWorkflows = makeColorfulIcon(SvgSparkle, "sidebar_agents");
// Schedules uses the accent theme color so it adapts to Ocean/Emerald/Violet.
const ColorfulSchedules = makeAccentColorfulIcon(SvgClock);

/**
 * How a row behaves when clicked. Everything except "link" needs a handler
 * wired up in `AppSidebar`, which is the only place allowed to know about
 * modals, command menus and query state.
 */
export type AppNavBehavior =
  | "link"
  | "new-session"
  | "search-chats"
  | "new-workspace";

/**
 * Which block the row belongs to. v1 ignores this and renders one flat list;
 * v2 renders the blocks separated by a hairline.
 */
export type AppNavGroupId = "primary" | "library";

/** Key into `useAppFocus()` for the active-row check. */
export type AppNavFocusKey =
  | "newSession"
  | "workspacesDashboard"
  | "workflowsGallery"
  | "schedules";

export interface AppNavItem {
  id: string;
  label: string;
  icon: React.FunctionComponent<IconProps>;
  group: AppNavGroupId;
  behavior: AppNavBehavior;
  href?: string;
  testId?: string;
  focusKey?: AppNavFocusKey;
  /** Rendered dimmer when the sidebar is expanded (secondary actions). */
  lowlight?: boolean;
}

export interface GetAppNavItemsOpts {
  settings: CombinedSettings | null;
  /** Used only when the deployment disables the default agent. */
  currentAgentId?: number | string | null;
}

/**
 * The end-user sidebar catalog — the single source of truth for both nav
 * versions, mirroring `components/admin/adminNavItems.ts`.
 *
 * Adding a row here makes it appear in v1 and v2 at once. The nav version is
 * deliberately not an argument: it is a rendering concern, not a catalog one.
 */
export function getAppNavItems({
  settings,
  currentAgentId,
}: GetAppNavItemsOpts): AppNavItem[] {
  const items: AppNavItem[] = [];

  // Some deployments pin new chats to the current agent instead of the default.
  const newSessionHref =
    settings?.settings?.disable_default_assistant && currentAgentId != null
      ? `/app?assistantId=${currentAgentId}`
      : "/app";

  items.push(
    {
      id: "new-session",
      label: "New Chat",
      icon: ColorfulNewSession,
      group: "primary",
      behavior: "new-session",
      href: newSessionHref,
      testId: "AppSidebar/new-session",
      focusKey: "newSession",
    },
    {
      id: "search-chats",
      label: "Search Chats",
      icon: ColorfulSearchChats,
      group: "primary",
      behavior: "search-chats",
    },
    {
      id: "workspaces",
      label: "Workspaces",
      icon: ColorfulWorkspaces,
      group: "library",
      behavior: "link",
      href: "/app/workspaces",
      testId: "AppSidebar/workspaces",
      focusKey: "workspacesDashboard",
    },
    {
      id: "new-workspace",
      label: "New Workspace",
      icon: ColorfulNewWorkspace,
      group: "library",
      behavior: "new-workspace",
      lowlight: true,
    },
    {
      id: "workflows",
      label: "Workflows",
      icon: ColorfulWorkflows,
      group: "library",
      behavior: "link",
      href: "/app/workflows",
      testId: "AppSidebar/workflows",
      focusKey: "workflowsGallery",
    },
    {
      id: "schedules",
      label: "Pulse",
      icon: ColorfulSchedules,
      group: "library",
      behavior: "link",
      href: "/app/schedules",
      testId: "AppSidebar/schedules",
      focusKey: "schedules",
    }
  );

  // Craft is opt-in; only an explicit true enables it.
  if (settings?.settings?.om_craft_enabled === true) {
    items.push({
      id: "craft",
      label: "Craft",
      icon: ColorfulCraft,
      group: "library",
      behavior: "link",
      href: CRAFT_PATH,
      testId: "AppSidebar/build",
    });
  }

  return items;
}

export const APP_NAV_GROUP_ORDER: AppNavGroupId[] = ["primary", "library"];
