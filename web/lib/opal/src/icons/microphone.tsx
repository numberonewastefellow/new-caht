import type { IconProps } from "@opal/types";
const SvgMicrophone = ({ size, ...props }: IconProps) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 16 16"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    stroke="currentColor"
    {...props}
  >
    <rect
      x="5.5"
      y="1.5"
      width="5"
      height="7"
      rx="2.5"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <path
      d="M3 8C3 10.2091 5.23858 12 8 12C10.7614 12 13 10.2091 13 8"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <path
      d="M8 12V14.5"
      strokeWidth={1.5}
      strokeLinecap="round"
    />
    <path
      d="M6 14.5H10"
      strokeWidth={1.5}
      strokeLinecap="round"
    />
  </svg>
);
export default SvgMicrophone;
