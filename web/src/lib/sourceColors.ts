import { ValidSources } from "@/lib/types";
import { SourceCategory } from "@/lib/search/interfaces";
import { getSourceMetadata } from "@/lib/sources";

export interface SourceCategoryColor {
  /** Accent bar / solid background */
  solid: string;
  /** Light tinted background for icon badges */
  bg: string;
  /** Text / icon color */
  text: string;
  /** Border color */
  border: string;
}

/**
 * Color palette for each source category.
 * Uses explicit dark: variants for proper dark/light theme support.
 */
const CATEGORY_COLORS: Record<SourceCategory, SourceCategoryColor> = {
  [SourceCategory.Wiki]: {
    solid: "bg-blue-500",
    bg: "bg-blue-50 dark:bg-blue-950/40",
    text: "text-blue-600 dark:text-blue-400",
    border: "border-blue-200 dark:border-blue-800",
  },
  [SourceCategory.Storage]: {
    solid: "bg-emerald-500",
    bg: "bg-emerald-50 dark:bg-emerald-950/40",
    text: "text-emerald-600 dark:text-emerald-400",
    border: "border-emerald-200 dark:border-emerald-800",
  },
  [SourceCategory.TicketingAndTaskManagement]: {
    solid: "bg-violet-500",
    bg: "bg-violet-50 dark:bg-violet-950/40",
    text: "text-violet-600 dark:text-violet-400",
    border: "border-violet-200 dark:border-violet-800",
  },
  [SourceCategory.Messaging]: {
    solid: "bg-amber-500",
    bg: "bg-amber-50 dark:bg-amber-950/40",
    text: "text-amber-600 dark:text-amber-400",
    border: "border-amber-200 dark:border-amber-800",
  },
  [SourceCategory.Sales]: {
    solid: "bg-rose-500",
    bg: "bg-rose-50 dark:bg-rose-950/40",
    text: "text-rose-600 dark:text-rose-400",
    border: "border-rose-200 dark:border-rose-800",
  },
  [SourceCategory.CodeRepository]: {
    solid: "bg-slate-500",
    bg: "bg-slate-50 dark:bg-slate-900/40",
    text: "text-slate-600 dark:text-slate-400",
    border: "border-slate-200 dark:border-slate-700",
  },
  [SourceCategory.Other]: {
    solid: "bg-cyan-500",
    bg: "bg-cyan-50 dark:bg-cyan-950/40",
    text: "text-cyan-600 dark:text-cyan-400",
    border: "border-cyan-200 dark:border-cyan-800",
  },
};

const DEFAULT_COLOR: SourceCategoryColor = CATEGORY_COLORS[SourceCategory.Other];

/**
 * Get the color scheme for a given source type based on its category.
 */
export function getSourceColor(source: ValidSources): SourceCategoryColor {
  const metadata = getSourceMetadata(source);
  if (metadata.category && CATEGORY_COLORS[metadata.category]) {
    return CATEGORY_COLORS[metadata.category];
  }
  return DEFAULT_COLOR;
}
