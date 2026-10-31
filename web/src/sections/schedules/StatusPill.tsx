"use client";

import React from "react";
import type { IconProps } from "@opal/types";
import { cn } from "@/lib/utils";
import {
  SvgAlertTriangle,
  SvgCheck,
  SvgCheckCircle,
  SvgClock,
  SvgHourglass,
  SvgMinusCircle,
  SvgPauseCircle,
  SvgPlayCircle,
  SvgLink,
  SvgQuestionMarkSmall,
  SvgSlash,
  SvgX,
  SvgXCircle,
} from "@opal/icons";
import type {
  PulseRunStatus,
  PulseRunFiredBy,
  PulseSchedule,
} from "@/lib/schedules/interfaces";
import {
  DISABLED_REASON_META,
  RUN_STATUS_META,
  ScheduleDot,
  StatusTone,
} from "@/lib/schedules/status";
import SimpleTooltip from "@/refresh-components/SimpleTooltip";

export const ACCENT = "var(--virtualai-accent, var(--theme-primary-05))";
export const ACCENT_SUBTLE =
  "var(--virtualai-accent-subtle, var(--background-tint-02))";
export const ACCENT_GLOW = "var(--virtualai-accent-glow, var(--border-01))";
export const ACCENT_GLOW_STRONG =
  "var(--virtualai-accent-glow-strong, var(--border-02))";

export const TONE_STYLE: Record<StatusTone, React.CSSProperties> = {
  success: {
    backgroundColor: "var(--status-success-01)",
    color: "var(--status-text-success-05)",
  },
  error: {
    backgroundColor: "var(--status-error-01)",
    color: "var(--status-text-error-05)",
  },
  warning: {
    backgroundColor: "var(--status-warning-01)",
    color: "var(--status-text-warning-05)",
  },
  info: {
    backgroundColor: "var(--status-info-01)",
    color: "var(--status-text-info-05)",
  },
  muted: {
    backgroundColor: "var(--background-tint-02)",
    color: "var(--text-03)",
  },
  accent: {
    backgroundColor: ACCENT_SUBTLE,
    color: ACCENT,
    boxShadow: `inset 0 0 0 1px ${ACCENT_GLOW}`,
  },
};

export const TONE_TEXT_COLOR: Record<StatusTone, string> = {
  success: "var(--status-text-success-05)",
  error: "var(--status-text-error-05)",
  warning: "var(--status-text-warning-05)",
  info: "var(--status-text-info-05)",
  muted: "var(--text-03)",
  accent: ACCENT,
};

const RUN_STATUS_ICON: Record<
  PulseRunStatus,
  React.FunctionComponent<IconProps> | "spinner"
> = {
  pending: "spinner",
  running: "spinner",
  succeeded: SvgCheck,
  needs_input: SvgQuestionMarkSmall,
  failed: SvgX,
  timed_out: SvgHourglass,
  cancelled: SvgSlash,
  interrupted: SvgSlash,
  skipped: SvgPlayCircle,
  missed: SvgMinusCircle,
};

export function Spinner({ className }: { className?: string }) {
  return (
    <span
      aria-hidden
      className={cn(
        "inline-block w-[11px] h-[11px] rounded-full border-2 border-current border-r-transparent animate-spin flex-shrink-0",
        className
      )}
    />
  );
}

interface PillProps {
  tone: StatusTone;
  icon?: React.FunctionComponent<IconProps> | "spinner";
  label: string;
  tooltip?: string;
}

export function Pill({ tone, icon: Icon, label, tooltip }: PillProps) {
  const pill = (
    <span
      className="inline-flex items-center gap-1 h-[22px] px-2 rounded-full text-xs font-medium whitespace-nowrap"
      style={TONE_STYLE[tone]}
    >
      {Icon === "spinner" ? (
        <Spinner />
      ) : Icon ? (
        <Icon className="w-3 h-3 stroke-current" />
      ) : null}
      {label}
    </span>
  );
  if (!tooltip) return pill;
  return (
    <SimpleTooltip tooltip={tooltip} side="top">
      {pill}
    </SimpleTooltip>
  );
}

export interface RunStatusPillProps {
  status: PulseRunStatus;
  suffix?: string;
  tooltip?: string;
}

export function RunStatusPill({ status, suffix, tooltip }: RunStatusPillProps) {
  const meta = RUN_STATUS_META[status] ?? {
    label: status,
    tone: "muted" as StatusTone,
  };
  return (
    <Pill
      tone={meta.tone}
      icon={RUN_STATUS_ICON[status]}
      label={suffix ? `${meta.label} · ${suffix}` : meta.label}
      tooltip={tooltip}
    />
  );
}

/** Small icon for the "Last run" column. */
const RUN_STATUS_GLYPH: Partial<
  Record<PulseRunStatus, React.FunctionComponent<IconProps>>
> = {
  succeeded: SvgCheckCircle,
  failed: SvgXCircle,
  timed_out: SvgXCircle,
  interrupted: SvgSlash,
  needs_input: SvgQuestionMarkSmall,
  skipped: SvgMinusCircle,
  missed: SvgMinusCircle,
  cancelled: SvgSlash,
};

export function RunStatusGlyph({ status }: { status: PulseRunStatus }) {
  const meta = RUN_STATUS_META[status];
  const Icon = RUN_STATUS_GLYPH[status];
  return (
    <SimpleTooltip tooltip={meta?.label ?? status} side="top">
      <span
        className="inline-flex items-center justify-center"
        style={{ color: TONE_TEXT_COLOR[meta?.tone ?? "muted"] }}
      >
        {Icon ? <Icon className="w-4 h-4 stroke-current" /> : <Spinner />}
      </span>
    </SimpleTooltip>
  );
}

/**
 * Badge describing why a schedule is not running normally
 * (auto-paused, access revoked, paused, needs input). Null when healthy.
 */
export function ScheduleStateBadge({
  schedule,
  showActive = false,
}: {
  schedule: Pick<
    PulseSchedule,
    "enabled" | "disabled_reason" | "last_run_status" | "consecutive_failures"
  >;
  showActive?: boolean;
}) {
  const reason = schedule.disabled_reason;
  if (reason) {
    const meta = DISABLED_REASON_META[reason];
    return (
      <Pill
        tone={meta.tone}
        icon={
          reason === "auto_paused_failures" ? SvgPauseCircle : SvgAlertTriangle
        }
        label={meta.label}
        tooltip={meta.explanation}
      />
    );
  }
  if (!schedule.enabled)
    return <Pill tone="muted" icon={SvgPauseCircle} label="Paused" />;
  if (schedule.last_run_status === "needs_input")
    return (
      <Pill
        tone="info"
        icon={SvgQuestionMarkSmall}
        label="Needs input"
        tooltip="The last run is waiting for your reply"
      />
    );
  if (showActive) return <ActivePill />;
  return null;
}

function ActivePill() {
  return (
    <span
      className="inline-flex items-center gap-1.5 h-[22px] px-2 rounded-full text-xs font-medium"
      style={TONE_STYLE.success}
    >
      <span
        className="w-1.5 h-1.5 rounded-full"
        style={{ backgroundColor: "var(--status-success-05)" }}
      />
      Active
    </span>
  );
}

const DOT_COLOR: Record<ScheduleDot, string> = {
  ok: "var(--status-success-05)",
  error: "var(--status-error-05)",
  warning: "var(--status-warning-05)",
  muted: "var(--border-03)",
  running: ACCENT,
};

export function StatusDot({ dot }: { dot: ScheduleDot }) {
  return (
    <span
      aria-hidden
      className={cn(
        "w-2 h-2 rounded-full flex-shrink-0",
        dot === "running" && "animate-pulse"
      )}
      style={{ backgroundColor: DOT_COLOR[dot] }}
    />
  );
}

export function FiredByTag({ firedBy }: { firedBy: PulseRunFiredBy }) {
  const Icon = firedBy === "manual" ? SvgPlayCircle : firedBy === "webhook" ? SvgLink : SvgClock;
  return (
    <span className="inline-flex items-center gap-1 text-xs px-1.5 py-px rounded-04 border border-border-01 text-text-03 bg-background-tint-01">
      <Icon className="w-3 h-3 stroke-current" />
      {firedBy === "manual" ? "Manual" : firedBy === "webhook" ? "Webhook" : "Scheduled"}
    </span>
  );
}

/**
 * 16px accent-tinted clock badge (IconProps-compatible) marking chats that were
 * created by a scheduled run, e.g. in the sidebar's chat list.
 */
export function ScheduledRunBadgeIcon(_props: IconProps) {
  return (
    <span
      aria-label="Scheduled run"
      className="inline-flex items-center justify-center w-4 h-4 rounded-04 flex-shrink-0"
      style={{
        backgroundColor: ACCENT_SUBTLE,
        boxShadow: `inset 0 0 0 1px ${ACCENT_GLOW}`,
      }}
    >
      <SvgClock className="w-3 h-3" style={{ stroke: ACCENT }} />
    </span>
  );
}

/** Accent-tinted square icon container used in headers / templates. */
export function AccentIconTile({
  icon: Icon,
  size = 48,
  iconSize = 24,
  glow = true,
}: {
  icon: React.FunctionComponent<IconProps>;
  size?: number;
  iconSize?: number;
  glow?: boolean;
}) {
  return (
    <div
      className="rounded-12 flex items-center justify-center flex-shrink-0"
      style={{
        width: size,
        height: size,
        backgroundColor: ACCENT_SUBTLE,
        boxShadow: glow
          ? `0 0 0 1px ${ACCENT_GLOW}, 0 8px 24px ${ACCENT_GLOW}`
          : `0 0 0 1px ${ACCENT_GLOW}`,
      }}
    >
      <Icon style={{ stroke: ACCENT, width: iconSize, height: iconSize }} />
    </div>
  );
}
