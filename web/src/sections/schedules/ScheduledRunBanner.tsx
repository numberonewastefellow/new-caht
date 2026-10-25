"use client";

import Link from "next/link";
import type { Route } from "next";
import { useSchedule, useScheduleRuns } from "@/hooks/useSchedules";
import { scheduleHref } from "@/lib/schedules/api";
import { formatDurationMs, formatRunTime } from "@/lib/schedules/format";
import { SvgArrowRight, SvgClock } from "@opal/icons";
import {
  ACCENT,
  ACCENT_GLOW_STRONG,
  ACCENT_SUBTLE,
  RunStatusPill,
} from "@/sections/schedules/StatusPill";

export interface ScheduledRunBannerProps {
  chatSessionId: string | null;
  pulseScheduleId: number | null | undefined;
}

/**
 * Slim banner above the messages of a chat created by a scheduled run:
 * "⏱ Scheduled run of '<name>' · <time> · View schedule".
 */
export default function ScheduledRunBanner({
  chatSessionId,
  pulseScheduleId,
}: ScheduledRunBannerProps) {
  const id = pulseScheduleId ?? null;
  const { schedule, error } = useSchedule(id);
  const { runs } = useScheduleRuns(id);
  if (id == null) return null;

  const run = chatSessionId
    ? runs.find((r) => r.chat_session_id === chatSessionId)
    : undefined;
  const deleted = !!error && !schedule;
  const suffix =
    run?.duration_ms != null ? formatDurationMs(run.duration_ms) : undefined;

  return (
    <div className="w-full max-w-[var(--app-page-main-content-width)] px-4 pt-2 flex-shrink-0">
      <div
        className="flex items-center gap-2.5 rounded-12 border px-3.5 py-2.5 text-[13.5px] text-text-04"
        style={{
          backgroundColor: ACCENT_SUBTLE,
          borderColor: ACCENT_GLOW_STRONG,
        }}
      >
        <SvgClock
          className="w-[18px] h-[18px] flex-shrink-0"
          style={{ stroke: ACCENT }}
        />
        <div className="flex-1 min-w-0 truncate">
          <span className="font-semibold text-text-05">Scheduled run</span>
          {schedule ? (
            <>
              {" of “"}
              {schedule.name}
              {"”"}
            </>
          ) : deleted ? (
            " · the schedule was deleted"
          ) : null}
          {run && <> · {formatRunTime(run.scheduled_for)}</>}
          {schedule && (
            <>
              {" · "}
              <Link
                href={scheduleHref(schedule.id) as Route}
                className="inline-flex items-center gap-0.5 font-medium hover:underline"
                style={{ color: ACCENT }}
              >
                View schedule
                <SvgArrowRight className="w-3 h-3 stroke-current" />
              </Link>
            </>
          )}
        </div>
        {run && <RunStatusPill status={run.status} suffix={suffix} />}
      </div>
    </div>
  );
}
