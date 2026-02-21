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
  SvgWallet,
  SvgArrowExchange,
  SvgActions,
  SvgDiscordMono,
} from "@opal/icons";
import SvgMcp from "@opal/icons/mcp";
import {
  ClipboardIcon,
  NotebookIconSkeleton,
  SlackIconSkeleton,
  BrainIcon,
} from "@/components/icons/icons";
import type { CombinedSettings } from "@/app/admin/settings/interfaces";
import type { IconProps } from "@opal/types";

export interface AdminNavItem {
  name: string;
  /** Old name shown as tooltip for reference (will be removed later) */
  oldName?: string;
  icon: React.FunctionComponent<IconProps>;
  link: string;
  isAiRelated?: boolean;
  error?: boolean;
}

export interface AdminNavGroup {
  id: string;
  name: string;
  /** Old group name shown as tooltip for reference (will be removed later) */
  oldName?: string;
  icon: React.FunctionComponent<IconProps>;
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
  enableEnterprise: boolean;
  settings: CombinedSettings | null;
  kgExposed: boolean;
  customAnalyticsEnabled: boolean;
  hasSubscription: boolean;
}): AdminNavGroup[] {
  const {
    isCurator,
    enableCloud,
    enableEnterprise,
    settings,
    kgExposed,
    customAnalyticsEnabled,
    hasSubscription,
  } = opts;

  const vectorDbEnabled = settings?.settings.vector_db_enabled !== false;

  const groups: AdminNavGroup[] = [];

  // ── Knowledge (was: Data / Connectors + Document Management) ──
  if (vectorDbEnabled) {
    groups.push({
      id: "knowledge",
      name: "Knowledge",
      oldName: "Data",
      icon: SvgUploadCloud,
      items: [
        {
          name: "Active Sources",
          oldName: "Existing Connectors",
          icon: NotebookIconSkeleton,
          link: "/admin/indexing/status",
        },
        {
          name: "Connect Source",
          oldName: "Add Connector",
          icon: SvgUploadCloud,
          link: "/admin/add-connector",
        },
        {
          name: "Collections",
          oldName: "Document Sets",
          icon: SvgFolder,
          link: "/admin/documents/sets",
        },
        {
          name: "Knowledge Explorer",
          oldName: "Explorer",
          icon: SvgZoomIn,
          link: "/admin/documents/explorer",
        },
        {
          name: "Quality Signals",
          oldName: "Feedback",
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
      oldName: "Assistants",
      icon: SvgOnyxOctagon,
      link: "/admin/assistants",
      isAiRelated: true,
    },
  ];

  if (!isCurator) {
    agentItems.push(
      {
        name: "Slack Agents",
        oldName: "Slack Bots",
        icon: SlackIconSkeleton,
        link: "/admin/bots",
      },
      {
        name: "Discord Agents",
        oldName: "Discord Bots",
        icon: SvgDiscordMono,
        link: "/admin/discord-bot",
      }
    );
  }

  agentItems.push(
    {
      name: "MCP Tools",
      oldName: "MCP Actions",
      icon: SvgMcp,
      link: "/admin/actions/mcp",
    },
    {
      name: "API Tools",
      oldName: "OpenAPI Actions",
      icon: SvgActions,
      link: "/admin/actions/open-api",
    }
  );

  if (enableEnterprise) {
    agentItems.push({
      name: "Curated Responses",
      oldName: "Standard Answers",
      icon: ClipboardIcon,
      link: "/ee/admin/standard-answer",
    });
  }

  groups.push({
    id: "agents",
    name: "Agents",
    oldName: "Custom Assistants",
    icon: SvgOnyxOctagon,
    items: agentItems,
  });

  // ── AI Models (was: Configuration) — only for non-curators ──
  if (!isCurator) {
    const modelItems: AdminNavItem[] = [
      {
        name: "Default Agent",
        oldName: "Default Assistant",
        icon: SvgOnyxLogo,
        link: "/admin/configuration/default-assistant",
        isAiRelated: true,
      },
      {
        name: "Language Models",
        oldName: "LLM",
        icon: SvgCpu,
        link: "/admin/configuration/llm",
        isAiRelated: true,
      },
      {
        name: "Web Grounding",
        oldName: "Web Search",
        icon: SvgGlobe,
        link: "/admin/configuration/web-search",
        isAiRelated: true,
      },
      {
        name: "Vision Models",
        oldName: "Image Generation",
        icon: SvgImage,
        link: "/admin/configuration/image-generation",
        isAiRelated: true,
      },
    ];

    if (!enableCloud && vectorDbEnabled) {
      modelItems.push({
        name: "Retrieval Tuning",
        oldName: "Search Settings",
        icon: SvgSearch,
        link: "/admin/configuration/search",
        isAiRelated: true,
        error: settings?.settings.needs_reindexing,
      });
    }

    modelItems.push({
      name: "Ingestion Pipeline",
      oldName: "Document Processing",
      icon: SvgFileText,
      link: "/admin/configuration/document-processing",
    });

    if (kgExposed) {
      modelItems.push({
        name: "Knowledge Graph",
        oldName: "Knowledge Graph",
        icon: BrainIcon,
        link: "/admin/kg",
        isAiRelated: true,
      });
    }

    groups.push({
      id: "models",
      name: "AI Models",
      oldName: "Configuration",
      icon: SvgCpu,
      items: modelItems,
    });
  }

  // ── Governance (was: User Management / Access) ──
  const governanceItems: AdminNavItem[] = [];

  if (isCurator && enableEnterprise) {
    governanceItems.push({
      name: "Access Groups",
      oldName: "Groups",
      icon: SvgUsers,
      link: "/ee/admin/groups",
    });
  }

  if (!isCurator) {
    governanceItems.push(
      {
        name: "Team Members",
        oldName: "Users",
        icon: SvgUser,
        link: "/admin/users",
      },
      ...(enableEnterprise
        ? [
            {
              name: "Access Groups",
              oldName: "Groups",
              icon: SvgUsers,
              link: "/ee/admin/groups",
            },
          ]
        : []),
      {
        name: "API Credentials",
        oldName: "API Keys",
        icon: SvgKey,
        link: "/admin/api-key",
      },
      {
        name: "Usage Limits",
        oldName: "Token Rate Limits",
        icon: SvgShield,
        link: "/admin/token-rate-limits",
      }
    );
  }

  if (governanceItems.length > 0) {
    groups.push({
      id: "governance",
      name: "Governance",
      oldName: "User Management",
      icon: SvgUsers,
      items: governanceItems,
    });
  }

  // ── Workspace (was: Settings + Performance) ──
  if (!isCurator) {
    const workspaceItems: AdminNavItem[] = [
      {
        name: "General",
        oldName: "Workspace Settings",
        icon: SvgSettings,
        link: "/admin/settings",
      },
    ];

    if (enableEnterprise) {
      workspaceItems.push({
        name: "Branding",
        oldName: "Appearance & Theming",
        icon: SvgPaintBrush,
        link: "/ee/admin/theme",
      });
    }

    if (hasSubscription) {
      workspaceItems.push({
        name: "Plan & Billing",
        oldName: "Plans & Billing",
        icon: SvgWallet,
        link: "/admin/billing",
      });
    }

    if (settings?.settings.opensearch_indexing_enabled) {
      workspaceItems.push({
        name: "Index Migration",
        oldName: "Document Index Migration",
        icon: SvgArrowExchange,
        link: "/admin/document-index-migration",
      });
    }

    // Performance / Observability items (enterprise only)
    if (enableEnterprise) {
      workspaceItems.push({
        name: "Analytics",
        oldName: "Usage Statistics",
        icon: SvgActivity,
        link: "/ee/admin/performance/usage",
      });

      if (settings?.settings.query_history_type !== "disabled") {
        workspaceItems.push({
          name: "Query Logs",
          oldName: "Query History",
          icon: SvgServer,
          link: "/ee/admin/performance/query-history",
        });
      }

      if (!enableCloud && customAnalyticsEnabled) {
        workspaceItems.push({
          name: "Custom Reports",
          oldName: "Custom Analytics",
          icon: SvgBarChart,
          link: "/ee/admin/performance/custom-analytics",
        });
      }
    }

    groups.push({
      id: "workspace",
      name: "Workspace",
      oldName: "Settings",
      icon: SvgSettings,
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
  status: "Active Sources",
  "add-connector": "Connect Source",
  documents: "Knowledge",
  sets: "Collections",
  explorer: "Knowledge Explorer",
  feedback: "Quality Signals",
  assistants: "AI Agents",
  bots: "Slack Agents",
  "discord-bot": "Discord Agents",
  actions: "Tools",
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
  groups: "Access Groups",
  "api-key": "API Credentials",
  "token-rate-limits": "Usage Limits",
  performance: "Observability",
  usage: "Analytics",
  "query-history": "Query Logs",
  "custom-analytics": "Custom Reports",
  settings: "General",
  theme: "Branding",
  billing: "Plan & Billing",
  "document-index-migration": "Index Migration",
  embeddings: "Embeddings",
  connectors: "Connectors",
  connector: "Connector",
  federated: "Federated",
  systeminfo: "System Information",
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
