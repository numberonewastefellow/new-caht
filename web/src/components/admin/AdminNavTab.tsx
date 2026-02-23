"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import Popover from "@/refresh-components/Popover";
import { cn } from "@/lib/utils";
import { SvgChevronDown } from "@opal/icons";
import Text from "@/refresh-components/texts/Text";
import type { AdminNavGroup, AdminNavItem, NavGroupColor } from "./adminNavItems";

/** Map group color to Tailwind classes for various elements.
 * All classes are full static strings so Tailwind can detect them at build time. */
const colorMap: Record<
  NavGroupColor,
  {
    activeBg: string;
    activeText: string;
    hoverBg: string;
    iconBg: string;
    iconText: string;
    groupHoverIconBg: string;
    groupHoverIconText: string;
    accentBorder: string;
  }
> = {
  green: {
    activeBg: "bg-theme-green-01",
    activeText: "text-theme-green-05",
    hoverBg: "hover:bg-theme-green-01",
    iconBg: "bg-theme-green-01",
    iconText: "text-theme-green-05",
    groupHoverIconBg: "group-hover:bg-theme-green-01",
    groupHoverIconText: "group-hover:text-theme-green-05",
    accentBorder: "border-l-theme-green-05",
  },
  purple: {
    activeBg: "bg-theme-purple-01",
    activeText: "text-theme-purple-05",
    hoverBg: "hover:bg-theme-purple-01",
    iconBg: "bg-theme-purple-01",
    iconText: "text-theme-purple-05",
    groupHoverIconBg: "group-hover:bg-theme-purple-01",
    groupHoverIconText: "group-hover:text-theme-purple-05",
    accentBorder: "border-l-theme-purple-05",
  },
  blue: {
    activeBg: "bg-theme-blue-01",
    activeText: "text-theme-blue-05",
    hoverBg: "hover:bg-theme-blue-01",
    iconBg: "bg-theme-blue-01",
    iconText: "text-theme-blue-05",
    groupHoverIconBg: "group-hover:bg-theme-blue-01",
    groupHoverIconText: "group-hover:text-theme-blue-05",
    accentBorder: "border-l-theme-blue-05",
  },
  orange: {
    activeBg: "bg-theme-orange-01",
    activeText: "text-theme-orange-05",
    hoverBg: "hover:bg-theme-orange-01",
    iconBg: "bg-theme-orange-01",
    iconText: "text-theme-orange-05",
    groupHoverIconBg: "group-hover:bg-theme-orange-01",
    groupHoverIconText: "group-hover:text-theme-orange-05",
    accentBorder: "border-l-theme-orange-05",
  },
  cyan: {
    activeBg: "bg-theme-cyan-01",
    activeText: "text-theme-cyan-05",
    hoverBg: "hover:bg-theme-cyan-01",
    iconBg: "bg-theme-cyan-01",
    iconText: "text-theme-cyan-05",
    groupHoverIconBg: "group-hover:bg-theme-cyan-01",
    groupHoverIconText: "group-hover:text-theme-cyan-05",
    accentBorder: "border-l-theme-cyan-05",
  },
};

interface AdminNavTabProps {
  group: AdminNavGroup;
}

export default function AdminNavTab({ group }: AdminNavTabProps) {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();
  const colors = colorMap[group.color];

  // Check if any item in this group matches the current route
  const isActive = group.items.some((item) => pathname.startsWith(item.link));

  const GroupIcon = group.icon;

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <Popover.Trigger asChild>
        <button
          className={cn(
            "flex items-center gap-1.5 px-3 py-1.5 rounded-08 text-sm font-medium transition-all cursor-pointer select-none",
            isActive
              ? cn(colors.activeBg, colors.activeText)
              : cn("text-text-03 hover:text-text-05", colors.hoverBg),
            open && cn(colors.activeBg, colors.activeText)
          )}
        >
          <GroupIcon className={cn("w-4 h-4", (isActive || open) && colors.iconText)} />
          <span className="hidden md:inline">{group.name}</span>
          <SvgChevronDown
            className={cn(
              "w-3 h-3 transition-transform hidden md:block",
              open && "rotate-180"
            )}
          />
        </button>
      </Popover.Trigger>

      <Popover.Content
        align="start"
        sideOffset={8}
        width="fit"
      >
        <div className="p-2 min-w-[18rem] max-w-[32rem]">
          {/* Group header inside dropdown */}
          <div className="flex items-center gap-2 px-2.5 py-1.5 mb-1">
            <div className={cn("w-6 h-6 rounded-04 flex items-center justify-center", colors.iconBg)}>
              <GroupIcon className={cn("w-3.5 h-3.5", colors.iconText)} />
            </div>
            <Text as="span" mainUiBody className={cn("font-semibold", colors.activeText)}>
              {group.name}
            </Text>
          </div>

          <div className="w-full h-px bg-border-01 mb-1" />

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-0.5">
            {group.items.map((item) => (
              <NavDropdownItem
                key={item.link}
                item={item}
                groupColor={group.color}
                isActive={pathname.startsWith(item.link)}
                onNavigate={() => setOpen(false)}
              />
            ))}
          </div>
        </div>
      </Popover.Content>
    </Popover>
  );
}

interface NavDropdownItemProps {
  item: AdminNavItem;
  groupColor: NavGroupColor;
  isActive: boolean;
  onNavigate: () => void;
}

function NavDropdownItem({ item, groupColor, isActive, onNavigate }: NavDropdownItemProps) {
  const Icon = item.icon;
  const colors = colorMap[groupColor];

  return (
    <Link
      href={item.link as any}
      onClick={onNavigate}
      className={cn(
        "flex items-center gap-2.5 px-2.5 py-2 rounded-08 transition-all group",
        colors.hoverBg,
        isActive && cn(colors.activeBg, "border-l-2", colors.accentBorder)
      )}
    >
      {/* Colorful icon badge */}
      <div
        className={cn(
          "w-7 h-7 rounded-08 flex items-center justify-center flex-shrink-0 transition-colors",
          isActive ? colors.iconBg : cn("bg-background-neutral-02", colors.groupHoverIconBg)
        )}
      >
        <Icon
          className={cn(
            "w-3.5 h-3.5 flex-shrink-0 transition-colors",
            isActive ? colors.iconText : cn("text-text-03", colors.groupHoverIconText)
          )}
        />
      </div>
      <div className="flex flex-col min-w-0">
        <Text
          as="span"
          mainUiBody
          className={cn(
            "transition-colors",
            isActive ? "text-text-05 font-medium" : "text-text-04 group-hover:text-text-05"
          )}
        >
          {item.name}
        </Text>
      </div>
      {item.error && (
        <span className="w-2 h-2 rounded-full bg-status-error-05 flex-shrink-0 animate-pulse" />
      )}
    </Link>
  );
}
