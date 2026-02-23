"use client";

import React from "react";
import Link from "next/link";
import Logo from "@/refresh-components/Logo";
import SystemHealthDot from "./SystemHealthDot";
import ThemeToggleButton from "./ThemeToggleButton";
import AdminNavTab from "./AdminNavTab";
import { SvgSearch, SvgArrowLeft } from "@opal/icons";
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
    <header className="h-14 flex-shrink-0 bg-background-neutral-00 border-b border-border-01 z-sticky flex items-center px-4 gap-2">
      {/* Left zone: Logo + Admin pill + health */}
      <div className="flex items-center gap-2.5 flex-shrink-0">
        <Link href={"/admin" as any} className="flex items-center gap-2">
          <Logo folded size={24} />
          <span className="text-sm font-semibold text-text-05 tracking-tight">
            Admin
          </span>
        </Link>
        <SystemHealthDot />
      </div>

      {/* Separator */}
      <div className="hidden md:block w-px h-6 bg-border-01 mx-1" />

      {/* Center zone: Navigation tabs (hidden on mobile) */}
      <nav className="hidden md:flex items-center gap-1 flex-1 min-w-0 overflow-x-auto scrollbar-hide">
        {groups.map((group) => (
          <AdminNavTab key={group.id} group={group} />
        ))}
      </nav>

      {/* Mobile: spacer to push right zone to the end */}
      <div className="flex-1 md:hidden" />

      {/* Mobile hamburger menu */}
      <AdminMobileMenu groups={groups} />

      {/* Right zone: Command palette trigger + exit + theme + user */}
      <div className="flex items-center gap-1 flex-shrink-0">
        <button
          onClick={onOpenCommandPalette}
          className="flex items-center gap-2 px-2.5 py-1.5 rounded-08 text-sm text-text-03 hover:text-text-05 hover:bg-background-neutral-02 transition-colors cursor-pointer"
          aria-label="Open command palette"
        >
          <SvgSearch className="w-4 h-4" />
          <span className="hidden lg:inline text-xs text-text-03">
            <kbd className="px-1.5 py-0.5 rounded-04 bg-background-neutral-02 border border-border-01 text-text-03 font-mono text-2xs">
              ⌘K
            </kbd>
          </span>
        </button>

        {/* Separator */}
        <div className="hidden md:block w-px h-6 bg-border-01 mx-0.5" />

        <Link
          href={"/app" as any}
          className="hidden md:flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all hover:opacity-90 hover:shadow-md"
          style={{
            backgroundColor: "var(--virtualai-accent, var(--theme-primary-05))",
            color: "var(--text-light-05, #fff)",
          }}
        >
          <SvgArrowLeft className="w-3 h-3" />
          <span>Back to App</span>
        </Link>
        <ThemeToggleButton />
        <div className="ml-1">
          <UserAvatarPopover folded />
        </div>
      </div>
    </header>
  );
}
