"use client";

import { AdminPageTitle } from "@/components/admin/Title";
import { Card } from "@/refresh-components/cards";
import Text from "@/refresh-components/texts/Text";
import {
  SvgShield,
  SvgUsers,
  SvgUser,
  SvgEye,
  SvgLock,
  SvgCheck,
  SvgMinus,
  SvgInfoSmall,
} from "@opal/icons";
import type { IconProps } from "@opal/types";

/**
 * Roles & Permissions — a read-only reference for the RBAC tiers.
 *
 * The role tiers and what each may do are defined in the backend
 * (`om.auth.schemas.UserRole` + the access-control checks it drives) and
 * cannot be edited from the UI. This screen simply documents that matrix so
 * admins can reason about who can do what before assigning roles.
 */

type ThemeColor = "purple" | "blue" | "cyan" | "green" | "orange";

function tone(color: ThemeColor): { bg: string; fg: string } {
  return { bg: `var(--theme-${color}-01)`, fg: `var(--theme-${color}-05)` };
}

interface RoleDef {
  /** Backend UserRole enum value */
  value: string;
  label: string;
  color: ThemeColor;
  icon: React.FunctionComponent<IconProps>;
  tagline: string;
  /** The blast radius of this role's abilities */
  scope: string;
  can: string[];
  cannot: string[];
}

const ROLES: RoleDef[] = [
  {
    value: "admin",
    label: "Admin",
    color: "purple",
    icon: SvgShield,
    tagline: "Full instance administration",
    scope: "Entire instance",
    can: [
      "Access every admin surface and setting",
      "Create, edit and delete teams",
      "Invite users and assign any role",
      "Manage LLM providers, connectors and configuration",
      "Curate resources across all teams",
    ],
    cannot: [],
  },
  {
    value: "global_curator",
    label: "Global Curator",
    color: "blue",
    icon: SvgUsers,
    tagline: "Curate & manage every team they belong to",
    scope: "Teams they are a member of",
    can: [
      "Curate resources (connectors, document sets, assistants) in their teams",
      "Add and remove members of teams they belong to",
      "Appoint curators within those teams",
    ],
    cannot: ["Create or delete teams", "Manage LLM providers or users"],
  },
  {
    value: "curator",
    label: "Curator",
    color: "cyan",
    icon: SvgUser,
    tagline: "Curate the specific teams they are assigned to",
    scope: "Teams they curate",
    can: [
      "Curate resources for teams they are a curator of",
      "Add and remove members of those teams",
    ],
    cannot: [
      "Appoint other curators — separation of duties",
      "Create or delete teams",
      "Manage LLM providers or users",
    ],
  },
  {
    value: "basic",
    label: "Basic",
    color: "green",
    icon: SvgEye,
    tagline: "Everyday member access",
    scope: "Teams they belong to",
    can: [
      "View the teams they belong to",
      "Use shared assistants, connectors and documents",
      "Chat and search across resources they can access",
    ],
    cannot: ["Perform any admin or curation action"],
  },
  {
    value: "limited",
    label: "Limited",
    color: "orange",
    icon: SvgLock,
    tagline: "Minimal, restricted access",
    scope: "A limited set of endpoints",
    can: ["Reach a minimal set of basic API endpoints"],
    cannot: ["Access the full application or team resources"],
  },
];

type Cell = "yes" | "scoped" | "no";

interface CapabilityRow {
  label: string;
  detail?: string;
  cells: Record<string, Cell>;
}

const CAPABILITIES: CapabilityRow[] = [
  {
    label: "Use shared resources",
    detail: "Chat, search, shared assistants & documents",
    cells: {
      admin: "yes",
      global_curator: "yes",
      curator: "yes",
      basic: "yes",
      limited: "scoped",
    },
  },
  {
    label: "View teams they belong to",
    cells: {
      admin: "yes",
      global_curator: "yes",
      curator: "yes",
      basic: "yes",
      limited: "no",
    },
  },
  {
    label: "Curate team resources",
    detail: "Connectors, document sets & assistants",
    cells: {
      admin: "yes",
      global_curator: "scoped",
      curator: "scoped",
      basic: "no",
      limited: "no",
    },
  },
  {
    label: "Manage team members",
    detail: "Add & remove users",
    cells: {
      admin: "yes",
      global_curator: "scoped",
      curator: "scoped",
      basic: "no",
      limited: "no",
    },
  },
  {
    label: "Appoint curators",
    cells: {
      admin: "yes",
      global_curator: "scoped",
      curator: "no",
      basic: "no",
      limited: "no",
    },
  },
  {
    label: "Create & delete teams",
    cells: {
      admin: "yes",
      global_curator: "no",
      curator: "no",
      basic: "no",
      limited: "no",
    },
  },
  {
    label: "Manage users & roles",
    cells: {
      admin: "yes",
      global_curator: "no",
      curator: "no",
      basic: "no",
      limited: "no",
    },
  },
  {
    label: "Manage LLM providers & settings",
    cells: {
      admin: "yes",
      global_curator: "no",
      curator: "no",
      basic: "no",
      limited: "no",
    },
  },
];

function RoleBadge({
  Icon,
  color,
}: {
  Icon: React.FunctionComponent<IconProps>;
  color: ThemeColor;
}) {
  const { bg, fg } = tone(color);
  return (
    <div
      className="w-10 h-10 rounded-12 flex items-center justify-center flex-shrink-0"
      style={{
        backgroundColor: bg,
        boxShadow: `0 0 0 1px color-mix(in srgb, ${fg} 22%, transparent)`,
      }}
    >
      <Icon className="w-5 h-5" style={{ color: fg }} size={20} />
    </div>
  );
}

function EnumChip({ value }: { value: string }) {
  return (
    <span
      className="px-1.5 py-0.5 rounded-8 font-main-content-mono text-xs"
      style={{
        backgroundColor: "var(--background-tint-02)",
        color: "var(--text-03)",
      }}
    >
      {value}
    </span>
  );
}

function RoleCard({ role }: { role: RoleDef }) {
  const { fg } = tone(role.color);
  return (
    <Card className="h-full">
      <div className="flex items-center gap-3 w-full">
        <RoleBadge Icon={role.icon} color={role.color} />
        <div className="flex flex-col min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <Text mainContentEmphasis className="truncate">
              {role.label}
            </Text>
            <EnumChip value={role.value} />
          </div>
          <Text secondaryBody text03 className="truncate">
            {role.tagline}
          </Text>
        </div>
      </div>

      <div
        className="flex items-center gap-1.5 rounded-8 px-2 py-1 w-full"
        style={{ backgroundColor: "var(--background-tint-01)" }}
      >
        <Text secondaryBody text03 className="text-xs">
          Scope
        </Text>
        <Text secondaryBody className="text-xs" style={{ color: fg }}>
          {role.scope}
        </Text>
      </div>

      <div className="flex flex-col gap-1.5 w-full">
        {role.can.map((item) => (
          <div key={item} className="flex items-start gap-2">
            <SvgCheck
              className="w-4 h-4 mt-0.5 flex-shrink-0"
              style={{ color: "var(--theme-green-05)" }}
            />
            <Text secondaryBody text02 className="text-sm">
              {item}
            </Text>
          </div>
        ))}
        {role.cannot.map((item) => (
          <div key={item} className="flex items-start gap-2">
            <SvgMinus
              className="w-4 h-4 mt-0.5 flex-shrink-0"
              style={{ color: "var(--theme-red-05)" }}
            />
            <Text secondaryBody text03 className="text-sm">
              {item}
            </Text>
          </div>
        ))}
      </div>
    </Card>
  );
}

function MatrixCell({ state }: { state: Cell }) {
  if (state === "yes") {
    return (
      <div className="flex justify-center">
        <div
          className="w-6 h-6 rounded-full flex items-center justify-center"
          style={{ backgroundColor: "var(--theme-green-01)" }}
        >
          <SvgCheck
            className="w-4 h-4"
            style={{ color: "var(--theme-green-05)" }}
          />
        </div>
      </div>
    );
  }
  if (state === "scoped") {
    return (
      <div className="flex flex-col items-center gap-0.5">
        <div
          className="w-6 h-6 rounded-full flex items-center justify-center"
          style={{ backgroundColor: "var(--theme-amber-01)" }}
        >
          <SvgCheck
            className="w-4 h-4"
            style={{ color: "var(--theme-amber-05)" }}
          />
        </div>
        <Text
          secondaryBody
          className="text-[0.65rem] leading-none"
          style={{ color: "var(--theme-amber-05)" }}
        >
          own teams
        </Text>
      </div>
    );
  }
  return (
    <div className="flex justify-center">
      <SvgMinus className="w-4 h-4" style={{ color: "var(--text-03)" }} />
    </div>
  );
}

function LegendItem({
  state,
  label,
}: {
  state: Cell;
  label: string;
}) {
  return (
    <div className="flex items-center gap-1.5">
      <MatrixCell state={state} />
      <Text secondaryBody text03 className="text-xs">
        {label}
      </Text>
    </div>
  );
}

export default function Page() {
  return (
    <>
      <AdminPageTitle
        title="Roles & Permissions"
        icon={SvgShield}
        description="How each access tier maps to what a user can do"
      />

      {/* Read-only reference notice */}
      <Card variant="secondary" className="mb-6">
        <div className="flex items-start gap-3 w-full">
          <SvgInfoSmall
            className="w-5 h-5 mt-0.5 flex-shrink-0"
            style={{ color: "var(--virtualai-accent, var(--theme-primary-05))" }}
          />
          <div className="flex flex-col gap-1">
            <Text mainContentEmphasis className="text-sm">
              This is a read-only reference
            </Text>
            <Text secondaryBody text03 className="text-sm">
              Roles are fixed in code and can&apos;t be edited here. Assign a
              user&apos;s role from{" "}
              <span className="font-main-content-emphasis">Team Members</span>,
              and grant Curator status from within a{" "}
              <span className="font-main-content-emphasis">Team</span>.
            </Text>
          </div>
        </div>
      </Card>

      {/* Role tiers */}
      <div className="mb-2">
        <Text as="p" headingH3 className="text-text-05">
          Role tiers
        </Text>
        <Text as="p" secondaryBody text03 className="mt-0.5">
          Ordered from most to least privileged.
        </Text>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 mb-8">
        {ROLES.map((role) => (
          <RoleCard key={role.value} role={role} />
        ))}
      </div>

      {/* Permission matrix */}
      <div className="mb-2">
        <Text as="p" headingH3 className="text-text-05">
          Permission matrix
        </Text>
        <Text as="p" secondaryBody text03 className="mt-0.5">
          What each tier is allowed to do at a glance.
        </Text>
      </div>
      <Card padding={0} className="overflow-hidden">
        <div className="w-full overflow-x-auto">
          <table className="w-full border-collapse text-sm min-w-[720px]">
            <thead>
              <tr
                style={{
                  borderBottom: "1px solid var(--line-01)",
                  backgroundColor: "var(--background-tint-01)",
                }}
              >
                <th className="text-left align-bottom p-4 w-[24rem]">
                  <Text secondaryBody text03 className="text-xs uppercase tracking-wide">
                    Capability
                  </Text>
                </th>
                {ROLES.map((role) => {
                  const { fg } = tone(role.color);
                  return (
                    <th key={role.value} className="p-3 align-bottom">
                      <div className="flex flex-col items-center gap-1">
                        <role.icon
                          className="w-4 h-4"
                          style={{ color: fg }}
                          size={16}
                        />
                        <Text
                          secondaryBody
                          className="text-xs text-center"
                          style={{ color: fg }}
                        >
                          {role.label}
                        </Text>
                      </div>
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody>
              {CAPABILITIES.map((row, idx) => (
                <tr
                  key={row.label}
                  style={{
                    borderBottom:
                      idx === CAPABILITIES.length - 1
                        ? "none"
                        : "1px solid var(--line-01)",
                  }}
                >
                  <td className="p-4 align-middle">
                    <Text mainUiBody text02 className="text-sm">
                      {row.label}
                    </Text>
                    {row.detail && (
                      <Text secondaryBody text03 className="text-xs mt-0.5">
                        {row.detail}
                      </Text>
                    )}
                  </td>
                  {ROLES.map((role) => (
                    <td key={role.value} className="p-3 align-middle">
                      <MatrixCell state={row.cells[role.value] ?? "no"} />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Legend */}
      <div className="flex items-center gap-5 flex-wrap mt-4">
        <LegendItem state="yes" label="Allowed" />
        <LegendItem state="scoped" label="Allowed within their own teams" />
        <LegendItem state="no" label="Not allowed" />
      </div>
    </>
  );
}
