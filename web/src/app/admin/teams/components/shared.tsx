"use client";

import { cn } from "@/lib/utils";
import Text from "@/refresh-components/texts/Text";
import {
  Team,
  TeamMember,
  TeamMemberRole,
  UserRole,
} from "@/lib/types";
import {
  SvgGlobe,
  SvgLock,
  SvgShield,
  SvgSparkle,
  SvgUser,
} from "@opal/icons";

/* ============================================================================
   Theme-aware color palette (per project CLAUDE.md — never hardcode accents).
   Each entry maps to `--theme-<key>-01` (subtle bg) and `--theme-<key>-05`
   (readable foreground), both of which have light AND dark variants defined in
   web/src/app/css/colors.css. A stable hash of the entity id selects a color so
   avatars are deterministic and consistent across renders.
   ========================================================================== */

const AVATAR_PALETTE = ["purple", "blue", "green", "amber", "red"] as const;
type PaletteKey = (typeof AVATAR_PALETTE)[number];

function hashString(input: string): number {
  let hash = 0;
  for (let i = 0; i < input.length; i++) {
    hash = (hash << 5) - hash + input.charCodeAt(i);
    hash |= 0; // force 32-bit int
  }
  return Math.abs(hash);
}

function paletteFor(id: string | number): PaletteKey {
  const idx = hashString(String(id)) % AVATAR_PALETTE.length;
  return AVATAR_PALETTE[idx]!;
}

function avatarStyle(id: string | number): React.CSSProperties {
  const key = paletteFor(id);
  return {
    backgroundColor: `var(--theme-${key}-01)`,
    color: `var(--theme-${key}-05)`,
  };
}

function initialsFromName(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length >= 2) {
    return `${parts[0]![0] ?? ""}${parts[1]![0] ?? ""}`.toUpperCase();
  }
  const single = parts[0] ?? name;
  return (single.slice(0, 2) || "?").toUpperCase();
}

function initialsFromEmail(email: string): string {
  const local = (email.split("@")[0] || email).trim();
  const parts = local.split(/[._-]+/).filter(Boolean);
  if (parts.length >= 2) {
    return `${parts[0]![0] ?? ""}${parts[1]![0] ?? ""}`.toUpperCase();
  }
  return (local.slice(0, 2) || "?").toUpperCase();
}

/* ============================================================================
   Avatars
   ========================================================================== */

export function TeamAvatar({
  team,
  size = 40,
}: {
  team: Pick<Team, "id" | "name">;
  size?: number;
}) {
  return (
    <div
      className="flex items-center justify-center rounded-12 font-main-ui-body shrink-0"
      style={{
        width: size,
        height: size,
        fontSize: size * 0.36,
        ...avatarStyle(team.id),
      }}
      aria-hidden
    >
      {initialsFromName(team.name)}
    </div>
  );
}

export function UserAvatar({
  id,
  name,
  email,
  size = 32,
}: {
  id: string;
  name?: string | null;
  email: string;
  size?: number;
}) {
  const label = name && name.trim() ? initialsFromName(name) : initialsFromEmail(email);
  return (
    <div
      className="flex items-center justify-center rounded-full font-main-ui-body shrink-0 border-2"
      style={{
        width: size,
        height: size,
        fontSize: size * 0.38,
        borderColor: "var(--background-tint-00)",
        ...avatarStyle(id),
      }}
      title={email}
      aria-hidden
    >
      {label}
    </div>
  );
}

/* ============================================================================
   Badges
   ========================================================================== */

function BadgePill({
  icon: Icon,
  children,
  bg,
  fg,
  border,
}: {
  icon?: React.FunctionComponent<{ className?: string; style?: React.CSSProperties }>;
  children: React.ReactNode;
  bg?: string;
  fg?: string;
  border?: string;
}) {
  return (
    <span
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full whitespace-nowrap font-secondary-body text-xs border"
      style={{
        backgroundColor: bg ?? "var(--background-tint-02)",
        color: fg ?? "var(--text-03)",
        borderColor: border ?? "transparent",
      }}
    >
      {Icon && <Icon className="w-3 h-3" style={{ color: fg }} />}
      {children}
    </span>
  );
}

const ROLE_META: Record<
  TeamMemberRole,
  {
    label: string;
    icon: React.FunctionComponent<{ className?: string; style?: React.CSSProperties }>;
    color?: PaletteKey;
  }
> = {
  OWNER: { label: "Owner", icon: SvgSparkle, color: "amber" },
  ADMIN: { label: "Admin", icon: SvgShield, color: "blue" },
  MEMBER: { label: "Member", icon: SvgUser },
};

export function RoleBadge({ role }: { role: TeamMemberRole }) {
  const meta = ROLE_META[role];
  if (!meta.color) {
    return <BadgePill icon={meta.icon}>{meta.label}</BadgePill>;
  }
  return (
    <BadgePill
      icon={meta.icon}
      bg={`var(--theme-${meta.color}-01)`}
      fg={`var(--theme-${meta.color}-05)`}
    >
      {meta.label}
    </BadgePill>
  );
}

export function VisibilityBadge({ isPublic }: { isPublic: boolean }) {
  if (isPublic) {
    return (
      <BadgePill
        icon={SvgGlobe}
        bg="var(--theme-green-01)"
        fg="var(--theme-green-05)"
      >
        Public
      </BadgePill>
    );
  }
  return (
    <BadgePill icon={SvgLock}>Private</BadgePill>
  );
}

export function SourceBadge({ source }: { source: string }) {
  return (
    <span
      className="inline-flex items-center px-1.5 py-0.5 rounded-04 border font-secondary-body text-[0.65rem] uppercase tracking-wide"
      style={{ color: "var(--text-03)", borderColor: "var(--border-02)" }}
    >
      {source}
    </span>
  );
}

export function TagChip({ children }: { children: React.ReactNode }) {
  return (
    <span
      className="inline-flex items-center px-2 py-0.5 rounded-full font-secondary-body text-xs"
      style={{ backgroundColor: "var(--background-tint-02)", color: "var(--text-03)" }}
    >
      {children}
    </span>
  );
}

/* ============================================================================
   Member normalization
   Prefer the enriched `members` array; fall back to legacy `users` so the UI
   works against a not-yet-upgraded backend.
   ========================================================================== */

export function deriveMemberRole(team: Team, userId: string, userRole: UserRole): TeamMemberRole {
  if (team.owner?.id === userId) return "OWNER";
  if (userRole === UserRole.ADMIN) return "ADMIN";
  if (team.curator_ids?.map(String).includes(userId)) return "ADMIN";
  return "MEMBER";
}

export function getTeamMembers(team: Team): TeamMember[] {
  if (team.members && team.members.length > 0) {
    return team.members;
  }
  return (team.users ?? []).map((u) => ({
    id: u.id,
    name: (u.email.split("@")[0] || u.email).replace(/[._-]+/g, " "),
    email: u.email,
    role: deriveMemberRole(team, u.id, u.role),
    joined_at: null,
    source: "MANUAL" as const,
  }));
}

export function getMemberCount(team: Team): number {
  return team.member_count ?? getTeamMembers(team).length;
}

export function getKbCount(team: Team): number {
  return (
    team.kb_count ??
    (team.document_sets?.length ?? 0) + (team.cc_pairs?.length ?? 0)
  );
}

export function getTeamOwner(team: Team): { id: string; name: string; email: string } | null {
  if (team.owner) return team.owner;
  const members = getTeamMembers(team);
  const owner = members.find((m) => m.role === "OWNER") ?? members[0];
  if (!owner) return null;
  return { id: owner.id, name: owner.name, email: owner.email };
}

export function formatJoinedAt(joinedAt: string | null): string {
  if (!joinedAt) return "—";
  const d = new Date(joinedAt);
  if (Number.isNaN(d.getTime())) return joinedAt;
  return d.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "2-digit",
  });
}

/* Small labelled section header used inside the detail panel + dialogs. */
export function SectionLabel({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <Text
      as="p"
      secondaryBody
      text03
      className={cn("uppercase tracking-wide", className)}
    >
      {children}
    </Text>
  );
}
