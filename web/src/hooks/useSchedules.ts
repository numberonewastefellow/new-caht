"use client";

import useSWR from "swr";
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

  const { data, error, isLoading, mutate } = useSWR<PulseSchedule[]>(
    url,
    errorHandlingFetcher,
    {
      revalidateOnFocus: true,
      // Poll faster while any schedule has a run in flight.
      refreshInterval: (latest) =>
        latest && anyActive(latest.map((s) => s.last_run?.status))
          ? ACTIVE_POLL_MS
          : IDLE_POLL_MS,
    }
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
  const { data, error, isLoading, mutate } = useSWR<PulseSchedule>(
    id != null ? scheduleUrl(id) : null,
    errorHandlingFetcher,
    {
      revalidateOnFocus: true,
      refreshInterval: (latest) =>
        latest && anyActive([latest.last_run?.status]) ? ACTIVE_POLL_MS : 0,
    }
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
  const { data, error, isLoading, mutate } = useSWR<PulseRun[]>(
    id != null ? scheduleRunsUrl(id, limit) : null,
    errorHandlingFetcher,
    {
      revalidateOnFocus: true,
      refreshInterval: (latest) =>
        latest && anyActive(latest.map((r) => r.status)) ? ACTIVE_POLL_MS : 0,
    }
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
  const { data, error, isLoading, mutate } = useSWR<PulseSidebarItem[]>(
    PULSE_SIDEBAR_URL,
    errorHandlingFetcher,
    {
      revalidateOnFocus: false,
      dedupingInterval: 15000,
      refreshInterval: (latest) =>
        latest && anyActive(latest.map((r) => r.last_run_status))
          ? ACTIVE_POLL_MS * 2
          : IDLE_POLL_MS,
    }
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
