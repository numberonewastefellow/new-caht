"use client";

import React, { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import CommandMenu from "@/refresh-components/commandmenu/CommandMenu";
import { SvgArrowUpDown } from "@opal/icons";
import Text from "@/refresh-components/texts/Text";
import type { AdminNavGroup } from "./adminNavItems";

interface AdminCommandPaletteProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  groups: AdminNavGroup[];
}

export default function AdminCommandPalette({
  open,
  onOpenChange,
  groups,
}: AdminCommandPaletteProps) {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState("");

  // Reset search when closing
  useEffect(() => {
    if (!open) {
      setSearchQuery("");
    }
  }, [open]);

  // Global keyboard shortcut: Cmd+K / Ctrl+K
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        onOpenChange(!open);
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open, onOpenChange]);

  const handleNavigate = useCallback(
    (link: string) => {
      router.push(link as any);
    },
    [router]
  );

  // Filter items based on search query
  const lowerQuery = searchQuery.toLowerCase();

  return (
    <CommandMenu open={open} onOpenChange={onOpenChange}>
      <CommandMenu.Content>
        <CommandMenu.Header
          placeholder="Search admin pages..."
          value={searchQuery}
          onValueChange={setSearchQuery}
          onClose={() => onOpenChange(false)}
        />
        <CommandMenu.List emptyMessage="No matching admin pages found.">
          {groups.map((group) => {
            const filteredItems = group.items.filter((item) =>
              lowerQuery
                ? item.name.toLowerCase().includes(lowerQuery) ||
                  (item.oldName?.toLowerCase().includes(lowerQuery) ?? false)
                : true
            );

            if (filteredItems.length === 0) return null;

            return (
              <React.Fragment key={group.id}>
                <CommandMenu.Filter
                  value={`filter-${group.id}`}
                  isApplied
                  icon={group.icon}
                >
                  {group.name}
                </CommandMenu.Filter>
                {filteredItems.map((item) => (
                  <CommandMenu.Item
                    key={item.link}
                    value={item.link}
                    icon={item.icon}
                    onSelect={() => handleNavigate(item.link)}
                    rightContent={
                      item.oldName && item.oldName !== item.name ? (
                        <Text as="span" secondaryBody text04 className="text-[10px] whitespace-nowrap">
                          was: {item.oldName}
                        </Text>
                      ) : undefined
                    }
                  >
                    {item.name}
                  </CommandMenu.Item>
                ))}
              </React.Fragment>
            );
          })}
        </CommandMenu.List>
        <CommandMenu.Footer
          leftActions={
            <>
              <CommandMenu.FooterAction
                icon={SvgArrowUpDown}
                label="Navigate"
              />
            </>
          }
        />
      </CommandMenu.Content>
    </CommandMenu>
  );
}
