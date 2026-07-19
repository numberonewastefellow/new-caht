import {
  SvgUploadCloud,
  SvgFolder,
  SvgZoomIn,
  SvgThumbsUp,
  SvgOnyxOctagon,
  SvgOnyxLogo,
  SvgCpu,
  SvgGlobe,
  SvgImage,
  SvgSearch,
  SvgFileText,
  SvgUser,
  SvgUsers,
  SvgKey,
  SvgShield,
  SvgActivity,
  SvgServer,
  SvgBarChart,
  SvgSettings,
  SvgPaintBrush,
  SvgArrowExchange,
  SvgActions,
  SvgDiscordMono,
  SvgSliders,
} from "@opal/icons";
import SvgMcp from "@opal/icons/mcp";
import {
  ClipboardIcon,
  SlackIconSkeleton,
  BrainIcon,
} from "@/components/icons/icons";
import type { CombinedSettings } from "@/app/admin/settings/interfaces";
import type { IconProps } from "@opal/types";

export interface AdminNavItem {
  name: string;
  icon: React.FunctionComponent<IconProps>;
  link: string;
  isAiRelated?: boolean;
  error?: boolean;
}

/** Color identity for each nav group — maps to the design system theme tokens */
export type NavGroupColor = "blue" | "purple" | "green" | "orange" | "cyan";

export interface AdminNavGroup {
  id: string;
  name: string;
  icon: React.FunctionComponent<IconProps>;
  color: NavGroupColor;
  items: AdminNavItem[];
}

/**
 * Build the admin navigation groups.
 * Consolidated from 7 sidebar sections into 5 top-level groups
 * with modern AI-native naming.
 */
export function getAdminNavGroups(opts: {
  isCurator: boolean;
  enableCloud: boolean;
  settings: CombinedSettings | null;
  kgExposed: boolean;
  customAnalyticsEnabled: boolean;
}): AdminNavGroup[] {
  const {
    isCurator,
    enableCloud,
    settings,
    kgExposed,
    customAnalyticsEnabled,
  } = opts;

  const vectorDbEnabled = settings?.settings.vector_db_enabled !== false;

  const groups: AdminNavGroup[] = [];

  // ── Knowledge (was: Data / Connectors + Document Management) ──
  if (vectorDbEnabled) {
    groups.push({
      id: "knowledge",
      name: "Knowledge",
      icon: SvgUploadCloud,
      color: "green",
      items: [
        {
          name: "Data Sources",
          icon: SvgFolder,
          link: "/admin/indexing/status",
        },
        {
          name: "Add Source",
          icon: SvgUploadCloud,
          link: "/admin/add-connector",
        },
        {
          name: "Collections",
          icon: SvgFolder,
          link: "/admin/documents/sets",
        },
        {
          name: "Knowledge Explorer",
          icon: SvgZoomIn,
          link: "/admin/documents/explorer",
        },
        {
          name: "Quality Signals",
          icon: SvgThumbsUp,
          link: "/admin/documents/feedback",
        },
      ],
    });
  }

  // ── Agents (was: Custom Assistants) ──
  const agentItems: AdminNavItem[] = [
    {
      name: "AI Agents",
      icon: SvgOnyxOctagon,
      link: "/admin/assistants",
      isAiRelated: true,
    },
  ];

  if (!isCurator) {
    agentItems.push(
      {
        name: "Slack Agents",
        icon: SlackIconSkeleton,
        link: "/admin/bots",
      },
      {
        name: "Discord Agents",
        icon: SvgDiscordMono,
        link: "/admin/discord-bot",
      }
    );
  }

  agentItems.push(
    {
      name: "Workflows",
      icon: SvgSliders,
      link: "/admin/workflows",
    },
    {
      name: "MCP Tools",
      icon: SvgMcp,
      link: "/admin/actions/mcp",
    },
    {
      name: "API Tools",
      icon: SvgActions,
      link: "/admin/actions/open-api",
    }
  );

  agentItems.push({
    name: "Curated Responses",
    icon: ClipboardIcon,
    link: "/admin/standard-answer",
  });

  groups.push({
    id: "agents",
    name: "Agents",
    icon: SvgOnyxOctagon,
    color: "purple",
    items: agentItems,
  });

  // ── AI Models (was: Configuration) — only for non-curators ──
  if (!isCurator) {
    const modelItems: AdminNavItem[] = [
      {
        name: "Default Agent",
        icon: SvgOnyxLogo,
        link: "/admin/configuration/default-assistant",
        isAiRelated: true,
      },
      {
        name: "Language Models",
        icon: SvgCpu,
        link: "/admin/configuration/llm",
        isAiRelated: true,
      },
      {
        name: "Web Grounding",
        icon: SvgGlobe,
        link: "/admin/configuration/web-search",
        isAiRelated: true,
      },
      {
        name: "Vision Models",
        icon: SvgImage,
        link: "/admin/configuration/image-generation",
        isAiRelated: true,
      },
    ];

    if (!enableCloud && vectorDbEnabled) {
      modelItems.push({
        name: "Retrieval Tuning",
        icon: SvgSearch,
        link: "/admin/configuration/search",
        isAiRelated: true,
        error: settings?.settings.needs_reindexing,
      });
    }

    modelItems.push({
      name: "Ingestion Pipeline",
      icon: SvgFileText,
      link: "/admin/configuration/document-processing",
    });

    if (kgExposed) {
      modelItems.push({
        name: "Knowledge Graph",
        icon: BrainIcon,
        link: "/admin/kg",
        isAiRelated: true,
      });
    }

    groups.push({
      id: "models",
      name: "AI Models",
      icon: SvgCpu,
      color: "blue",
      items: modelItems,
    });
  }

  // ── Governance (was: User Management / Access) ──
  const governanceItems: AdminNavItem[] = [];

  if (isCurator) {
    governanceItems.push({
      name: "Teams",
      icon: SvgUsers,
      link: "/admin/teams",
    });
  }

  if (!isCurator) {
    governanceItems.push(
      {
        name: "Team Members",
        icon: SvgUser,
        link: "/admin/users",
      },
      {
        name: "Teams",
        icon: SvgUsers,
        link: "/admin/teams",
      },
      {
        name: "Roles",
        icon: SvgShield,
        link: "/admin/roles",
      },
      {
        name: "API Credentials",
        icon: SvgKey,
        link: "/admin/api-key",
      },
      {
        name: "Usage Limits",
        icon: SvgShield,
        link: "/admin/token-rate-limits",
      },
      {
        name: "Single Sign-On",
        icon: SvgKey,
        link: "/admin/auth/sso",
      }
    );

    // WS-M: tenant administration only functions in multi-tenant (cloud) mode — the
    // backend routes 400 otherwise — so only surface it there.
    if (enableCloud) {
      governanceItems.push({
        name: "Tenants",
        icon: SvgServer,
        link: "/admin/tenants",
      });
    }
  }

  if (governanceItems.length > 0) {
    groups.push({
      id: "governance",
      name: "Governance",
      icon: SvgUsers,
      color: "orange",
      items: governanceItems,
    });
  }

  // ── Workspace (was: Settings + Performance) ──
  if (!isCurator) {
    const workspaceItems: AdminNavItem[] = [
      {
        name: "General",
        icon: SvgSettings,
        link: "/admin/settings",
      },
    ];

    workspaceItems.push({
      name: "Branding",
      icon: SvgPaintBrush,
      link: "/admin/theme",
    });

    if (settings?.settings.opensearch_indexing_enabled) {
      workspaceItems.push({
        name: "Index Migration",
        icon: SvgArrowExchange,
        link: "/admin/document-index-migration",
      });
    }

    // Platform Services
    workspaceItems.push(
      {
        name: "Services Dashboard",
        icon: SvgServer,
        link: "/admin/services",
      },
      {
        name: "LLM Traces",
        icon: SvgActivity,
        link: "/phoenix/",
      }
    );

    // Performance / Observability items
    workspaceItems.push({
      name: "Analytics",
      icon: SvgActivity,
      link: "/admin/performance/usage",
    });

    if (settings?.settings.query_history_type !== "disabled") {
      workspaceItems.push({
        name: "Query Logs",
        icon: SvgServer,
        link: "/admin/performance/query-history",
      });
    }

    if (!enableCloud && customAnalyticsEnabled) {
      workspaceItems.push({
        name: "Custom Reports",
        icon: SvgBarChart,
        link: "/admin/performance/custom-analytics",
      });
    }

    groups.push({
      id: "workspace",
      name: "Workspace",
      icon: SvgSettings,
      color: "cyan",
      items: workspaceItems,
    });
  }

  return groups;
}

/**
 * Flatten all nav groups into a single array for the command palette.
 */
export function flattenNavItems(groups: AdminNavGroup[]): AdminNavItem[] {
  return groups.flatMap((g) => g.items);
}

/**
 * Route segment to human-readable label mapping for breadcrumbs.
 * Uses new AI-native names.
 */
export const ADMIN_ROUTE_LABELS: Record<string, string> = {
  admin: "Admin",
  indexing: "Indexing",
  status: "Data Sources",
  "add-connector": "Add Source",
  documents: "Knowledge",
  sets: "Collections",
  explorer: "Knowledge Explorer",
  feedback: "Quality Signals",
  assistants: "AI Agents",
  bots: "Slack Agents",
  "discord-bot": "Discord Agents",
  actions: "Tools",
  workflows: "Workflows",
  mcp: "MCP Tools",
  "open-api": "API Tools",
  "standard-answer": "Curated Responses",
  configuration: "AI Models",
  "default-assistant": "Default Agent",
  llm: "Language Models",
  "web-search": "Web Grounding",
  "image-generation": "Vision Models",
  search: "Retrieval Tuning",
  "document-processing": "Ingestion Pipeline",
  kg: "Knowledge Graph",
  users: "Team Members",
  teams: "Teams",
  roles: "Roles",
  "api-key": "API Credentials",
  "token-rate-limits": "Usage Limits",
  tenants: "Tenants",
  auth: "Authentication",
  sso: "Single Sign-On",
  performance: "Observability",
  usage: "Analytics",
  "query-history": "Query Logs",
  "custom-analytics": "Custom Reports",
  settings: "General",
  theme: "Branding",
  "document-index-migration": "Index Migration",
  embeddings: "Embeddings",
  connectors: "Connectors",
  connector: "Connector",
  federated: "Federated",
  systeminfo: "System Information",
  services: "Platform Services",
  debug: "Debug",
  new: "New",
  channels: "Channels",
  edit: "Edit",
};

/**
 * Convert a raw pathname segment to a human-readable label.
 * Falls back to Title Case conversion for unmapped segments.
 */
export function getSegmentLabel(segment: string): string {
  if (ADMIN_ROUTE_LABELS[segment]) {
    return ADMIN_ROUTE_LABELS[segment];
  }
  // Fallback: convert kebab-case to Title Case
  return segment
    .split("-")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

/**
 * Check if a pathname segment looks like a dynamic route parameter (e.g., a UUID or numeric ID).
 */
/**
 * Resolve the nav group color for a given admin pathname.
 * Uses a static prefix → color map so we don't need runtime feature flags.
 */
const PATH_GROUP_COLORS: [string, NavGroupColor][] = [
  // Knowledge (green)
  ["/admin/indexing", "green"],
  ["/admin/add-connector", "green"],
  ["/admin/documents", "green"],
  ["/admin/connectors", "green"],
  ["/admin/embeddings", "green"],
  // Agents (purple)
  ["/admin/assistants", "purple"],
  ["/admin/bots", "purple"],
  ["/admin/discord-bot", "purple"],
  ["/admin/actions", "purple"],
  ["/admin/workflows", "purple"],
  ["/admin/standard-answer", "purple"],
  // AI Models (blue)
  ["/admin/configuration", "blue"],
  ["/admin/kg", "blue"],
  // Governance (orange)
  ["/admin/users", "orange"],
  ["/admin/teams", "orange"],
  ["/admin/roles", "orange"],
  ["/admin/api-key", "orange"],
  ["/admin/token-rate-limits", "orange"],
  ["/admin/tenants", "orange"],
  ["/admin/auth/sso", "orange"],
  // Workspace (cyan)
  ["/admin/services", "cyan"],
  ["/admin/settings", "cyan"],
  ["/admin/theme", "cyan"],
  ["/admin/document-index-migration", "cyan"],
  ["/admin/performance", "cyan"],
];

export function getGroupColorForPath(pathname: string): NavGroupColor | null {
  for (const [prefix, color] of PATH_GROUP_COLORS) {
    if (pathname.startsWith(prefix)) return color;
  }
  return null;
}

/**
 * Maps intermediate breadcrumb paths (that don't have their own page.tsx)
 * to the correct child page URL so breadcrumb links navigate properly.
 */
export const BREADCRUMB_REDIRECT_MAP: Record<string, string> = {
  "/admin": "/admin/workflows",
  "/admin/indexing": "/admin/indexing/status",
  "/admin/configuration": "/admin/configuration/default-assistant",
  "/admin/documents": "/admin/documents/sets",
  "/admin/actions": "/admin/actions/mcp",
  "/admin/performance": "/admin/performance/usage",
};

export function isDynamicSegment(segment: string): boolean {
  // UUIDs
  if (
    /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(
      segment
    )
  ) {
    return true;
  }
  // Pure numeric IDs
  if (/^\d+$/.test(segment)) {
    return true;
  }
  return false;
}
