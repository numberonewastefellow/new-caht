/**
 * Deterministic color palette for agent label chips.
 * Each label gets a color based on its ID (modulo palette length).
 * Colors include dark: variants for proper dark mode support.
 */
export interface LabelColor {
  bg: string;
  text: string;
  border: string;
  selectedBg: string;
}

const LABEL_COLORS: LabelColor[] = [
  { bg: "bg-blue-100 dark:bg-blue-900/40", text: "text-blue-700 dark:text-blue-300", border: "border-blue-300 dark:border-blue-700", selectedBg: "bg-blue-500" },
  { bg: "bg-emerald-100 dark:bg-emerald-900/40", text: "text-emerald-700 dark:text-emerald-300", border: "border-emerald-300 dark:border-emerald-700", selectedBg: "bg-emerald-500" },
  { bg: "bg-violet-100 dark:bg-violet-900/40", text: "text-violet-700 dark:text-violet-300", border: "border-violet-300 dark:border-violet-700", selectedBg: "bg-violet-500" },
  { bg: "bg-amber-100 dark:bg-amber-900/40", text: "text-amber-700 dark:text-amber-300", border: "border-amber-300 dark:border-amber-700", selectedBg: "bg-amber-500" },
  { bg: "bg-rose-100 dark:bg-rose-900/40", text: "text-rose-700 dark:text-rose-300", border: "border-rose-300 dark:border-rose-700", selectedBg: "bg-rose-500" },
  { bg: "bg-teal-100 dark:bg-teal-900/40", text: "text-teal-700 dark:text-teal-300", border: "border-teal-300 dark:border-teal-700", selectedBg: "bg-teal-500" },
  { bg: "bg-indigo-100 dark:bg-indigo-900/40", text: "text-indigo-700 dark:text-indigo-300", border: "border-indigo-300 dark:border-indigo-700", selectedBg: "bg-indigo-500" },
  { bg: "bg-sky-100 dark:bg-sky-900/40", text: "text-sky-700 dark:text-sky-300", border: "border-sky-300 dark:border-sky-700", selectedBg: "bg-sky-500" },
  { bg: "bg-pink-100 dark:bg-pink-900/40", text: "text-pink-700 dark:text-pink-300", border: "border-pink-300 dark:border-pink-700", selectedBg: "bg-pink-500" },
  { bg: "bg-orange-100 dark:bg-orange-900/40", text: "text-orange-700 dark:text-orange-300", border: "border-orange-300 dark:border-orange-700", selectedBg: "bg-orange-500" },
];

const DEFAULT_LABEL_COLOR: LabelColor = LABEL_COLORS[0]!;

export function getLabelColor(labelId: number): LabelColor {
  return LABEL_COLORS[labelId % LABEL_COLORS.length] ?? DEFAULT_LABEL_COLOR;
}
