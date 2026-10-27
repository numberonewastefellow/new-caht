/**
 * "What should each run receive?" — input modes for scheduled workflows.
 * Mirrors backend/om/pulse/inputs.py (pure helpers, unit-tested).
 */
import type { InputMode, PulseSchedule } from "@/lib/schedules/interfaces";

export const DEFAULT_WINDOW_MESSAGE =
  "Run for {{date}}. Only include what changed since {{window_start}}.";
export const DEFAULT_LIST_MESSAGE = "{{item}}";
export const MAX_LIST_ITEMS = 500;

export interface InputModeOption {
  mode: InputMode;
  label: string;
  /** When to pick it — shown under the option. */
  hint: string;
  /** Short badge text for lists/tables. */
  badge: string;
}

export const INPUT_MODE_OPTIONS: InputModeOption[] = [
  {
    mode: "fixed",
    label: "The same request every run",
    hint: "Questions, fixed reports and checks — e.g. “What is the use of paracetamol?”",
    badge: "Same request",
  },
  {
    mode: "window",
    label: "New information since the last run",
    hint: "Digests and monitoring of files, connectors or the web — each run covers what's new.",
    badge: "What's new",
  },
  {
    mode: "ask",
    label: "Different input each run — ask me",
    hint: "When only you have the input (today's notes, a new document). Each run opens the chat and waits for you.",
    badge: "Asks you",
  },
  {
    mode: "list",
    label: "The next item from a list",
    hint: "Rotate through topics, patients or sites — one item per run, then start over.",
    badge: "List",
  },
];

export function inputModeOption(mode: InputMode): InputModeOption {
  return (
    INPUT_MODE_OPTIONS.find((o) => o.mode === mode) ?? INPUT_MODE_OPTIONS[0]!
  );
}

/** The default message for a mode ("" = the user must write one). */
export function defaultMessageFor(
  mode: InputMode,
  starterMessage?: string | null
): string {
  if (mode === "window") return DEFAULT_WINDOW_MESSAGE;
  if (mode === "list") return DEFAULT_LIST_MESSAGE;
  if (mode === "fixed") return starterMessage?.trim() ?? "";
  return "";
}

/** True when the message differs from the mode's default (drives the "Customize" toggle). */
export function isCustomMessage(mode: InputMode, message: string): boolean {
  if (mode === "window") return message.trim() !== DEFAULT_WINDOW_MESSAGE;
  if (mode === "list") return message.trim() !== DEFAULT_LIST_MESSAGE;
  return true;
}

/** "one item per line" text -> items (trimmed, blanks dropped). */
export function parseItems(text: string): string[] {
  return text
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter((l) => l.length > 0);
}

export function hasItemPlaceholder(message: string): boolean {
  return /\{\{\s*item\s*\}\}/.test(message);
}

/** Client-side validation; null = valid. Mirrors the backend rules. */
export function validateInputs(
  mode: InputMode,
  message: string,
  itemsText: string
): string | null {
  if (mode === "fixed" && !message.trim())
    return "Write the request the workflow should receive on every run.";
  if (mode === "list") {
    const items = parseItems(itemsText);
    if (items.length === 0) return "Add at least one item (one per line).";
    if (items.length > MAX_LIST_ITEMS)
      return `At most ${MAX_LIST_ITEMS} items.`;
    if (!hasItemPlaceholder(message || DEFAULT_LIST_MESSAGE))
      return "The message must contain {{item}} where each item goes.";
  }
  return null;
}

export function defaultAskPrompt(workflowName: string): string {
  return `Your scheduled run of “${workflowName}” is ready. Send the input for this run below to start it.`;
}

/** One-line description of what a schedule sends, for lists and cards. */
export function inputSummary(
  s: Pick<
    PulseSchedule,
    | "input_mode"
    | "input_message"
    | "input_prompt"
    | "input_items"
    | "workflow_name"
  >
): string {
  switch (s.input_mode) {
    case "ask":
      return s.input_prompt || "Asks you for the input on each run";
    case "list": {
      const n = s.input_items?.length ?? 0;
      return `${n} item${n === 1 ? "" : "s"} · ${s.input_message}`;
    }
    default:
      return s.input_message;
  }
}
