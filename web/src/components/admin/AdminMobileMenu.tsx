"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { SvgMenu, SvgX, SvgChevronDown } from "@opal/icons";
import { Button } from "@opal/components";
import { cn } from "@/lib/utils";
import Text from "@/refresh-components/texts/Text";
import type { AdminNavGroup } from "./adminNavItems";

interface AdminMobileMenuProps {
  groups: AdminNavGroup[];
}

export default function AdminMobileMenu({ groups }: AdminMobileMenuProps) {
  const [open, setOpen] = useState(false);
  const [expandedGroup, setExpandedGroup] = useState<string | null>(null);
  const pathname = usePathname();

  const toggleGroup = (groupId: string) => {
    setExpandedGroup((prev) => (prev === groupId ? null : groupId));
  };

  return (
    <DialogPrimitive.Root open={open} onOpenChange={setOpen}>
      <DialogPrimitive.Trigger asChild>
        <div className="md:hidden">
          <Button
            icon={SvgMenu}
            prominence="tertiary"
            size="sm"
            aria-label="Open navigation menu"
          />
        </div>
      </DialogPrimitive.Trigger>

      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-modal-overlay bg-mask-03 backdrop-blur-03 md:hidden" />
        <DialogPrimitive.Content className="fixed top-14 left-0 right-0 z-modal bg-background-neutral-00 border-b shadow-lg max-h-[70vh] overflow-y-auto md:hidden">
          <DialogPrimitive.Title className="sr-only">
            Navigation Menu
          </DialogPrimitive.Title>
          <div className="p-3 flex flex-col gap-1">
            {/* Close button */}
            <div className="flex justify-end mb-1">
              <DialogPrimitive.Close asChild>
                <Button
                  icon={SvgX}
                  prominence="tertiary"
                  size="sm"
                  aria-label="Close menu"
                />
              </DialogPrimitive.Close>
            </div>

            {groups.map((group) => {
              const GroupIcon = group.icon;
              const isExpanded = expandedGroup === group.id;
              const hasActiveItem = group.items.some((item) =>
                pathname.startsWith(item.link)
              );

              return (
                <div key={group.id}>
                  <button
                    onClick={() => toggleGroup(group.id)}
                    className={cn(
                      "flex items-center gap-2 w-full px-3 py-2.5 rounded-08 text-left transition-colors cursor-pointer",
                      "hover:bg-background-neutral-02",
                      hasActiveItem && "text-text-01 font-medium"
                    )}
                  >
                    <GroupIcon className="w-4 h-4 flex-shrink-0" />
                    <div className="flex flex-col flex-1 min-w-0">
                      <Text as="span" mainUiBody>
                        {group.name}
                      </Text>
                      {group.oldName && (
                        <Text as="span" secondaryBody text04 className="text-[10px]">
                          was: {group.oldName}
                        </Text>
                      )}
                    </div>
                    <SvgChevronDown
                      className={cn(
                        "w-4 h-4 transition-transform",
                        isExpanded && "rotate-180"
                      )}
                    />
                  </button>

                  {isExpanded && (
                    <div className="ml-4 mt-0.5 flex flex-col gap-0.5">
                      {group.items.map((item) => {
                        const ItemIcon = item.icon;
                        const isActive = pathname.startsWith(item.link);

                        return (
                          <Link
                            key={item.link}
                            href={item.link as any}
                            onClick={() => setOpen(false)}
                            className={cn(
                              "flex items-center gap-2 px-3 py-2 rounded-08 transition-colors",
                              "hover:bg-background-neutral-02",
                              isActive && "bg-background-neutral-02"
                            )}
                          >
                            <ItemIcon
                              className={cn(
                                "w-4 h-4 flex-shrink-0",
                                isActive
                                  ? "stroke-text-01"
                                  : "stroke-text-03"
                              )}
                            />
                            <div className="flex flex-col min-w-0">
                              <Text
                                as="span"
                                secondaryBody
                                className={isActive ? "text-text-01" : "text-text-03"}
                              >
                                {item.name}
                              </Text>
                              {item.oldName && item.oldName !== item.name && (
                                <Text as="span" secondaryBody text04 className="text-[10px]">
                                  was: {item.oldName}
                                </Text>
                              )}
                            </div>
                          </Link>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}

            {/* Exit Admin link */}
            <div className="mt-2 pt-2 border-t">
              <Link
                href={"/app" as any}
                onClick={() => setOpen(false)}
                className="flex items-center gap-2 px-3 py-2 rounded-08 hover:bg-background-neutral-02 transition-colors"
              >
                <Text as="span" mainUiBody text03>
                  Exit Admin
                </Text>
              </Link>
            </div>
          </div>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
