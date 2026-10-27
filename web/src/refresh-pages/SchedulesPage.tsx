"use client";

import React, { useMemo, useState } from "react";
import Link from "next/link";
import type { Route } from "next";
import { useRouter, useSearchParams } from "next/navigation";
import * as SettingsLayouts from "@/layouts/settings-layouts";
import Button from "@/refresh-components/buttons/Button";
import Text from "@/refresh-components/texts/Text";
import { Card } from "@/refresh-components/cards";
import InputTypeIn from "@/refresh-components/inputs/InputTypeIn";
import Switch from "@/refresh-components/inputs/Switch";
import SimpleTooltip from "@/refresh-components/SimpleTooltip";
import { useCreateModal } from "@/refresh-components/contexts/ModalContext";
import {
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";
import { useSchedules, usePulseStats } from "@/hooks/useSchedules";
import type { PulseSchedule } from "@/lib/schedules/interfaces";
import { needsAttention } from "@/lib/schedules/status";
import { formatAbsolute, formatRelative } from "@/lib/schedules/format";
import { chatHref, scheduleHref } from "@/lib/schedules/api";
import {
  SvgClock,
  SvgExternalLink,
  SvgInfoSmall,
  SvgPlus,
  SvgSparkle,
  SvgZap,
} from "@opal/icons";
import ScheduleModal, {
  ScheduleTemplate,
} from "@/sections/schedules/ScheduleModal";
import ScheduleActionsMenu from "@/sections/schedules/ScheduleActionsMenu";
import Th from "@/sections/schedules/Th";
import DeleteScheduleModal from "@/sections/schedules/DeleteScheduleModal";
import EmptySchedules from "@/sections/schedules/EmptySchedules";
import { inputModeOption, inputSummary } from "@/lib/schedules/inputModes";
import {
  ACCENT,
  AccentIconTile,
  RunStatusGlyph,
  ScheduleStateBadge,
} from "@/sections/schedules/StatusPill";
import {
  duplicateWithToast,
  runNowWithToast,
  setEnabledWithToast,
} from "@/sections/schedules/scheduleActions";

type FilterKey = "all" | "active" | "paused" | "attention";

const FILTERS: { key: FilterKey; label: string }[] = [
  { key: "all", label: "All" },
  { key: "active", label: "Active" },
  { key: "paused", label: "Paused" },
  { key: "attention", label: "Needs attention" },
];

function inFilter(s: PulseSchedule, f: FilterKey): boolean {
  if (f === "active") return s.enabled;
  if (f === "paused") return !s.enabled;
  if (f === "attention") return needsAttention(s);
  return true;
}

type ModalState =
  | { mode: "create"; template?: ScheduleTemplate | null }
  | { mode: "edit"; schedule: PulseSchedule };

function SchedulesHero({
  onNew,
  children,
}: {
  onNew: () => void;
  children?: React.ReactNode;
}) {
  return (
    <div className="w-full bg-background-tint-01 px-4 pt-10 pb-5 border-b border-border-01">
      <div className="flex flex-col gap-5">
        <div className="flex flex-row justify-between items-start gap-4">
          <div className="flex items-start gap-3 min-w-0">
            <AccentIconTile icon={SvgClock} />
            <div className="flex flex-col min-w-0">
              <Text as="p" headingH1 className="virtualai-gradient-text">
                Schedules
              </Text>
              <div className="flex items-center gap-1 flex-wrap">
                <Text as="span" secondaryBody text03>
                  Run workflows automatically — powered by
                </Text>
                <span
                  className="inline-flex items-center gap-0.5 font-semibold text-xs"
                  style={{ color: ACCENT }}
                >
                  <SvgZap className="w-3 h-3 stroke-current" />
                  Pulse
                </span>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <Button leftIcon={SvgPlus} onClick={onNew}>
              New schedule
            </Button>
          </div>
        </div>
        {children}
      </div>
    </div>
  );
}

function KpiTile({
  value,
  label,
  color,
}: {
  value: number | string;
  label: string;
  color?: string;
}) {
  return (
    <Card padding={1}>
      <div className="flex flex-col w-full">
        <div
          className="text-[1.75rem] leading-none font-bold tabular-nums"
          style={{ color: color ?? "var(--text-05)" }}
        >
          {value}
        </div>
        <Text
          secondaryBody
          text03
          className="text-xs pt-1.5 uppercase tracking-wide"
        >
          {label}
        </Text>
      </div>
    </Card>
  );
}

function NextRunCell({ schedule }: { schedule: PulseSchedule }) {
  if (!schedule.enabled || !schedule.next_run_at) {
    return (
      <div className="flex flex-col">
        <Text as="span" secondaryBody text02>
          —
        </Text>
        <Text as="span" secondaryBody text02 className="text-xs">
          {schedule.disabled_reason === "completed_once" ? "Done" : "Paused"}
        </Text>
      </div>
    );
  }
  return (
    <SimpleTooltip
      side="top"
      tooltip={`${formatAbsolute(schedule.next_run_at, schedule.timezone)} · ${
        schedule.timezone
      }`}
    >
      <span className="text-text-05 text-sm cursor-default">
        {formatRelative(schedule.next_run_at)}
      </span>
    </SimpleTooltip>
  );
}

function LastRunCell({ schedule }: { schedule: PulseSchedule }) {
  const status = schedule.last_run?.status ?? schedule.last_run_status;
  const at =
    schedule.last_run?.finished_at ??
    schedule.last_run?.started_at ??
    schedule.last_run_at;
  const chatId =
    schedule.last_run?.chat_session_id ?? schedule.latest_chat_session_id;
  if (!status) {
    return (
      <Text as="span" secondaryBody text02>
        Never run
      </Text>
    );
  }
  return (
    <div className="flex flex-col gap-0.5">
      <div className="flex items-center gap-1.5 text-sm text-text-04">
        <RunStatusGlyph status={status} />
        <span>{formatRelative(at)}</span>
      </div>
      {chatId && (
        <Link
          href={chatHref(chatId) as Route}
          className="inline-flex items-center gap-0.5 text-[12.5px] font-medium hover:underline w-fit"
          style={{ color: ACCENT }}
        >
          Open chat
          <SvgExternalLink className="w-3 h-3 stroke-current" />
        </Link>
      )}
    </div>
  );
}

export default function SchedulesPage() {
  const router = useRouter();
  const { schedules, isLoading, error } = useSchedules();
  const { stats } = usePulseStats();
  const [filter, setFilter] = useState<FilterKey>("all");
  const [query, setQuery] = useState("");
  const [modal, setModal] = useState<ModalState | null>(null);
  const deleteModal = useCreateModal();
  const [toDelete, setToDelete] = useState<PulseSchedule | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const searchParams = useSearchParams();
  // Deep link from the sidebar "+" button: /app/schedules?new=1
  const wantsNew = searchParams?.get("new") === "1";
  const activeModal: ModalState | null =
    modal ?? (wantsNew ? { mode: "create" } : null);

  function closeModal() {
    setModal(null);
    if (wantsNew) router.replace("/app/schedules" as Route);
  }

  const counts = useMemo(() => {
    const c: Record<FilterKey, number> = {
      all: 0,
      active: 0,
      paused: 0,
      attention: 0,
    };
    for (const s of schedules)
      for (const f of FILTERS) if (inFilter(s, f.key)) c[f.key]++;
    return c;
  }, [schedules]);

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    return schedules.filter(
      (s) =>
        inFilter(s, filter) &&
        (!q || `${s.name} ${s.workflow_name ?? ""}`.toLowerCase().includes(q))
    );
  }, [schedules, filter, query]);

  async function toggleEnabled(s: PulseSchedule, enabled: boolean) {
    setBusyId(s.id);
    await setEnabledWithToast(s, enabled);
    setBusyId(null);
  }

  const isEmpty = !isLoading && !error && schedules.length === 0;

  return (
    <>
      <deleteModal.Provider>
        {toDelete && (
          <DeleteScheduleModal
            schedule={toDelete}
            onClose={() => {
              setToDelete(null);
              deleteModal.toggle(false);
            }}
          />
        )}
      </deleteModal.Provider>

      {activeModal && (
        <ScheduleModal
          onClose={closeModal}
          schedule={activeModal.mode === "edit" ? activeModal.schedule : null}
          template={activeModal.mode === "create" ? activeModal.template : null}
        />
      )}

      <SettingsLayouts.Root width="lg">
        <SchedulesHero onNew={() => setModal({ mode: "create" })}>
          {!isEmpty && (
            <>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <KpiTile
                  value={stats?.active_schedules ?? counts.active}
                  label="Active"
                  color={ACCENT}
                />
                <KpiTile
                  value={stats?.paused_schedules ?? counts.paused}
                  label="Paused"
                />
                <KpiTile
                  value={stats?.runs_last_24h ?? "—"}
                  label="Runs · 24 h"
                />
                <KpiTile
                  value={stats?.failed_last_24h ?? "—"}
                  label="Failed · 24 h"
                  color={
                    stats && stats.failed_last_24h > 0
                      ? "var(--status-text-error-05)"
                      : undefined
                  }
                />
              </div>

              <div className="flex items-center gap-2 flex-wrap">
                <div
                  className="flex items-center gap-2 flex-wrap"
                  role="tablist"
                  aria-label="Filter schedules"
                >
                  {FILTERS.map((f) => {
                    const active = filter === f.key;
                    return (
                      <button
                        key={f.key}
                        type="button"
                        role="tab"
                        aria-selected={active}
                        onClick={() => setFilter(f.key)}
                        className={cn(
                          "inline-flex items-center gap-1.5 h-[30px] px-3 rounded-full text-[12.5px] font-medium border transition-colors",
                          active
                            ? "text-text-inverted-05"
                            : "bg-background-tint-02 text-text-03 border-border-01 hover:text-text-05"
                        )}
                        style={
                          active
                            ? { backgroundColor: ACCENT, borderColor: ACCENT }
                            : undefined
                        }
                      >
                        {f.label}
                        <span className="text-[11px] opacity-75">
                          {counts[f.key]}
                        </span>
                      </button>
                    );
                  })}
                </div>
                <div className="ml-auto w-full sm:w-[18rem]">
                  <InputTypeIn
                    leftSearchIcon
                    placeholder="Search schedules or workflows…"
                    aria-label="Search schedules"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                  />
                </div>
              </div>
            </>
          )}
        </SchedulesHero>

        <SettingsLayouts.Body>
          {isLoading ? (
            <div className="flex flex-col gap-2">
              {[1, 2, 3].map((i) => (
                <Card key={i} padding={1}>
                  <div className="h-12 w-full animate-pulse bg-background-tint-02 rounded-08" />
                </Card>
              ))}
            </div>
          ) : error ? (
            <Card padding={1}>
              <Text as="p" mainUiBody text03>
                Couldn&apos;t load schedules. Try again in a moment.
              </Text>
            </Card>
          ) : isEmpty ? (
            <EmptySchedules
              onUseTemplate={(template) =>
                setModal({ mode: "create", template })
              }
            />
          ) : (
            <div className="flex flex-col gap-3">
              <div className="rounded-12 border border-border-01 bg-background-tint-00 shadow-[0_1px_2px_var(--shadow-01)] overflow-hidden">
                <Table className="table-fixed">
                  <TableHeader>
                    <TableRow
                      noHover
                      className="border-border-01 bg-background-tint-01"
                    >
                      <Th>Name / workflow</Th>
                      <Th className="w-[13rem]">Frequency</Th>
                      <Th className="w-[7rem]">Next run</Th>
                      <Th className="w-[9.5rem]">Last run</Th>
                      <Th className="w-[5.5rem] text-center">Enabled</Th>
                      <Th className="w-[3.5rem]" />
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {rows.length === 0 ? (
                      <TableRow noHover>
                        <TableCell colSpan={6} className="text-center py-7">
                          <Text as="span" mainUiBody text03>
                            No schedules match these filters.
                          </Text>
                        </TableCell>
                      </TableRow>
                    ) : (
                      rows.map((s) => (
                        <TableRow
                          key={s.id}
                          noHover
                          className="border-border-01 hover:bg-background-tint-01"
                        >
                          <TableCell className="py-3">
                            <div className="flex items-center gap-1.5 flex-wrap min-w-0">
                              <Link
                                href={scheduleHref(s.id) as Route}
                                className="text-text-05 font-medium hover:underline truncate"
                              >
                                {s.name}
                              </Link>
                              <ScheduleStateBadge schedule={s} />
                            </div>
                            <div className="flex items-center gap-1 pt-0.5 min-w-0">
                              <SvgSparkle
                                className="w-3 h-3 flex-shrink-0"
                                style={{ stroke: ACCENT }}
                              />
                              <Text
                                as="span"
                                secondaryBody
                                text03
                                className="truncate"
                              >
                                {s.workflow_name ??
                                  `Workflow #${s.workflow_id}`}
                              </Text>
                              {s.owner_email && (
                                <Text
                                  as="span"
                                  secondaryBody
                                  text02
                                  className="truncate"
                                >
                                  {`· ${s.owner_email}`}
                                </Text>
                              )}
                            </div>
                            {/* What each run sends — empty for other users' schedules */}
                            {(s.input_message || s.input_mode !== "fixed") &&
                              !s.owner_email && (
                                <div
                                  className="pt-0.5 min-w-0 max-w-[26rem]"
                                  title={inputSummary(s)}
                                >
                                  <Text
                                    as="span"
                                    secondaryBody
                                    text02
                                    className="truncate block"
                                  >
                                    {`${
                                      inputModeOption(s.input_mode).badge
                                    }: ${inputSummary(s)}`}
                                  </Text>
                                </div>
                              )}
                          </TableCell>
                          <TableCell className="py-3">
                            <Text as="p" mainUiBody text04 className="truncate">
                              {s.description.replace(` (${s.timezone})`, "")}
                            </Text>
                            <Text
                              as="p"
                              secondaryBody
                              text03
                              className="truncate"
                            >
                              {s.timezone}
                            </Text>
                          </TableCell>
                          <TableCell className="py-3">
                            <NextRunCell schedule={s} />
                          </TableCell>
                          <TableCell className="py-3">
                            <LastRunCell schedule={s} />
                          </TableCell>
                          <TableCell className="py-3 text-center">
                            <div className="inline-flex">
                              <Switch
                                checked={s.enabled}
                                disabled={
                                  busyId === s.id ||
                                  s.disabled_reason === "workflow_deleted"
                                }
                                aria-label={`Enable ${s.name}`}
                                onCheckedChange={(v) => toggleEnabled(s, v)}
                              />
                            </div>
                          </TableCell>
                          <TableCell className="py-3 text-right">
                            <ScheduleActionsMenu
                              onRunNow={() => runNowWithToast(s)}
                              onEdit={() =>
                                setModal({ mode: "edit", schedule: s })
                              }
                              onDuplicate={() => duplicateWithToast(s)}
                              onViewRuns={() =>
                                router.push(scheduleHref(s.id) as Route)
                              }
                              onDelete={() => {
                                setToDelete(s);
                                deleteModal.toggle(true);
                              }}
                            />
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </div>
              <div className="flex items-center gap-1.5">
                <SvgInfoSmall className="w-4 h-4 stroke-text-02" />
                <Text as="p" secondaryBody text02>
                  Times are shown in each schedule&apos;s timezone. Each run
                  happens in the background and opens as its own chat.
                </Text>
              </div>
            </div>
          )}
        </SettingsLayouts.Body>
      </SettingsLayouts.Root>
    </>
  );
}
