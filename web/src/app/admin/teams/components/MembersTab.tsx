"use client";

import { useMemo, useState } from "react";
import { cn } from "@/lib/utils";
import { Team, TeamMember, TeamMemberRole } from "@/lib/types";
import { toast } from "@/hooks/useToast";
import Text from "@/refresh-components/texts/Text";
import Button from "@/refresh-components/buttons/Button";
import IconButton from "@/refresh-components/buttons/IconButton";
import Checkbox from "@/refresh-components/inputs/Checkbox";
import InputTypeIn from "@/refresh-components/inputs/InputTypeIn";
import InputSelect from "@/refresh-components/inputs/InputSelect";
import Popover from "@/refresh-components/Popover";
import LineItem from "@/refresh-components/buttons/LineItem";
import {
  SvgDownload,
  SvgMoreHorizontal,
  SvgTrash,
  SvgUserPlus,
  SvgUsers,
  SvgX,
} from "@opal/icons";
import { patchTeamMembership, setTeamRole } from "../lib";
import {
  RoleBadge,
  SourceBadge,
  UserAvatar,
  formatJoinedAt,
  getTeamMembers,
} from "./shared";

const ROLE_OPTIONS: TeamMemberRole[] = ["OWNER", "ADMIN", "MEMBER"];
const ROLE_LABEL: Record<TeamMemberRole, string> = {
  OWNER: "Owner",
  ADMIN: "Admin",
  MEMBER: "Member",
};

const GRID =
  "grid grid-cols-[36px_minmax(0,2fr)_130px_120px_90px_44px] items-center gap-3";

interface MembersTabProps {
  team: Team;
  canManage: boolean;
  onAddMembers: () => void;
  onRefresh: () => void;
}

export default function MembersTab({
  team,
  canManage,
  onAddMembers,
  onRefresh,
}: MembersTabProps) {
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState<"all" | TeamMemberRole>("all");
  const [selected, setSelected] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);

  const members = useMemo(() => getTeamMembers(team), [team]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return members.filter((m) => {
      if (roleFilter !== "all" && m.role !== roleFilter) return false;
      if (
        q &&
        !m.name.toLowerCase().includes(q) &&
        !m.email.toLowerCase().includes(q)
      )
        return false;
      return true;
    });
  }, [members, search, roleFilter]);

  function toggle(id: string) {
    setSelected((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  }

  async function removeMembers(ids: string[]) {
    if (ids.length === 0) return;
    setBusy(true);
    const remaining = members
      .map((m) => m.id)
      .filter((id) => !ids.includes(id));
    const ccPairIds = team.cc_pairs.map((cc) => cc.id);
    try {
      const res = await patchTeamMembership(team.id, remaining, ccPairIds);
      if (res.ok) {
        toast.success(
          ids.length === 1
            ? "Removed member from team"
            : `Removed ${ids.length} members from team`
        );
        setSelected([]);
      } else {
        const body = await res.json().catch(() => ({}));
        toast.error(
          `Failed to remove member(s) - ${body.detail || body.message || res.status}`
        );
      }
    } catch (e: any) {
      toast.error(`Failed to remove member(s) - ${e?.message ?? "unknown error"}`);
    } finally {
      setBusy(false);
      onRefresh();
    }
  }

  async function changeRole(member: TeamMember, role: TeamMemberRole) {
    if (member.role === role) return;
    setBusy(true);
    try {
      const res = await setTeamRole(team.id, member.id, role);
      if (res.ok) {
        toast.success(`Updated ${member.name || member.email} to ${ROLE_LABEL[role]}`);
      } else {
        const body = await res.json().catch(() => ({}));
        toast.error(
          `Failed to change role - ${body.detail || body.message || res.status}`
        );
      }
    } catch (e: any) {
      toast.error(`Failed to change role - ${e?.message ?? "unknown error"}`);
    } finally {
      setBusy(false);
      onRefresh();
    }
  }

  function exportCsv() {
    const header = ["Name", "Email", "Role", "Joined", "Source"];
    const rows = filtered.map((m) => [
      m.name,
      m.email,
      ROLE_LABEL[m.role],
      m.joined_at ?? "",
      m.source,
    ]);
    const escape = (v: string) => `"${String(v).replace(/"/g, '""')}"`;
    const csv = [header, ...rows]
      .map((r) => r.map(escape).join(","))
      .join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${team.name.replace(/\s+/g, "_")}_members.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  const allChecked =
    filtered.length > 0 && filtered.every((m) => selected.includes(m.id));

  return (
    <div className="flex flex-col gap-3">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-2">
        <div className="flex-1 min-w-[220px] max-w-md">
          <InputTypeIn
            leftSearchIcon
            placeholder="Search members by name or email"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="w-[150px]">
          <InputSelect
            value={roleFilter}
            onValueChange={(v) => setRoleFilter(v as "all" | TeamMemberRole)}
          >
            <InputSelect.Trigger placeholder="All roles" />
            <InputSelect.Content>
              <InputSelect.Item value="all">All roles</InputSelect.Item>
              {ROLE_OPTIONS.map((r) => (
                <InputSelect.Item key={r} value={r}>
                  {ROLE_LABEL[r]}
                </InputSelect.Item>
              ))}
            </InputSelect.Content>
          </InputSelect>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <Button
            main
            secondary
            leftIcon={SvgDownload}
            onClick={exportCsv}
            disabled={filtered.length === 0}
          >
            Export CSV
          </Button>
          {canManage && (
            <Button action leftIcon={SvgUserPlus} onClick={onAddMembers}>
              Add members
            </Button>
          )}
        </div>
      </div>

      {/* Bulk action bar */}
      {canManage && selected.length > 0 && (
        <div
          className="flex items-center gap-3 rounded-12 border px-4 py-2"
          style={{
            borderColor: "var(--virtualai-accent-glow-strong)",
            backgroundColor: "var(--virtualai-accent-subtle)",
          }}
        >
          <Text mainUiBody text04 className="text-sm">
            {selected.length} selected
          </Text>
          <Button
            danger
            tertiary
            leftIcon={SvgTrash}
            disabled={busy}
            onClick={() => removeMembers(selected)}
          >
            Remove
          </Button>
          <div className="ml-auto">
            <IconButton
              main
              tertiary
              icon={SvgX}
              tooltip="Clear selection"
              onClick={() => setSelected([])}
            />
          </div>
        </div>
      )}

      {/* Table */}
      <div className="overflow-hidden rounded-16 border bg-background-tint-01">
        <div
          className={cn(
            GRID,
            "border-b bg-background-tint-02 px-4 py-2.5"
          )}
        >
          <div>
            {canManage ? (
              <Checkbox
                checked={allChecked}
                onCheckedChange={(v) =>
                  setSelected(v ? filtered.map((m) => m.id) : [])
                }
                aria-label="Select all members"
              />
            ) : null}
          </div>
          <HeaderCell>Member</HeaderCell>
          <HeaderCell>Role</HeaderCell>
          <HeaderCell>Joined</HeaderCell>
          <HeaderCell>Source</HeaderCell>
          <div />
        </div>

        <div className="divide-y divide-border-01">
          {filtered.map((m) => {
            const isSel = selected.includes(m.id);
            return (
              <div
                key={m.id}
                className={cn(
                  GRID,
                  "px-4 py-3 transition-colors hover:bg-background-tint-02",
                  isSel && "bg-background-tint-02"
                )}
              >
                <div>
                  {canManage ? (
                    <Checkbox
                      checked={isSel}
                      onCheckedChange={() => toggle(m.id)}
                      aria-label={`Select ${m.name}`}
                    />
                  ) : null}
                </div>
                <div className="flex items-center gap-3 min-w-0">
                  <UserAvatar id={m.id} name={m.name} email={m.email} size={34} />
                  <div className="flex flex-col min-w-0">
                    <Text mainUiBody text04 className="block truncate">
                      {m.name}
                    </Text>
                    <Text secondaryBody text03 className="block truncate text-xs">
                      {m.email}
                      {m.title ? ` · ${m.title}` : ""}
                    </Text>
                  </div>
                </div>
                <div>
                  <RoleBadge role={m.role} />
                </div>
                <div>
                  <Text secondaryBody text03 className="text-xs">
                    {formatJoinedAt(m.joined_at)}
                  </Text>
                </div>
                <div>
                  <SourceBadge source={m.source} />
                </div>
                <div className="flex justify-end">
                  {canManage && (
                    <RowMenu
                      member={m}
                      onChangeRole={(role) => changeRole(m, role)}
                      onRemove={() => removeMembers([m.id])}
                      disabled={busy}
                    />
                  )}
                </div>
              </div>
            );
          })}

          {filtered.length === 0 && (
            <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
              <div
                className="w-12 h-12 rounded-full flex items-center justify-center"
                style={{ backgroundColor: "var(--background-tint-02)" }}
              >
                <SvgUsers className="w-6 h-6 stroke-text-03" />
              </div>
              <div>
                <Text mainContentEmphasis>No members match your filters</Text>
                <Text secondaryBody text03 className="text-xs">
                  Try clearing the search or role filter.
                </Text>
              </div>
              {canManage && (
                <Button
                  main
                  secondary
                  leftIcon={SvgUserPlus}
                  onClick={onAddMembers}
                >
                  Add members
                </Button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function HeaderCell({ children }: { children: React.ReactNode }) {
  return (
    <Text
      as="span"
      secondaryBody
      text03
      className="text-[0.65rem] uppercase tracking-wide"
    >
      {children}
    </Text>
  );
}

function RowMenu({
  member,
  onChangeRole,
  onRemove,
  disabled,
}: {
  member: TeamMember;
  onChangeRole: (role: TeamMemberRole) => void;
  onRemove: () => void;
  disabled?: boolean;
}) {
  const [open, setOpen] = useState(false);
  return (
    <Popover open={open} onOpenChange={setOpen}>
      <Popover.Trigger asChild>
        <div>
          <IconButton
            main
            tertiary
            small
            icon={SvgMoreHorizontal}
            disabled={disabled}
            tooltip="Member actions"
          />
        </div>
      </Popover.Trigger>
      <Popover.Content align="end" side="bottom" width="md">
        <Popover.Menu>
          {ROLE_OPTIONS.map((r) => (
            <LineItem
              key={r}
              selected={member.role === r}
              onClick={() => {
                setOpen(false);
                onChangeRole(r);
              }}
            >
              {`Set as ${ROLE_LABEL[r]}`}
            </LineItem>
          ))}
          {null}
          <LineItem
            danger
            icon={SvgTrash}
            onClick={() => {
              setOpen(false);
              onRemove();
            }}
          >
            Remove from team
          </LineItem>
        </Popover.Menu>
      </Popover.Content>
    </Popover>
  );
}
