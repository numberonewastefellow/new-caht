import { css } from "lit";
import { colors } from "./colors";

/**
 * VertualAI Design System - Theme
 * Typography, spacing, and layout tokens from Figma
 */
export const theme = css`
  ${colors}

  :host {
    /* Typography - Hanken Grotesk */
    --virtualai-font-family: "Hanken Grotesk", -apple-system, BlinkMacSystemFont,
      "Segoe UI", sans-serif;
    --virtualai-font-family-mono: "DM Mono", "Monaco", "Menlo", monospace;

    /* Font Sizes */
    --virtualai-font-size-small: 10px;
    --virtualai-font-size-secondary: 12px;
    --virtualai-font-size-sm: 13px;
    --virtualai-font-size-main: 14px;
    --virtualai-font-size-label: 16px;

    /* Line Heights */
    --virtualai-line-height-small: 12px;
    --virtualai-line-height-secondary: 16px;
    --virtualai-line-height-main: 20px;
    --virtualai-line-height-label: 24px;
    --virtualai-line-height-section: 28px;
    --virtualai-line-height-headline: 36px;

    /* Font Weights */
    --virtualai-weight-regular: 400;
    --virtualai-weight-medium: 500;
    --virtualai-weight-semibold: 600;

    /* Content Heights */
    --virtualai-height-content-secondary: 12px;
    --virtualai-height-content-main: 16px;
    --virtualai-height-content-label: 18px;
    --virtualai-height-content-section: 24px;

    /* Border Radius - from Figma */
    --virtualai-radius-04: 4px;
    --virtualai-radius-08: 8px;
    --virtualai-radius-12: 12px;
    --virtualai-radius-16: 16px;
    --virtualai-radius-round: 1000px;

    /* Spacing - Block */
    --virtualai-space-block-1x: 4px;
    --virtualai-space-block-2x: 8px;
    --virtualai-space-block-3x: 12px;
    --virtualai-space-block-4x: 16px;
    --virtualai-space-block-6x: 24px;

    /* Spacing - Inline */
    --virtualai-space-inline-0: 0px;
    --virtualai-space-inline-0_5x: 2px;
    --virtualai-space-inline-1x: 4px;

    /* Legacy spacing aliases (for compatibility) */
    --virtualai-space-2xs: var(--virtualai-space-block-1x);
    --virtualai-space-xs: var(--virtualai-space-block-2x);
    --virtualai-space-sm: var(--virtualai-space-block-3x);
    --virtualai-space-md: var(--virtualai-space-block-4x);
    --virtualai-space-lg: var(--virtualai-space-block-6x);

    /* Padding */
    --virtualai-padding-icon-0: 0px;
    --virtualai-padding-icon-0_5x: 2px;
    --virtualai-padding-text-0_5x: 2px;
    --virtualai-padding-text-1x: 4px;

    /* Icon Weights (stroke-width) */
    --virtualai-icon-weight-secondary: 1px;
    --virtualai-icon-weight-main: 1.5px;
    --virtualai-icon-weight-section: 2px;

    /* Z-index */
    --virtualai-z-launcher: 9999;
    --virtualai-z-widget: 10000;

    /* Transitions */
    --virtualai-transition-fast: 150ms cubic-bezier(0.4, 0, 0.2, 1);
    --virtualai-transition-base: 200ms cubic-bezier(0.4, 0, 0.2, 1);
  }

  * {
    box-sizing: border-box;
  }
`;
