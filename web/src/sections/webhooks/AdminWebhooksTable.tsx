"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import type { Route } from "next";
import Button from "@/refresh-components/buttons/Button";
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
import { useWebhooks } from "@/hooks/useWebhooks";
import { SvgSlash } from "@opal/icons";
import { formatRelative } from "@/lib/schedules/format";
import {
  PulseWebhook,
  refreshWebhooks,
  revokeWebhook,
  updateWebhook,
  webhookHref,
} from "@/lib/schedules/webhooks";
import Th from "@/sections/schedules/Th";
import { WebhookStateBadge } from "@/sections/webhooks/WebhookBits";

/**
 * Every user's webhooks. Admins can pause, revoke and open any of them. They can't read
 * event data or rotate: new credentials would let them start runs as the owner.
 */
export default function AdminWebhooksTable() {
  const { webhooks, isLoading, error } = useWebhooks({ allUsers: true });
  const [query, setQuery] = useState("");
  const [busyId, setBusyId] = useState<number | null>(null);
  const [toRevoke, setToRevoke] = useState<PulseWebhook | null>(null);
  const revokeModal = useCreateModal();

  function closeRevoke() {
    setToRevoke(null);
    revokeModal.toggle(false);
  }

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    return webhooks.filter(
      (w) => !q || `${w.name} ${w.workflow_name ?? ""} ${w.owner_email ?? ""}`.toLowerCase().includes(q)
    );
  }, [webhooks, query]);

  async function act(webhook: PulseWebhook, action: () => Promise<unknown>) {
    setBusyId(webhook.id);
    try {
      await action();
      await refreshWebhooks();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not update the webhook");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <revokeModal.Provider>
        {toRevoke && (
          <ConfirmationModalLayout
            icon={SvgSlash}
            title="Revoke webhook"
            submit={
              <Button
                danger
                onClick={async () => {
                  const webhook = toRevoke;
                  closeRevoke();
                  await act(webhook, () => revokeWebhook(webhook.id));
                }}
              >
                Revoke
              </Button>
            }
            onClose={closeRevoke}
          >
            <Text>
              Revoke {toRevoke.owner_email ?? "this user"}&apos;s webhook &quot;{toRevoke.name}
              &quot;? Its URL and secret stop working immediately, and runs still waiting won&apos;t
              start. They&apos;ll be notified, and only they can issue new credentials.
            </Text>
          </ConfirmationModalLayout>
        )}
      </revokeModal.Provider>
      <div className="w-full max-w-xs">
        <InputTypeIn
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search by name, workflow or owner"
        />
      </div>
      <div className="rounded-12 border border-border-01 overflow-hidden">
        <Table className="table-fixed">
          <TableHeader>
            <TableRow noHover className="border-border-01 bg-background-tint-01">
              <Th>Name / workflow</Th>
              <Th className="w-[13rem]">Owner</Th>
              <Th className="w-[8rem]">State</Th>
              <Th className="w-[8rem]">Last event</Th>
              <Th className="w-[5.5rem] text-center">Enabled</Th>
              <Th className="w-[7rem]" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.length === 0 ? (
              <TableRow noHover>
                <TableCell colSpan={6} className="text-center py-7">
                  <Text as="span" mainUiBody text03>
                    {isLoading ? "Loading…" : error ? "Could not load webhooks." : "No webhooks."}
                  </Text>
                </TableCell>
              </TableRow>
            ) : (
              rows.map((w) => (
                <TableRow key={w.id} noHover className="border-border-01">
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
                  <TableCell className="py-3 text-sm text-text-04 truncate">{w.owner_email}</TableCell>
                  <TableCell className="py-3">
                    <WebhookStateBadge webhook={w} />
                  </TableCell>
                  <TableCell className="py-3 text-sm text-text-04">
                    {w.last_received_at ? formatRelative(w.last_received_at) : "None"}
                  </TableCell>
                  <TableCell className="py-3 text-center">
                    <Switch
                      aria-label={`Enable ${w.name}`}
                      checked={w.enabled && !w.revoked}
                      disabled={w.revoked || busyId === w.id}
                      onCheckedChange={(enabled) => act(w, () => updateWebhook(w.id, { enabled }))}
                    />
                  </TableCell>
                  <TableCell className="py-3">
                    {!w.revoked && (
                      <Button
                        secondary
                        danger
                        leftIcon={SvgSlash}
                        disabled={busyId === w.id}
                        onClick={() => {
                          setToRevoke(w);
                          revokeModal.toggle(true);
                        }}
                      >
                        Revoke
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
