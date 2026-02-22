"use client";

import React, { useMemo, useCallback } from "react";
import { ToolSnapshot } from "@/lib/tools/interfaces";
import {
  SEARCH_TOOL_ID,
  WEB_SEARCH_TOOL_ID,
  IMAGE_GENERATION_TOOL_ID,
  PYTHON_TOOL_ID,
} from "@/app/app/components/tools/constants";
import { getIconForAction } from "@/app/app/services/actionUtils";
import { cn } from "@/lib/utils";

/** In-code tool IDs to surface as quick-toggle chips, in display order */
const QUICK_TOOL_IDS = [
  SEARCH_TOOL_ID,
  WEB_SEARCH_TOOL_ID,
  IMAGE_GENERATION_TOOL_ID,
  PYTHON_TOOL_ID,
];

/** Short display labels matching ChatGPT's concise naming */
const QUICK_TOOL_LABELS: Record<string, string> = {
  [SEARCH_TOOL_ID]: "Search",
  [WEB_SEARCH_TOOL_ID]: "Web",
  [IMAGE_GENERATION_TOOL_ID]: "Create image",
  [PYTHON_TOOL_ID]: "Code",
};

export interface QuickActionChipsProps {
  tools: ToolSnapshot[];
  forcedToolIds: number[];
  disabledToolIds: number[];
  onToggleForce: (toolId: number) => void;
  disabled: boolean;
}

/**
 * Horizontal row of quick action chip buttons inside the input bar.
 * Rounded pill buttons with icon + short label, like ChatGPT.
 */
export default function QuickActionChips({
  tools,
  forcedToolIds,
  disabledToolIds,
  onToggleForce,
  disabled,
}: QuickActionChipsProps) {
  const quickTools = useMemo(() => {
    return tools.filter(
      (t) =>
        t.in_code_tool_id &&
        QUICK_TOOL_IDS.includes(t.in_code_tool_id) &&
        !disabledToolIds.includes(t.id)
    );
  }, [tools, disabledToolIds]);

  const handleClick = useCallback(
    (toolId: number) => {
      if (!disabled) onToggleForce(toolId);
    },
    [disabled, onToggleForce]
  );

  if (quickTools.length === 0) return null;

  return (
    <div className="flex flex-row items-center gap-1">
      {quickTools.map((tool) => {
        const isForced = forcedToolIds.includes(tool.id);
        const Icon = getIconForAction(tool);
        const label =
          (tool.in_code_tool_id && QUICK_TOOL_LABELS[tool.in_code_tool_id]) ||
          tool.display_name ||
          tool.name;

        return (
          <button
            key={tool.id}
            type="button"
            onClick={() => handleClick(tool.id)}
            disabled={disabled}
            className={cn(
              "inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full",
              "text-xs font-medium transition-all duration-150",
              "cursor-pointer select-none",
              isForced
                ? "bg-background-neutral-03 border border-border-03 text-text-05"
                : [
                    "border border-border-02 hover:border-border-03",
                    "text-text-03 hover:text-text-05",
                    "hover:bg-background-neutral-02",
                  ],
              disabled && "opacity-50 pointer-events-none"
            )}
          >
            <Icon className="w-4 h-4" />
            <span>{label}</span>
          </button>
        );
      })}
    </div>
  );
}
