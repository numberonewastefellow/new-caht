/**
 * Types for "Schedules" (engine: Pulse) — scheduled workflow runs.
 * Mirrors backend/om/server/features/pulse/models.py.
 */

export type ScheduleType = "cron" | "interval" | "once";

export type PulseRunStatus =
  | "pending"
  | "running"
  | "succeeded"
  | "needs_input"
  | "failed"
  | "timed_out"
  | "cancelled"
  | "interrupted"
  | "skipped"
  | "missed";

export type PulseRunTrigger = "scheduled" | "manual";

/** Why a schedule is disabled. `null` + `enabled=false` means paused by the user. */
export type PulseDisabledReason =
  | "auto_paused_failures"
  | "access_revoked"
  | "workflow_deleted"
  | "completed_once"
  | "invalid_schedule";

export interface PulseRun {
  id: number;
  schedule_id: number;
  scheduled_for: string;
  trigger: PulseRunTrigger;
  status: PulseRunStatus;
  chat_session_id: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  duration_ms: number | null;
  output_preview: string | null;
  error: string | null;
  skip_reason: string | null;
}

export interface PulseSchedule {
  id: number;
  name: string;
  workflow_id: number;
  workflow_name: string | null;
  user_id: string;
  owner_email: string | null;
  enabled: boolean;
  schedule_type: ScheduleType;
  cron_expression: string | null;
  interval_seconds: number | null;
  run_at: string | null;
  timezone: string;
  input_message: string;
  /** Human-readable rule, e.g. "Every weekday at 09:00". */
  description: string;
  next_run_at: string | null;
  last_run_at: string | null;
  last_run_status: PulseRunStatus | null;
  consecutive_failures: number;
  disabled_reason: PulseDisabledReason | null;
  retention_count: number;
  created_at: string;
  updated_at: string;
  last_run: PulseRun | null;
  latest_chat_session_id: string | null;
}

/** The timing part of a schedule — what /pulse/preview validates. */
export interface ScheduleSpec {
  schedule_type: ScheduleType;
  cron_expression?: string | null;
  interval_seconds?: number | null;
  /** ISO 8601 */
  run_at?: string | null;
  timezone: string;
}

export interface PulseScheduleCreate extends ScheduleSpec {
  workflow_id: number;
  name: string;
  input_message: string;
  enabled: boolean;
  retention_count?: number | null;
}

export type PulseScheduleUpdate = Partial<
  Omit<PulseScheduleCreate, "workflow_id">
>;

export interface PulsePreviewResponse {
  valid: boolean;
  error: string | null;
  description: string | null;
  /** ISO strings (UTC) */
  next_runs: string[];
  cron_expression: string | null;
}

export interface PulseConfig {
  min_interval_seconds: number;
  max_schedules_per_user: number;
  max_retention: number;
  default_retention: number;
  template_variables: string[];
}

export interface PulseSidebarItem {
  schedule_id: number;
  name: string;
  enabled: boolean;
  disabled_reason: PulseDisabledReason | null;
  last_run_status: PulseRunStatus | null;
  last_run_at: string | null;
  latest_chat_session_id: string | null;
}

export interface PulseStats {
  active_schedules: number;
  paused_schedules: number;
  needs_attention: number;
  runs_last_24h: number;
  failed_last_24h: number;
}
