/**
 * Status semantics for schedules and runs (labels + tones). UI components map
 * tones to `--status-*` / accent tokens.
 */

import type {
  PulseDisabledReason,
  PulseRunStatus,
  PulseSchedule,
} from "@/lib/schedules/interfaces";

export type StatusTone =
  | "success"
  | "error"
  | "warning"
  | "info"
  | "muted"
  | "accent";

export const RUN_STATUS_META: Record<
  PulseRunStatus,
  { label: string; tone: StatusTone }
> = {
  pending: { label: "Queued", tone: "accent" },
  running: { label: "Running", tone: "accent" },
  succeeded: { label: "Succeeded", tone: "success" },
  needs_input: { label: "Needs input", tone: "info" },
  failed: { label: "Failed", tone: "error" },
  timed_out: { label: "Timed out", tone: "error" },
  cancelled: { label: "Cancelled", tone: "muted" },
  interrupted: { label: "Interrupted", tone: "warning" },
  skipped: { label: "Skipped", tone: "muted" },
  missed: { label: "Missed", tone: "muted" },
};

export const ACTIVE_RUN_STATUSES: ReadonlySet<PulseRunStatus> =
  new Set<PulseRunStatus>(["pending", "running"]);

const FAILED_RUN_STATUSES: ReadonlySet<PulseRunStatus> =
  new Set<PulseRunStatus>(["failed", "timed_out", "interrupted"]);

export const DISABLED_REASON_META: Record<
  PulseDisabledReason,
  { label: string; tone: StatusTone; explanation: string }
> = {
  auto_paused_failures: {
    label: "Auto-paused",
    tone: "warning",
    explanation: "Paused after 5 failed runs in a row.",
  },
  access_revoked: {
    label: "Access revoked",
    tone: "error",
    explanation: "Paused because you no longer have access to this workflow.",
  },
  workflow_deleted: {
    label: "Workflow deleted",
    tone: "error",
    explanation: "The workflow this schedule runs was deleted.",
  },
  completed_once: {
    label: "Completed",
    tone: "muted",
    explanation: "This one-time schedule has already run.",
  },
  invalid_schedule: {
    label: "Invalid",
    tone: "error",
    explanation:
      "The timing of this schedule is no longer valid. Edit it to fix.",
  },
};

export function isFailedRunStatus(s: PulseRunStatus | null | undefined) {
  return !!s && FAILED_RUN_STATUSES.has(s);
}

export function needsAttention(
  s: Pick<PulseSchedule, "disabled_reason" | "last_run_status">
): boolean {
  const reason = s.disabled_reason;
  if (reason && reason !== "completed_once") return true;
  return (
    isFailedRunStatus(s.last_run_status) || s.last_run_status === "needs_input"
  );
}

export type ScheduleDot = "ok" | "error" | "warning" | "muted" | "running";

/** Sidebar status dot for a schedule row. */
export function scheduleDot(s: {
  enabled: boolean;
  disabled_reason: PulseDisabledReason | null;
  last_run_status: PulseRunStatus | null;
}): ScheduleDot {
  if (s.last_run_status && ACTIVE_RUN_STATUSES.has(s.last_run_status))
    return "running";
  if (s.disabled_reason && s.disabled_reason !== "completed_once") {
    return DISABLED_REASON_META[s.disabled_reason].tone === "error"
      ? "error"
      : "warning";
  }
  if (!s.enabled) return "muted";
  if (s.last_run_status === "needs_input") return "warning";
  if (isFailedRunStatus(s.last_run_status)) return "error";
  if (s.last_run_status === "succeeded") return "ok";
  return "muted";
}
