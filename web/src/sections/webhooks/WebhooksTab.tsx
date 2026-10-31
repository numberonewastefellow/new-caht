"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import type { Route } from "next";
import Button from "@/refresh-components/buttons/Button";
import IconButton from "@/refresh-components/buttons/IconButton";
import Text from "@/refresh-components/texts/Text";
import InputTypeIn from "@/refresh-components/inputs/InputTypeIn";
import Switch from "@/refresh-components/inputs/Switch";
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
import { useWebhookConfig, useWebhooks } from "@/hooks/useWebhooks";
import { SvgAlertTriangle, SvgExternalLink, SvgLink, SvgPlus, SvgTrash } from "@opal/icons";
import { chatHref } from "@/lib/schedules/api";
import { formatRelative } from "@/lib/schedules/format";
import {
  deleteWebhook,
  PulseWebhook,
  refreshWebhooks,
  updateWebhook,
  webhookHref,
  WebhookCredentials,
} from "@/lib/schedules/webhooks";
import Th from "@/sections/schedules/Th";
import { ACCENT, AccentIconTile, RunStatusGlyph } from "@/sections/schedules/StatusPill";
import WebhookModal from "@/sections/webhooks/WebhookModal";
import WebhookSecretDialog from "@/sections/webhooks/WebhookSecretDialog";
import { WebhookStateBadge } from "@/sections/webhooks/WebhookBits";

function LastEventCell({ webhook }: { webhook: PulseWebhook }) {
  const rejectedLast =
    !!webhook.last_rejected_at &&
    (!webhook.last_received_at || webhook.last_rejected_at > webhook.last_received_at);
  return (
    <div className="flex flex-col gap-0.5 min-w-0">
      <span className="text-sm text-text-04">
        {webhook.last_received_at ? formatRelative(webhook.last_received_at) : "No events yet"}
      </span>
      {rejectedLast && (
        <span
          className="inline-flex items-center gap-1 text-[12.5px] text-status-text-error-05 truncate"
          title={webhook.last_rejected_reason ?? undefined}
        >
          <SvgAlertTriangle className="w-3 h-3 flex-shrink-0 stroke-current" />
          Refused {formatRelative(webhook.last_rejected_at)}
        </span>
      )}
    </div>
  );
}

function LastRunCell({ webhook }: { webhook: PulseWebhook }) {
  const status = webhook.last_run?.status ?? webhook.last_run_status;
  const chatId = webhook.last_run?.chat_session_id ?? webhook.latest_chat_session_id;
  if (!status) {
    return (
      <Text as="span" secondaryBody text02>
        Never run
      </Text>
    );
  }
  return (
    <div className="flex flex-col gap-0.5">
      <div className="flex items-center gap-1.5 text-sm text-text-04">
        <RunStatusGlyph status={status} />
        <span>{formatRelative(webhook.last_run?.finished_at ?? webhook.last_run_at)}</span>
      </div>
      {chatId && (
        <Link
          href={chatHref(chatId) as Route}
          className="inline-flex items-center gap-0.5 text-[12.5px] font-medium hover:underline w-fit"
          style={{ color: ACCENT }}
        >
          Open chat
          <SvgExternalLink className="w-3 h-3 stroke-current" />
        </Link>
      )}
    </div>
  );
}

function EmptyWebhooks({ onNew, disabled }: { onNew: () => void; disabled: boolean }) {
  return (
    <div className="flex flex-col items-center gap-3 py-12 text-center">
      <AccentIconTile icon={SvgLink} />
      <Text as="p" headingH3>
        Start workflows from other systems
      </Text>
      <Text as="p" mainUiBody text03 className="max-w-md">
        Give a system a secure URL. When something happens there, like a new complaint or ticket,
        it calls the URL and the workflow runs with that data.
      </Text>
      <Button leftIcon={SvgPlus} onClick={onNew} disabled={disabled}>
        New webhook
      </Button>
    </div>
  );
}

export interface WebhooksTabProps {
  creating: boolean;
  onCreatingChange: (creating: boolean) => void;
}

export default function WebhooksTab({ creating, onCreatingChange }: WebhooksTabProps) {
  const { webhooks, isLoading, error } = useWebhooks();
  const { config } = useWebhookConfig();
  const [query, setQuery] = useState("");
  const [credentials, setCredentials] = useState<WebhookCredentials | null>(null);
  const [toDelete, setToDelete] = useState<PulseWebhook | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const deleteModal = useCreateModal();

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    return webhooks.filter(
      (w) => !q || `${w.name} ${w.workflow_name ?? ""}`.toLowerCase().includes(q)
    );
  }, [webhooks, query]);

  async function toggle(webhook: PulseWebhook, enabled: boolean) {
    setBusyId(webhook.id);
    try {
      await updateWebhook(webhook.id, { enabled });
      await refreshWebhooks();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not update the webhook");
    } finally {
      setBusyId(null);
    }
  }

  async function confirmDelete() {
    if (!toDelete) return;
    try {
      await deleteWebhook(toDelete.id);
      toast.success("Webhook deleted");
      await refreshWebhooks();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not delete the webhook");
    }
    setToDelete(null);
    deleteModal.toggle(false);
  }

  const switchedOff = config?.enabled === false;

  return (
    <div className="flex flex-col gap-3">
      <deleteModal.Provider>
        {toDelete && (
          <ConfirmationModalLayout
            icon={SvgTrash}
            title="Delete webhook"
            submit={
              <Button danger onClick={confirmDelete}>
                Delete
              </Button>
            }
            onClose={() => {
              setToDelete(null);
              deleteModal.toggle(false);
            }}
          >
            <Text>
              Delete &quot;{toDelete.name}&quot;? Its URL stops working at once and its run history
              is removed. Chats from earlier runs stay in your chat history.
            </Text>
          </ConfirmationModalLayout>
        )}
      </deleteModal.Provider>

      {creating && (
        <WebhookModal
          onClose={() => onCreatingChange(false)}
          onCreated={(created) => {
            onCreatingChange(false);
            setCredentials(created);
          }}
        />
      )}
      {credentials && (
        <WebhookSecretDialog
          credentials={credentials}
          reason="created"
          onClose={() => setCredentials(null)}
        />
      )}

      {switchedOff && (
        <div
          data-testid="webhooks-switched-off"
          className="flex items-center gap-2 rounded-08 border border-border-01 bg-background-tint-01 px-3 py-2"
        >
          <SvgAlertTriangle className="w-4 h-4 flex-shrink-0 stroke-text-04" />
          <Text as="p" secondaryBody text04>
            An admin has turned webhooks off for this workspace. Calls are refused and new webhooks
            can&apos;t be created.
          </Text>
        </div>
      )}

      {!isLoading && !error && webhooks.length === 0 ? (
        <EmptyWebhooks onNew={() => onCreatingChange(true)} disabled={switchedOff} />
      ) : (
        <>
          <div className="w-full max-w-xs">
            <InputTypeIn
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search webhooks"
            />
          </div>
          <div className="rounded-12 border border-border-01 bg-background-tint-00 shadow-[0_1px_2px_var(--shadow-01)] overflow-hidden">
            <Table className="table-fixed">
              <TableHeader>
                <TableRow noHover className="border-border-01 bg-background-tint-01">
                  <Th>Name / workflow</Th>
                  <Th className="w-[8rem]">State</Th>
                  <Th className="w-[10rem]">Last event</Th>
                  <Th className="w-[9.5rem]">Last run</Th>
                  <Th className="w-[5.5rem] text-center">Enabled</Th>
                  <Th className="w-[3.5rem]" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.length === 0 ? (
                  <TableRow noHover>
                    <TableCell colSpan={6} className="text-center py-7">
                      <Text as="span" mainUiBody text03>
                        {error ? "Could not load webhooks." : "No webhooks match."}
                      </Text>
                    </TableCell>
                  </TableRow>
                ) : (
                  rows.map((w) => (
                    <TableRow key={w.id} noHover className="border-border-01 hover:bg-background-tint-01">
                      <TableCell className="py-3">
                        <Link
                          href={webhookHref(w.id) as Route}
                          className="block text-text-05 font-medium hover:underline truncate"
                        >
                          {w.name}
                        </Link>
                        <Text as="p" secondaryBody text03 className="truncate">
                          {w.workflow_name ?? `Workflow #${w.workflow_id}`}
                        </Text>
                      </TableCell>
                      <TableCell className="py-3">
                        <WebhookStateBadge webhook={w} />
                      </TableCell>
                      <TableCell className="py-3">
                        <LastEventCell webhook={w} />
                      </TableCell>
                      <TableCell className="py-3">
                        <LastRunCell webhook={w} />
                      </TableCell>
                      <TableCell className="py-3 text-center">
                        <Switch
                          aria-label={`Enable ${w.name}`}
                          checked={w.enabled && !w.revoked}
                          disabled={w.revoked || busyId === w.id}
                          onCheckedChange={(checked) => toggle(w, checked)}
                        />
                      </TableCell>
                      <TableCell className="py-3">
                        <IconButton
                          icon={SvgTrash}
                          tertiary
                          tooltip="Delete"
                          onClick={() => {
                            setToDelete(w);
                            deleteModal.toggle(true);
                          }}
                        />
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </>
      )}
    </div>
  );
}
