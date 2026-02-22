import React from "react";
import { TimelineIconColumn, TimelineRailVariant } from "./TimelineIconColumn";
import type { TimelineAccent } from "@/app/app/message/messageComponents/interfaces";

/**
 * TimelineRowRailVariant controls how the left column is rendered.
 * - rail: normal icon + connector column.
 * - spacer: empty column that preserves rail width.
 * - none: no left column at all.
 */
export type TimelineRowRailVariant = TimelineRailVariant | "none";

export interface TimelineRowProps {
  railVariant?: TimelineRowRailVariant;
  icon?: React.ReactNode;
  showIcon?: boolean;
  disableTopConnectorHover?: boolean;
  /**
   * Controls the height of the icon row within the rail.
   * Use compact when the header is hidden to keep alignment stable.
   */
  iconRowVariant?: "default" | "compact";
  isFirst?: boolean;
  isLast?: boolean;
  isHover?: boolean;
  /** Optional color accent for the step icon background */
  accent?: TimelineAccent;
  children?: React.ReactNode;
}

/**
 * TimelineRow composes the rail column + content column.
 * It is the base layout primitive for all timeline rows.
 */
export function TimelineRow({
  railVariant = "rail",
  icon,
  showIcon = true,
  disableTopConnectorHover = false,
  iconRowVariant = "default",
  isFirst = false,
  isLast = false,
  isHover = false,
  accent,
  children,
}: TimelineRowProps) {
  return (
    <div className="flex w-full">
      {railVariant !== "none" && (
        <TimelineIconColumn
          variant={railVariant === "spacer" ? "spacer" : "rail"}
          icon={icon}
          showIcon={showIcon}
          disableTopConnectorHover={disableTopConnectorHover}
          iconRowVariant={iconRowVariant}
          isFirst={isFirst}
          isLast={isLast}
          isHover={isHover}
          accent={accent}
        />
      )}
      <div className="flex-1">{children}</div>
    </div>
  );
}

export default TimelineRow;
