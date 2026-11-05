import {
  SvgUploadCloud,
  SvgFolder,
  SvgZoomIn,
  SvgThumbsUp,
  SvgOmOctagon,
  SvgOmLogo,
  SvgCpu,
  SvgGlobe,
  SvgImage,
  SvgSearch,
  SvgFileText,
  SvgUser,
  SvgUsers,
  SvgUserManage,
  SvgKey,
  SvgLock,
  SvgShield,
  SvgActivity,
  SvgBarChart,
  SvgFileChartPie,
  SvgHistory,
  SvgServer,
  SvgHardDrive,
  SvgTerminal,
  SvgInfoSmall,
  SvgSettings,
  SvgPaintBrush,
  SvgArrowExchange,
  SvgActions,
  SvgPlug,
  SvgDiscordMono,
  SvgSliders,
  SvgClock,
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
  /** Renders an attention dot — used when a setting needs follow-up action. */
  error?: boolean;
  /** Opens outside the Next router (e.g. the Phoenix tracing UI). */
  external?: boolean;
}

/** Color identity for each nav group — maps to the design system theme tokens */
export type NavGroupColor =
  | "blue"
  | "purple"
  | "green"
  | "sky"
  | "orange"
  | "amber"
  | "cyan";

export interface AdminNavGroup {
  id: string;
  name: string;
  icon: React.FunctionComponent<IconProps>;
  color: NavGroupColor;
  items: AdminNavItem[];
}

/**
 * Build the admin navigation groups.
 *
 * Seven sections, each rendered as an expandable block in the admin rail:
 * what you *build* (Agents), what it *knows* (Knowledge), what it *thinks with*
 * (AI Models), what it *talks to* (Integrations), who may *use* it (Governance),
 * how it is *behaving* (Monitoring), and how it *looks* (Settings).
 */
export function getAdminNavGroups(opts: {
  isCurator: boolean;
  enableCloud: boolean;
  settings: CombinedSettings | null;
  kgExposed: boolean;
}): AdminNavGroup[] {
  const { isCurator, enableCloud, settings, kgExposed } = opts;

  const vectorDbEnabled = settings?.settings.vector_db_enabled !== false;

  const groups: AdminNavGroup[] = [];

  // ── Agents — the things users actually run ──
  groups.push({
    id: "agents",
    name: "Agents",
    icon: SvgOmOctagon,
    color: "purple",
    items: [
      {
        name: "AI Agents",
        icon: SvgOmOctagon,
        link: "/admin/assistants",
      },
      {
        name: "Workflows",
        icon: SvgSliders,
        link: "/admin/workflows",
      },
      {
        name: "Pulse",
        icon: SvgClock,
        link: "/admin/schedules",
      },
      {
        name: "Standard Answers",
        icon: ClipboardIcon,
        link: "/admin/standard-answers",
      },
    ],
  });

  // ── Knowledge — everything that feeds retrieval ──
  if (vectorDbEnabled) {
    const knowledgeItems: AdminNavItem[] = [
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
    ];

    if (!isCurator) {
      if (kgExposed) {
        knowledgeItems.push({
          name: "Knowledge Graph",
          icon: BrainIcon,
          link: "/admin/kg",
        });
      }

      knowledgeItems.push({
        name: "Ingestion Pipeline",
        icon: SvgFileText,
        link: "/admin/configuration/document-processing",
      });

      if (settings?.settings.opensearch_indexing_enabled) {
        knowledgeItems.push({
          name: "Index Migration",
          icon: SvgArrowExchange,
          link: "/admin/document-index-migration",
        });
      }
    }

    groups.push({
      id: "knowledge",
      name: "Knowledge",
      icon: SvgUploadCloud,
      color: "green",
      items: knowledgeItems,
    });
  }

  // ── AI Models — only for non-curators ──
  if (!isCurator) {
    const modelItems: AdminNavItem[] = [
      {
        name: "Language Models",
        icon: SvgCpu,
        link: "/admin/configuration/llm",
      },
      {
        name: "Default Agent",
        icon: SvgOmLogo,
        link: "/admin/configuration/default-assistant",
      },
      {
        name: "Web Grounding",
        icon: SvgGlobe,
        link: "/admin/configuration/web-search",
      },
      {
        name: "Vision Models",
        icon: SvgImage,
        link: "/admin/configuration/image-generation",
      },
    ];

    if (!enableCloud && vectorDbEnabled) {
      modelItems.push({
        name: "Retrieval Tuning",
        icon: SvgSearch,
        link: "/admin/configuration/search",
        error: settings?.settings.needs_reindexing,
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

  // ── Integrations — tools the agents call, and channels they answer on ──
  const integrationItems: AdminNavItem[] = [
    {
      name: "MCP Tools",
      icon: SvgMcp,
      link: "/admin/actions/mcp",
    },
    {
      name: "API Tools",
      icon: SvgActions,
      link: "/admin/actions/open-api",
    },
  ];

  if (!isCurator) {
    integrationItems.push(
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

  groups.push({
    id: "integrations",
    name: "Integrations",
    icon: SvgPlug,
    color: "sky",
    items: integrationItems,
  });

  // ── Governance — who can do what ──
  const governanceItems: AdminNavItem[] = [];

  if (isCurator) {
    governanceItems.push({
      name: "Teams",
      icon: SvgUsers,
      link: "/admin/teams",
    });
  } else {
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
        name: "Rate Limits",
        icon: SvgLock,
        link: "/admin/rate-limits",
      },
      {
        name: "Single Sign-On",
        icon: SvgKey,
        link: "/admin/auth/sso",
      },
      {
        name: "SCIM Provisioning",
        icon: SvgUserManage,
        link: "/admin/scim",
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

  // ── Monitoring — observability, health and diagnostics ──
  if (!isCurator) {
    const monitoringItems: AdminNavItem[] = [
      {
        name: "Analytics",
        icon: SvgBarChart,
        link: "/admin/performance/analytics",
      },
    ];

    if (settings?.settings.query_history_type !== "disabled") {
      monitoringItems.push({
        name: "Query Logs",
        icon: SvgHistory,
        link: "/admin/performance/query-log",
      });
    }

    monitoringItems.push(
      {
        name: "Usage Reports",
        icon: SvgFileChartPie,
        link: "/admin/performance/reports",
      },
      {
        name: "Services Dashboard",
        icon: SvgHardDrive,
        link: "/admin/services",
      },
      {
        name: "LLM Traces",
        icon: SvgActivity,
        link: "/phoenix/",
        external: true,
      },
      {
        name: "Debug Logs",
        icon: SvgTerminal,
        link: "/admin/debug",
      },
      {
        name: "System Info",
        icon: SvgInfoSmall,
        link: "/admin/systeminfo",
      }
    );

    groups.push({
      id: "monitoring",
      name: "Monitoring",
      icon: SvgActivity,
      color: "amber",
      items: monitoringItems,
    });
  }

  // ── Settings — how the workspace presents itself ──
  if (!isCurator) {
    groups.push({
      id: "settings",
      name: "Settings",
      icon: SvgSettings,
      color: "cyan",
      items: [
        {
          name: "General",
          icon: SvgSettings,
          link: "/admin/settings",
        },
        {
          name: "Branding",
          icon: SvgPaintBrush,
          link: "/admin/theme",
        },
        {
          name: "New Features",
          icon: SvgOmOctagon,
          link: "/admin/features",
        },
      ],
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
  schedules: "Pulse",
  mcp: "MCP Tools",
  "open-api": "API Tools",
  "standard-answers": "Standard Answers",
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
  "rate-limits": "Rate Limits",
  tenants: "Tenants",
  auth: "Authentication",
  sso: "Single Sign-On",
  scim: "SCIM Provisioning",
  features: "New Features",
  performance: "Observability",
  analytics: "Analytics",
  "query-log": "Query Logs",
  reports: "Usage Reports",
  settings: "General",
  theme: "Branding",
  "document-index-migration": "Index Migration",
  embeddings: "Embeddings",
  datasources: "Data Sources",
  connectors: "Connectors",
  connector: "Connector",
  federated: "Federated",
  systeminfo: "System Info",
  services: "Services Dashboard",
  debug: "Debug Logs",
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
 * Resolve the nav group color for a given admin pathname.
 * Uses a static prefix → color map so we don't need runtime feature flags.
 *
 * Ordered longest-prefix-first where prefixes overlap, since the first match wins.
 */
const PATH_GROUP_COLORS: [string, NavGroupColor][] = [
  // Agents (purple)
  ["/admin/assistants", "purple"],
  ["/admin/workflows", "purple"],
  ["/admin/schedules", "purple"],
  ["/admin/standard-answers", "purple"],
  // Knowledge (green)
  ["/admin/indexing", "green"],
  ["/admin/add-connector", "green"],
  ["/admin/documents", "green"],
  ["/admin/datasources", "green"],
  ["/admin/connectors", "green"],
  ["/admin/connector", "green"],
  ["/admin/federated", "green"],
  ["/admin/embeddings", "green"],
  ["/admin/kg", "green"],
  ["/admin/configuration/document-processing", "green"],
  ["/admin/document-index-migration", "green"],
  // AI Models (blue) — must come after the two /admin/configuration/* overrides above
  ["/admin/configuration", "blue"],
  // Integrations (sky)
  ["/admin/actions", "sky"],
  ["/admin/bots", "sky"],
  ["/admin/discord-bot", "sky"],
  // Governance (orange)
  ["/admin/users", "orange"],
  ["/admin/teams", "orange"],
  ["/admin/roles", "orange"],
  ["/admin/api-key", "orange"],
  ["/admin/rate-limits", "orange"],
  ["/admin/tenants", "orange"],
  ["/admin/auth", "orange"],
  ["/admin/scim", "orange"],
  // Monitoring (amber)
  ["/admin/performance", "amber"],
  ["/admin/services", "amber"],
  ["/admin/debug", "amber"],
  ["/admin/systeminfo", "amber"],
  // Settings (cyan)
  ["/admin/settings", "cyan"],
  ["/admin/theme", "cyan"],
  ["/admin/app-settings", "cyan"],
  ["/admin/features", "cyan"],
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
  "/admin/performance": "/admin/performance/analytics",
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
