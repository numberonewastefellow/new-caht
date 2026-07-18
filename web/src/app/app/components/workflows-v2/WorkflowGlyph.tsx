"use client";

import { cn } from "@/lib/utils";
import { swatchForId } from "@/app/app/components/workspaces/workspace-v2/workspaceTheme";

/**
 * The colored, rounded-square workflow glyph (gradient background + white node
 * graph). Color is derived deterministically from the workflow id via the same
 * swatch palette used by workspaces, so the two galleries feel like one system.
 */
export default function WorkflowGlyph({
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
      {/* Small node-graph mark to distinguish workflows from the workspace grid */}
      <svg
        width={inner}
        height={inner}
        viewBox="0 0 16 16"
        fill="none"
        className="text-white"
      >
        <path
          d="M4 4.5 H8 M8 4.5 V11.5 M8 11.5 H12 M8 4.5 H12"
          stroke="currentColor"
          strokeWidth="1.25"
          strokeLinecap="round"
        />
        <circle cx="3" cy="4.5" r="2" fill="currentColor" />
        <circle cx="13" cy="4.5" r="2" fill="currentColor" />
        <circle cx="13" cy="11.5" r="2" fill="currentColor" />
      </svg>
    </span>
  );
}
