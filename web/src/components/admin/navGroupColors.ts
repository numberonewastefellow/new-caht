import type { NavGroupColor } from "./adminNavItems";

export interface NavGroupColorClasses {
  /** Background for the active/open state of a group trigger. */
  activeBg: string;
  /** Text color for the active/open state of a group trigger. */
  activeText: string;
  /** Hover background for an inactive group trigger. */
  hoverBg: string;
  /** Background of the small rounded icon badge. */
  iconBg: string;
  /** Icon color inside the badge. */
  iconText: string;
  /** Icon badge background, applied on parent hover. */
  groupHoverIconBg: string;
  /** Icon badge color, applied on parent hover. */
  groupHoverIconText: string;
  /** Left accent border used to mark the active item. */
  accentBorder: string;
}

/**
 * Tailwind classes for each nav group color, shared by every admin nav surface
 * (sidebar rail, mobile menu, breadcrumbs).
 *
 * All classes are full static strings so Tailwind can detect them at build time —
 * never build these names by interpolation.
 */
export const NAV_GROUP_COLORS: Record<NavGroupColor, NavGroupColorClasses> = {
  green: {
    activeBg: "bg-theme-green-01",
    activeText: "text-theme-green-05",
    hoverBg: "hover:bg-theme-green-01",
    iconBg: "bg-theme-green-01",
    iconText: "text-theme-green-05",
    groupHoverIconBg: "group-hover:bg-theme-green-01",
    groupHoverIconText: "group-hover:text-theme-green-05",
    accentBorder: "border-l-theme-green-05",
  },
  purple: {
    activeBg: "bg-theme-purple-01",
    activeText: "text-theme-purple-05",
    hoverBg: "hover:bg-theme-purple-01",
    iconBg: "bg-theme-purple-01",
    iconText: "text-theme-purple-05",
    groupHoverIconBg: "group-hover:bg-theme-purple-01",
    groupHoverIconText: "group-hover:text-theme-purple-05",
    accentBorder: "border-l-theme-purple-05",
  },
  blue: {
    activeBg: "bg-theme-blue-01",
    activeText: "text-theme-blue-05",
    hoverBg: "hover:bg-theme-blue-01",
    iconBg: "bg-theme-blue-01",
    iconText: "text-theme-blue-05",
    groupHoverIconBg: "group-hover:bg-theme-blue-01",
    groupHoverIconText: "group-hover:text-theme-blue-05",
    accentBorder: "border-l-theme-blue-05",
  },
  sky: {
    activeBg: "bg-theme-sky-01",
    activeText: "text-theme-sky-05",
    hoverBg: "hover:bg-theme-sky-01",
    iconBg: "bg-theme-sky-01",
    iconText: "text-theme-sky-05",
    groupHoverIconBg: "group-hover:bg-theme-sky-01",
    groupHoverIconText: "group-hover:text-theme-sky-05",
    accentBorder: "border-l-theme-sky-05",
  },
  orange: {
    activeBg: "bg-theme-orange-01",
    activeText: "text-theme-orange-05",
    hoverBg: "hover:bg-theme-orange-01",
    iconBg: "bg-theme-orange-01",
    iconText: "text-theme-orange-05",
    groupHoverIconBg: "group-hover:bg-theme-orange-01",
    groupHoverIconText: "group-hover:text-theme-orange-05",
    accentBorder: "border-l-theme-orange-05",
  },
  amber: {
    activeBg: "bg-theme-amber-01",
    activeText: "text-theme-amber-05",
    hoverBg: "hover:bg-theme-amber-01",
    iconBg: "bg-theme-amber-01",
    iconText: "text-theme-amber-05",
    groupHoverIconBg: "group-hover:bg-theme-amber-01",
    groupHoverIconText: "group-hover:text-theme-amber-05",
    accentBorder: "border-l-theme-amber-05",
  },
  cyan: {
    activeBg: "bg-theme-cyan-01",
    activeText: "text-theme-cyan-05",
    hoverBg: "hover:bg-theme-cyan-01",
    iconBg: "bg-theme-cyan-01",
    iconText: "text-theme-cyan-05",
    groupHoverIconBg: "group-hover:bg-theme-cyan-01",
    groupHoverIconText: "group-hover:text-theme-cyan-05",
    accentBorder: "border-l-theme-cyan-05",
  },
};
