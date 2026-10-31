"use client";

import { useState } from "react";
import Link from "next/link";
import type { Route } from "next";
import { useRouter } from "next/navigation";
import * as SettingsLayouts from "@/layouts/settings-layouts";
import Button from "@/refresh-components/buttons/Button";
import Text from "@/refresh-components/texts/Text";
import InputSelect from "@/refresh-components/inputs/InputSelect";
import ConfirmationModalLayout from "@/refresh-components/layouts/ConfirmationModalLayout";
import { useCreateModal } from "@/refresh-components/contexts/ModalContext";
import {
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { toast } from "@/hooks/useToast";
import { useWebhook, useWebhookConfig, useWebhookRuns } from "@/hooks/useWebhooks";
import { useUser } from "@/providers/UserProvider";
import { SvgAlertTriangle, SvgArrowLeft, SvgEdit, SvgExternalLink, SvgLink, SvgRefreshCw, SvgSlash } from "@opal/icons";
import { chatHref } from "@/lib/schedules/api";
import { formatDurationMs, formatRelative, formatRunTime } from "@/lib/schedules/format";
import type { PulseRun } from "@/lib/schedules/interfaces";
import {
  AUTH_MODE_LABELS,
  dedupOptions,
  disabledReasonText,
  fetchRunPayload,
  maskedToken,
  refreshWebhooks,
  revokeWebhook,
  rotateWebhook,
  WebhookCapture,
  WebhookCredentials,
} from "@/lib/schedules/webhooks";
import Th from "@/sections/schedules/Th";
import { ACCENT, AccentIconTile, RunStatusPill } from "@/sections/schedules/StatusPill";
import { WebhookStateBadge } from "@/sections/webhooks/WebhookBits";
import WebhookListenPanel from "@/sections/webhooks/WebhookListenPanel";
import WebhookModal from "@/sections/webhooks/WebhookModal";
import WebhookSecretDialog from "@/sections/webhooks/WebhookSecretDialog";

const GRACE_CHOICES = [
  { hours: 0, label: "Stop them now" },
  { hours: 1, label: "Keep them for 1 hour" },
  { hours: 24, label: "Keep them for 24 hours" },
  { hours: 168, label: "Keep them for 7 days" },
];

function Fact({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-0.5 min-w-0">
      <Text as="span" secondaryBody text03>
        {label}
      </Text>
      <div className="text-sm text-text-05 break-words">{children}</div>
    </div>
  );
}

function RunPayload({ webhookId, run }: { webhookId: number; run: PulseRun }) {
  const [data, setData] = useState<{ payload: WebhookCapture["payload"] | null } | null>(null);
  const [failed, setFailed] = useState(false);

  async function load() {
    try {
      setData(await fetchRunPayload(webhookId, run.id));
    } catch {
      setFailed(true);
    }
  }

  if (failed) {
    return (
      <Text as="span" secondaryBody text03>
        Couldn&apos;t load the event data
      </Text>
    );
  }
  if (!data) {
    return (
      <button
        type="button"
        onClick={load}
        className="self-start text-[12.5px] font-medium hover:underline"
        style={{ color: ACCENT }}
      >
        Show event data
      </button>
    );
  }
  if (!data.payload) {
    return (
      <Text as="span" secondaryBody text03>
        Event data has been cleared by retention
      </Text>
    );
  }
  return (
    <pre className="overflow-auto max-h-64 rounded-08 border border-border-01 bg-background-tint-01 p-3 text-[12px] text-text-04 font-mono">
      {JSON.stringify(data.payload.body, null, 2)}
    </pre>
  );
}

export default function WebhookDetailPage({ webhookId }: { webhookId: number }) {
  const router = useRouter();
  const { user } = useUser();
  const { webhook, error, isLoading } = useWebhook(webhookId);
  const { runs } = useWebhookRuns(webhookId);
  const { config } = useWebhookConfig();
  const [editing, setEditing] = useState(false);
  const [credentials, setCredentials] = useState<WebhookCredentials | null>(null);
  const [grace, setGrace] = useState("24");
  const rotateModal = useCreateModal();
  const revokeModal = useCreateModal();
  const [busy, setBusy] = useState(false);

  async function handleRotate() {
    setBusy(true);
    try {
      setCredentials(await rotateWebhook(webhookId, Number(grace)));
      await refreshWebhooks();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not rotate the webhook");
    } finally {
      setBusy(false);
      rotateModal.toggle(false);
    }
  }

  async function handleRevoke() {
    setBusy(true);
    try {
      await revokeWebhook(webhookId);
      toast.success("Webhook revoked: its URL and secret no longer work");
      await refreshWebhooks();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not revoke the webhook");
    } finally {
      setBusy(false);
      revokeModal.toggle(false);
    }
  }

  if (!webhook) {
    return (
      <SettingsLayouts.Root width="lg">
        <SettingsLayouts.Body>
          <div className="py-10 text-center">
            <Text as="p" mainUiBody text03>
              {error && !isLoading ? "This webhook doesn't exist or you can't see it." : "Loading…"}
            </Text>
          </div>
        </SettingsLayouts.Body>
      </SettingsLayouts.Root>
    );
  }

  const isOwner = !!user && webhook.user_id === user.id;
  const dedupLabel = (
    dedupOptions(webhook.auth_mode).find((o) => o.value === webhook.dedup_source)?.label ??
    webhook.dedup_source
  ).replace(" (recommended)", "");
  const rejectedLast =
    !!webhook.last_rejected_at &&
    (!webhook.last_received_at || webhook.last_rejected_at > webhook.last_received_at);
  const graceActive =
    !!webhook.previous_valid_until && new Date(webhook.previous_valid_until) > new Date();

  return (
    <>
      {editing && (
        <WebhookModal
          webhook={webhook}
          onClose={() => setEditing(false)}
          ownerNote={
            isOwner
              ? null
              : `You are editing ${webhook.owner_email ?? "another user"}'s webhook as an admin. It stays theirs and keeps running as them; they will be notified.`
          }
        />
      )}
      {credentials && (
        <WebhookSecretDialog
          credentials={credentials}
          reason="rotated"
          onClose={() => setCredentials(null)}
        />
      )}
      <rotateModal.Provider>
        <ConfirmationModalLayout
          icon={SvgRefreshCw}
          title="Rotate credentials"
          submit={
            <Button disabled={busy} onClick={handleRotate}>
              Rotate
            </Button>
          }
          onClose={() => rotateModal.toggle(false)}
        >
          <div className="flex flex-col gap-3">
            <Text>
              You&apos;ll get a new URL and secret, shown once. Update the calling system with them.
            </Text>
            {!webhook.revoked && (
              <div>
                <Text as="p" mainUiAction text05 className="pb-1.5">
                  The old URL and secret
                </Text>
                <InputSelect value={grace} onValueChange={setGrace}>
                  <InputSelect.Trigger />
                  <InputSelect.Content>
                    {GRACE_CHOICES.filter((c) => c.hours <= (config?.max_grace_hours ?? 168)).map(
                      (c) => (
                        <InputSelect.Item key={c.hours} value={String(c.hours)}>
                          {c.label}
                        </InputSelect.Item>
                      )
                    )}
                  </InputSelect.Content>
                </InputSelect>
              </div>
            )}
          </div>
        </ConfirmationModalLayout>
      </rotateModal.Provider>
      <revokeModal.Provider>
        <ConfirmationModalLayout
          icon={SvgSlash}
          title="Revoke webhook"
          submit={
            <Button danger disabled={busy} onClick={handleRevoke}>
              Revoke
            </Button>
          }
          onClose={() => revokeModal.toggle(false)}
        >
          <Text>
            Use this if the URL or secret may have leaked. They stop working immediately, any
            caller using them gets an error, and runs still waiting won&apos;t start. Run history
            stays.
            {isOwner ? " You can rotate it later to get new credentials." : ""}
          </Text>
        </ConfirmationModalLayout>
      </revokeModal.Provider>

      <SettingsLayouts.Root width="lg">
        <div className="w-full bg-background-tint-01 px-4 pt-10 pb-5 border-b border-border-01">
          <div className="flex flex-col gap-4">
            <Link
              href={"/app/schedules?tab=webhooks" as Route}
              className="inline-flex items-center gap-1 text-[13px] text-text-03 hover:underline w-fit"
            >
              <SvgArrowLeft className="w-3.5 h-3.5 stroke-current" />
              Webhooks
            </Link>
            <div className="flex items-start justify-between gap-4 flex-wrap">
              <div className="flex items-start gap-3 min-w-0">
                <AccentIconTile icon={SvgLink} />
                <div className="flex flex-col min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <Text as="p" headingH2 className="truncate">
                      {webhook.name}
                    </Text>
                    <WebhookStateBadge webhook={webhook} />
                  </div>
                  <Text as="p" secondaryBody text03>
                    Runs “{webhook.workflow_name ?? `Workflow #${webhook.workflow_id}`}”
                    {webhook.owner_email ? ` as ${webhook.owner_email}` : ""}
                  </Text>
                </div>
              </div>
              <div className="flex items-center gap-2 flex-wrap">
                <Button secondary leftIcon={SvgEdit} onClick={() => setEditing(true)}>
                  Edit
                </Button>
                {isOwner && (
                  <Button secondary leftIcon={SvgRefreshCw} onClick={() => rotateModal.toggle(true)}>
                    Rotate
                  </Button>
                )}
                {!webhook.revoked && (
                  <Button secondary danger leftIcon={SvgSlash} onClick={() => revokeModal.toggle(true)}>
                    Revoke
                  </Button>
                )}
              </div>
            </div>
          </div>
        </div>

        <SettingsLayouts.Body>
          <div className="flex flex-col gap-4">
            {rejectedLast && (
              <div
                data-testid="webhook-last-rejected"
                className="flex items-start gap-2 rounded-08 border border-border-01 bg-background-tint-01 px-3 py-2"
              >
                <SvgAlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0 stroke-current text-status-text-error-05" />
                <Text as="p" secondaryBody text04>
                  The latest call was refused {formatRelative(webhook.last_rejected_at)}:{" "}
                  {webhook.last_rejected_reason}
                </Text>
              </div>
            )}
            {webhook.disabled_reason && (
              <Text as="p" mainUiBody text04>
                {disabledReasonText(webhook.disabled_reason)}. Fix the cause, then turn it back on.
              </Text>
            )}

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 rounded-12 border border-border-01 bg-background-tint-00 p-4">
              <Fact label="URL ends with">
                <code className="font-mono text-[12.5px]">{maskedToken(webhook.token_last4)}</code>
              </Fact>
              <Fact label="Caller proves itself with">{AUTH_MODE_LABELS[webhook.auth_mode]}</Fact>
              <Fact label="Repeats are found by">
                {dedupLabel}
                {webhook.dedup_path ? `: ${webhook.dedup_path}` : ""}
              </Fact>
              <Fact label="Last event">
                {webhook.last_received_at ? formatRelative(webhook.last_received_at) : "None yet"}
              </Fact>
              {graceActive && (
                <Fact label="Old credentials work until">
                  {formatRelative(webhook.previous_valid_until)}
                </Fact>
              )}
              <div className="col-span-2 md:col-span-4">
                <Fact label="What the workflow receives">
                  <pre className="whitespace-pre-wrap font-mono text-[12.5px] text-text-04">
                    {webhook.input_message}
                  </pre>
                </Fact>
              </div>
            </div>

            {isOwner && <WebhookListenPanel webhook={webhook} />}

            <div className="rounded-12 border border-border-01 bg-background-tint-00 overflow-hidden">
              <Table className="table-fixed">
                <TableHeader>
                  <TableRow noHover className="border-border-01 bg-background-tint-01">
                    <Th className="w-[11rem]">Received</Th>
                    <Th className="w-[9rem]">Result</Th>
                    <Th>Details</Th>
                    <Th className="w-[6rem]">Chat</Th>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {runs.length === 0 ? (
                    <TableRow noHover>
                      <TableCell colSpan={4} className="text-center py-7">
                        <Text as="span" mainUiBody text03>
                          No runs yet. Runs appear here when a call is accepted.
                        </Text>
                      </TableCell>
                    </TableRow>
                  ) : (
                    runs.map((run) => (
                      <TableRow key={run.id} noHover className="border-border-01 align-top">
                        <TableCell className="py-3 text-sm text-text-04">
                          {formatRunTime(run.scheduled_for)}
                        </TableCell>
                        <TableCell className="py-3">
                          <RunStatusPill
                            status={run.status}
                            suffix={run.duration_ms != null ? formatDurationMs(run.duration_ms) : undefined}
                          />
                        </TableCell>
                        <TableCell className="py-3">
                          <div className="flex flex-col gap-1 min-w-0">
                            {(run.error || run.skip_reason || run.output_preview) && (
                              <Text as="p" secondaryBody text03 className="line-clamp-2">
                                {run.error ?? run.skip_reason ?? run.output_preview}
                              </Text>
                            )}
                            {isOwner && <RunPayload webhookId={webhookId} run={run} />}
                          </div>
                        </TableCell>
                        <TableCell className="py-3">
                          {run.chat_session_id && (
                            <button
                              type="button"
                              className="inline-flex items-center gap-0.5 text-[12.5px] font-medium hover:underline"
                              style={{ color: ACCENT }}
                              onClick={() => router.push(chatHref(run.chat_session_id as string) as Route)}
                            >
                              Open
                              <SvgExternalLink className="w-3 h-3 stroke-current" />
                            </button>
                          )}
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>
          </div>
        </SettingsLayouts.Body>
      </SettingsLayouts.Root>
    </>
  );
}
