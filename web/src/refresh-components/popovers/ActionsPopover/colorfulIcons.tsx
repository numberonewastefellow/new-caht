"use client";

import React from "react";
import type { IconProps } from "@opal/types";
import {
  SEARCH_TOOL_ID,
  WEB_SEARCH_TOOL_ID,
  IMAGE_GENERATION_TOOL_ID,
  PYTHON_TOOL_ID,
  FILE_READER_TOOL_ID,
} from "@/app/app/components/tools/constants";
import { cn, getFileExtension, isImageFile, isCodeFile } from "@/lib/utils";
import {
  SvgFileText,
  SvgImage,
  SvgFileBraces,
  SvgFileChartPie,
} from "@opal/icons";

/**
 * Color map — each tool type gets a distinctive background color.
 * Uses Tailwind classes so purging/JIT works correctly.
 */
const TOOL_COLORS: Record<string, { bg: string; text: string }> = {
  // Actions popover — tools
  [SEARCH_TOOL_ID]: { bg: "bg-blue-500", text: "text-white" },
  [WEB_SEARCH_TOOL_ID]: { bg: "bg-emerald-500", text: "text-white" },
  [IMAGE_GENERATION_TOOL_ID]: { bg: "bg-violet-500", text: "text-white" },
  [PYTHON_TOOL_ID]: { bg: "bg-amber-500", text: "text-white" },
  [FILE_READER_TOOL_ID]: { bg: "bg-sky-500", text: "text-white" },
  KnowledgeGraphTool: { bg: "bg-teal-500", text: "text-white" },
  deep_research: { bg: "bg-rose-500", text: "text-white" },
  manage_actions: { bg: "bg-slate-500", text: "text-white" },
  mcp_default: { bg: "bg-indigo-500", text: "text-white" },

  // Sidebar — navigation
  sidebar_new_session: { bg: "bg-blue-500", text: "text-white" },
  sidebar_search: { bg: "bg-violet-500", text: "text-white" },
  sidebar_craft: { bg: "bg-amber-500", text: "text-white" },
  sidebar_agents: { bg: "bg-teal-500", text: "text-white" },
  sidebar_workspaces: { bg: "bg-emerald-500", text: "text-white" },
  sidebar_admin: { bg: "bg-slate-500", text: "text-white" },
};

const DEFAULT_COLOR = { bg: "bg-indigo-500", text: "text-white" };

/**
 * Get the color scheme for a given tool ID.
 */
export function getToolColor(toolId: string | null | undefined) {
  if (!toolId) return DEFAULT_COLOR;
  return TOOL_COLORS[toolId] ?? DEFAULT_COLOR;
}

/**
 * Factory: wraps a base SVG icon inside a small colored rounded square.
 *
 * Rendered at 20px — slightly larger than LineItem's default 16px icon
 * so the colored background is visually distinctive.
 * The returned component satisfies `React.FunctionComponent<IconProps>`
 * so it works as a drop-in replacement wherever icons are expected.
 */
export function makeColorfulIcon(
  BaseIcon: React.FunctionComponent<IconProps>,
  colorKey: string
): React.FunctionComponent<IconProps> {
  const colors = TOOL_COLORS[colorKey] ?? DEFAULT_COLOR;

  return function ColorfulToolIcon() {
    return (
      <span
        className={cn(
          "inline-flex items-center justify-center rounded-[5px]",
          "w-5 h-5 flex-shrink-0",
          colors.bg
        )}
      >
        <BaseIcon className={cn("w-3 h-3", colors.text)} />
      </span>
    );
  };
}

/**
 * Factory: wraps a base SVG icon inside a small colored rounded square
 * that uses the app's accent color (--virtualai-accent) as background.
 * Falls back to indigo-500 when no accent color is set.
 */
export function makeAccentColorfulIcon(
  BaseIcon: React.FunctionComponent<IconProps>
): React.FunctionComponent<IconProps> {
  return function AccentColorfulIcon() {
    return (
      <span
        className="inline-flex items-center justify-center rounded-[5px] w-5 h-5 flex-shrink-0"
        style={{ backgroundColor: "var(--virtualai-accent, var(--theme-primary-05))" }}
      >
        <BaseIcon className="w-3 h-3 text-text-inverted-05" />
      </span>
    );
  };
}

/**
 * File-type color map — maps file categories to distinctive background colors.
 */
const FILE_TYPE_COLORS = {
  pdf: "bg-rose-500",
  doc: "bg-blue-500",
  docx: "bg-blue-500",
  xls: "bg-emerald-500",
  xlsx: "bg-emerald-500",
  csv: "bg-emerald-500",
  ppt: "bg-orange-500",
  pptx: "bg-orange-500",
  image: "bg-violet-500",
  code: "bg-amber-500",
  default: "bg-slate-400",
} as const;

const FILE_TYPE_LOOKUP: Record<string, string> = FILE_TYPE_COLORS;

/**
 * Returns a bg color class for a given filename based on its extension.
 */
export function getFileTypeColor(fileName: string | null | undefined): string {
  if (!fileName) return FILE_TYPE_COLORS.default;
  if (isImageFile(fileName)) return FILE_TYPE_COLORS.image;
  if (isCodeFile(fileName)) return FILE_TYPE_COLORS.code;
  const ext = getFileExtension(fileName).toLowerCase();
  return FILE_TYPE_LOOKUP[ext] ?? FILE_TYPE_COLORS.default;
}

/**
 * Returns a colorful file icon component — the base file icon wrapped
 * in a colored rounded square whose color depends on the file extension.
 */
export function getColorfulFileIcon(
  fileName: string | null | undefined
): React.FunctionComponent<IconProps> {
  const bg = getFileTypeColor(fileName);

  let BaseIcon: React.FunctionComponent<IconProps> = SvgFileText;
  if (fileName) {
    if (isImageFile(fileName)) BaseIcon = SvgImage;
    else if (/\.pptx?$/i.test(fileName)) BaseIcon = SvgFileChartPie;
    else if (isCodeFile(fileName)) BaseIcon = SvgFileBraces;
  }

  return function ColorfulFileIcon() {
    return (
      <span
        className={cn(
          "inline-flex items-center justify-center rounded-[5px]",
          "w-5 h-5 flex-shrink-0",
          bg
        )}
      >
        <BaseIcon className="w-3 h-3 text-white" />
      </span>
    );
  };
}
