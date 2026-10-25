import type { IconProps } from "@opal/types";

const SvgZap = ({ size, ...props }: IconProps) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 16 16"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    stroke="currentColor"
    {...props}
  >
    <path
      d="M8.66667 1.33334L2.66667 9.33334H7.33333L6.66667 14.6667L12.6667 6.66667H8L8.66667 1.33334Z"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

export default SvgZap;
