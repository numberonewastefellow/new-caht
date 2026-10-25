"use client";

import React from "react";
import { cn } from "@/lib/utils";
import Text from "@/refresh-components/texts/Text";
import InputTypeIn from "@/refresh-components/inputs/InputTypeIn";
import InputNumber from "@/refresh-components/inputs/InputNumber";
import InputSelect from "@/refresh-components/inputs/InputSelect";
import { SvgAlertTriangle } from "@opal/icons";
import {
  DAY_NAMES,
  FrequencyPreset,
  FrequencyState,
  MonthDay,
  WEEK_ORDER,
} from "@/lib/schedules/cron";
import { ACCENT, ACCENT_GLOW_STRONG } from "@/sections/schedules/StatusPill";

interface PresetOption {
  key: FrequencyPreset;
  label: string;
}

/** Segmented control options; "Every N min" covers both interval presets. */
const PRESET_OPTIONS: PresetOption[] = [
  { key: "everyNMinutes", label: "Every N min" },
  { key: "hourly", label: "Hourly" },
  { key: "daily", label: "Daily" },
  { key: "weekdays", label: "Weekdays" },
  { key: "weekly", label: "Weekly" },
  { key: "monthly", label: "Monthly" },
  { key: "once", label: "Once" },
  { key: "custom", label: "Custom cron" },
];

const CRON_EXAMPLES = ["*/15 * * * *", "0 9 * * 1-5", "30 8 1 * *"];

function ordinal(n: number): string {
  const s = ["th", "st", "nd", "rd"];
  const v = n % 100;
  return `${n}${s[(v - 20) % 10] || s[v] || s[0]}`;
}

export interface FrequencyPickerProps {
  value: FrequencyState;
  onChange: (next: FrequencyState) => void;
  /** Minimum interval in seconds (from /pulse/config). */
  minIntervalSeconds?: number;
  /** Error for the custom cron input (from /pulse/preview). */
  cronError?: string | null;
}

function TimeInput({
  value,
  onChange,
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="w-[8rem]">
      <InputTypeIn
        type="time"
        aria-label="Time"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        showClearButton={false}
      />
    </div>
  );
}

function Label({ children }: { children: string }) {
  return (
    <Text as="span" mainUiBody text04>
      {children}
    </Text>
  );
}

export default function FrequencyPicker({
  value,
  onChange,
  minIntervalSeconds = 300,
  cronError,
}: FrequencyPickerProps) {
  const set = (patch: Partial<FrequencyState>) =>
    onChange({ ...value, ...patch });
  const isInterval =
    value.preset === "everyNMinutes" || value.preset === "everyNHours";
  const minMinutes = Math.max(1, Math.ceil(minIntervalSeconds / 60));

  function selectPreset(key: FrequencyPreset) {
    if (key === "everyNMinutes" && isInterval) return; // keep current unit
    set({ preset: key });
  }

  function toggleDay(day: number) {
    const has = value.weekdays.includes(day);
    set({
      weekdays: has
        ? value.weekdays.filter((d) => d !== day)
        : [...value.weekdays, day],
    });
  }

  let box: React.ReactNode = null;
  switch (value.preset) {
    case "everyNMinutes":
    case "everyNHours":
      box = (
        <>
          <Label>Every</Label>
          <div className="w-[7rem]">
            <InputNumber
              value={value.everyN}
              min={1}
              onChange={(n) => set({ everyN: n })}
            />
          </div>
          <div className="w-[8rem]">
            <InputSelect
              value={value.preset === "everyNHours" ? "hours" : "minutes"}
              onValueChange={(v) =>
                set({ preset: v === "hours" ? "everyNHours" : "everyNMinutes" })
              }
            >
              <InputSelect.Trigger />
              <InputSelect.Content>
                <InputSelect.Item value="minutes">minutes</InputSelect.Item>
                <InputSelect.Item value="hours">hours</InputSelect.Item>
              </InputSelect.Content>
            </InputSelect>
          </div>
          <Text as="p" secondaryBody text02 className="w-full">
            {`Counted from when you save. The shortest interval is ${minMinutes} minute${
              minMinutes === 1 ? "" : "s"
            }.`}
          </Text>
        </>
      );
      break;
    case "hourly":
      box = (
        <>
          <Label>At minute</Label>
          <div className="w-[7rem]">
            <InputNumber
              value={value.minute}
              min={0}
              max={59}
              onChange={(n) => set({ minute: n })}
            />
          </div>
          <Label>past every hour</Label>
        </>
      );
      break;
    case "daily":
      box = (
        <>
          <Label>Every day at</Label>
          <TimeInput value={value.time} onChange={(time) => set({ time })} />
        </>
      );
      break;
    case "weekdays":
      box = (
        <>
          <Label>Monday to Friday at</Label>
          <TimeInput value={value.time} onChange={(time) => set({ time })} />
        </>
      );
      break;
    case "weekly":
      box = (
        <>
          <div
            className="flex gap-1"
            role="group"
            aria-label="Days of the week"
          >
            {WEEK_ORDER.map((d) => {
              const on = value.weekdays.includes(d);
              return (
                <button
                  key={d}
                  type="button"
                  aria-pressed={on}
                  title={DAY_NAMES[d]}
                  onClick={() => toggleDay(d)}
                  className={cn(
                    "w-[34px] h-[34px] rounded-full border text-xs font-semibold transition-colors",
                    on
                      ? "text-text-inverted-05"
                      : "border-border-01 bg-background-tint-00 text-text-03 hover:text-text-05"
                  )}
                  style={
                    on
                      ? { backgroundColor: ACCENT, borderColor: ACCENT }
                      : undefined
                  }
                >
                  {DAY_NAMES[d].charAt(0)}
                </button>
              );
            })}
          </div>
          <Label>at</Label>
          <TimeInput value={value.time} onChange={(time) => set({ time })} />
        </>
      );
      break;
    case "monthly":
      box = (
        <>
          <Label>On the</Label>
          <div className="w-[8rem]">
            <InputSelect
              value={String(value.monthDay)}
              onValueChange={(v) =>
                set({ monthDay: (v === "L" ? "L" : Number(v)) as MonthDay })
              }
            >
              <InputSelect.Trigger />
              <InputSelect.Content>
                {Array.from({ length: 28 }, (_, i) => i + 1).map((d) => (
                  <InputSelect.Item key={d} value={String(d)}>
                    {ordinal(d)}
                  </InputSelect.Item>
                ))}
                <InputSelect.Item value="L">Last day</InputSelect.Item>
              </InputSelect.Content>
            </InputSelect>
          </div>
          <Label>of every month at</Label>
          <TimeInput value={value.time} onChange={(time) => set({ time })} />
        </>
      );
      break;
    case "once":
      box = (
        <>
          <Label>On</Label>
          <div className="w-[10rem]">
            <InputTypeIn
              type="date"
              aria-label="Date"
              value={value.onceDate}
              onChange={(e) => set({ onceDate: e.target.value })}
              showClearButton={false}
            />
          </div>
          <Label>at</Label>
          <div className="w-[8rem]">
            <InputTypeIn
              type="time"
              aria-label="Time"
              value={value.onceTime}
              onChange={(e) => set({ onceTime: e.target.value })}
              showClearButton={false}
            />
          </div>
          <Text as="p" secondaryBody text02 className="w-full">
            The schedule turns itself off after this run.
          </Text>
        </>
      );
      break;
    case "custom":
      box = (
        <div className="w-full flex flex-col gap-1">
          <InputTypeIn
            aria-label="Cron expression"
            aria-invalid={!!cronError}
            variant={cronError ? "error" : "primary"}
            value={value.cron}
            onChange={(e) => set({ cron: e.target.value })}
            spellCheck={false}
            autoComplete="off"
            placeholder="0 9 * * 1-5"
            className="font-mono"
            showClearButton={false}
          />
          <div className="grid grid-cols-5 px-2">
            {["min", "hour", "day", "month", "weekday"].map((p) => (
              <Text
                key={p}
                as="span"
                secondaryBody
                text02
                className="uppercase tracking-wide text-[11px]"
              >
                {p}
              </Text>
            ))}
          </div>
          {cronError && (
            <div
              role="alert"
              className="flex items-center gap-1.5 text-xs"
              style={{ color: "var(--status-text-error-05)" }}
            >
              <SvgAlertTriangle className="w-3.5 h-3.5 stroke-current" />
              {cronError}
            </div>
          )}
          <div className="flex items-center gap-1.5 flex-wrap pt-1">
            <Text as="span" secondaryBody text03>
              Examples:
            </Text>
            {CRON_EXAMPLES.map((ex) => (
              <button
                key={ex}
                type="button"
                onClick={() => set({ cron: ex })}
                className="font-mono text-xs px-1.5 py-px rounded-04 bg-background-tint-03 text-text-04 hover:bg-background-tint-04"
              >
                {ex}
              </button>
            ))}
          </div>
        </div>
      );
      break;
  }

  return (
    <div className="flex flex-col gap-2.5 w-full">
      <div
        role="radiogroup"
        aria-label="Frequency"
        className="grid grid-cols-4 gap-[3px] p-[3px] rounded-08 bg-background-tint-02"
      >
        {PRESET_OPTIONS.map((opt) => {
          const on =
            opt.key === "everyNMinutes" ? isInterval : value.preset === opt.key;
          return (
            <button
              key={opt.key}
              type="button"
              role="radio"
              aria-checked={on}
              onClick={() => selectPreset(opt.key)}
              className={cn(
                "h-8 rounded-08 text-[13px] whitespace-nowrap transition-colors",
                on
                  ? "bg-background-tint-00 text-text-05 font-semibold"
                  : "text-text-03 hover:text-text-05"
              )}
              style={
                on
                  ? {
                      boxShadow: `0 1px 2px var(--shadow-02), 0 0 0 1px ${ACCENT_GLOW_STRONG}`,
                    }
                  : undefined
              }
            >
              {opt.label}
            </button>
          );
        })}
      </div>
      <div className="flex items-center flex-wrap gap-2 p-3 rounded-08 border border-border-01 bg-background-tint-01 min-h-[62px]">
        {box}
      </div>
    </div>
  );
}
