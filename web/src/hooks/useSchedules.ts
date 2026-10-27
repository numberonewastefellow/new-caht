"use client";

import { useState } from "react";
import useSWR, { type SWRConfiguration } from "swr";
import { errorHandlingFetcher } from "@/lib/fetcher";
import {
  PULSE_CONFIG_URL,
  PULSE_SCHEDULES_URL,
  PULSE_SIDEBAR_URL,
  PULSE_STATS_URL,
  scheduleRunsUrl,
  scheduleUrl,
} from "@/lib/schedules/api";
import type {
  PulseConfig,
  PulseRun,
  PulseSchedule,
  PulseSidebarItem,
  PulseStats,
} from "@/lib/schedules/interfaces";
import { ACTIVE_RUN_STATUSES } from "@/lib/schedules/status";

const ACTIVE_POLL_MS = 4000;
const IDLE_POLL_MS = 60000;

function anyActive(statuses: (string | null | undefined)[]) {
  return statuses.some(
    (s) => !!s && ACTIVE_RUN_STATUSES.has(s as PulseRun["status"])
  );
}

/**
 * useSWR whose polling interval follows the data ("fast while a run is active").
 *
 * NOT `refreshInterval: (latest) => …`: the React Compiler memoizes that inline
 * function, SWR evaluates it once at mount (no data yet -> 0) and never re-arms the
 * timer, so polling silently never starts. Keeping the interval in state (updated
 * in onSuccess) gives SWR a changing number, which re-arms the timer.
 */
function usePolledSWR<T>(
  key: string | null,
  isActive: (data: T) => boolean,
  activeMs: number,
  idleMs: number,
  config: SWRConfiguration<T> = {}
) {
  const [intervalMs, setIntervalMs] = useState(idleMs);
  return useSWR<T>(key, errorHandlingFetcher, {
    ...config,
    refreshInterval: intervalMs,
    onSuccess: (data) => setIntervalMs(isActive(data) ? activeMs : idleMs),
  });
}

export interface UseSchedulesParams {
  allUsers?: boolean;
  workflowId?: number | null;
}

/** All schedules visible to the user (optionally admin-wide / per workflow). */
export function useSchedules(params: UseSchedulesParams = {}) {
  const qs = new URLSearchParams();
  if (params.allUsers) qs.set("all_users", "true");
  if (params.workflowId != null)
    qs.set("workflow_id", String(params.workflowId));
  const url = qs.toString()
    ? `${PULSE_SCHEDULES_URL}?${qs.toString()}`
    : PULSE_SCHEDULES_URL;

  // Poll faster while any schedule has a run in flight.
  const { data, error, isLoading, mutate } = usePolledSWR<PulseSchedule[]>(
    url,
    (latest) => anyActive(latest.map((s) => s.last_run?.status)),
    ACTIVE_POLL_MS,
    IDLE_POLL_MS,
    { revalidateOnFocus: true }
  );

  return {
    schedules: data ?? [],
    isLoading,
    error,
    refresh: mutate,
  };
}

/** One schedule by id. */
export function useSchedule(id: number | null | undefined) {
  const { data, error, isLoading, mutate } = usePolledSWR<PulseSchedule>(
    id != null ? scheduleUrl(id) : null,
    (latest) => anyActive([latest.last_run?.status]),
    ACTIVE_POLL_MS,
    0,
    { revalidateOnFocus: true }
  );

  return {
    schedule: data ?? null,
    isLoading,
    error,
    refresh: mutate,
  };
}

/** Run history for a schedule (newest first); polls while a run is active. */
export function useScheduleRuns(id: number | null | undefined, limit = 50) {
  const { data, error, isLoading, mutate } = usePolledSWR<PulseRun[]>(
    id != null ? scheduleRunsUrl(id, limit) : null,
    (latest) => anyActive(latest.map((r) => r.status)),
    ACTIVE_POLL_MS,
    0,
    { revalidateOnFocus: true }
  );

  return {
    runs: data ?? [],
    isLoading,
    error,
    refresh: mutate,
  };
}

/** Rows for the chat sidebar's "Scheduled" section. */
export function usePulseSidebar() {
  const { data, error, isLoading, mutate } = usePolledSWR<PulseSidebarItem[]>(
    PULSE_SIDEBAR_URL,
    (latest) => anyActive(latest.map((r) => r.last_run_status)),
    ACTIVE_POLL_MS * 2,
    IDLE_POLL_MS,
    { revalidateOnFocus: false, dedupingInterval: 15000 }
  );

  return {
    items: data ?? [],
    isLoading,
    error,
    refresh: mutate,
  };
}

/** KPI tiles on the Schedules page. */
export function usePulseStats() {
  const { data, error, isLoading, mutate } = useSWR<PulseStats>(
    PULSE_STATS_URL,
    errorHandlingFetcher,
    { revalidateOnFocus: true, refreshInterval: IDLE_POLL_MS }
  );

  return { stats: data ?? null, isLoading, error, refresh: mutate };
}

/** Server limits (min interval, retention bounds, template variables). */
export function usePulseConfig() {
  const { data, error, isLoading } = useSWR<PulseConfig>(
    PULSE_CONFIG_URL,
    errorHandlingFetcher,
    { revalidateOnFocus: false, dedupingInterval: 600000 }
  );

  return { config: data ?? null, isLoading, error };
}
