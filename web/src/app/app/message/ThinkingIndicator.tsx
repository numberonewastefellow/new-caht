"use client";

import React from "react";

/**
 * SpinnerRing — a small SVG ring that spins, using the VirtualAI accent color.
 * Used as the primary thinking/loading indicator.
 */
export function SpinnerRing({ size = 16 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill="none"
      className="virtualai-spinner flex-none"
    >
      <circle
        cx="8"
        cy="8"
        r="6"
        stroke="var(--border-02)"
        strokeWidth="2"
        fill="none"
      />
      <path
        d="M14 8a6 6 0 0 0-6-6"
        stroke="var(--virtualai-accent, var(--theme-primary-05))"
        strokeWidth="2"
        strokeLinecap="round"
        fill="none"
      />
    </svg>
  );
}

/**
 * WaveDots — three small dots that bounce in sequence.
 * Compact alternative to the spinner for inline usage.
 */
export function WaveDots() {
  return (
    <span className="inline-flex items-center gap-[3px] h-4">
      <span className="virtualai-wave-dot w-[4px] h-[4px] rounded-full bg-text-03 inline-block" />
      <span className="virtualai-wave-dot w-[4px] h-[4px] rounded-full bg-text-03 inline-block" />
      <span className="virtualai-wave-dot w-[4px] h-[4px] rounded-full bg-text-03 inline-block" />
    </span>
  );
}

/**
 * TypingCursor — a blinking block cursor for streaming text.
 * Replaces the old BlinkingDot.
 */
export function TypingCursor() {
  return (
    <span
      className="virtualai-typing-cursor inline-block w-[2px] h-[1em] bg-text-04 ml-[1px] align-text-bottom rounded-[1px]"
      aria-hidden="true"
    />
  );
}

/**
 * ThinkingIndicator — combined spinner ring + status text + wave dots.
 * This is the main "Thinking" display used in the timeline header.
 */
export function ThinkingIndicator({ text }: { text: string }) {
  return (
    <span className="inline-flex items-center gap-2">
      <SpinnerRing size={14} />
      <span className="text-text-04 font-main-ui-body">{text}</span>
      <WaveDots />
    </span>
  );
}
