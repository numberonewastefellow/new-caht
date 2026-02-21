"use client";

import React from "react";
import Link from "next/link";
import Logo from "@/refresh-components/Logo";
import { Badge } from "@/components/ui/badge";
import SystemHealthDot from "./SystemHealthDot";
import ThemeToggleButton from "./ThemeToggleButton";
import AdminNavTab from "./AdminNavTab";
import { SvgSearch, SvgArrowUpRight } from "@opal/icons";
import UserAvatarPopover from "@/sections/sidebar/UserAvatarPopover";
import AdminMobileMenu from "./AdminMobileMenu";
import type { AdminNavGroup } from "./adminNavItems";

interface AdminTopBarProps {
  groups: AdminNavGroup[];
  onOpenCommandPalette: () => void;
}

export default function AdminTopBar({
  groups,
  onOpenCommandPalette,
}: AdminTopBarProps) {
  return (
    <header className="h-14 flex-shrink-0 bg-background-tint-02 border-b z-sticky flex items-center px-4 gap-2">
      {/* Left zone: Logo + Admin badge + health */}
      <div className="flex items-center gap-2 flex-shrink-0">
        <Link href={"/admin" as any} className="flex items-center">
          <Logo folded size={24} />
        </Link>
        <Badge variant="outline" className="text-xs font-medium">
          Admin
        </Badge>
        <SystemHealthDot />
      </div>

      {/* Center zone: Navigation tabs (hidden on mobile) */}
      <nav className="hidden md:flex items-center gap-0.5 ml-4 flex-1 min-w-0 overflow-x-auto scrollbar-hide">
        {groups.map((group) => (
          <AdminNavTab key={group.id} group={group} />
        ))}
      </nav>

      {/* Mobile: spacer to push right zone to the end */}
      <div className="flex-1 md:hidden" />

      {/* Mobile hamburger menu */}
      <AdminMobileMenu groups={groups} />

      {/* Right zone: Command palette trigger + theme + user */}
      <div className="flex items-center gap-1 flex-shrink-0">
        <button
          onClick={onOpenCommandPalette}
          className="flex items-center gap-2 px-2.5 py-1.5 rounded-08 text-sm text-text-03 hover:text-text-01 hover:bg-background-neutral-02 transition-colors cursor-pointer"
          aria-label="Open command palette"
        >
          <SvgSearch className="w-4 h-4" />
          <span className="hidden lg:inline text-xs text-text-04">
            <kbd className="px-1 py-0.5 rounded bg-background-neutral-03 text-text-03 font-mono text-xs">
              ⌘K
            </kbd>
          </span>
        </button>
        <Link
          href={"/app" as any}
          className="hidden md:flex items-center gap-1 px-2 py-1.5 rounded-08 text-xs text-text-03 hover:text-text-01 hover:bg-background-neutral-02 transition-colors"
        >
          <SvgArrowUpRight className="w-3 h-3" />
          <span>Exit Admin</span>
        </Link>
        <ThemeToggleButton />
        <div className="ml-1">
          <UserAvatarPopover folded />
        </div>
      </div>
    </header>
  );
}
