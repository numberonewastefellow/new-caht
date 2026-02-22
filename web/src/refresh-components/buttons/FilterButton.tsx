"use client";

import React, { useState } from "react";
import Text from "@/refresh-components/texts/Text";
import { cn, noProp } from "@/lib/utils";
import type { IconProps } from "@opal/types";
import IconButton from "./IconButton";
import { SvgChevronDownSmall, SvgX } from "@opal/icons";
const buttonClasses = (transient?: boolean) =>
  ({
    active: [
      "bg-[var(--theme-primary-05)]",
      "hover:bg-[var(--theme-primary-06)]",
      transient && "bg-[var(--theme-primary-06)]",
      "active:bg-[var(--theme-primary-04)]",
    ],
    inactive: [
      "bg-background-tint-01",
      "hover:bg-background-tint-02",
      transient && "bg-background-tint-02",
      "active:bg-background-tint-00",
    ],
  }) as const;

const textClasses = (transient?: boolean) => ({
  active: ["text-text-light-05 dark:text-text-dark-05"],
  inactive: [
    "text-text-04",
    "group-hover/FilterButton:text-text-05",
    transient && "text-text-05",
    "group-active/FilterButton:text-text-05",
  ],
});

const iconClasses = (transient?: boolean) =>
  ({
    active: ["stroke-text-light-05 dark:stroke-text-dark-05"],
    inactive: [
      "stroke-text-04",
      "group-hover/FilterButton:stroke-text-05",
      transient && "stroke-text-05",
      "group-active/FilterButton:stroke-text-05",
    ],
  }) as const;

export interface FilterButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  // Button states:
  active?: boolean;
  transient?: boolean;

  leftIcon: React.FunctionComponent<IconProps>;
  onClear?: () => void;

  children?: string;
}

export default function FilterButton({
  active,
  transient,

  leftIcon: LeftIcon,

  onClick,
  onClear,
  children,
  className,
  ...props
}: FilterButtonProps) {
  const state = active ? "active" : "inactive";

  return (
    <button
      className={cn(
        "p-2 h-fit rounded-12 group/FilterButton flex flex-row items-center justify-center gap-1 w-fit transition-colors duration-200",
        buttonClasses(transient)[state],
        className
      )}
      onClick={onClick}
      {...props}
    >
      <div className="pr-0.5">
        <LeftIcon
          className={cn("w-[1rem] h-[1rem]", iconClasses(transient)[state])}
        />
      </div>

      <Text as="p" mainUiAction nowrap className={cn(textClasses(transient)[state])}>
        {children}
      </Text>
      <div className="pl-0">
        {active ? (
          <IconButton
            icon={SvgX}
            onClick={noProp(onClear)}
            secondary
            className="!p-0 !rounded-04 !bg-transparent"
            iconClassName="!stroke-text-light-05 dark:!stroke-text-dark-05"
          />
        ) : (
          <div className="w-[1rem] h-[1rem]">
            <SvgChevronDownSmall
              className={cn(
                "w-[1rem] h-[1rem] transition-transform duration-200 ease-in-out",
                iconClasses(transient)[state],
                transient && "-rotate-180"
              )}
            />
          </div>
        )}
      </div>
    </button>
  );
}
