/**
 * Brand color palette for LLM providers.
 * Each provider gets distinctive colors for cards, tiles, and modals.
 * Uses Tailwind classes so purging/JIT works correctly.
 */

import { LLMProviderName } from "./interfaces";

export interface ProviderColor {
  /** Solid brand color for accents (left borders, buttons) */
  solid: string;
  /** Light tinted background */
  bg: string;
  /** Text color that matches the brand */
  text: string;
  /** Border color for cards */
  border: string;
  /** Gradient top bar for tiles */
  gradient: string;
  /** Human-readable provider tagline */
  tagline: string;
}

const PROVIDER_COLORS: Record<string, ProviderColor> = {
  [LLMProviderName.OPENAI]: {
    solid: "bg-emerald-500",
    bg: "bg-emerald-50 dark:bg-emerald-950/30",
    text: "text-emerald-600 dark:text-emerald-400",
    border: "border-emerald-200 dark:border-emerald-800",
    gradient: "from-emerald-500 to-emerald-400",
    tagline: "GPT-4.5, o3, and more",
  },
  [LLMProviderName.ANTHROPIC]: {
    solid: "bg-amber-500",
    bg: "bg-amber-50 dark:bg-amber-950/30",
    text: "text-amber-600 dark:text-amber-400",
    border: "border-amber-200 dark:border-amber-800",
    gradient: "from-amber-500 to-amber-400",
    tagline: "Claude Opus, Sonnet, Haiku",
  },
  [LLMProviderName.AZURE]: {
    solid: "bg-blue-500",
    bg: "bg-blue-50 dark:bg-blue-950/30",
    text: "text-blue-600 dark:text-blue-400",
    border: "border-blue-200 dark:border-blue-800",
    gradient: "from-blue-500 to-blue-400",
    tagline: "Azure OpenAI Service",
  },
  [LLMProviderName.BEDROCK]: {
    solid: "bg-orange-500",
    bg: "bg-orange-50 dark:bg-orange-950/30",
    text: "text-orange-600 dark:text-orange-400",
    border: "border-orange-200 dark:border-orange-800",
    gradient: "from-orange-500 to-orange-400",
    tagline: "AWS foundation models",
  },
  [LLMProviderName.VERTEX_AI]: {
    solid: "bg-sky-500",
    bg: "bg-sky-50 dark:bg-sky-950/30",
    text: "text-sky-600 dark:text-sky-400",
    border: "border-sky-200 dark:border-sky-800",
    gradient: "from-sky-500 to-sky-400",
    tagline: "Gemini and Google AI",
  },
  [LLMProviderName.OLLAMA_CHAT]: {
    solid: "bg-slate-500",
    bg: "bg-slate-50 dark:bg-slate-950/30",
    text: "text-slate-600 dark:text-slate-400",
    border: "border-slate-200 dark:border-slate-800",
    gradient: "from-slate-500 to-slate-400",
    tagline: "Local open-source models",
  },
  [LLMProviderName.OPENROUTER]: {
    solid: "bg-violet-500",
    bg: "bg-violet-50 dark:bg-violet-950/30",
    text: "text-violet-600 dark:text-violet-400",
    border: "border-violet-200 dark:border-violet-800",
    gradient: "from-violet-500 to-violet-400",
    tagline: "Unified model gateway",
  },
  [LLMProviderName.CUSTOM]: {
    solid: "bg-indigo-500",
    bg: "bg-indigo-50 dark:bg-indigo-950/30",
    text: "text-indigo-600 dark:text-indigo-400",
    border: "border-indigo-200 dark:border-indigo-800",
    gradient: "from-indigo-500 to-indigo-400",
    tagline: "Custom OpenAI-compatible endpoint",
  },
};

const DEFAULT_PROVIDER_COLOR: ProviderColor = {
  solid: "bg-indigo-500",
  bg: "bg-indigo-50 dark:bg-indigo-950/30",
  text: "text-indigo-600 dark:text-indigo-400",
  border: "border-indigo-200 dark:border-indigo-800",
  gradient: "from-indigo-500 to-indigo-400",
  tagline: "Custom LLM provider",
};

export function getProviderColor(providerName: string): ProviderColor {
  return PROVIDER_COLORS[providerName] ?? DEFAULT_PROVIDER_COLOR;
}
