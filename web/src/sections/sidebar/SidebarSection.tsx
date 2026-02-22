"use client";

import React from "react";
import type { IconProps } from "@opal/types";
import Text from "@/refresh-components/texts/Text";
import { cn } from "@/lib/utils";

export interface SidebarSectionProps {
  title: string;
  icon?: React.FunctionComponent<IconProps>;
  divider?: boolean;
  /** Make the section header clickable (toggles children visibility) */
  collapsible?: boolean;
  collapsed?: boolean;
  onToggle?: () => void;
  children?: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
}

export default function SidebarSection({
  title,
  icon: Icon,
  divider,
  collapsible,
  collapsed,
  onToggle,
  children,
  action,
  className,
}: SidebarSectionProps) {
  return (
    <div className={cn("flex flex-col group/SidebarSection", className)}>
      <div
        className={cn(
          "pl-2 pr-1.5 py-1 sticky top-[0rem] bg-background-tint-02 z-10 flex flex-row items-center justify-between min-h-[2rem]",
          collapsible && "cursor-pointer"
        )}
        onClick={collapsible ? onToggle : undefined}
      >
        <div className="flex flex-row items-center gap-1">
          <Text as="p" secondaryBody text02>
            {title}
          </Text>
          {collapsible && (
            <svg
              width="12"
              height="12"
              viewBox="0 0 12 12"
              className={cn(
                "transition-transform duration-150",
                collapsed ? "" : "rotate-90"
              )}
              style={{ stroke: "var(--text-02)", fill: "none", strokeWidth: 1.5, strokeLinecap: "round", strokeLinejoin: "round" }}
            >
              <polyline points="4,2 8,6 4,10" />
            </svg>
          )}
        </div>
        {action && (
          <div className="flex-shrink-0 opacity-0 group-hover/SidebarSection:opacity-100 transition-opacity">
            {action}
          </div>
        )}
      </div>
      {(!collapsible || !collapsed) && <div>{children}</div>}
    </div>
  );
}
