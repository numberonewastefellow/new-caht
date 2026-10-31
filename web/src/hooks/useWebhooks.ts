"use client";

import useSWR from "swr";
import { errorHandlingFetcher } from "@/lib/fetcher";
import { pulseTriggerRunsUrl, pulseTriggerUrl } from "@/lib/schedules/api";
import type { PulseRun, PulseTriggerSummary } from "@/lib/schedules/interfaces";
import { ACTIVE_RUN_STATUSES } from "@/lib/schedules/status";
import {
  PulseWebhook,
  WEBHOOK_CONFIG_URL,
  WebhookConfig,
  webhookListenUrl,
  WebhookListenStatus,
  webhookRunsUrl,
  webhookUrl,
  WEBHOOKS_URL,
} from "@/lib/schedules/webhooks";

const IDLE_POLL_MS = 60000;
const ACTIVE_POLL_MS = 4000;
const LISTEN_POLL_MS = 2000;

export function useWebhooks(params: { allUsers?: boolean } = {}) {
  const key = params.allUsers ? `${WEBHOOKS_URL}?all_users=true` : WEBHOOKS_URL;
  const { data, error, isLoading, mutate } = useSWR<PulseWebhook[]>(key, errorHandlingFetcher, {
    refreshInterval: IDLE_POLL_MS,
  });
  return { webhooks: data ?? [], error, isLoading, refresh: mutate };
}

export function useWebhook(id: number | null | undefined) {
  const { data, error, isLoading, mutate } = useSWR<PulseWebhook>(
    id != null ? webhookUrl(id) : null,
    errorHandlingFetcher,
    { refreshInterval: ACTIVE_POLL_MS }
  );
  return { webhook: data, error, isLoading, refresh: mutate };
}

export function useWebhookRuns(id: number | null | undefined, limit = 50) {
  const { data, error, isLoading, mutate } = useSWR<PulseRun[]>(
    id != null ? webhookRunsUrl(id, limit) : null,
    errorHandlingFetcher,
    { refreshInterval: ACTIVE_POLL_MS }
  );
  return { runs: data ?? [], error, isLoading, refresh: mutate };
}

export function useWebhookConfig() {
  const { data, error, isLoading } = useSWR<WebhookConfig>(WEBHOOK_CONFIG_URL, errorHandlingFetcher);
  return { config: data, error, isLoading };
}

/** Only polls while the panel is open, because the owner is waiting for a call to arrive. */
export function useWebhookListen(id: number, active: boolean) {
  const { data, error, mutate } = useSWR<WebhookListenStatus>(
    active ? webhookListenUrl(id) : null,
    errorHandlingFetcher,
    { refreshInterval: active ? LISTEN_POLL_MS : 0 }
  );
  return { status: data, error, refresh: mutate };
}

/** The trigger behind a chat's run, whatever its kind (the chat banner). */
export function usePulseTrigger(id: number | null | undefined) {
  const { data, error, isLoading } = useSWR<PulseTriggerSummary>(
    id != null ? pulseTriggerUrl(id) : null,
    errorHandlingFetcher
  );
  return { trigger: data, error, isLoading };
}

export function usePulseTriggerRuns(id: number | null | undefined, limit = 50) {
  const { data, error, isLoading } = useSWR<PulseRun[]>(
    id != null ? pulseTriggerRunsUrl(id, limit) : null,
    errorHandlingFetcher,
    {
      refreshInterval: (runs) =>
        runs?.some((r) => ACTIVE_RUN_STATUSES.has(r.status)) ? ACTIVE_POLL_MS : IDLE_POLL_MS,
    }
  );
  return { runs: data ?? [], error, isLoading };
}
