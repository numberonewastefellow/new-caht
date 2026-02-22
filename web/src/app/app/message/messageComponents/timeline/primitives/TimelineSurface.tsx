import React from "react";
import { cn } from "@/lib/utils";
import type { TimelineAccent } from "@/app/app/message/messageComponents/interfaces";

export type TimelineSurfaceBackground = "tint" | "transparent";

export interface TimelineSurfaceProps {
  children: React.ReactNode;
  className?: string;
  isHover?: boolean;
  roundedTop?: boolean;
  roundedBottom?: boolean;
  background?: TimelineSurfaceBackground;
  /** Optional color accent — adds a left border and subtle tinted background */
  accent?: TimelineAccent;
}

const accentStyles: Record<TimelineAccent, { border: string; bg: string }> = {
  purple: {
    border: "border-l-2 border-l-[var(--theme-purple-05)]",
    bg: "bg-[var(--theme-purple-01)]",
  },
  blue: {
    border: "border-l-2 border-l-[var(--theme-blue-05)]",
    bg: "bg-[var(--theme-blue-01)]",
  },
  green: {
    border: "border-l-2 border-l-[var(--theme-green-05)]",
    bg: "bg-[var(--theme-green-01)]",
  },
};

/**
 * TimelineSurface provides the shared background + rounded corners for a row.
 * Use it to keep hover and tint behavior consistent across timeline items.
 */
export function TimelineSurface({
  children,
  className,
  isHover = false,
  roundedTop = false,
  roundedBottom = false,
  background = "tint",
  accent,
}: TimelineSurfaceProps) {
  if (React.Children.count(children) === 0) {
    return null;
  }

  const accentStyle = accent ? accentStyles[accent] : null;
  const baseBackground = accentStyle
    ? accentStyle.bg
    : background === "tint"
      ? "bg-background-tint-00"
      : "";
  const hoverBackground =
    background === "tint" && isHover && !accentStyle
      ? "bg-background-tint-02"
      : "";

  return (
    <div
      className={cn(
        "transition-colors duration-200",
        baseBackground,
        hoverBackground,
        accentStyle?.border,
        roundedTop && "rounded-t-12",
        roundedBottom && "rounded-b-12",
        className
      )}
    >
      {children}
    </div>
  );
}

export default TimelineSurface;
