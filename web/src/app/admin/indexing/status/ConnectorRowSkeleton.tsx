import React from "react";
import { cn } from "@/lib/utils";

const ACCENT_COLORS = [
  "bg-blue-500",
  "bg-emerald-500",
  "bg-violet-500",
  "bg-amber-500",
  "bg-rose-500",
  "bg-slate-500",
  "bg-cyan-500",
];

// Staggered loading animation skeleton that matches the colorful card-based layout
export function ConnectorStaggeredSkeleton({
  rowCount = 5,
  standalone = false,
  height = "h-20",
}: {
  rowCount?: number;
  standalone?: boolean;
  height?: string;
}) {
  const skeletonCards = [...Array(rowCount)].map((_, index) => {
    const accentColor = ACCENT_COLORS[index % ACCENT_COLORS.length]!;

    return (
      <div
        key={index}
        className={cn(
          "flex items-center justify-between rounded-12 border border-border-01 animate-pulse overflow-hidden",
          height
        )}
        style={{
          animationDelay: `${index * 150}ms`,
          animationDuration: "1.5s",
        }}
      >
        {/* Colored accent bar */}
        <div className="flex items-center gap-0 flex-1 min-w-0">
          <div className={cn("w-1 self-stretch flex-shrink-0", accentColor, "opacity-30")} />

          <div className="flex items-center gap-3 px-4 py-4 flex-1 min-w-0">
            {/* Chevron placeholder */}
            <div className="w-4 h-4 bg-background-neutral-02 dark:bg-neutral-700 rounded flex-shrink-0" />
            {/* Icon badge placeholder */}
            <div className="w-10 h-10 bg-background-neutral-02 dark:bg-neutral-700 rounded-08 flex-shrink-0" />
            {/* Name placeholder */}
            <div className="w-32 h-4 bg-background-neutral-02 dark:bg-neutral-700 rounded" />
          </div>
        </div>

        {/* Right: metric pills placeholder */}
        <div className="flex items-center gap-4 pr-4 flex-shrink-0">
          <div className="flex flex-col items-center gap-1">
            <div className="w-8 h-2.5 bg-background-neutral-02 dark:bg-neutral-700 rounded" />
            <div className="w-6 h-4 bg-background-neutral-02 dark:bg-neutral-700 rounded" />
          </div>
          <div className="w-px h-8 bg-border-01" />
          <div className="flex flex-col items-center gap-1">
            <div className="w-10 h-2.5 bg-background-neutral-02 dark:bg-neutral-700 rounded" />
            <div className="w-8 h-4 bg-background-neutral-02 dark:bg-neutral-700 rounded" />
          </div>
          <div className="w-px h-8 bg-border-01" />
          <div className="flex flex-col items-center gap-1">
            <div className="w-8 h-2.5 bg-background-neutral-02 dark:bg-neutral-700 rounded" />
            <div className="w-10 h-4 bg-background-neutral-02 dark:bg-neutral-700 rounded" />
          </div>
          <div className="ml-2 w-2.5 h-2.5 bg-background-neutral-02 dark:bg-neutral-700 rounded-full" />
        </div>
      </div>
    );
  });

  if (standalone) {
    return <div className="flex flex-col gap-3">{skeletonCards}</div>;
  }

  return <>{skeletonCards}</>;
}
