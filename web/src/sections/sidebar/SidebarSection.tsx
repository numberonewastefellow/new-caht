"use client";

import React from "react";
import type { IconProps } from "@opal/types";
import Text from "@/refresh-components/texts/Text";
import { cn } from "@/lib/utils";

export interface SidebarSectionProps {
  title: string;
  icon?: React.FunctionComponent<IconProps>;
  divider?: boolean;
  children?: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
}

export default function SidebarSection({
  title,
  icon: Icon,
  divider,
  children,
  action,
  className,
}: SidebarSectionProps) {
  return (
    <div className={cn("flex flex-col group/SidebarSection", className)}>
      {divider && <div className="mx-2 border-t border-border-01 mb-1" />}
      <div className="pl-2 pr-1.5 py-1 sticky top-[0rem] bg-background-tint-02 z-10 flex flex-row items-center justify-between min-h-[2rem]">
        <div className="flex flex-row items-center gap-1.5">
          {Icon && (
            <Icon className="h-3.5 w-3.5 flex-shrink-0" style={{ stroke: "var(--text-02)" }} />
          )}
          <Text as="p" secondaryBody text02>
            {title}
          </Text>
        </div>
        {action && (
          <div className="flex-shrink-0 opacity-0 group-hover/SidebarSection:opacity-100 transition-opacity">
            {action}
          </div>
        )}
      </div>
      <div>{children}</div>
    </div>
  );
}
