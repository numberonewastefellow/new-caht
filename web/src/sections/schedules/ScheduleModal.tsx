"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import type { Route } from "next";
import Modal, { BasicModalFooter } from "@/refresh-components/Modal";
import Button from "@/refresh-components/buttons/Button";
import Text from "@/refresh-components/texts/Text";
import InputTypeIn from "@/refresh-components/inputs/InputTypeIn";
import InputTextArea from "@/refresh-components/inputs/InputTextArea";
import InputSelect from "@/refresh-components/inputs/InputSelect";
import InputNumber from "@/refresh-components/inputs/InputNumber";
import SimpleTooltip from "@/refresh-components/SimpleTooltip";
import { toast } from "@/hooks/useToast";
import { useWorkflows } from "@/hooks/useWorkflows";
import { useAgents } from "@/hooks/useAgents";
import { usePulseConfig } from "@/hooks/useSchedules";
import { cn } from "@/lib/utils";
import {
  SvgAlertTriangle,
  SvgChevronRight,
  SvgClock,
  SvgInfoSmall,
  SvgPlayCircle,
  SvgSparkle,
  SvgZap,
} from "@opal/icons";
import type {
  PulsePreviewResponse,
  PulseSchedule,
  ScheduleSpec,
} from "@/lib/schedules/interfaces";
import {
  defaultFrequencyState,
  FrequencyState,
  presetSentence,
  presetToSpec,
  specToPreset,
  utcIsoToZonedWallTime,
} from "@/lib/schedules/cron";
import {
  browserTimeZone,
  formatRelative,
  formatRunTime,
  timezoneOptions,
} from "@/lib/schedules/format";
import {
  chatHref,
  createSchedule,
  previewSchedule,
  refreshPulse,
  runScheduleNow,
  scheduleHref,
  updateSchedule,
  waitForRunChat,
} from "@/lib/schedules/api";
import FrequencyPicker from "@/sections/schedules/FrequencyPicker";
import {
  ACCENT,
  ACCENT_GLOW,
  ACCENT_GLOW_STRONG,
  ACCENT_SUBTLE,
  Spinner,
} from "@/sections/schedules/StatusPill";

const DEFAULT_VARIABLES = ["date", "now", "window_start", "window_end"];

const VARIABLE_HELP: Record<string, string> = {
  date: "Run date, e.g. 2026-10-27",
  now: "Exact run date and time",
  window_start: "When the last successful run was scheduled",
  window_end: "When this run is scheduled",
};

const DEFAULT_MESSAGE =
  "Run for {{date}}. Only include what changed since {{window_start}}.";

/** Prefill used by the empty-state templates and entry points. */
export interface ScheduleTemplate {
  frequency?: Partial<FrequencyState>;
  message?: string;
  /** Pick the first workflow whose name contains this (case-insensitive). */
  workflowNameHint?: string;
}

export interface ScheduleModalProps {
  onClose: () => void;
  /** Existing schedule => edit mode. */
  schedule?: PulseSchedule | null;
  /** Prefill the workflow (entry points from workflow cards). */
  initialWorkflowId?: number | null;
  template?: ScheduleTemplate | null;
  onSaved?: (schedule: PulseSchedule) => void;
}

type PreviewState =
  | { status: "idle" | "loading" }
  | { status: "ok"; data: PulsePreviewResponse }
  | { status: "error"; error: string };

function lowerFirst(s: string) {
  return s ? s.charAt(0).toLowerCase() + s.slice(1) : s;
}

function tzAbbrev(iso: string, timeZone: string): string {
  try {
    const part = new Intl.DateTimeFormat("en-US", {
      timeZone,
      timeZoneName: "short",
    })
      .formatToParts(new Date(iso))
      .find((p) => p.type === "timeZoneName");
    return part?.value ?? "";
  } catch {
    return "";
  }
}

function fmtVar(iso: string, timeZone: string, withTime: boolean): string {
  const wall = utcIsoToZonedWallTime(iso, timeZone);
  if (!wall) return iso;
  if (!withTime) return wall.date;
  return `${wall.date} ${wall.time} ${tzAbbrev(iso, timeZone)}`.trim();
}

/** Did the timing of an existing schedule change? (decides whether to PATCH it) */
function timingChanged(schedule: PulseSchedule, spec: ScheduleSpec): boolean {
  if (schedule.schedule_type !== spec.schedule_type) return true;
  if (schedule.timezone !== spec.timezone) return true;
  if (spec.schedule_type === "cron")
    return (
      (schedule.cron_expression ?? "").trim().replace(/\s+/g, " ") !==
      (spec.cron_expression ?? "")
    );
  if (spec.schedule_type === "interval")
    return schedule.interval_seconds !== spec.interval_seconds;
  const a = schedule.run_at ? new Date(schedule.run_at).getTime() : NaN;
  const b = spec.run_at ? new Date(spec.run_at).getTime() : NaN;
  return a !== b;
}

function MessagePreview({
  message,
  firstRun,
  secondRun,
  intervalSeconds,
  timezone,
  knownVariables,
}: {
  message: string;
  firstRun: string;
  secondRun: string | null;
  intervalSeconds: number | null;
  timezone: string;
  knownVariables: string[];
}) {
  const periodMs = intervalSeconds
    ? intervalSeconds * 1000
    : secondRun
      ? new Date(secondRun).getTime() - new Date(firstRun).getTime()
      : null;
  const windowStart =
    periodMs != null
      ? fmtVar(
          new Date(new Date(firstRun).getTime() - periodMs).toISOString(),
          timezone,
          true
        )
      : "the beginning";
  const values: Record<string, string> = {
    date: fmtVar(firstRun, timezone, false),
    now: fmtVar(firstRun, timezone, true),
    window_start: windowStart,
    window_end: fmtVar(firstRun, timezone, true),
  };

  const parts: React.ReactNode[] = [];
  const re = /\{\{\s*([a-zA-Z_]+)\s*\}\}/g;
  let last = 0;
  let m: RegExpExecArray | null;
  let i = 0;
  while ((m = re.exec(message))) {
    if (m.index > last) parts.push(message.slice(last, m.index));
    const key = m[1]!;
    if (knownVariables.includes(key) && key in values) {
      parts.push(
        <mark
          key={i++}
          className="rounded-04 px-0.5"
          style={{
            backgroundColor: ACCENT_SUBTLE,
            color: ACCENT,
            boxShadow: `inset 0 0 0 1px ${ACCENT_GLOW}`,
          }}
        >
          {values[key]}
        </mark>
      );
    } else {
      parts.push(
        <span
          key={i++}
          title="Unknown variable — it will be sent as typed"
          className="underline decoration-wavy"
          style={{ color: "var(--status-text-error-05)" }}
        >
          {m[0]}
        </span>
      );
    }
    last = m.index + m[0].length;
  }
  if (last < message.length) parts.push(message.slice(last));

  return (
    <div className="text-[12.5px] leading-normal text-text-04 bg-background-tint-00 border border-border-01 rounded-08 px-2.5 py-2 break-words whitespace-pre-wrap">
      {parts.length ? parts : <span className="text-text-02">No message</span>}
    </div>
  );
}

function FieldLabel({
  children,
  htmlFor,
}: {
  children: string;
  htmlFor?: string;
}) {
  return (
    <label htmlFor={htmlFor} className="block pb-1.5">
      <Text as="span" mainUiAction text05>
        {children}
      </Text>
    </label>
  );
}

function SectionLabel({ children }: { children: string }) {
  return (
    <Text
      as="p"
      secondaryAction
      text03
      className="uppercase tracking-wide text-[11.5px]"
    >
      {children}
    </Text>
  );
}

export default function ScheduleModal({
  onClose,
  schedule,
  initialWorkflowId,
  template,
  onSaved,
}: ScheduleModalProps) {
  const router = useRouter();
  const isEdit = !!schedule;
  const { workflows, isLoading: workflowsLoading } = useWorkflows();
  const { agents, isLoading: agentsLoading } = useAgents();
  const { config } = usePulseConfig();

  const [workflowId, setWorkflowId] = useState<number | null>(
    schedule?.workflow_id ?? initialWorkflowId ?? null
  );
  const [name, setName] = useState(schedule?.name ?? "");
  const [nameDirty, setNameDirty] = useState(isEdit);
  const [message, setMessage] = useState(
    schedule?.input_message ?? template?.message ?? ""
  );
  const [messageDirty, setMessageDirty] = useState(
    isEdit || !!template?.message
  );
  const [freq, setFreq] = useState<FrequencyState>(() =>
    schedule
      ? specToPreset(schedule)
      : { ...defaultFrequencyState(), ...(template?.frequency ?? {}) }
  );
  const [timezone, setTimezone] = useState(
    schedule?.timezone ?? browserTimeZone()
  );
  const [retention, setRetention] = useState<number | null>(
    schedule?.retention_count ?? null
  );
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [saving, setSaving] = useState<"save" | "run" | null>(null);
  const [preview, setPreview] = useState<PreviewState>({ status: "idle" });

  const messageRef = useRef<HTMLTextAreaElement | null>(null);
  const messageTouched = useRef(false);
  const unmounted = useRef(false);
  useEffect(() => {
    // Reset on (re)mount: React StrictMode runs mount -> cleanup -> mount in dev,
    // which would otherwise leave this stuck at `true` and the modal hung on
    // "Starting run…".
    unmounted.current = false;
    return () => {
      unmounted.current = true;
    };
  }, []);

  const variables = config?.template_variables ?? DEFAULT_VARIABLES;
  const minInterval = config?.min_interval_seconds ?? 300;
  const maxRetention = config?.max_retention ?? 500;
  const retentionValue = retention ?? config?.default_retention ?? 50;

  const starterFor = (wfId: number | null): string | null => {
    if (wfId == null) return null;
    const agent = agents.find((a) => a.workflow_id === wfId);
    const starter = agent?.starter_messages?.find((s) => !!s.message?.trim());
    return starter?.message ?? null;
  };

  // Resolve the default workflow once the list is available (create mode).
  useEffect(() => {
    if (workflowId != null || workflowsLoading || workflows.length === 0)
      return;
    const hint = template?.workflowNameHint?.toLowerCase();
    const match = hint
      ? workflows.find((w) => w.name.toLowerCase().includes(hint))
      : undefined;
    setWorkflowId((match ?? workflows[0]!).id);
  }, [workflowId, workflowsLoading, workflows, template?.workflowNameHint]);

  // Pre-fill the message from the workflow's starter message (create mode).
  useEffect(() => {
    if (messageDirty || message !== "" || workflowId == null || agentsLoading)
      return;
    setMessage(starterFor(workflowId) ?? DEFAULT_MESSAGE);
  }, [workflowId, agentsLoading, messageDirty, message]);

  const workflow = workflows.find((w) => w.id === workflowId) ?? null;
  const workflowName = workflow?.name ?? schedule?.workflow_name ?? "";

  const specResult = useMemo(
    () => presetToSpec(freq, timezone),
    [freq, timezone]
  );
  const specKey = JSON.stringify(specResult);

  const autoName = workflowName
    ? `${workflowName} — ${lowerFirst(presetSentence(freq))}`
    : "";
  const displayName = nameDirty ? name : autoName;

  // Live preview (debounced) via POST /pulse/preview.
  useEffect(() => {
    if (specResult.error !== null) {
      setPreview({ status: "error", error: specResult.error });
      return;
    }
    const controller = new AbortController();
    setPreview((p) => (p.status === "ok" ? p : { status: "loading" }));
    const t = setTimeout(async () => {
      try {
        const data = await previewSchedule(specResult.spec, controller.signal);
        if (controller.signal.aborted) return;
        setPreview(
          data.valid
            ? { status: "ok", data }
            : { status: "error", error: data.error ?? "Invalid frequency." }
        );
      } catch (e) {
        if (controller.signal.aborted) return;
        setPreview({
          status: "error",
          error:
            e instanceof Error ? e.message : "Couldn't check this frequency.",
        });
      }
    }, 300);
    return () => {
      clearTimeout(t);
      controller.abort();
    };
  }, [specKey]);

  const timingDirty =
    !schedule ||
    specResult.spec === null ||
    timingChanged(schedule, specResult.spec);
  const previewError = preview.status === "error" ? preview.error : null;
  const tzOptions = useMemo(() => timezoneOptions(timezone), [timezone]);
  const browserTz = browserTimeZone();

  function insertVariable(v: string) {
    const token = `{{${v}}}`;
    const ta = messageRef.current;
    const touched = messageTouched.current && !!ta;
    const start = touched ? ta!.selectionStart : message.length;
    const end = touched ? ta!.selectionEnd : message.length;
    const before = message.slice(0, start);
    const ins = (before.length > 0 && !/\s$/.test(before) ? " " : "") + token;
    const next = before + ins + message.slice(end);
    setMessage(next);
    setMessageDirty(true);
    requestAnimationFrame(() => {
      if (!ta) return;
      ta.focus();
      const pos = start + ins.length;
      ta.setSelectionRange(pos, pos);
    });
  }

  function handleWorkflowChange(value: string) {
    const id = Number(value);
    setWorkflowId(id);
    if (!messageDirty) setMessage(starterFor(id) ?? DEFAULT_MESSAGE);
  }

  async function save(runNow: boolean) {
    if (workflowId == null) {
      toast.error("Pick a workflow to schedule");
      return;
    }
    if (!message.trim()) {
      toast.error("Add the message to send to the workflow");
      return;
    }
    if (timingDirty && (specResult.spec === null || previewError)) {
      toast.error("Fix the frequency before saving");
      return;
    }
    const finalName = (displayName.trim() || workflowName || "Schedule").slice(
      0,
      200
    );

    setSaving(runNow ? "run" : "save");
    try {
      let saved: PulseSchedule;
      const spec = specResult.spec;
      const timing: Partial<ScheduleSpec> =
        spec && timingDirty
          ? {
              schedule_type: spec.schedule_type,
              cron_expression: spec.cron_expression ?? null,
              interval_seconds: spec.interval_seconds ?? null,
              run_at: spec.run_at ?? null,
              timezone: spec.timezone,
            }
          : {};
      if (schedule) {
        saved = await updateSchedule(schedule.id, {
          name: finalName,
          input_message: message,
          retention_count: retentionValue,
          ...timing,
        });
      } else {
        saved = await createSchedule({
          workflow_id: workflowId,
          name: finalName,
          input_message: message,
          enabled: true,
          retention_count: retentionValue,
          ...(timing as ScheduleSpec),
        });
      }
      void refreshPulse();
      onSaved?.(saved);

      if (!runNow) {
        const next = saved.next_run_at
          ? ` · next run ${formatRelative(saved.next_run_at)}`
          : "";
        toast.success(
          `${isEdit ? "Saved changes to" : "Created"} “${saved.name}”${next}`
        );
        onClose();
        return;
      }

      // The schedule is saved at this point: if the run can't start (409/429),
      // don't leave the modal open (a second click would create a duplicate).
      let run;
      try {
        run = await runScheduleNow(saved.id);
      } catch (e) {
        void refreshPulse();
        toast.error(
          `“${saved.name}” was saved, but the run didn't start: ${
            e instanceof Error ? e.message : "unknown error"
          }`
        );
        onClose();
        router.push(scheduleHref(saved.id) as Route);
        return;
      }
      void refreshPulse();
      toast.success(`“${saved.name}” saved — first run started`);
      const chatId = await waitForRunChat(run.id, {
        shouldStop: () => unmounted.current,
      });
      if (unmounted.current) return;
      onClose();
      router.push(
        (chatId ? chatHref(chatId) : scheduleHref(saved.id)) as Route
      );
    } catch (e) {
      toast.error(
        e instanceof Error ? e.message : "Couldn't save the schedule"
      );
    } finally {
      if (!unmounted.current) setSaving(null);
    }
  }

  const nextRuns = preview.status === "ok" ? preview.data.next_runs : [];

  return (
    <Modal open onOpenChange={(open) => !open && onClose()}>
      <Modal.Content width="md" height="lg">
        <Modal.Header
          icon={SvgClock}
          title={isEdit ? "Edit schedule" : "New schedule"}
          description="Pulse runs the workflow in the background. Each run becomes its own chat."
          onClose={onClose}
        />
        <Modal.Body twoTone={false}>
          <div className="w-full grid grid-cols-1 md:grid-cols-[minmax(0,1fr)_18rem] gap-5">
            {/* ── Form ─────────────────────────────────────────── */}
            <div className="flex flex-col gap-5 min-w-0">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <FieldLabel>Workflow</FieldLabel>
                  <InputSelect
                    value={workflowId != null ? String(workflowId) : ""}
                    onValueChange={handleWorkflowChange}
                    disabled={isEdit}
                  >
                    <InputSelect.Trigger
                      placeholder={
                        workflowsLoading
                          ? "Loading workflows…"
                          : "Pick a workflow"
                      }
                    />
                    <InputSelect.Content>
                      {workflows.map((w) => (
                        <InputSelect.Item key={w.id} value={String(w.id)}>
                          {w.name}
                        </InputSelect.Item>
                      ))}
                      {schedule &&
                        !workflows.some(
                          (w) => w.id === schedule.workflow_id
                        ) && (
                          <InputSelect.Item
                            value={String(schedule.workflow_id)}
                          >
                            {schedule.workflow_name ??
                              `Workflow #${schedule.workflow_id}`}
                          </InputSelect.Item>
                        )}
                    </InputSelect.Content>
                  </InputSelect>
                  {isEdit && (
                    <Text as="p" secondaryBody text02 className="pt-1.5">
                      To run a different workflow, create a new schedule.
                    </Text>
                  )}
                </div>
                <div>
                  <FieldLabel htmlFor="schedule-name">Name</FieldLabel>
                  <InputTypeIn
                    id="schedule-name"
                    value={displayName}
                    placeholder="Name this schedule"
                    onChange={(e) => {
                      setNameDirty(true);
                      setName(e.target.value);
                    }}
                    maxLength={200}
                  />
                  {!nameDirty && (
                    <div className="flex items-center gap-1 pt-1.5">
                      <SvgSparkle
                        className="w-3 h-3"
                        style={{ stroke: ACCENT }}
                      />
                      <Text as="span" secondaryBody text03>
                        Filled in for you. Edit it to use your own name.
                      </Text>
                    </div>
                  )}
                </div>
              </div>

              <div>
                <FieldLabel htmlFor="schedule-message">
                  Message sent to the workflow
                </FieldLabel>
                <InputTextArea
                  id="schedule-message"
                  ref={messageRef}
                  rows={3}
                  value={message}
                  onFocus={() => {
                    messageTouched.current = true;
                  }}
                  onChange={(e) => {
                    setMessage(e.target.value);
                    setMessageDirty(true);
                  }}
                  maxLength={20000}
                />
                <div className="flex items-center gap-1.5 flex-wrap pt-2">
                  <Text as="span" secondaryBody text03>
                    Insert:
                  </Text>
                  {variables.map((v) => (
                    <SimpleTooltip
                      key={v}
                      tooltip={VARIABLE_HELP[v] ?? v}
                      side="top"
                    >
                      <button
                        type="button"
                        onClick={() => insertVariable(v)}
                        className="font-mono text-xs h-6 px-2 rounded-full border transition-colors hover:brightness-95"
                        style={{
                          borderColor: ACCENT_GLOW_STRONG,
                          backgroundColor: ACCENT_SUBTLE,
                          color: ACCENT,
                        }}
                      >
                        {`{{${v}}}`}
                      </button>
                    </SimpleTooltip>
                  ))}
                </div>
              </div>

              <div>
                <FieldLabel>Frequency</FieldLabel>
                <FrequencyPicker
                  value={freq}
                  onChange={setFreq}
                  minIntervalSeconds={minInterval}
                  cronError={freq.preset === "custom" ? previewError : null}
                />
              </div>

              <div>
                <FieldLabel>Timezone</FieldLabel>
                <InputSelect value={timezone} onValueChange={setTimezone}>
                  <InputSelect.Trigger />
                  <InputSelect.Content>
                    {tzOptions.map((tz) => (
                      <InputSelect.Item key={tz} value={tz}>
                        {tz === browserTz ? `${tz} (browser)` : tz}
                      </InputSelect.Item>
                    ))}
                  </InputSelect.Content>
                </InputSelect>
              </div>

              <div className="border border-border-01 rounded-08">
                <button
                  type="button"
                  aria-expanded={advancedOpen}
                  onClick={() => setAdvancedOpen((o) => !o)}
                  className="w-full flex items-center gap-1.5 px-3 py-2.5 text-left"
                >
                  <SvgChevronRight
                    className={cn(
                      "w-3.5 h-3.5 stroke-text-03 transition-transform",
                      advancedOpen && "rotate-90"
                    )}
                  />
                  <Text as="span" mainUiAction text05>
                    Advanced
                  </Text>
                </button>
                {advancedOpen && (
                  <div className="px-3 pb-3 flex flex-col gap-2.5">
                    <div className="flex items-center gap-2 flex-wrap">
                      <Text as="span" mainUiBody text04>
                        Keep the last
                      </Text>
                      <div className="w-[7rem]">
                        <InputNumber
                          value={retentionValue}
                          min={1}
                          max={maxRetention}
                          onChange={setRetention}
                        />
                      </div>
                      <Text as="span" mainUiBody text04>
                        run chats
                      </Text>
                      <Text as="span" secondaryBody text02>
                        (chats you replied to or shared are always kept)
                      </Text>
                    </div>
                    <div className="flex items-start gap-1.5 rounded-08 bg-background-tint-02 px-2.5 py-2">
                      <SvgInfoSmall className="w-4 h-4 stroke-text-03 flex-shrink-0" />
                      <Text as="p" secondaryBody text03>
                        If the previous run is still going, the new run is
                        skipped. After 5 failed runs in a row the schedule
                        pauses itself until you resume it.
                      </Text>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* ── Preview ──────────────────────────────────────── */}
            <aside className="flex flex-col gap-4 min-w-0">
              <div
                aria-live="polite"
                className="rounded-12 border p-3.5 bg-background-tint-00"
                style={
                  preview.status === "error"
                    ? {
                        borderColor: "var(--status-error-05)",
                        boxShadow: "0 0 0 3px var(--status-error-01)",
                      }
                    : {
                        borderColor: "var(--border-01)",
                        boxShadow: `0 0 0 3px ${ACCENT_SUBTLE}`,
                      }
                }
              >
                <SectionLabel>Preview</SectionLabel>
                <div className="flex items-start gap-1.5 pt-1 pb-3">
                  {preview.status === "error" ? (
                    <>
                      <SvgAlertTriangle
                        className="w-4 h-4 flex-shrink-0 mt-0.5 stroke-current"
                        style={{ color: "var(--status-text-error-05)" }}
                      />
                      <Text
                        as="p"
                        mainUiAction
                        style={{ color: "var(--status-text-error-05)" }}
                      >
                        {preview.error}
                      </Text>
                    </>
                  ) : preview.status === "ok" ? (
                    <Text as="p" mainContentEmphasis text05>
                      {preview.data.description ?? presetSentence(freq)}
                    </Text>
                  ) : (
                    <div className="flex items-center gap-2 text-text-03">
                      <Spinner />
                      <Text as="span" secondaryBody text03>
                        Checking…
                      </Text>
                    </div>
                  )}
                </div>
                <SectionLabel>
                  {freq.preset === "once" ? "Runs once" : "Next 5 runs"}
                </SectionLabel>
                <ul className="pt-1.5">
                  {preview.status === "error" ? (
                    <li className="py-1.5 border-t border-dashed border-border-01">
                      <Text as="span" secondaryBody text03>
                        No upcoming runs until this is fixed.
                      </Text>
                    </li>
                  ) : (
                    nextRuns.map((iso) => (
                      <li
                        key={iso}
                        className="flex justify-between gap-2 py-1.5 border-t border-dashed border-border-01 text-[13px] tabular-nums text-text-04"
                      >
                        <span>{formatRunTime(iso, timezone)}</span>
                        <span className="text-text-03">
                          {formatRelative(iso)}
                        </span>
                      </li>
                    ))
                  )}
                </ul>
                {timezone !== browserTz && preview.status === "ok" && (
                  <Text as="p" secondaryBody text02 className="pt-1">
                    {`Times shown in ${timezone}.`}
                  </Text>
                )}
              </div>

              <div className="flex flex-col gap-1.5">
                <SectionLabel>First run will send</SectionLabel>
                {preview.status === "ok" && nextRuns[0] ? (
                  <MessagePreview
                    message={message}
                    firstRun={nextRuns[0]}
                    secondRun={nextRuns[1] ?? null}
                    intervalSeconds={
                      specResult.spec?.schedule_type === "interval"
                        ? specResult.spec.interval_seconds ?? null
                        : null
                    }
                    timezone={timezone}
                    knownVariables={variables}
                  />
                ) : (
                  <Text as="p" secondaryBody text02>
                    Fix the frequency to preview the message.
                  </Text>
                )}
              </div>
            </aside>
          </div>
        </Modal.Body>
        <Modal.Footer>
          <BasicModalFooter
            left={
              <span className="inline-flex items-center gap-1 text-xs text-text-02">
                <SvgZap className="w-3 h-3 stroke-current" />
                Pulse
              </span>
            }
            cancel={
              <Button tertiary onClick={onClose} disabled={saving !== null}>
                Cancel
              </Button>
            }
            submit={
              <>
                <Button
                  secondary
                  leftIcon={saving === "run" ? undefined : SvgPlayCircle}
                  onClick={() => save(true)}
                  disabled={saving !== null}
                >
                  {saving === "run" ? "Starting run…" : "Save & run now"}
                </Button>
                <Button onClick={() => save(false)} disabled={saving !== null}>
                  {saving === "save"
                    ? "Saving…"
                    : isEdit
                      ? "Save changes"
                      : "Save"}
                </Button>
              </>
            }
          />
        </Modal.Footer>
      </Modal.Content>
    </Modal>
  );
}
