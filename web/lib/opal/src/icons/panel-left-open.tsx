import type { IconProps } from "@opal/types";

const SvgPanelLeftOpen = ({ size, ...props }: IconProps) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 16 16"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    stroke="currentColor"
    {...props}
  >
    {/* Panel outline */}
    <rect
      x={2}
      y={2}
      width={12}
      height={12}
      rx={1.33}
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    {/* Sidebar divider */}
    <path d="M6 2V14" strokeWidth={1.5} strokeLinecap="round" />
    {/* Right-pointing chevron (open direction) */}
    <path
      d="M9 6.5L11 8L9 9.5"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);
export default SvgPanelLeftOpen;
