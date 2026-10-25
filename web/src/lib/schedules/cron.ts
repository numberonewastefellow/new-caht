/**
 * Frequency presets <-> stored schedule spec.
 *
 * The schedule modal edits a `FrequencyState` (friendly presets); the API stores a
 * `ScheduleSpec` (cron / interval / once). Everything here is pure so it can be
 * unit-tested without a DOM.
 *
 *   | Preset                      | Stored as                  |
 *   |-----------------------------|----------------------------|
 *   | everyNMinutes / everyNHours | interval (interval_seconds)|
 *   | hourly                      | cron "M * * * *"           |
 *   | daily                       | cron "M H * * *"           |
 *   | weekdays                    | cron "M H * * 1-5"         |
 *   | weekly                      | cron "M H * * d,d"         |
 *   | monthly                     | cron "M H D * *" (D = L ok)|
 *   | once                        | run_at (UTC ISO)           |
 *   | custom                      | cron (as typed)            |
 */

import type { ScheduleSpec, ScheduleType } from "@/lib/schedules/interfaces";

export type FrequencyPreset =
  | "everyNMinutes"
  | "everyNHours"
  | "hourly"
  | "daily"
  | "weekdays"
  | "weekly"
  | "monthly"
  | "once"
  | "custom";

export type MonthDay = number | "L";

export interface FrequencyState {
  preset: FrequencyPreset;
  /** N for everyNMinutes / everyNHours */
  everyN: number;
  /** Minute past the hour for `hourly` (0-59) */
  minute: number;
  /** "HH:MM" for daily / weekdays / weekly / monthly */
  time: string;
  /** Days for `weekly`; 0 = Sunday … 6 = Saturday (cron numbering) */
  weekdays: number[];
  /** Day of month for `monthly` (1-31) or "L" for the last day */
  monthDay: MonthDay;
  /** "YYYY-MM-DD" wall date for `once`, in the schedule's timezone */
  onceDate: string;
  /** "HH:MM" wall time for `once`, in the schedule's timezone */
  onceTime: string;
  /** Raw expression for `custom` */
  cron: string;
}

/** Shape of the timing fields of a stored schedule (PulseSchedule is compatible). */
export interface StoredTiming {
  schedule_type: ScheduleType | string;
  cron_expression?: string | null;
  interval_seconds?: number | null;
  run_at?: string | null;
  timezone: string;
}

export const DAY_NAMES = [
  "Sunday",
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
] as const;

/** Monday-first display order of cron day numbers. */
export const WEEK_ORDER = [1, 2, 3, 4, 5, 6, 0] as const;

/** Server cap on interval schedules (PATCH/POST return 422 above it). */
export const MAX_INTERVAL_SECONDS = 366 * 24 * 3600;

const pad2 = (n: number) => String(n).padStart(2, "0");

function isoDateLocal(d: Date): string {
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`;
}

/** Sensible defaults; `once` defaults to tomorrow at 09:00. */
export function defaultFrequencyState(now: Date = new Date()): FrequencyState {
  const tomorrow = new Date(now.getTime());
  tomorrow.setDate(tomorrow.getDate() + 1);
  return {
    preset: "daily",
    everyN: 15,
    minute: 0,
    time: "09:00",
    weekdays: [1],
    monthDay: 1,
    onceDate: isoDateLocal(tomorrow),
    onceTime: "09:00",
    cron: "0 9 * * 1-5",
  };
}

// ---------------------------------------------------------------------------
// Timezone helpers (no external tz library; uses Intl)
// ---------------------------------------------------------------------------

interface WallParts {
  year: number;
  month: number;
  day: number;
  hour: number;
  minute: number;
}

function wallPartsAt(instantMs: number, timeZone: string): WallParts {
  const fmt = new Intl.DateTimeFormat("en-US", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hourCycle: "h23",
  });
  const parts: Record<string, string> = {};
  for (const p of fmt.formatToParts(new Date(instantMs))) {
    parts[p.type] = p.value;
  }
  return {
    year: Number(parts.year),
    month: Number(parts.month),
    day: Number(parts.day),
    hour: Number(parts.hour) % 24,
    minute: Number(parts.minute),
  };
}

/** Offset (ms) of `timeZone` from UTC at the given instant. */
function tzOffsetMs(instantMs: number, timeZone: string): number {
  const p = wallPartsAt(instantMs, timeZone);
  const asUtc = Date.UTC(p.year, p.month - 1, p.day, p.hour, p.minute);
  const truncated = instantMs - (((instantMs % 60000) + 60000) % 60000);
  return asUtc - truncated;
}

/**
 * Convert a wall-clock date/time in `timeZone` to a UTC ISO string.
 * Returns null for malformed input or an unknown timezone.
 */
export function zonedWallTimeToUtcIso(
  date: string,
  time: string,
  timeZone: string
): string | null {
  const dm = /^(\d{4})-(\d{2})-(\d{2})$/.exec(date);
  const tm = /^(\d{1,2}):(\d{2})$/.exec(time);
  if (!dm || !tm) return null;
  const [y, mo, d] = [Number(dm[1]), Number(dm[2]), Number(dm[3])];
  const [h, mi] = [Number(tm[1]), Number(tm[2])];
  if (mo < 1 || mo > 12 || d < 1 || d > 31 || h > 23 || mi > 59) return null;
  try {
    const guess = Date.UTC(y, mo - 1, d, h, mi);
    const off1 = tzOffsetMs(guess, timeZone);
    let utc = guess - off1;
    const off2 = tzOffsetMs(utc, timeZone);
    if (off2 !== off1) utc = guess - off2;
    return new Date(utc).toISOString();
  } catch {
    return null;
  }
}

/** Inverse of `zonedWallTimeToUtcIso`: UTC ISO -> wall date/time in `timeZone`. */
export function utcIsoToZonedWallTime(
  iso: string,
  timeZone: string
): { date: string; time: string } | null {
  const ms = new Date(iso).getTime();
  if (Number.isNaN(ms)) return null;
  try {
    const p = wallPartsAt(ms, timeZone);
    return {
      date: `${p.year}-${pad2(p.month)}-${pad2(p.day)}`,
      time: `${pad2(p.hour)}:${pad2(p.minute)}`,
    };
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// State -> spec
// ---------------------------------------------------------------------------

function parseTime(time: string): { h: number; m: number } | null {
  const m = /^(\d{1,2}):(\d{2})$/.exec(time.trim());
  if (!m) return null;
  const h = Number(m[1]);
  const mi = Number(m[2]);
  if (h > 23 || mi > 59) return null;
  return { h, m: mi };
}

/** Collapse whitespace in a cron expression. */
export function normalizeCron(expr: string): string {
  return expr.trim().split(/\s+/).filter(Boolean).join(" ");
}

export type SpecResult =
  | { spec: ScheduleSpec; error: null }
  | { spec: null; error: string };

/**
 * Build the API spec for a preset state. Only checks what the UI can know
 * locally (shape of the inputs); the server validates the rest via /preview.
 */
export function presetToSpec(
  state: FrequencyState,
  timezone: string
): SpecResult {
  const fail = (error: string): SpecResult => ({ spec: null, error });
  const cron = (expr: string): SpecResult => ({
    spec: { schedule_type: "cron", cron_expression: expr, timezone },
    error: null,
  });

  switch (state.preset) {
    case "everyNMinutes":
    case "everyNHours": {
      const n = Math.floor(Number(state.everyN));
      if (!Number.isFinite(n) || n < 1)
        return fail("Enter a number of 1 or more.");
      const unit = state.preset === "everyNHours" ? 3600 : 60;
      if (n * unit > MAX_INTERVAL_SECONDS)
        return fail("The longest interval is 366 days.");
      return {
        spec: {
          schedule_type: "interval",
          interval_seconds: n * unit,
          timezone,
        },
        error: null,
      };
    }
    case "hourly": {
      const m = Math.floor(Number(state.minute));
      if (!Number.isFinite(m) || m < 0 || m > 59)
        return fail("Minute must be between 0 and 59.");
      return cron(`${m} * * * *`);
    }
    case "daily":
    case "weekdays":
    case "weekly":
    case "monthly": {
      const t = parseTime(state.time);
      if (!t) return fail("Pick a time.");
      if (state.preset === "daily") return cron(`${t.m} ${t.h} * * *`);
      if (state.preset === "weekdays") return cron(`${t.m} ${t.h} * * 1-5`);
      if (state.preset === "weekly") {
        const days = Array.from(
          new Set(state.weekdays.map((d) => (d === 7 ? 0 : d)))
        )
          .filter((d) => Number.isInteger(d) && d >= 0 && d <= 6)
          .sort((a, b) => a - b);
        if (days.length === 0)
          return fail("Pick at least one day of the week.");
        return cron(`${t.m} ${t.h} * * ${days.join(",")}`);
      }
      const dom = state.monthDay;
      if (dom !== "L" && (!Number.isInteger(dom) || dom < 1 || dom > 31))
        return fail("Pick a day of the month.");
      return cron(`${t.m} ${t.h} ${dom} * *`);
    }
    case "once": {
      const iso = zonedWallTimeToUtcIso(
        state.onceDate,
        state.onceTime,
        timezone
      );
      if (!iso) return fail("Pick a date and a time.");
      return {
        spec: { schedule_type: "once", run_at: iso, timezone },
        error: null,
      };
    }
    case "custom": {
      const expr = normalizeCron(state.cron);
      if (!expr) return fail("Enter a cron expression.");
      return cron(expr);
    }
  }
}

// ---------------------------------------------------------------------------
// Spec -> state
// ---------------------------------------------------------------------------

const INT = "(\\d{1,2})";

function inRange(n: number, lo: number, hi: number) {
  return Number.isInteger(n) && n >= lo && n <= hi;
}

/**
 * Map a cron expression back to a preset. Only the exact shapes the UI itself
 * generates are recognised; anything else becomes `custom` (keeping the text).
 */
export function cronToPreset(
  expr: string,
  base: FrequencyState = defaultFrequencyState()
): FrequencyState {
  const e = normalizeCron(expr);
  const custom: FrequencyState = { ...base, preset: "custom", cron: e };
  let m: RegExpExecArray | null;

  if ((m = new RegExp(`^${INT} \\* \\* \\* \\*$`).exec(e))) {
    const minute = Number(m[1]);
    if (!inRange(minute, 0, 59)) return custom;
    return { ...base, preset: "hourly", minute, cron: e };
  }

  m = new RegExp(`^${INT} ${INT} (\\S+) \\* (\\S+)$`).exec(e);
  if (!m) return custom;
  const minute = Number(m[1]);
  const hour = Number(m[2]);
  const dom = m[3]!;
  const dow = m[4]!;
  if (!inRange(minute, 0, 59) || !inRange(hour, 0, 23)) return custom;
  const time = `${pad2(hour)}:${pad2(minute)}`;

  if (dom === "*" && dow === "*")
    return { ...base, preset: "daily", time, cron: e };
  if (dom === "*" && dow === "1-5")
    return { ...base, preset: "weekdays", time, cron: e };
  if (dom === "*" && /^[0-7](,[0-7])*$/.test(dow)) {
    const days = Array.from(
      new Set(dow.split(",").map((d) => (Number(d) === 7 ? 0 : Number(d))))
    ).sort((a, b) => a - b);
    return { ...base, preset: "weekly", time, weekdays: days, cron: e };
  }
  if (dow === "*" && dom === "L")
    return { ...base, preset: "monthly", time, monthDay: "L", cron: e };
  if (dow === "*" && /^\d{1,2}$/.test(dom)) {
    const day = Number(dom);
    // The picker offers 1-28 + "last day"; keep other days as custom cron.
    if (!inRange(day, 1, 28)) return custom;
    return { ...base, preset: "monthly", time, monthDay: day, cron: e };
  }
  return custom;
}

/** Map a stored schedule back to the preset state used by the modal. */
export function specToPreset(
  timing: StoredTiming,
  now: Date = new Date()
): FrequencyState {
  const base = defaultFrequencyState(now);
  if (timing.schedule_type === "interval" && timing.interval_seconds) {
    const s = timing.interval_seconds;
    if (s % 3600 === 0)
      return { ...base, preset: "everyNHours", everyN: s / 3600 };
    return {
      ...base,
      preset: "everyNMinutes",
      everyN: Math.max(1, Math.round(s / 60)),
    };
  }
  if (timing.schedule_type === "once" && timing.run_at) {
    const wall = utcIsoToZonedWallTime(timing.run_at, timing.timezone);
    if (wall)
      return {
        ...base,
        preset: "once",
        onceDate: wall.date,
        onceTime: wall.time,
      };
    return { ...base, preset: "once" };
  }
  if (timing.schedule_type === "cron" && timing.cron_expression) {
    return cronToPreset(timing.cron_expression, base);
  }
  return { ...base, preset: "custom", cron: timing.cron_expression ?? "" };
}

// ---------------------------------------------------------------------------
// Short human sentence (used to auto-fill the schedule name)
// ---------------------------------------------------------------------------

function ordinal(n: number): string {
  const s = ["th", "st", "nd", "rd"];
  const v = n % 100;
  return `${n}${s[(v - 20) % 10] || s[v] || s[0]}`;
}

export function presetSentence(state: FrequencyState): string {
  switch (state.preset) {
    case "everyNMinutes":
    case "everyNHours": {
      const n = Math.floor(Number(state.everyN)) || 0;
      const unit = state.preset === "everyNHours" ? "hour" : "minute";
      return n === 1 ? `Every ${unit}` : `Every ${n} ${unit}s`;
    }
    case "hourly":
      return `Every hour at :${pad2(Math.floor(Number(state.minute)) || 0)}`;
    case "daily":
      return `Every day at ${state.time}`;
    case "weekdays":
      return `Weekdays at ${state.time}`;
    case "weekly": {
      const days = WEEK_ORDER.filter((d) => state.weekdays.includes(d));
      if (days.length === 1) return `${DAY_NAMES[days[0]!]}s at ${state.time}`;
      return `${days.map((d) => DAY_NAMES[d].slice(0, 3)).join(", ")} at ${
        state.time
      }`;
    }
    case "monthly":
      return `Monthly on the ${
        state.monthDay === "L" ? "last day" : ordinal(Number(state.monthDay))
      } at ${state.time}`;
    case "once":
      return `Once on ${state.onceDate} at ${state.onceTime}`;
    case "custom":
      return `Cron "${normalizeCron(state.cron)}"`;
  }
}
