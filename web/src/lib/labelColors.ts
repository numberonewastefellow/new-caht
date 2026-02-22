/**
 * Deterministic color palette for agent label chips.
 * Each label gets a color based on its ID (modulo palette length).
 */
export interface LabelColor {
  bg: string;
  text: string;
  border: string;
  selectedBg: string;
}

const LABEL_COLORS: LabelColor[] = [
  { bg: "bg-blue-100", text: "text-blue-700", border: "border-blue-300", selectedBg: "bg-blue-500" },
  { bg: "bg-emerald-100", text: "text-emerald-700", border: "border-emerald-300", selectedBg: "bg-emerald-500" },
  { bg: "bg-violet-100", text: "text-violet-700", border: "border-violet-300", selectedBg: "bg-violet-500" },
  { bg: "bg-amber-100", text: "text-amber-700", border: "border-amber-300", selectedBg: "bg-amber-500" },
  { bg: "bg-rose-100", text: "text-rose-700", border: "border-rose-300", selectedBg: "bg-rose-500" },
  { bg: "bg-teal-100", text: "text-teal-700", border: "border-teal-300", selectedBg: "bg-teal-500" },
  { bg: "bg-indigo-100", text: "text-indigo-700", border: "border-indigo-300", selectedBg: "bg-indigo-500" },
  { bg: "bg-sky-100", text: "text-sky-700", border: "border-sky-300", selectedBg: "bg-sky-500" },
  { bg: "bg-pink-100", text: "text-pink-700", border: "border-pink-300", selectedBg: "bg-pink-500" },
  { bg: "bg-orange-100", text: "text-orange-700", border: "border-orange-300", selectedBg: "bg-orange-500" },
];

const DEFAULT_LABEL_COLOR: LabelColor = LABEL_COLORS[0]!;

export function getLabelColor(labelId: number): LabelColor {
  return LABEL_COLORS[labelId % LABEL_COLORS.length] ?? DEFAULT_LABEL_COLOR;
}
