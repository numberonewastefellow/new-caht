"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import type { Route } from "next";
import { usePathname } from "next/navigation";
import Logo from "@/refresh-components/Logo";
import SimpleTooltip from "@/refresh-components/SimpleTooltip";
import SystemHealthDot from "./SystemHealthDot";
import { cn } from "@/lib/utils";
import {
  SvgArrowLeft,
  SvgChevronDown,
  SvgPanelLeftClose,
  SvgPanelLeftOpen,
  SvgSearch,
} from "@opal/icons";
import type { AdminNavGroup, AdminNavItem } from "./adminNavItems";
import { NAV_GROUP_COLORS } from "./navGroupColors";

const FOLDED_STORAGE_KEY = "adminSidebarFolded";

/**
 * Longest-prefix match, so `/admin/actions/mcp` doesn't also light up
 * `/admin/actions/open-api`, and `/admin/documents/sets/3` still resolves to
 * Collections. External links never match.
 */
function findActiveLink(
  groups: AdminNavGroup[],
  pathname: string
): string | null {
  let best: string | null = null;

  for (const group of groups) {
    for (const item of group.items) {
      if (item.external) continue;
      const matches =
        pathname === item.link || pathname.startsWith(`${item.link}/`);
      if (matches && (best === null || item.link.length > best.length)) {
        best = item.link;
      }
    }
  }

  return best;
}

interface AdminNavRowProps {
  item: AdminNavItem;
  group: AdminNavGroup;
  isActive: boolean;
}

function AdminNavRow({ item, group, isActive }: AdminNavRowProps) {
  const colors = NAV_GROUP_COLORS[group.color];
  const ItemIcon = item.icon;

  return (
    <Link
      href={item.link as Route}
      target={item.external ? "_blank" : undefined}
      rel={item.external ? "noopener noreferrer" : undefined}
      className={cn(
        "group flex items-center gap-2 pl-3 pr-2 py-1.5 ml-3 rounded-r-08 border-l-2 transition-colors",
        isActive
          ? cn(colors.activeBg, colors.accentBorder)
          : "border-l-transparent hover:bg-background-neutral-01"
      )}
    >
      <ItemIcon
        className={cn(
          "w-4 h-4 flex-shrink-0 transition-colors",
          isActive ? colors.iconText : "text-text-03 group-hover:text-text-05"
        )}
      />
      <span
        className={cn(
          "truncate text-[13px] transition-colors",
          isActive
            ? cn("font-medium", colors.activeText)
            : "text-text-04 group-hover:text-text-05"
        )}
      >
        {item.name}
      </span>
      {item.error && (
        <span className="ml-auto w-2 h-2 rounded-full bg-status-error-05 flex-shrink-0 animate-pulse" />
      )}
    </Link>
  );
}

interface AdminNavGroupBlockProps {
  group: AdminNavGroup;
  activeLink: string | null;
  expanded: boolean;
  onToggle: () => void;
}

function AdminNavGroupBlock({
  group,
  activeLink,
  expanded,
  onToggle,
}: AdminNavGroupBlockProps) {
  const colors = NAV_GROUP_COLORS[group.color];
  const GroupIcon = group.icon;
  const containsActive = group.items.some((item) => item.link === activeLink);

  return (
    <div className="flex flex-col">
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={expanded}
        className={cn(
          "group flex items-center gap-2 px-2 py-1.5 rounded-08 transition-colors cursor-pointer select-none",
          containsActive && !expanded ? colors.activeBg : colors.hoverBg
        )}
      >
        <span
          className={cn(
            "w-5 h-5 rounded-04 flex items-center justify-center flex-shrink-0",
            colors.iconBg
          )}
        >
          <GroupIcon className={cn("w-3.5 h-3.5", colors.iconText)} />
        </span>
        <span
          className={cn(
            "flex-1 text-left truncate text-[13px] font-medium",
            containsActive ? colors.activeText : "text-text-04"
          )}
        >
          {group.name}
        </span>
        <SvgChevronDown
          className={cn(
            "w-3 h-3 flex-shrink-0 text-text-03 transition-transform",
            expanded && "rotate-180"
          )}
        />
      </button>

      {expanded && (
        <div className="flex flex-col gap-0.5 mt-0.5 mb-1">
          {group.items.map((item) => (
            <AdminNavRow
              key={item.link}
              item={item}
              group={group}
              isActive={item.link === activeLink}
            />
          ))}
        </div>
      )}
    </div>
  );
}

/** Folded rail: one icon per group, navigating to the group's first item. */
function FoldedGroupButton({
  group,
  activeLink,
}: {
  group: AdminNavGroup;
  activeLink: string | null;
}) {
  const colors = NAV_GROUP_COLORS[group.color];
  const GroupIcon = group.icon;
  const containsActive = group.items.some((item) => item.link === activeLink);
  const firstItem = group.items[0];

  if (!firstItem) return null;

  return (
    <SimpleTooltip tooltip={group.name} side="right">
      <Link
        href={firstItem.link as Route}
        className={cn(
          "w-8 h-8 rounded-08 flex items-center justify-center transition-colors",
          containsActive ? colors.activeBg : colors.hoverBg
        )}
        aria-label={group.name}
      >
        <GroupIcon
          className={cn(
            "w-4 h-4",
            containsActive ? colors.iconText : "text-text-03"
          )}
        />
      </Link>
    </SimpleTooltip>
  );
}

export interface AdminSidebarProps {
  groups: AdminNavGroup[];
  onOpenCommandPalette: () => void;
}

export default function AdminSidebar({
  groups,
  onOpenCommandPalette,
}: AdminSidebarProps) {
  const pathname = usePathname();
  const [folded, setFolded] = useState(false);
  const [manuallyToggled, setManuallyToggled] = useState<
    Record<string, boolean>
  >({});

  // Restore the folded preference after hydration so SSR markup stays stable.
  useEffect(() => {
    if (typeof window === "undefined") return;
    setFolded(window.localStorage.getItem(FOLDED_STORAGE_KEY) === "true");
  }, []);

  const toggleFolded = useCallback(() => {
    setFolded((prev) => {
      const next = !prev;
      if (typeof window !== "undefined") {
        window.localStorage.setItem(FOLDED_STORAGE_KEY, String(next));
      }
      return next;
    });
  }, []);

  const activeLink = useMemo(
    () => findActiveLink(groups, pathname),
    [groups, pathname]
  );

  const activeGroupId = useMemo(
    () =>
      groups.find((group) => group.items.some((i) => i.link === activeLink))
        ?.id ?? null,
    [groups, activeLink]
  );

  // Navigating into a section re-opens it, even if it was collapsed earlier —
  // otherwise you'd land on a page whose section looks shut. Collapsing the
  // section you're already in still sticks.
  useEffect(() => {
    if (!activeGroupId) return;
    setManuallyToggled((prev) => {
      if (prev[activeGroupId] !== false) return prev;
      const next = { ...prev };
      delete next[activeGroupId];
      return next;
    });
  }, [activeGroupId]);

  // The section you're in is open by default; anything else follows your clicks.
  const isExpanded = useCallback(
    (groupId: string) => manuallyToggled[groupId] ?? groupId === activeGroupId,
    [manuallyToggled, activeGroupId]
  );

  const toggleGroup = useCallback(
    (groupId: string) => {
      setManuallyToggled((prev) => ({
        ...prev,
        [groupId]: !isExpanded(groupId),
      }));
    },
    [isExpanded]
  );

  return (
    <aside
      className={cn(
        "hidden md:flex flex-col flex-shrink-0 h-full border-r border-border-01 bg-background-neutral-00 transition-[width] duration-150",
        folded ? "w-[3.25rem]" : "w-[15rem]"
      )}
    >
      {/* Brand + fold toggle */}
      <div
        className={cn(
          "group/AdminSidebarHeader h-14 flex items-center flex-shrink-0 border-b border-border-01",
          folded ? "justify-center px-2" : "gap-2 px-3"
        )}
      >
        {!folded && (
          <>
            <Link
              href={"/admin" as Route}
              className="flex items-center gap-2 min-w-0"
            >
              <Logo folded size={24} />
              <span className="text-sm font-semibold text-text-05 tracking-tight truncate">
                Admin
              </span>
            </Link>
            <SystemHealthDot />
            <div className="flex-1" />
          </>
        )}
        <button
          type="button"
          onClick={toggleFolded}
          aria-label={folded ? "Expand navigation" : "Collapse navigation"}
          className={cn(
            "w-7 h-7 rounded-08 flex items-center justify-center text-text-03 hover:text-text-05 hover:bg-background-neutral-02 transition-colors cursor-pointer",
            folded && "opacity-0 group-hover/AdminSidebarHeader:opacity-100"
          )}
        >
          {folded ? (
            <SvgPanelLeftOpen className="w-4 h-4" />
          ) : (
            <SvgPanelLeftClose className="w-4 h-4" />
          )}
        </button>
      </div>

      {/* Search / command palette */}
      <div className={cn("flex-shrink-0 py-2", folded ? "px-2" : "px-2")}>
        <button
          type="button"
          onClick={onOpenCommandPalette}
          aria-label="Search admin"
          className={cn(
            "flex items-center rounded-08 text-text-03 hover:text-text-05 hover:bg-background-neutral-02 transition-colors cursor-pointer",
            folded
              ? "w-8 h-8 justify-center mx-auto"
              : "w-full gap-2 px-2 py-1.5 border border-border-01"
          )}
        >
          <SvgSearch className="w-4 h-4 flex-shrink-0" />
          {!folded && (
            <>
              <span className="text-[13px]">Search</span>
              <kbd className="ml-auto px-1.5 py-0.5 rounded-04 bg-background-neutral-02 border border-border-01 font-mono text-2xs">
                ⌘K
              </kbd>
            </>
          )}
        </button>
      </div>

      {/* Sections */}
      <nav
        className={cn(
          "flex-1 min-h-0 overflow-y-auto scrollbar-hide flex flex-col gap-0.5 pb-2",
          folded ? "px-2 items-center" : "px-2"
        )}
      >
        {groups.map((group) =>
          folded ? (
            <FoldedGroupButton
              key={group.id}
              group={group}
              activeLink={activeLink}
            />
          ) : (
            <AdminNavGroupBlock
              key={group.id}
              group={group}
              activeLink={activeLink}
              expanded={isExpanded(group.id)}
              onToggle={() => toggleGroup(group.id)}
            />
          )
        )}
      </nav>

      {/* Exit */}
      <div className="flex-shrink-0 border-t border-border-01 p-2">
        <SimpleTooltip tooltip={folded ? "Back to App" : undefined} side="right">
          <Link
            href={"/app" as Route}
            className={cn(
              "flex items-center rounded-08 text-text-04 hover:text-text-05 hover:bg-background-neutral-02 transition-colors",
              folded ? "w-8 h-8 justify-center mx-auto" : "gap-2 px-2 py-1.5"
            )}
          >
            <SvgArrowLeft className="w-4 h-4 flex-shrink-0" />
            {!folded && <span className="text-[13px]">Back to App</span>}
          </Link>
        </SimpleTooltip>
      </div>
    </aside>
  );
}
