"use client";

import React, { useMemo } from "react";
import { ToolSnapshot } from "@/lib/tools/interfaces";
import {
  SEARCH_TOOL_ID,
  WEB_SEARCH_TOOL_ID,
  IMAGE_GENERATION_TOOL_ID,
} from "@/app/app/components/tools/constants";
import { getIconForAction } from "@/app/app/services/actionUtils";
import { Button } from "@opal/components";

/** In-code tool IDs to surface as quick-toggle chips, in display order */
const QUICK_TOOL_IDS = [
  SEARCH_TOOL_ID,
  WEB_SEARCH_TOOL_ID,
  IMAGE_GENERATION_TOOL_ID,
];

/** Short display labels for quick chips */
const QUICK_TOOL_LABELS: Record<string, string> = {
  [SEARCH_TOOL_ID]: "Search",
  [WEB_SEARCH_TOOL_ID]: "Web",
  [IMAGE_GENERATION_TOOL_ID]: "Image",
};

export interface QuickActionChipsProps {
  tools: ToolSnapshot[];
  forcedToolIds: number[];
  disabledToolIds: number[];
  onToggleForce: (toolId: number) => void;
  disabled: boolean;
}

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

  if (quickTools.length === 0) return null;

  return (
    <div className="flex flex-row items-center gap-0.5">
      {quickTools.map((tool) => {
        const isForced = forcedToolIds.includes(tool.id);
        const label =
          (tool.in_code_tool_id && QUICK_TOOL_LABELS[tool.in_code_tool_id]) ||
          tool.display_name ||
          tool.name;

        return (
          <Button
            key={tool.id}
            icon={getIconForAction(tool)}
            onClick={() => onToggleForce(tool.id)}
            variant="select"
            selected={isForced}
            foldable={!isForced}
            disabled={disabled}
          >
            {label}
          </Button>
        );
      })}
    </div>
  );
}
