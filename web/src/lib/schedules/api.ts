/**
 * Fetch helpers for Schedules (Pulse). Reads go through SWR hooks in
 * `@/hooks/useSchedules`; mutations call these and then `refreshPulse()`.
 */

import { mutate } from "swr";
import type {
  PulsePreviewResponse,
  PulseRun,
  PulseSchedule,
  PulseScheduleCreate,
  PulseScheduleUpdate,
  ScheduleSpec,
} from "@/lib/schedules/interfaces";

export const PULSE_BASE = "/api/pulse";
export const PULSE_CONFIG_URL = `${PULSE_BASE}/config`;
export const PULSE_SCHEDULES_URL = `${PULSE_BASE}/schedules`;
export const PULSE_SIDEBAR_URL = `${PULSE_BASE}/sidebar`;
export const PULSE_STATS_URL = `${PULSE_BASE}/stats`;

export const scheduleUrl = (id: number) => `${PULSE_SCHEDULES_URL}/${id}`;
export const scheduleRunsUrl = (id: number, limit = 50) =>
  `${PULSE_SCHEDULES_URL}/${id}/runs?limit=${limit}`;
export const runUrl = (runId: number) => `${PULSE_BASE}/runs/${runId}`;

/** Chat link for a run / latest run. */
export const chatHref = (chatSessionId: string) =>
  `/app?chatId=${chatSessionId}`;
export const scheduleHref = (id: number) => `/app/schedules/${id}`;

export class PulseApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function parse<T>(res: Response): Promise<T> {
  if (res.ok) {
    if (res.status === 204) return undefined as T;
    const text = await res.text();
    return (text ? JSON.parse(text) : undefined) as T;
  }
  let detail = `Request failed (${res.status})`;
  try {
    const body = await res.json();
    if (typeof body?.detail === "string") detail = body.detail;
    else if (Array.isArray(body?.detail) && body.detail[0]?.msg)
      detail = String(body.detail[0].msg);
    else if (typeof body?.message === "string") {
      // The backend's validation-error handler returns
      // {status_code, message: "1 validation error: {... 'msg': '...' ...} File ..."};
      // show only the pydantic message, never the raw dump.
      const m =
        /'msg':\s*'([^']+)'/.exec(body.message) ??
        /"msg":\s*"([^"]+)"/.exec(body.message);
      if (m?.[1]) detail = m[1];
      else if (res.status === 422) detail = "Some fields are invalid.";
    }
  } catch {
    // keep the generic message
  }
  throw new PulseApiError(detail, res.status);
}

function jsonInit(method: string, body?: unknown, signal?: AbortSignal) {
  return {
    method,
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal,
  } satisfies RequestInit;
}

export async function previewSchedule(
  spec: ScheduleSpec,
  signal?: AbortSignal
): Promise<PulsePreviewResponse> {
  return parse(
    await fetch(`${PULSE_BASE}/preview`, jsonInit("POST", spec, signal))
  );
}

export async function createSchedule(
  body: PulseScheduleCreate
): Promise<PulseSchedule> {
  return parse(await fetch(PULSE_SCHEDULES_URL, jsonInit("POST", body)));
}

export async function updateSchedule(
  id: number,
  patch: PulseScheduleUpdate
): Promise<PulseSchedule> {
  return parse(await fetch(scheduleUrl(id), jsonInit("PATCH", patch)));
}

export async function deleteSchedule(id: number): Promise<void> {
  return parse(await fetch(scheduleUrl(id), { method: "DELETE" }));
}

export async function duplicateSchedule(id: number): Promise<PulseSchedule> {
  return parse(await fetch(`${scheduleUrl(id)}/duplicate`, jsonInit("POST")));
}

export async function runScheduleNow(id: number): Promise<PulseRun> {
  return parse(await fetch(`${scheduleUrl(id)}/run-now`, jsonInit("POST")));
}

export async function fetchRun(runId: number): Promise<PulseRun> {
  return parse(await fetch(runUrl(runId)));
}

/**
 * Poll a run until it has a chat session (or finishes without one).
 * Resolves with the chat session id, or null on timeout / no chat.
 */
export async function waitForRunChat(
  runId: number,
  {
    timeoutMs = 60000,
    intervalMs = 1500,
    shouldStop,
  }: {
    timeoutMs?: number;
    intervalMs?: number;
    /** Stop polling early (e.g. the caller unmounted). */
    shouldStop?: () => boolean;
  } = {}
): Promise<string | null> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline && !shouldStop?.()) {
    try {
      const run = await fetchRun(runId);
      if (run.chat_session_id) return run.chat_session_id;
      if (run.status !== "pending" && run.status !== "running") return null;
    } catch {
      // transient; keep polling until the deadline
    }
    await new Promise((r) => setTimeout(r, intervalMs));
  }
  return null;
}

/** Revalidate every cached Pulse request (lists, detail, runs, sidebar, stats). */
export function refreshPulse() {
  // Single-argument form: revalidate only, keep the cached data meanwhile.
  return mutate((key) => typeof key === "string" && key.startsWith(PULSE_BASE));
}
