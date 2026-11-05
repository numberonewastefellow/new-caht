"use client";

import React from "react";
import Link from "next/link";
import type { Route } from "next";
import Logo from "@/refresh-components/Logo";
import SystemHealthDot from "./SystemHealthDot";
import ThemeToggleButton from "./ThemeToggleButton";
import AdminNavTab from "./AdminNavTab";
import { SvgSearch, SvgArrowLeft } from "@opal/icons";
import UserAvatarPopover from "@/sections/sidebar/UserAvatarPopover";
import AdminMobileMenu from "./AdminMobileMenu";
import { cn } from "@/lib/utils";
import type { AdminNavGroup } from "./adminNavItems";

/**
 * - "tabs" (nav v1): the classic bar — this is the whole navigation, so it
 *   carries the group dropdowns, search and the exit link.
 * - "slim" (nav v2): the left rail owns navigation, so the bar keeps only the
 *   global actions. Mobile is identical in both: the rail is hidden below `md`,
 *   so the brand, search and hamburger always render there.
 */
export type AdminTopBarVariant = "tabs" | "slim";

interface AdminTopBarProps {
  groups: AdminNavGroup[];
  onOpenCommandPalette: () => void;
  variant?: AdminTopBarVariant;
  /** Show the brand on desktop too (v1 always; v2 only on wizard routes). */
  showBrand?: boolean;
}

export default function AdminTopBar({
  groups,
  onOpenCommandPalette,
  variant = "slim",
  showBrand = false,
}: AdminTopBarProps) {
  const isTabs = variant === "tabs";
  // In "slim" the rail already provides these on desktop; mobile still needs them.
  const desktopOnlyInTabs = !isTabs && !showBrand ? "md:hidden" : undefined;

  return (
    <header className="h-14 flex-shrink-0 bg-background-neutral-00 border-b border-border-01 z-sticky flex items-center px-4 gap-2">
      {/* Brand */}
      <div
        className={cn(
          "flex items-center gap-2.5 flex-shrink-0",
          !isTabs && !showBrand && "md:hidden"
        )}
      >
        <Link href={"/admin" as Route} className="flex items-center gap-2">
          <Logo folded size={24} />
          <span className="text-sm font-semibold text-text-05 tracking-tight">
            Admin
          </span>
        </Link>
        <SystemHealthDot />
      </div>

      {isTabs ? (
        <>
          <div className="hidden md:block w-px h-6 bg-border-01 mx-1" />
          <nav className="hidden md:flex items-center gap-1 flex-1 min-w-0 overflow-x-auto scrollbar-hide">
            {groups.map((group) => (
              <AdminNavTab key={group.id} group={group} />
            ))}
          </nav>
          {/* Mobile: push the right zone to the end */}
          <div className="flex-1 md:hidden" />
        </>
      ) : (
        <div className="flex-1 min-w-0" />
      )}

      {/* Mobile hamburger menu (hidden at md+ by the component itself) */}
      <AdminMobileMenu groups={groups} />

      <div className="flex items-center gap-1 flex-shrink-0">
        <button
          onClick={onOpenCommandPalette}
          className={cn(
            "flex items-center gap-2 p-1.5 rounded-08 text-sm text-text-03 hover:text-text-05 hover:bg-background-neutral-02 transition-colors cursor-pointer",
            desktopOnlyInTabs
          )}
          aria-label="Open command palette"
        >
          <SvgSearch className="w-4 h-4" />
          {isTabs && (
            <span className="hidden lg:inline text-xs text-text-03">
              <kbd className="px-1.5 py-0.5 rounded-04 bg-background-neutral-02 border border-border-01 text-text-03 font-mono text-2xs">
                ⌘K
              </kbd>
            </span>
          )}
        </button>

        {(isTabs || showBrand) && (
          <>
            <div className="hidden md:block w-px h-6 bg-border-01 mx-0.5" />
            <Link
              href={"/app" as Route}
              className="hidden md:flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all hover:opacity-90 hover:shadow-md text-text-inverted-05"
              style={{
                backgroundColor:
                  "var(--virtualai-accent, var(--theme-primary-05))",
              }}
            >
              <SvgArrowLeft className="w-3 h-3" />
              <span>Back to App</span>
            </Link>
          </>
        )}

        <ThemeToggleButton />
        <div className="ml-1">
          <UserAvatarPopover folded />
        </div>
      </div>
    </header>
  );
}
