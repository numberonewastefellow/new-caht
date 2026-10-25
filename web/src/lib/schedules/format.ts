/**
 * Display helpers for Schedules: relative times (past and future), run times
 * and durations. Pure functions; `now` is injectable for tests.
 */

/** "in 5 min", "in 3 h", "in 2 d", "just now", "50 min ago", "5 h ago", "1 d ago". */
export function formatRelative(
  iso: string | null | undefined,
  now: Date = new Date()
): string {
  if (!iso) return "—";
  const ms = new Date(iso).getTime();
  if (Number.isNaN(ms)) return "—";
  const diff = ms - now.getTime();
  const future = diff > 0;
  const abs = Math.abs(diff);
  const min = Math.round(abs / 60000);
  if (min < 1) return future ? "in < 1 min" : "just now";
  let text: string;
  if (min < 60) text = `${min} min`;
  else {
    const h = Math.round(min / 60);
    if (h < 48) text = `${h} h`;
    else text = `${Math.round(h / 24)} d`;
  }
  return future ? `in ${text}` : `${text} ago`;
}

/** "Mon 26 Oct, 09:00" in the viewer's locale/timezone (or a given zone). */
export function formatRunTime(
  iso: string | null | undefined,
  timeZone?: string
): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  try {
    const date = d.toLocaleDateString(undefined, {
      weekday: "short",
      day: "numeric",
      month: "short",
      timeZone,
    });
    const time = d.toLocaleTimeString(undefined, {
      hour: "2-digit",
      minute: "2-digit",
      timeZone,
    });
    return `${date}, ${time}`;
  } catch {
    return d.toLocaleString();
  }
}

/** Full absolute timestamp for tooltips, e.g. "Monday, 26 October 2026 at 09:00". */
export function formatAbsolute(
  iso: string | null | undefined,
  timeZone?: string
): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  try {
    return d.toLocaleString(undefined, {
      dateStyle: "full",
      timeStyle: "short",
      timeZone,
    });
  } catch {
    return d.toLocaleString();
  }
}

/** 248000 -> "4m 08s", 41000 -> "41s", 3_725_000 -> "1h 02m". */
export function formatDurationMs(ms: number | null | undefined): string {
  if (ms == null || !Number.isFinite(ms) || ms < 0) return "—";
  const total = Math.round(ms / 1000);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  if (h > 0) return `${h}h ${String(m).padStart(2, "0")}m`;
  if (m > 0) return `${m}m ${String(s).padStart(2, "0")}s`;
  return `${s}s`;
}

/**
 * One-line plain text for run output previews: drops common markdown syntax
 * (`**bold**`, `# headings`, list markers, links, code fences) and collapses
 * whitespace, so the runs table doesn't show raw `**Executive Summary**`.
 */
export function plainTextPreview(text: string | null | undefined): string {
  if (!text) return "";
  return text
    .replace(/```[\s\S]*?```/g, " ")
    .replace(/!\[([^\]]*)\]\([^)]*\)/g, "$1")
    .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
    .replace(/^\s{0,3}#{1,6}\s+/gm, "")
    .replace(/^\s*(?:[-*+]|\d+[.)])\s+/gm, "")
    .replace(/(\*\*|__)(.+?)\1/g, "$2")
    .replace(/(^|[^\w*])[*_]([^*_\n]+)[*_](?=$|[^\w*])/g, "$1$2")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/\s+/g, " ")
    .trim();
}

/** The browser's IANA timezone, falling back to UTC. */
export function browserTimeZone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
  } catch {
    return "UTC";
  }
}

export const COMMON_TIMEZONES = [
  "UTC",
  "Asia/Kolkata",
  "Asia/Dubai",
  "Asia/Singapore",
  "Asia/Tokyo",
  "Australia/Sydney",
  "Europe/London",
  "Europe/Berlin",
  "Europe/Paris",
  "America/New_York",
  "America/Chicago",
  "America/Denver",
  "America/Los_Angeles",
  "America/Sao_Paulo",
] as const;

/** Browser tz first, then the common list (deduplicated), plus `extra` if set. */
export function timezoneOptions(extra?: string | null): string[] {
  const browser = browserTimeZone();
  const list = [browser, ...COMMON_TIMEZONES];
  if (extra) list.splice(1, 0, extra);
  return Array.from(new Set(list));
}
