import { css } from "@emotion/react";

/**
 * VirtualAI dot-cluster icon – matches the main app's OnyxIcon.
 * Pink → Magenta → Purple → Indigo gradient palette.
 */
export function Logo(props: { size?: number }) {
  const { size = 34 } = props;
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 100 100"
      width={size}
      height={size}
      css={css`
        flex-shrink: 0;
      `}
      aria-label="VertualAI"
      role="img"
    >
      {/* Dot cluster logo – transparent background */}
      <circle cx="28" cy="16" r="13" fill="#E8449A" />
      <circle cx="52" cy="7" r="4" fill="#D63384" />
      <circle cx="66" cy="12" r="3.5" fill="#7C3AED" />
      <circle cx="72" cy="24" r="5.5" fill="#6D28D9" />
      <circle cx="12" cy="32" r="3.5" fill="#EC4899" />
      <circle cx="23" cy="37" r="6" fill="#DB2777" />
      <circle cx="39" cy="36" r="8.5" fill="#C026D3" />
      <circle cx="56" cy="30" r="4.5" fill="#9333EA" />
      <circle cx="73" cy="40" r="13" fill="#4338CA" />
      <circle cx="8" cy="50" r="2.5" fill="#EC4899" />
      <circle cx="27" cy="54" r="6.5" fill="#A855F7" />
      <circle cx="45" cy="50" r="4.5" fill="#8B5CF6" />
      <circle cx="58" cy="56" r="7" fill="#6366F1" />
      <circle cx="18" cy="67" r="4.5" fill="#D946EF" />
      <circle cx="37" cy="68" r="6" fill="#7C3AED" />
      <circle cx="55" cy="66" r="4" fill="#4F46E5" />
      <circle cx="26" cy="80" r="3" fill="#A855F7" />
      <circle cx="42" cy="82" r="3.5" fill="#6366F1" />
      <circle cx="55" cy="79" r="2.5" fill="#4338CA" />
      <circle cx="34" cy="93" r="2.5" fill="#7C3AED" />
    </svg>
  );
}

export function LogoText({ className }: { className?: string }) {
  return (
    <span
      className={className}
      css={css`
        font-weight: 700;
        font-size: 15px;
        line-height: 1;
        white-space: nowrap;
        background: linear-gradient(
          135deg,
          #e8449a 0%,
          #c026d3 35%,
          #7c3aed 65%,
          #4338ca 100%
        );
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
      `}
    >
      VertualAI Traces
    </span>
  );
}
