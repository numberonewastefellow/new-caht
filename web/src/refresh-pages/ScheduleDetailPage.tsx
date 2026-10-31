"use client";

import React, { useMemo, useState } from "react";
import Link from "next/link";
import type { Route } from "next";
import { useRouter } from "next/navigation";
import useSWR from "swr";
import * as SettingsLayouts from "@/layouts/settings-layouts";
import Button from "@/refresh-components/buttons/Button";
import Text from "@/refresh-components/texts/Text";
import { Card } from "@/refresh-components/cards";
import Switch from "@/refresh-components/inputs/Switch";
import InputSelect from "@/refresh-components/inputs/InputSelect";
import SimpleTooltip from "@/refresh-components/SimpleTooltip";
import { useCreateModal } from "@/refresh-components/contexts/ModalContext";
import {
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useSchedule, useScheduleRuns } from "@/hooks/useSchedules";
import { useUser } from "@/providers/UserProvider";
import type {
  PulseRun,
  PulseRunStatus,
  PulseSchedule,
} from "@/lib/schedules/interfaces";
import {
  DISABLED_REASON_META,
  isFailedRunStatus,
} from "@/lib/schedules/status";
import {
  formatAbsolute,
  formatDurationMs,
  formatRelative,
  formatRunTime,
  plainTextPreview,
} from "@/lib/schedules/format";
import { chatHref, previewSchedule } from "@/lib/schedules/api";
import {
  SvgAlertTriangle,
  SvgChevronRight,
  SvgClock,
  SvgEdit,
  SvgExternalLink,
  SvgInfoSmall,
  SvgPlayCircle,
  SvgSparkle,
} from "@opal/icons";
import ScheduleModal from "@/sections/schedules/ScheduleModal";
import { defaultAskPrompt, inputModeOption } from "@/lib/schedules/inputModes";
import ScheduleActionsMenu from "@/sections/schedules/ScheduleActionsMenu";
import DeleteScheduleModal from "@/sections/schedules/DeleteScheduleModal";
import Th from "@/sections/schedules/Th";
import {
  ACCENT,
  ACCENT_GLOW_STRONG,
  ACCENT_SUBTLE,
  AccentIconTile,
  RunStatusPill,
  ScheduleStateBadge,
  FiredByTag,
} from "@/sections/schedules/StatusPill";
import {
  duplicateWithToast,
  runNowWithToast,
  setEnabledWithToast,
} from "@/sections/schedules/scheduleActions";

type RunFilter = "all" | "succeeded" | "failed" | "needs_input" | "skipped";

const RUN_FILTERS: Record<
  RunFilter,
  { label: string; match: (s: PulseRunStatus) => boolean }
> = {
  all: { label: "All statuses", match: () => true },
  succeeded: { label: "Succeeded", match: (s) => s === "succeeded" },
  failed: {
    label: "Failed",
    match: (s) => isFailedRunStatus(s) || s === "cancelled",
  },
  needs_input: { label: "Needs input", match: (s) => s === "needs_input" },
  skipped: {
    label: "Skipped / missed",
    match: (s) => s === "skipped" || s === "missed",
  },
};

/** Next fire times for the header chips. */
function useNextRuns(schedule: PulseSchedule | null): string[] {
  // Read nullable fields up front: the React Compiler memoizes the fetcher on its
  // dependencies (evaluated during render), so `schedule!.x` inside the closure
  // crashes the page while the schedule is still loading.
  const cronExpression = schedule?.cron_expression ?? "";
  const timezone = schedule?.timezone ?? "UTC";
  const cronKey =
    schedule && schedule.enabled && schedule.schedule_type === "cron"
      ? ["pulse-preview", cronExpression, timezone, schedule.updated_at]
      : null;
  const { data } = useSWR(
    cronKey,
    () =>
      previewSchedule({
        schedule_type: "cron",
        cron_expression: cronExpression,
        timezone,
      }),
    { revalidateOnFocus: false }
  );

  return useMemo(() => {
    if (!schedule || !schedule.enabled || !schedule.next_run_at) return [];
    if (schedule.schedule_type === "once") return [schedule.next_run_at];
    if (schedule.schedule_type === "interval" && schedule.interval_seconds) {
      const start = new Date(schedule.next_run_at).getTime();
      return Array.from({ length: 5 }, (_, i) =>
        new Date(start + i * schedule.interval_seconds! * 1000).toISOString()
      );
    }
    const fromPreview = data?.valid ? data.next_runs : [];
    // Make sure the server's actual next slot comes first.
    const first = schedule.next_run_at;
    const rest = fromPreview.filter(
      (iso) => new Date(iso).getTime() > new Date(first).getTime()
    );
    return [first, ...rest].slice(0, 5);
  }, [schedule, data]);
}

function Breadcrumb({ name }: { name: string }) {
  return (
    <nav
      aria-label="Breadcrumb"
      className="flex items-center gap-1 text-[13px] text-text-03"
    >
      <Link
        href={"/app/schedules" as Route}
        className="hover:text-text-05 hover:underline"
      >
        Schedules
      </Link>
      <SvgChevronRight className="w-3.5 h-3.5 stroke-text-02" />
      <span className="text-text-05 font-medium truncate">{name}</span>
    </nav>
  );
}

function StatTile({ value, label }: { value: string; label: string }) {
  return (
    <Card padding={0.75}>
      <div className="flex flex-col w-full px-1">
        <span className="text-lg font-semibold text-text-05 tabular-nums">
          {value}
        </span>
        <Text as="span" secondaryBody text03 className="text-xs">
          {label}
        </Text>
      </div>
    </Card>
  );
}

function AttentionBanner({
  schedule,
  isOwner,
  onResume,
  onEdit,
  resuming,
}: {
  schedule: PulseSchedule;
  isOwner: boolean;
  onResume: () => void;
  onEdit: () => void;
  resuming: boolean;
}) {
  const reason = schedule.disabled_reason;
  if (!reason || reason === "completed_once") return null;
  const meta = DISABLED_REASON_META[reason];
  const tone = meta.tone === "error" ? "error" : "warning";
  const lastRun = schedule.last_run;
  const headline =
    reason === "auto_paused_failures"
      ? `Paused after ${Math.max(
          schedule.consecutive_failures,
          5
        )} failed runs in a row.`
      : meta.explanation;
  const canResume =
    isOwner && reason !== "workflow_deleted" && reason !== "invalid_schedule";

  return (
    <div
      role="alert"
      className="flex items-center gap-3 flex-wrap rounded-12 px-3.5 py-3 border"
      style={{
        backgroundColor: `var(--status-${tone}-01)`,
        borderColor: `var(--status-${tone}-02)`,
      }}
    >
      <SvgAlertTriangle
        className="w-5 h-5 flex-shrink-0 stroke-current"
        style={{ color: `var(--status-text-${tone}-05)` }}
      />
      <div className="flex-1 min-w-0 text-sm text-text-04">
        <span className="font-semibold text-text-05">{headline}</span>
        {lastRun?.error && (
          <>
            {" "}
            Last error:{" "}
            <span className="font-mono text-[12.5px]">{lastRun.error}</span>
          </>
        )}
        {lastRun && <> · {formatRunTime(lastRun.scheduled_for)}</>}
      </div>
      {isOwner && lastRun?.chat_session_id && (
        <Button tertiary size="md" href={chatHref(lastRun.chat_session_id)}>
          View last run
        </Button>
      )}
      {canResume ? (
        <Button
          size="md"
          leftIcon={SvgPlayCircle}
          onClick={onResume}
          disabled={resuming}
        >
          Resume
        </Button>
      ) : isOwner && reason === "invalid_schedule" ? (
        <Button size="md" leftIcon={SvgEdit} onClick={onEdit}>
          Edit
        </Button>
      ) : null}
    </div>
  );
}

/** What each run of this schedule receives (owner only). */
function InputCard({
  schedule,
  onEdit,
}: {
  schedule: PulseSchedule;
  onEdit: () => void;
}) {
  const option = inputModeOption(schedule.input_mode);
  const items = schedule.input_items ?? [];
  const showMessage =
    schedule.input_mode === "fixed" ||
    schedule.input_mode === "window" ||
    (schedule.input_mode === "list" && schedule.input_message !== "{{item}}");
  return (
    <Card padding={1}>
      <div className="flex items-start gap-3">
        <div className="flex-1 min-w-0 flex flex-col gap-2">
          <div className="flex items-center gap-2 flex-wrap">
            <Text
              as="span"
              secondaryAction
              text03
              className="uppercase tracking-wide text-[11.5px]"
            >
              Each run receives
            </Text>
            <span
              className="inline-flex items-center h-[22px] px-2 rounded-full border text-[12px] font-medium"
              style={{
                backgroundColor: ACCENT_SUBTLE,
                borderColor: ACCENT_GLOW_STRONG,
                color: ACCENT,
              }}
            >
              {option.label}
            </span>
          </div>
          {schedule.input_mode === "ask" && (
            <Text as="p" mainUiBody text04>
              {`Asks you: “${
                schedule.input_prompt ||
                defaultAskPrompt(schedule.workflow_name ?? "this workflow")
              }”`}
            </Text>
          )}
          {schedule.input_mode === "list" && (
            <Text as="p" mainUiBody text04>
              {`${items.length} item${
                items.length === 1 ? "" : "s"
              } · next run uses “${schedule.next_item ?? items[0] ?? ""}”`}
            </Text>
          )}
          {showMessage && (
            <div className="text-[12.5px] font-mono text-text-04 bg-background-tint-00 border border-border-01 rounded-08 px-2.5 py-2 break-words whitespace-pre-wrap">
              {schedule.input_message}
            </div>
          )}
        </div>
        <Button secondary onClick={onEdit}>
          Edit
        </Button>
      </div>
    </Card>
  );
}

function RunsTable({
  runs,
  filter,
  canOpenChat,
}: {
  runs: PulseRun[];
  filter: RunFilter;
  /** Run chats belong to the owner; admins viewing others' schedules can't open them. */
  canOpenChat: boolean;
}) {
  const shown = runs.filter((r) => RUN_FILTERS[filter].match(r.status));
  return (
    <div className="rounded-12 border border-border-01 bg-background-tint-00 shadow-[0_1px_2px_var(--shadow-01)] overflow-hidden">
      <Table className="table-fixed">
        <TableHeader>
          <TableRow noHover className="border-border-01 bg-background-tint-01">
            <Th className="w-[10rem]">Scheduled for</Th>
            <Th className="w-[7.5rem]">Trigger</Th>
            <Th className="w-[9rem]">Status</Th>
            <Th className="w-[5.5rem]">Duration</Th>
            <Th>Output preview</Th>
            <Th className="w-[7rem]" />
          </TableRow>
        </TableHeader>
        <TableBody>
          {shown.length === 0 ? (
            <TableRow noHover>
              <TableCell colSpan={6} className="text-center py-7">
                <Text as="span" mainUiBody text03>
                  {runs.length === 0
                    ? "No runs yet. Use “Run now” to try it."
                    : "No runs match this filter."}
                </Text>
              </TableCell>
            </TableRow>
          ) : (
            shown.map((r) => {
              const out = plainTextPreview(
                r.output_preview || r.error || r.skip_reason || ""
              );
              return (
                <TableRow
                  key={r.id}
                  noHover
                  className="border-border-01 hover:bg-background-tint-01"
                >
                  <TableCell className="py-3 px-3.5">
                    <SimpleTooltip
                      side="top"
                      tooltip={formatAbsolute(r.scheduled_for)}
                    >
                      <span className="text-text-05 tabular-nums text-sm cursor-default">
                        {formatRunTime(r.scheduled_for)}
                      </span>
                    </SimpleTooltip>
                  </TableCell>
                  <TableCell className="py-3 px-3.5">
                    <FiredByTag firedBy={r.fired_by} />
                  </TableCell>
                  <TableCell className="py-3 px-3.5">
                    <RunStatusPill status={r.status} />
                  </TableCell>
                  <TableCell className="py-3 px-3.5 text-text-03 tabular-nums text-sm">
                    {formatDurationMs(r.duration_ms)}
                  </TableCell>
                  <TableCell className="py-3 px-3.5">
                    <div
                      className="truncate text-[13px]"
                      title={out}
                      style={{
                        color:
                          r.error && !r.output_preview
                            ? "var(--status-text-error-05)"
                            : "var(--text-03)",
                      }}
                    >
                      {out || "—"}
                    </div>
                  </TableCell>
                  <TableCell className="py-3 px-3.5 text-right">
                    {canOpenChat && r.chat_session_id ? (
                      <Link
                        href={chatHref(r.chat_session_id) as Route}
                        className="inline-flex items-center gap-0.5 text-[12.5px] font-medium hover:underline"
                        style={{ color: ACCENT }}
                      >
                        Open chat
                        <SvgExternalLink className="w-3 h-3 stroke-current" />
                      </Link>
                    ) : (
                      <SimpleTooltip side="top" tooltip="No chat was created">
                        <span className="text-text-02">—</span>
                      </SimpleTooltip>
                    )}
                  </TableCell>
                </TableRow>
              );
            })
          )}
        </TableBody>
      </Table>
    </div>
  );
}

export interface ScheduleDetailPageProps {
  scheduleId: number;
}

export default function ScheduleDetailPage({
  scheduleId,
}: ScheduleDetailPageProps) {
  const router = useRouter();
  const { user, isAdmin } = useUser();
  const validId = Number.isFinite(scheduleId) ? scheduleId : null;
  const { schedule, isLoading, error } = useSchedule(validId);
  const { runs, isLoading: runsLoading } = useScheduleRuns(validId);
  const nextRuns = useNextRuns(schedule);
  const [editing, setEditing] = useState(false);
  const [runFilter, setRunFilter] = useState<RunFilter>("all");
  const [busy, setBusy] = useState(false);
  const deleteModal = useCreateModal();

  const stats = useMemo(() => {
    const finished = runs.filter(
      (r) => !["pending", "running", "skipped", "missed"].includes(r.status)
    );
    const ok = finished.filter((r) => r.status === "succeeded").length;
    const durations = runs
      .map((r) => r.duration_ms)
      .filter((d): d is number => d != null);
    const avg = durations.length
      ? durations.reduce((a, b) => a + b, 0) / durations.length
      : null;
    return {
      rate: finished.length
        ? `${Math.round((ok / finished.length) * 100)}%`
        : "—",
      rateLabel: `Success rate · last ${finished.length} run${
        finished.length === 1 ? "" : "s"
      }`,
      avg: formatDurationMs(avg),
      total: `${runs.length}${runs.length >= 50 ? "+" : ""}`,
      withChat: runs.filter((r) => !!r.chat_session_id).length,
    };
  }, [runs]);

  if (isLoading) {
    return (
      <SettingsLayouts.Root width="lg">
        <div className="px-4 pt-10 flex flex-col gap-3">
          <div className="h-10 w-1/2 animate-pulse bg-background-tint-02 rounded-08" />
          <div className="h-40 w-full animate-pulse bg-background-tint-02 rounded-12" />
        </div>
      </SettingsLayouts.Root>
    );
  }

  if (error || !schedule) {
    return (
      <SettingsLayouts.Root width="lg">
        <div className="px-4 pt-10 flex flex-col gap-4 items-start">
          <Breadcrumb name="Not found" />
          <Card padding={1.5}>
            <Text as="p" mainUiBody text03>
              This schedule doesn&apos;t exist or you don&apos;t have access to
              it.
            </Text>
          </Card>
        </div>
      </SettingsLayouts.Root>
    );
  }

  const s = schedule;
  // Runs execute as the owner, so only the owner may run, edit, duplicate or
  // resume; an admin viewing someone else's schedule may only pause/delete it.
  const isOwner = !user || s.user_id === user.id;
  // Admins can edit / pause / resume / delete anyone's schedule (ownership never
  // changes); Run now and Duplicate stay owner-only (runs execute as the owner).
  const canEdit = isOwner || isAdmin;
  const updatedByOther = !!s.updated_by_email && s.updated_by_id !== s.user_id;

  async function toggle(enabled: boolean) {
    setBusy(true);
    await setEnabledWithToast(s, enabled);
    setBusy(false);
  }

  const created = new Date(s.created_at).toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
  });

  return (
    <>
      <deleteModal.Provider>
        <DeleteScheduleModal
          schedule={s}
          onClose={() => deleteModal.toggle(false)}
          onDeleted={() => router.push("/app/schedules" as Route)}
        />
      </deleteModal.Provider>
      {editing && (
        <ScheduleModal
          schedule={s}
          onClose={() => setEditing(false)}
          allowRunNow={isOwner}
          ownerNote={
            isOwner
              ? null
              : `You are editing ${
                  s.owner_email ?? "another user"
                }'s schedule as an admin. It stays theirs and keeps running as them; they will be notified.`
          }
        />
      )}

      <SettingsLayouts.Root width="lg">
        <div className="w-full bg-background-tint-01 px-4 pt-10 pb-5 border-b border-border-01">
          <div className="flex flex-col gap-4">
            <Breadcrumb name={s.name} />

            <div className="flex flex-row justify-between items-start gap-4 flex-wrap">
              <div className="flex items-start gap-3 min-w-0">
                <AccentIconTile icon={SvgClock} />
                <div className="min-w-0 flex flex-col gap-1">
                  <div className="flex items-center gap-2.5 flex-wrap">
                    <Text as="p" headingH2 text05>
                      {s.name}
                    </Text>
                    <ScheduleStateBadge schedule={s} showActive />
                  </div>
                  <div className="flex items-center gap-1.5 flex-wrap text-sm text-text-03">
                    <span>Runs</span>
                    <Link
                      href={"/app/workflows" as Route}
                      className="inline-flex items-center gap-1 font-medium hover:underline"
                      style={{ color: ACCENT }}
                    >
                      <SvgSparkle className="w-3.5 h-3.5 stroke-current" />
                      {s.workflow_name ?? `Workflow #${s.workflow_id}`}
                    </Link>
                    <span>·</span>
                    <span>{s.description}</span>
                    <span>·</span>
                    <span>
                      {isOwner
                        ? `Created by you on ${created}`
                        : `Owned by ${s.owner_email ?? "another user"}`}
                    </span>
                    {updatedByOther && (
                      <>
                        <span>·</span>
                        <span>{`Last updated by ${
                          s.updated_by_id === user?.id
                            ? "you"
                            : s.updated_by_email
                        }`}</span>
                      </>
                    )}
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2 flex-shrink-0">
                {isOwner && (
                  <Button
                    secondary
                    leftIcon={SvgPlayCircle}
                    onClick={() => runNowWithToast(s)}
                    disabled={s.disabled_reason === "workflow_deleted"}
                  >
                    Run now
                  </Button>
                )}
                {canEdit && (
                  <Button
                    secondary
                    leftIcon={SvgEdit}
                    onClick={() => setEditing(true)}
                  >
                    Edit
                  </Button>
                )}
                <label className="inline-flex items-center gap-2 h-9 px-3 rounded-08 border border-border-01 bg-background-tint-00 cursor-pointer">
                  <Switch
                    checked={s.enabled}
                    disabled={
                      busy ||
                      s.disabled_reason === "workflow_deleted" ||
                      !canEdit
                    }
                    aria-label="Enabled"
                    onCheckedChange={toggle}
                  />
                  <Text as="span" mainUiBody text04>
                    {s.enabled ? "Enabled" : "Paused"}
                  </Text>
                </label>
                <ScheduleActionsMenu
                  bordered
                  onDuplicate={
                    isOwner
                      ? async () => {
                          const copy = await duplicateWithToast(s);
                          if (copy)
                            router.push(`/app/schedules/${copy.id}` as Route);
                        }
                      : undefined
                  }
                  onOpenWorkflow={() => router.push("/app/workflows" as Route)}
                  onDelete={() => deleteModal.toggle(true)}
                />
              </div>
            </div>

            <div className="flex items-center gap-2.5 flex-wrap">
              <Text
                as="span"
                secondaryAction
                text03
                className="uppercase tracking-wide text-[11.5px]"
              >
                Next runs
              </Text>
              {nextRuns.length ? (
                <div className="flex gap-1.5 flex-wrap">
                  {nextRuns.map((iso, i) => (
                    <SimpleTooltip
                      key={iso}
                      side="top"
                      tooltip={formatRelative(iso)}
                    >
                      <span
                        className="h-[26px] inline-flex items-center px-2.5 rounded-full border text-[12.5px] tabular-nums"
                        style={
                          i === 0
                            ? {
                                backgroundColor: ACCENT_SUBTLE,
                                borderColor: ACCENT_GLOW_STRONG,
                                color: ACCENT,
                                fontWeight: 600,
                              }
                            : {
                                backgroundColor: "var(--background-tint-00)",
                                borderColor: "var(--border-01)",
                                color: "var(--text-04)",
                              }
                        }
                      >
                        {formatRunTime(iso, s.timezone)}
                      </span>
                    </SimpleTooltip>
                  ))}
                </div>
              ) : (
                <Text as="span" secondaryBody text02>
                  {s.enabled
                    ? "No upcoming runs."
                    : `No upcoming runs while paused.${
                        s.disabled_reason === "auto_paused_failures"
                          ? " Resume to schedule the next run."
                          : ""
                      }`}
                </Text>
              )}
            </div>

            {canEdit && (
              <InputCard schedule={s} onEdit={() => setEditing(true)} />
            )}

            <AttentionBanner
              schedule={s}
              isOwner={isOwner}
              resuming={busy}
              onResume={() => toggle(true)}
              onEdit={() => setEditing(true)}
            />

            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <StatTile value={stats.rate} label={stats.rateLabel} />
              <StatTile value={stats.avg} label="Average duration" />
              <StatTile value={stats.total} label="Recent runs" />
              <StatTile
                value={`${Math.min(stats.withChat, s.retention_count)} / ${
                  s.retention_count
                }`}
                label="Run chats kept"
              />
            </div>
          </div>
        </div>

        <SettingsLayouts.Body>
          <div className="flex flex-col gap-3">
            <div className="flex items-center gap-2.5">
              <Text as="p" headingH3 text05>
                Runs
              </Text>
              <Text as="span" secondaryBody text03>
                Newest first
              </Text>
              <div className="ml-auto w-[11rem]">
                <InputSelect
                  value={runFilter}
                  onValueChange={(v) => setRunFilter(v as RunFilter)}
                >
                  <InputSelect.Trigger />
                  <InputSelect.Content>
                    {(Object.keys(RUN_FILTERS) as RunFilter[]).map((k) => (
                      <InputSelect.Item key={k} value={k}>
                        {RUN_FILTERS[k].label}
                      </InputSelect.Item>
                    ))}
                  </InputSelect.Content>
                </InputSelect>
              </div>
            </div>
            {runsLoading ? (
              <div className="h-32 w-full animate-pulse bg-background-tint-02 rounded-12" />
            ) : (
              <RunsTable runs={runs} filter={runFilter} canOpenChat={isOwner} />
            )}
            <div className="flex items-start gap-1.5">
              <SvgInfoSmall className="w-4 h-4 stroke-text-02 flex-shrink-0" />
              <Text as="p" secondaryBody text02>
                {`Skipped and missed runs don't create a chat. Older run chats are removed after the last ${s.retention_count}, except chats you replied to or shared.`}
              </Text>
            </div>
          </div>
        </SettingsLayouts.Body>
      </SettingsLayouts.Root>
    </>
  );
}
