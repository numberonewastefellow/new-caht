"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { SvgMenu, SvgX, SvgChevronDown, SvgArrowLeft } from "@opal/icons";
import { Button } from "@opal/components";
import { cn } from "@/lib/utils";
import Text from "@/refresh-components/texts/Text";
import type { AdminNavGroup, NavGroupColor } from "./adminNavItems";

const colorMap: Record<NavGroupColor, { iconBg: string; iconText: string; activeBg: string; activeText: string }> = {
  green:  { iconBg: "bg-theme-green-01",  iconText: "text-theme-green-05",  activeBg: "bg-theme-green-01",  activeText: "text-theme-green-05"  },
  purple: { iconBg: "bg-theme-purple-01", iconText: "text-theme-purple-05", activeBg: "bg-theme-purple-01", activeText: "text-theme-purple-05" },
  blue:   { iconBg: "bg-theme-blue-01",   iconText: "text-theme-blue-05",   activeBg: "bg-theme-blue-01",   activeText: "text-theme-blue-05"   },
  orange: { iconBg: "bg-theme-orange-01", iconText: "text-theme-orange-05", activeBg: "bg-theme-orange-01", activeText: "text-theme-orange-05" },
  cyan:   { iconBg: "bg-theme-cyan-01",   iconText: "text-theme-cyan-05",   activeBg: "bg-theme-cyan-01",   activeText: "text-theme-cyan-05"   },
};

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
          <div className="p-3 flex flex-col gap-0.5">
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
              const colors = colorMap[group.color];
              const isExpanded = expandedGroup === group.id;
              const hasActiveItem = group.items.some((item) =>
                pathname.startsWith(item.link)
              );

              return (
                <div key={group.id}>
                  <button
                    onClick={() => toggleGroup(group.id)}
                    className={cn(
                      "flex items-center gap-2.5 w-full px-3 py-2.5 rounded-08 text-left transition-all cursor-pointer",
                      hasActiveItem
                        ? cn(colors.activeBg, colors.activeText, "font-medium")
                        : "hover:bg-background-neutral-02"
                    )}
                  >
                    <div className={cn("w-7 h-7 rounded-08 flex items-center justify-center flex-shrink-0", colors.iconBg)}>
                      <GroupIcon className={cn("w-3.5 h-3.5", colors.iconText)} />
                    </div>
                    <div className="flex flex-col flex-1 min-w-0">
                      <Text as="span" mainUiBody>
                        {group.name}
                      </Text>
                    </div>
                    <SvgChevronDown
                      className={cn(
                        "w-4 h-4 transition-transform text-text-03",
                        isExpanded && "rotate-180"
                      )}
                    />
                  </button>

                  {isExpanded && (
                    <div className="ml-5 mt-0.5 flex flex-col gap-0.5 border-l-2 border-border-01 pl-3">
                      {group.items.map((item) => {
                        const ItemIcon = item.icon;
                        const isActive = pathname.startsWith(item.link);

                        return (
                          <Link
                            key={item.link}
                            href={item.link as any}
                            onClick={() => setOpen(false)}
                            className={cn(
                              "flex items-center gap-2.5 px-2.5 py-2 rounded-08 transition-all",
                              isActive
                                ? cn(colors.activeBg, "border-l-2", "border-l-current", colors.activeText)
                                : "hover:bg-background-neutral-02"
                            )}
                          >
                            <div className={cn(
                              "w-6 h-6 rounded-04 flex items-center justify-center flex-shrink-0",
                              isActive ? colors.iconBg : "bg-background-neutral-02"
                            )}>
                              <ItemIcon className={cn("w-3 h-3", isActive ? colors.iconText : "text-text-03")} />
                            </div>
                            <div className="flex flex-col min-w-0">
                              <Text
                                as="span"
                                secondaryBody
                                className={isActive ? "text-text-05 font-medium" : "text-text-04"}
                              >
                                {item.name}
                              </Text>
                            </div>
                          </Link>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}

            {/* Back to App link */}
            <div className="mt-2 pt-2 border-t border-border-01">
              <Link
                href={"/app" as any}
                onClick={() => setOpen(false)}
                className="flex items-center gap-2.5 px-3 py-2.5 rounded-full mx-2 font-medium transition-all hover:opacity-90 text-text-inverted-05"
                style={{
                  backgroundColor: "var(--virtualai-accent, var(--theme-primary-05))",
                }}
              >
                <SvgArrowLeft className="w-4 h-4" />
                <Text as="span" mainUiBody className="!text-inherit">
                  Back to App
                </Text>
              </Link>
            </div>
          </div>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
