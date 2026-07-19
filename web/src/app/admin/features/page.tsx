"use client";

import React from "react";
import Link from "next/link";
import type { Route } from "next";
import {
  SvgUsers,
  SvgUser,
  SvgKey,
  SvgServer,
  SvgSearch,
  SvgShield,
  SvgBarChart,
  SvgActivity,
} from "@opal/icons";
import type { IconProps } from "@opal/types";

import { AdminPageTitle } from "@/components/admin/Title";
import CardSection from "@/components/admin/CardSection";
import Text from "@/refresh-components/texts/Text";
import { ClipboardIcon } from "@/components/icons/icons";

/**
 * Admin "New Features" overview.
 *
 * A single landing page that showcases every capability delivered by the
 * clean-room EE rewrite (the 9 workstreams) and links straight to each
 * feature's own admin screen. Purely presentational + navigational — it reads
 * no backend state, so it never gates or breaks if a feature is disabled.
 *
 * Design system: icons are tinted with `--virtualai-accent` (never hardcoded);
 * cards reuse the neutral surface + border tokens like every other admin card.
 */

interface FeatureItem {
  ws: string;
  name: string;
  description: string;
  icon: React.FunctionComponent<IconProps>;
  href?: string; // omitted => platform change with no dedicated screen
  tags?: string[];
}

interface FeatureGroup {
  id: string;
  title: string;
  blurb: string;
  items: FeatureItem[];
}

const FEATURE_GROUPS: FeatureGroup[] = [
  {
    id: "identity",
    title: "Access & Identity",
    blurb: "Who can get in, and what they can touch once they do.",
    items: [
      {
        ws: "WS-B",
        name: "Teams & Roles",
        description:
          "Enterprise RBAC — resource-scoped Teams plus an admin / curator / member role hierarchy, least-privilege by default.",
        icon: SvgUsers,
        href: "/admin/teams",
        tags: ["RBAC", "Teams"],
      },
      {
        ws: "WS-C",
        name: "SAML Single Sign-On",
        description:
          "Configure an IdP (Okta / Entra / any SAML 2.0) for SSO login, with an auditable, revocable session ledger.",
        icon: SvgKey,
        href: "/admin/auth/sso",
        tags: ["SSO", "SAML 2.0"],
      },
      {
        ws: "WS-G",
        name: "SCIM Provisioning",
        description:
          "SCIM 2.0 (RFC 7643/7644) user + group provisioning. Groups map to Teams; bearer tokens are admin-managed.",
        icon: SvgUser,
        href: "/admin/scim",
        tags: ["SCIM 2.0", "Provisioning"],
      },
      {
        ws: "WS-M",
        name: "Multi-Tenant Isolation",
        description:
          "Schema-per-tenant data isolation with a self-hosted tenant admin — no billing, no external control plane.",
        icon: SvgServer,
        href: "/admin/tenants",
        tags: ["Tenancy", "Isolation"],
      },
    ],
  },
  {
    id: "content",
    title: "Content & Search",
    blurb: "How answers get found and shaped.",
    items: [
      {
        ws: "WS-D",
        name: "Standard Answers",
        description:
          "Keyword / regex canned answers grouped into categories, matched into Slack and chat before the LLM runs.",
        icon: ClipboardIcon,
        href: "/admin/standard-answers",
        tags: ["Canned answers"],
      },
      {
        ws: "WS-E",
        name: "Search & Query Expansion",
        description:
          "LLM query expansion + reciprocal-rank fusion with tunable weights, surfaced under Retrieval settings.",
        icon: SvgSearch,
        href: "/admin/configuration/search",
        tags: ["Expansion", "RRF"],
      },
    ],
  },
  {
    id: "ops",
    title: "Operations & Insights",
    blurb: "Guardrails and visibility for a running deployment.",
    items: [
      {
        ws: "WS-F",
        name: "Rate Limits",
        description:
          "Sliding-window budgets per global / tenant / team / user scope, with a live remaining-budget gauge and throttle history. Enforced on chat and search.",
        icon: SvgShield,
        href: "/admin/rate-limits",
        tags: ["Budgets", "Observability"],
      },
      {
        ws: "WS-H",
        name: "Analytics & Reporting",
        description:
          "Usage dashboards (recharts), query history, and downloadable CSV usage reports — all tenant-scoped.",
        icon: SvgBarChart,
        href: "/admin/performance/analytics",
        tags: ["Dashboards", "CSV export"],
      },
    ],
  },
  {
    id: "platform",
    title: "Platform",
    blurb: "Changes that apply everywhere.",
    items: [
      {
        ws: "WS-A",
        name: "Self-hosted build — billing not enabled",
        description:
          "The upstream license paywall and Stripe / control-plane billing (checkout, seat counts, " +
          "subscription tiers, plan-based feature gating) were removed, so this runs purely self-hosted " +
          "with no seat checks or external billing calls. A billing / subscription feature is not " +
          "developed — it would need to be built if paid plans are ever required.",
        icon: SvgActivity,
        tags: ["Self-hosted", "Billing: not developed"],
      },
    ],
  },
];

function AccentIcon({
  icon: Icon,
}: {
  icon: React.FunctionComponent<IconProps>;
}) {
  return (
    <div
      className="flex items-center justify-center w-10 h-10 rounded-12 shrink-0"
      style={{
        backgroundColor:
          "var(--virtualai-accent-subtle, var(--theme-primary-04))",
        color: "var(--virtualai-accent, var(--theme-primary-05))",
      }}
    >
      <Icon className="w-5 h-5" />
    </div>
  );
}

function FeatureCard({ item }: { item: FeatureItem }) {
  const body = (
    <CardSection
      className={
        "h-full flex flex-col gap-3 transition-colors " +
        (item.href
          ? "hover:border-border-03 cursor-pointer"
          : "opacity-90")
      }
    >
      <div className="flex items-start gap-3">
        <AccentIcon icon={item.icon} />
        <div className="flex flex-col gap-0.5">
          <Text mainUiMuted text03>
            {item.ws}
          </Text>
          <Text headingH3 text05>
            {item.name}
          </Text>
        </div>
      </div>

      <Text mainUiMuted text04>
        {item.description}
      </Text>

      <div className="flex flex-wrap gap-2 mt-auto pt-1">
        {(item.tags ?? []).map((tag) => (
          <span
            key={tag}
            className="px-2 py-0.5 rounded-08 text-xs"
            style={{
              backgroundColor:
                "var(--virtualai-accent-subtle, var(--theme-primary-04))",
              color: "var(--virtualai-accent, var(--theme-primary-05))",
            }}
          >
            {tag}
          </span>
        ))}
        {item.href && (
          <span className="ml-auto self-center">
            <Text mainUiMuted text03>
              Open →
            </Text>
          </span>
        )}
      </div>
    </CardSection>
  );

  if (!item.href) return body;
  return (
    <Link href={item.href as Route} className="block h-full no-underline">
      {body}
    </Link>
  );
}

export default function AdminFeaturesPage() {
  return (
    <div className="mx-auto w-full max-w-6xl">
      <AdminPageTitle
        icon={SvgActivity}
        title="New Features"
        description="Everything delivered by the platform rewrite — jump straight to each feature's admin screen."
      />

      <div className="flex flex-col gap-8 mt-2">
        {FEATURE_GROUPS.map((group) => (
          <section key={group.id} className="flex flex-col gap-3">
            <div className="flex flex-col gap-0.5">
              <Text headingH2 text05>
                {group.title}
              </Text>
              <Text mainUiMuted text04>
                {group.blurb}
              </Text>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {group.items.map((item) => (
                <FeatureCard key={item.ws} item={item} />
              ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
