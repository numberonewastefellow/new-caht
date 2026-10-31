/**
 * Types and calls for Pulse webhooks. Reads go through SWR hooks in `@/hooks/useWebhooks`;
 * mutations call these and then `refreshWebhooks()`.
 */

import { mutate } from "swr";
import { jsonInit, parse, PULSE_BASE } from "@/lib/schedules/api";
import type { PulseRun, PulseRunStatus } from "@/lib/schedules/interfaces";

export type WebhookAuthMode = "standard_webhooks" | "header_token";
export type WebhookDedupSource = "webhook_id" | "header" | "json_path" | "none";

export interface PulseWebhook {
  id: number;
  kind: "webhook";
  name: string;
  workflow_id: number;
  workflow_name: string | null;
  user_id: string;
  owner_email: string | null;
  updated_by_email: string | null;
  enabled: boolean;
  disabled_reason: string | null;
  revoked: boolean;
  auth_mode: WebhookAuthMode;
  header_name: string | null;
  dedup_source: WebhookDedupSource;
  dedup_path: string | null;
  input_message: string;
  timezone: string;
  retention_count: number;
  token_last4: string;
  rotated_at: string | null;
  previous_valid_until: string | null;
  last_received_at: string | null;
  last_rejected_at: string | null;
  last_rejected_reason: string | null;
  last_run_at: string | null;
  last_run_status: PulseRunStatus | null;
  consecutive_failures: number;
  created_at: string;
  updated_at: string;
  last_run: PulseRun | null;
  latest_chat_session_id: string | null;
}

/** Returned once, when a webhook is created or rotated. Can't be read back later. */
export interface WebhookCredentials {
  webhook: PulseWebhook;
  url: string;
  test_url: string;
  signing_secret: string;
}

export interface WebhookCreate {
  workflow_id: number;
  name: string;
  input_message?: string;
  timezone?: string;
  auth_mode: WebhookAuthMode;
  header_name?: string | null;
  dedup_source?: WebhookDedupSource | null;
  dedup_path?: string | null;
  retention_count?: number | null;
}

export type WebhookUpdate = Partial<
  Pick<
    PulseWebhook,
    | "name"
    | "input_message"
    | "timezone"
    | "dedup_source"
    | "dedup_path"
    | "enabled"
    | "retention_count"
  >
>;

export interface WebhookConfig {
  enabled: boolean;
  secret_encryption_configured: boolean;
  default_input_message: string;
  max_body_bytes: number;
  listen_seconds: number;
  max_grace_hours: number;
  default_grace_hours: number;
  template_variables: string[];
}

export interface WebhookCapture {
  received_at: string;
  payload: { body: unknown; headers: Record<string, string> };
}

export interface WebhookListenStatus {
  listening: boolean;
  seconds_left: number;
  captures: WebhookCapture[];
}

export const WEBHOOKS_URL = `${PULSE_BASE}/webhooks`;
export const WEBHOOK_CONFIG_URL = `${WEBHOOKS_URL}/config`;
export const webhookUrl = (id: number) => `${WEBHOOKS_URL}/${id}`;
export const webhookRunsUrl = (id: number, limit = 50) =>
  `${webhookUrl(id)}/runs?limit=${limit}`;
export const webhookListenUrl = (id: number) => `${webhookUrl(id)}/listen`;
export const webhookHref = (id: number) => `/app/schedules/webhooks/${id}`;

/** Refresh every cached webhook read after a change. */
export function refreshWebhooks(): Promise<unknown> {
  // Single-argument form: revalidate only, keep the cached data meanwhile. Clearing it
  // would unmount the page, and with it a dialog showing credentials for the only time.
  return mutate((key) => typeof key === "string" && key.startsWith(WEBHOOKS_URL));
}

export async function createWebhook(body: WebhookCreate): Promise<WebhookCredentials> {
  return parse(await fetch(WEBHOOKS_URL, jsonInit("POST", body)));
}

export async function updateWebhook(id: number, body: WebhookUpdate): Promise<PulseWebhook> {
  return parse(await fetch(webhookUrl(id), jsonInit("PATCH", body)));
}

export async function deleteWebhook(id: number): Promise<void> {
  return parse(await fetch(webhookUrl(id), { method: "DELETE" }));
}

export async function rotateWebhook(id: number, graceHours: number): Promise<WebhookCredentials> {
  return parse(
    await fetch(`${webhookUrl(id)}/rotate`, jsonInit("POST", { grace_hours: graceHours }))
  );
}

export async function revokeWebhook(id: number): Promise<PulseWebhook> {
  return parse(await fetch(`${webhookUrl(id)}/revoke`, jsonInit("POST")));
}

export async function startListening(id: number): Promise<WebhookListenStatus> {
  return parse(await fetch(webhookListenUrl(id), jsonInit("POST")));
}

export async function stopListening(id: number): Promise<void> {
  return parse(await fetch(webhookListenUrl(id), { method: "DELETE" }));
}

export async function sendTestEvent(id: number, body: unknown): Promise<WebhookListenStatus> {
  return parse(await fetch(`${webhookUrl(id)}/test-event`, jsonInit("POST", { body })));
}

export async function previewWebhookMessage(
  id: number,
  body: unknown,
  inputMessage?: string
): Promise<string> {
  const response = await parse<{ message: string }>(
    await fetch(
      `${webhookUrl(id)}/preview`,
      jsonInit("POST", { body, input_message: inputMessage ?? null })
    )
  );
  return response.message;
}

export async function fetchRunPayload(
  webhookId: number,
  runId: number
): Promise<{ payload: WebhookCapture["payload"] | null; cleared: boolean }> {
  return parse(await fetch(`${webhookUrl(webhookId)}/runs/${runId}/payload`));
}

// ---------------------------------------------------------------- pure helpers

export const AUTH_MODE_LABELS: Record<WebhookAuthMode, string> = {
  standard_webhooks: "Signed (Standard Webhooks)",
  header_token: "Secret in a header",
};

export const DEFAULT_SECRET_HEADER = "x-webhook-secret";

export type WebhookState = "active" | "paused" | "revoked" | "attention";

/** One state for the list: revoked outranks paused, because a resume won't fix it. */
export function webhookState(webhook: PulseWebhook): WebhookState {
  if (webhook.revoked) return "revoked";
  if (webhook.disabled_reason) return "attention";
  return webhook.enabled ? "active" : "paused";
}

const DISABLED_REASONS: Record<string, string> = {
  auto_paused_failures: "Paused after repeated failures",
  access_revoked: "Paused: the owner lost access",
  workflow_deleted: "Paused: the workflow was deleted",
};

export function disabledReasonText(reason: string | null): string | null {
  if (!reason) return null;
  return DISABLED_REASONS[reason] ?? "Paused by the system";
}

/** The dedup sources that make sense for an auth mode. */
export function dedupOptions(mode: WebhookAuthMode): { value: WebhookDedupSource; label: string }[] {
  const common: { value: WebhookDedupSource; label: string }[] = [
    { value: "json_path", label: "A field in the body" },
    { value: "none", label: "Don't check: every call runs" },
  ];
  // A signature doesn't cover other headers, so a replay could change one and run again.
  return mode === "standard_webhooks"
    ? [{ value: "webhook_id", label: "The webhook-id header (recommended)" }, ...common]
    : [{ value: "header", label: "A header I choose" }, ...common];
}

export function defaultDedupSource(mode: WebhookAuthMode): WebhookDedupSource {
  return mode === "standard_webhooks" ? "webhook_id" : "none";
}

export function dedupNeedsPath(source: WebhookDedupSource): boolean {
  return source === "header" || source === "json_path";
}

export function validateWebhookForm(form: {
  name: string;
  workflowId: number | null;
  dedupSource: WebhookDedupSource;
  dedupPath: string;
}): string | null {
  if (form.workflowId == null) return "Pick a workflow";
  if (!form.name.trim()) return "Give the webhook a name";
  if (dedupNeedsPath(form.dedupSource) && !form.dedupPath.trim()) {
    return form.dedupSource === "header"
      ? "Enter the header that identifies an event"
      : "Enter the field that identifies an event";
  }
  return null;
}

function shellQuote(value: string): string {
  return `'${value.replace(/'/g, `'\\''`)}'`;
}

const SAMPLE_BODY = '{"message": "Hello"}';

/** A command to send a real call, with placeholders for what the UI can't read back. */
export function curlExample(options: {
  url: string;
  authMode: WebhookAuthMode;
  headerName: string | null;
  secret?: string;
}): string {
  const secret = options.secret ?? "<your secret>";
  const url = shellQuote(options.url);
  const body = shellQuote(SAMPLE_BODY);
  if (options.authMode === "header_token") {
    const name = options.headerName ?? DEFAULT_SECRET_HEADER;
    return [
      `curl -X POST ${url} \\`,
      `  -H 'Content-Type: application/json' \\`,
      `  -H ${shellQuote(`${name}: ${secret}`)} \\`,
      `  -d ${body}`,
    ].join("\n");
  }
  return [
    `SECRET=${shellQuote(secret)}`,
    `ID="msg_$(date +%s)"; TS=$(date +%s); BODY=${body}`,
    `SIG=$(printf '%s' "$ID.$TS.$BODY" | openssl dgst -sha256 -mac HMAC \\`,
    `  -macopt hexkey:"$(printf '%s' "\${SECRET#whsec_}" | base64 -d | xxd -p -c 256)" -binary | base64)`,
    `curl -X POST ${url} \\`,
    `  -H 'Content-Type: application/json' \\`,
    `  -H "webhook-id: $ID" -H "webhook-timestamp: $TS" -H "webhook-signature: v1,$SIG" \\`,
    `  -d "$BODY"`,
  ].join("\n");
}

/** The URL with the token hidden, for places that show it after creation. */
export function maskedToken(last4: string): string {
  return `whk_••••${last4}`;
}
