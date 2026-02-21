"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import Popover from "@/refresh-components/Popover";
import { cn } from "@/lib/utils";
import { SvgChevronDown } from "@opal/icons";
import Text from "@/refresh-components/texts/Text";
import type { AdminNavGroup, AdminNavItem } from "./adminNavItems";

interface AdminNavTabProps {
  group: AdminNavGroup;
}

export default function AdminNavTab({ group }: AdminNavTabProps) {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();

  // Check if any item in this group matches the current route
  const isActive = group.items.some((item) => pathname.startsWith(item.link));

  const GroupIcon = group.icon;

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <Popover.Trigger asChild>
        <button
          title={group.oldName ? `was: ${group.oldName}` : undefined}
          className={cn(
            "flex items-center gap-1.5 px-3 py-1.5 rounded-08 text-sm font-medium transition-colors cursor-pointer select-none",
            "hover:bg-background-neutral-02",
            isActive
              ? "bg-background-neutral-02 text-text-01"
              : "text-text-03 hover:text-text-01"
          )}
        >
          <GroupIcon className="w-4 h-4" />
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
        <div className="p-2 min-w-[16rem] max-w-[28rem]">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-0.5">
            {group.items.map((item) => (
              <NavDropdownItem
                key={item.link}
                item={item}
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
  isActive: boolean;
  onNavigate: () => void;
}

function NavDropdownItem({ item, isActive, onNavigate }: NavDropdownItemProps) {
  const Icon = item.icon;

  const linkContent = (
    <Link
      href={item.link as any}
      onClick={onNavigate}
      className={cn(
        "flex items-center gap-2.5 px-2.5 py-2 rounded-08 transition-colors group",
        "hover:bg-background-neutral-02",
        isActive && "bg-background-neutral-02",
        item.isAiRelated && "border-l-2 border-l-blue-500 dark:border-l-blue-400"
      )}
    >
      <Icon
        className={cn(
          "w-4 h-4 flex-shrink-0",
          isActive ? "stroke-text-01" : "stroke-text-03 group-hover:stroke-text-01"
        )}
      />
      <div className="flex flex-col min-w-0">
        <Text
          as="span"
          mainUiBody
          className={cn(
            isActive ? "text-text-01" : "text-text-03 group-hover:text-text-01"
          )}
        >
          {item.name}
        </Text>
        {item.oldName && item.oldName !== item.name && (
          <Text as="span" secondaryBody text04 className="text-[10px]">
            was: {item.oldName}
          </Text>
        )}
      </div>
      {item.error && (
        <span className="w-1.5 h-1.5 rounded-full bg-status-error-strong flex-shrink-0" />
      )}
    </Link>
  );

  return linkContent;
}
