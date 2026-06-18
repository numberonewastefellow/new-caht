"use client";

import { cn } from "@/lib/utils";
import { swatchForId } from "./workspaceTheme";

/**
 * The colored, rounded-square workspace glyph (gradient background + white grid).
 * Color is derived deterministically from the workspace id via the swatch palette.
 */
export default function WorkspaceGlyph({
  id,
  size = 40,
  radius = 12,
  className,
}: {
  id: number;
  size?: number;
  radius?: number;
  className?: string;
}) {
  const { from, to } = swatchForId(id);
  const inner = Math.round(size * 0.5);
  return (
    <span
      className={cn(
        "inline-flex items-center justify-center text-white shadow-sm flex-shrink-0",
        className
      )}
      style={{
        width: size,
        height: size,
        borderRadius: radius,
        backgroundImage: `linear-gradient(135deg, ${from}, ${to})`,
      }}
    >
      <svg
        width={inner}
        height={inner}
        viewBox="0 0 16 16"
        fill="none"
        className="text-white"
      >
        <rect x="1.5" y="1.5" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1.5" />
        <rect x="9.5" y="1.5" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1.5" />
        <rect x="1.5" y="9.5" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1.5" />
        <rect x="9.5" y="9.5" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1.5" />
      </svg>
    </span>
  );
}
