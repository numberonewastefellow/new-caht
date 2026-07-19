"use client";

import { usePathname } from "next/navigation";
import { useSettingsContext } from "@/providers/SettingsProvider";
import Text from "@/refresh-components/texts/Text";
import SidebarSection from "@/sections/sidebar/SidebarSection";
import SidebarWrapper from "@/sections/sidebar/SidebarWrapper";
import { useIsKGExposed } from "@/app/admin/kg/utils";
import { useCustomAnalyticsEnabled } from "@/lib/hooks/useCustomAnalyticsEnabled";
import { useUser } from "@/providers/UserProvider";
import { UserRole } from "@/lib/types";
import {
  useBillingInformation,
  useLicense,
  hasActiveSubscription,
} from "@/lib/billing";
import {
  ClipboardIcon,
  SlackIconSkeleton,
  BrainIcon,
} from "@/components/icons/icons";
import { CombinedSettings } from "@/app/admin/settings/interfaces";
import SidebarTab from "@/refresh-components/buttons/SidebarTab";
import SidebarBody from "@/sections/sidebar/SidebarBody";
import {
  SvgActions,
  SvgActivity,
  SvgArrowLeft,
  SvgArrowUpCircle,
  SvgBarChart,
  SvgCpu,
  SvgFileText,
  SvgFolder,
  SvgGlobe,
  SvgArrowExchange,
  SvgImage,
  SvgKey,
  SvgOnyxLogo,
  SvgOnyxOctagon,
  SvgSearch,
  SvgServer,
  SvgSettings,
  SvgShield,
  SvgThumbsUp,
  SvgUploadCloud,
  SvgUser,
  SvgUsers,
  SvgZoomIn,
  SvgPaintBrush,
  SvgDiscordMono,
  SvgWallet,
} from "@opal/icons";
import SvgMcp from "@opal/icons/mcp";
import UserAvatarPopover from "@/sections/sidebar/UserAvatarPopover";

const connectors_items = () => [
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
];

const document_management_items = () => [
  {
    name: "Document Sets",
    icon: SvgFolder,
    link: "/admin/documents/sets",
  },
  {
    name: "Explorer",
    icon: SvgZoomIn,
    link: "/admin/documents/explorer",
  },
  {
    name: "Feedback",
    icon: SvgThumbsUp,
    link: "/admin/documents/feedback",
  },
];

const custom_assistants_items = (isCurator: boolean) => {
  const items = [
    {
      name: "Assistants",
      icon: SvgOnyxOctagon,
      link: "/admin/assistants",
    },
  ];

  if (!isCurator) {
    items.push(
      {
        name: "Slack Bots",
        icon: SlackIconSkeleton,
        link: "/admin/bots",
      },
      {
        name: "Discord Bots",
        icon: SvgDiscordMono,
        link: "/admin/discord-bot",
      }
    );
  }

  items.push(
    {
      name: "MCP Actions",
      icon: SvgMcp,
      link: "/admin/actions/mcp",
    },
    {
      name: "OpenAPI Actions",
      icon: SvgActions,
      link: "/admin/actions/open-api",
    }
  );

  items.push({
    name: "Standard Answers",
    icon: ClipboardIcon,
    link: "/admin/standard-answer",
  });

  return items;
};

const collections = (
  isCurator: boolean,
  enableCloud: boolean,
  settings: CombinedSettings | null,
  kgExposed: boolean,
  customAnalyticsEnabled: boolean,
  hasSubscription: boolean
) => {
  const vectorDbEnabled = settings?.settings.vector_db_enabled !== false;

  return [
    ...(vectorDbEnabled
      ? [
          {
            name: "Connectors",
            items: connectors_items(),
          },
        ]
      : []),
    ...(vectorDbEnabled
      ? [
          {
            name: "Document Management",
            items: document_management_items(),
          },
        ]
      : []),
    {
      name: "Custom Assistants",
      items: custom_assistants_items(isCurator),
    },
    ...(isCurator
      ? [
          {
            name: "User Management",
            items: [
              {
                name: "Groups",
                icon: SvgUsers,
                link: "/admin/groups",
              },
            ],
          },
        ]
      : []),
    ...(!isCurator
      ? [
          {
            name: "Configuration",
            items: [
              {
                name: "Default Assistant",
                icon: SvgOnyxLogo,
                link: "/admin/configuration/default-assistant",
              },
              {
                name: "LLM",
                icon: SvgCpu,
                link: "/admin/configuration/llm",
              },
              {
                name: "Web Search",
                icon: SvgGlobe,
                link: "/admin/configuration/web-search",
              },
              {
                name: "Image Generation",
                icon: SvgImage,
                link: "/admin/configuration/image-generation",
              },
              ...(!enableCloud && vectorDbEnabled
                ? [
                    {
                      error: settings?.settings.needs_reindexing,
                      name: "Search Settings",
                      icon: SvgSearch,
                      link: "/admin/configuration/search",
                    },
                  ]
                : []),
              {
                name: "Document Processing",
                icon: SvgFileText,
                link: "/admin/configuration/document-processing",
              },
              ...(kgExposed
                ? [
                    {
                      name: "Knowledge Graph",
                      icon: BrainIcon,
                      link: "/admin/kg",
                    },
                  ]
                : []),
            ],
          },
          {
            name: "User Management",
            items: [
              {
                name: "Users",
                icon: SvgUser,
                link: "/admin/users",
              },
              {
                name: "Groups",
                icon: SvgUsers,
                link: "/admin/groups",
              },
              {
                name: "API Keys",
                icon: SvgKey,
                link: "/admin/api-key",
              },
              {
                name: "Rate Limits",
                icon: SvgShield,
                link: "/admin/rate-limits",
              },
            ],
          },
          {
            name: "Performance",
            items: [
              {
                name: "Usage Statistics",
                icon: SvgActivity,
                link: "/admin/performance/usage",
              },
              ...(settings?.settings.query_history_type !== "disabled"
                ? [
                    {
                      name: "Query History",
                      icon: SvgServer,
                      link: "/admin/performance/query-history",
                    },
                  ]
                : []),
              ...(!enableCloud && customAnalyticsEnabled
                ? [
                    {
                      name: "Custom Analytics",
                      icon: SvgBarChart,
                      link: "/admin/performance/custom-analytics",
                    },
                  ]
                : []),
            ],
          },
          {
            name: "Platform Services",
            items: [
              {
                name: "Services Dashboard",
                icon: SvgServer,
                link: "/admin/services",
              },
              {
                name: "LLM Traces",
                icon: SvgActivity,
                link: "/phoenix/",
              },
            ],
          },
          {
            name: "Settings",
            items: [
              {
                name: "Workspace Settings",
                icon: SvgSettings,
                link: "/admin/settings",
              },
              {
                name: "Appearance & Theming",
                icon: SvgPaintBrush,
                link: "/admin/theme",
              },
              {
                name: hasSubscription ? "Plans & Billing" : "Upgrade Plan",
                icon: hasSubscription ? SvgWallet : SvgArrowUpCircle,
                link: "/admin/billing",
              },
              ...(settings?.settings.opensearch_indexing_enabled
                ? [
                    {
                      name: "Document Index Migration",
                      icon: SvgArrowExchange,
                      link: "/admin/document-index-migration",
                    },
                  ]
                : []),
            ],
          },
        ]
      : []),
  ];
};

interface AdminSidebarProps {
  // Cloud flag is passed from server component (Layout.tsx) since it's a build-time constant
  enableCloudSS: boolean;
}

export default function AdminSidebar({ enableCloudSS }: AdminSidebarProps) {
  const { kgExposed } = useIsKGExposed();
  const pathname = usePathname();
  const { customAnalyticsEnabled } = useCustomAnalyticsEnabled();
  const { user } = useUser();
  const settings = useSettingsContext();
  const { data: billingData } = useBillingInformation();
  const { data: licenseData } = useLicense();

  const isCurator =
    user?.role === UserRole.CURATOR || user?.role === UserRole.GLOBAL_CURATOR;

  // Check if user has an active subscription or license for billing link text
  // Show "Plans & Billing" if they have either (even if Stripe connection fails)
  const hasSubscription = Boolean(
    (billingData && hasActiveSubscription(billingData)) ||
      licenseData?.has_license
  );

  const items = collections(
    isCurator,
    enableCloudSS,
    settings,
    kgExposed,
    customAnalyticsEnabled,
    hasSubscription
  );

  return (
    <SidebarWrapper>
      <SidebarBody
        scrollKey="admin-sidebar"
        actionButtons={
          <SidebarTab
            leftIcon={({ className }) => (
              <SvgArrowLeft className={className} size={16} />
            )}
            href="/app"
          >
            Back to App
          </SidebarTab>
        }
        footer={
          <div className="flex flex-col gap-2">
            {settings.webVersion && (
              <Text as="p" text02 secondaryBody className="px-2">
                {`VertualAI version: ${settings.webVersion}`}
              </Text>
            )}
            <UserAvatarPopover />
          </div>
        }
      >
        {items.map((collection, index) => (
          <SidebarSection key={index} title={collection.name}>
            <div className="flex flex-col w-full">
              {collection.items.map(({ link, icon: Icon, name }, index) => (
                <SidebarTab
                  key={index}
                  href={link}
                  transient={pathname.startsWith(link)}
                  leftIcon={({ className }) => (
                    <Icon className={className} size={16} />
                  )}
                >
                  {name}
                </SidebarTab>
              ))}
            </div>
          </SidebarSection>
        ))}
      </SidebarBody>
    </SidebarWrapper>
  );
}
