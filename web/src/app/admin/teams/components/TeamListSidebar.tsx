"use client";

import { useMemo, useState } from "react";
import { cn } from "@/lib/utils";
import { Team } from "@/lib/types";
import Text from "@/refresh-components/texts/Text";
import Button from "@/refresh-components/buttons/Button";
import Separator from "@/refresh-components/Separator";
import InputTypeIn from "@/refresh-components/inputs/InputTypeIn";
import { SvgGlobe, SvgLock, SvgPlus, SvgUsers } from "@opal/icons";
import { TeamAvatar, getKbCount, getMemberCount } from "./shared";

interface TeamListSidebarProps {
  teams: Team[];
  selectedId: number | null;
  onSelect: (id: number) => void;
  onNewTeam: () => void;
  canCreate: boolean;
}

export default function TeamListSidebar({
  teams,
  selectedId,
  onSelect,
  onNewTeam,
  canCreate,
}: TeamListSidebarProps) {
  const [search, setSearch] = useState("");

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    const active = teams.filter((t) => !t.is_up_for_deletion);
    if (!q) return active;
    return active.filter(
      (t) =>
        t.name.toLowerCase().includes(q) ||
        (t.description ?? "").toLowerCase().includes(q)
    );
  }, [teams, search]);

  return (
    <aside className="rounded-16 border bg-background-tint-01 flex flex-col min-h-0">
      <div className="p-3 flex flex-col gap-3">
        <div className="flex items-center gap-2">
          <SvgUsers className="w-4 h-4 stroke-text-03" />
          <Text mainUiBody text04>
            Teams
          </Text>
          <span
            className="ml-1 inline-flex items-center justify-center rounded-full px-1.5 h-5 text-[0.65rem] font-secondary-body"
            style={{
              backgroundColor: "var(--background-tint-02)",
              color: "var(--text-03)",
            }}
          >
            {filtered.length}
          </span>
        </div>
        <InputTypeIn
          leftSearchIcon
          placeholder="Search teams"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      <Separator noPadding />

      <div className="flex-1 min-h-0 overflow-y-auto p-2 flex flex-col gap-1">
        {filtered.map((t) => {
          const active = t.id === selectedId;
          return (
            <button
              key={t.id}
              type="button"
              onClick={() => onSelect(t.id)}
              className={cn(
                "group flex w-full items-center gap-3 rounded-12 border p-2 text-left transition-colors",
                active
                  ? "border-border-03 bg-background-tint-00"
                  : "border-transparent hover:bg-background-tint-02"
              )}
            >
              <TeamAvatar team={t} size={38} />
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1.5">
                  <Text mainUiBody text04 className="truncate">
                    {t.name}
                  </Text>
                  {t.is_public ? (
                    <SvgGlobe className="w-3 h-3 stroke-text-02 shrink-0" />
                  ) : (
                    <SvgLock className="w-3 h-3 stroke-text-02 shrink-0" />
                  )}
                </div>
                <div className="mt-0.5 flex items-center gap-1.5">
                  <Text secondaryBody text03 className="text-xs">
                    {getMemberCount(t)} member
                    {getMemberCount(t) !== 1 ? "s" : ""}
                  </Text>
                  <Text secondaryBody text03 className="text-xs">
                    ·
                  </Text>
                  <Text secondaryBody text03 className="text-xs">
                    {getKbCount(t)} KBs
                  </Text>
                </div>
              </div>
              {active && (
                <span
                  className="h-2 w-2 rounded-full shrink-0"
                  style={{
                    backgroundColor:
                      "var(--virtualai-accent, var(--theme-primary-05))",
                  }}
                />
              )}
            </button>
          );
        })}

        {filtered.length === 0 && (
          <div className="px-2 py-8 text-center">
            <Text secondaryBody text03 className="text-sm">
              No teams match your search.
            </Text>
          </div>
        )}
      </div>

      {canCreate && (
        <>
          <Separator noPadding />
          <div className="p-3">
            <Button
              action
              secondary
              leftIcon={SvgPlus}
              onClick={onNewTeam}
              className="w-full justify-center"
            >
              New team
            </Button>
          </div>
        </>
      )}
    </aside>
  );
}
