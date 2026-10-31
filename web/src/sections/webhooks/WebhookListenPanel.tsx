"use client";

import { useEffect, useState } from "react";
import { mutate } from "swr";
import Button from "@/refresh-components/buttons/Button";
import CopyIconButton from "@/refresh-components/buttons/CopyIconButton";
import Text from "@/refresh-components/texts/Text";
import { toast } from "@/hooks/useToast";
import { useWebhookListen } from "@/hooks/useWebhooks";
import { SvgLink } from "@opal/icons";
import {
  previewWebhookMessage,
  PulseWebhook,
  sendTestEvent,
  startListening,
  stopListening,
  webhookListenUrl,
} from "@/lib/schedules/webhooks";
import { ACCENT, Spinner } from "@/sections/schedules/StatusPill";

const SAMPLE = { message: "Hello from a test event" };

/**
 * Lets the owner see exactly what arrives and what the workflow would get, before going
 * live. Nothing here runs the workflow or uses up an event id.
 */
export default function WebhookListenPanel({ webhook }: { webhook: PulseWebhook }) {
  const [active, setActive] = useState(false);
  const [busy, setBusy] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);
  const { status, refresh } = useWebhookListen(webhook.id, active);

  const listening = active && !!status?.listening;
  const latest = status?.captures[0];
  const expired = active && status != null && !status.listening;

  useEffect(() => {
    if (expired) setActive(false);
  }, [expired]);

  const latestBody = latest?.payload.body;
  const latestKey = latest?.received_at;
  useEffect(() => {
    if (latestKey === undefined) {
      setPreview(null);
      return;
    }
    let cancelled = false;
    previewWebhookMessage(webhook.id, latestBody, webhook.input_message)
      .then((message) => {
        if (!cancelled) setPreview(message);
      })
      .catch(() => {
        if (!cancelled) setPreview(null);
      });
    return () => {
      cancelled = true;
    };
    // latestKey identifies the capture; the body is read from the same capture.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [latestKey, webhook.id, webhook.input_message]);

  async function handleStart() {
    setBusy(true);
    try {
      // Replace what's cached before polling resumes: an expired window would read as
      // already closed, and a stopped one would show its old captures.
      const started = await startListening(webhook.id);
      await mutate(webhookListenUrl(webhook.id), started, { revalidate: false });
      setActive(true);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not start listening");
    } finally {
      setBusy(false);
    }
  }

  async function handleStop() {
    setBusy(true);
    try {
      await stopListening(webhook.id);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not stop listening");
    } finally {
      setActive(false);
      setBusy(false);
    }
  }

  async function handleTestEvent() {
    setBusy(true);
    try {
      await refresh(await sendTestEvent(webhook.id, SAMPLE), { revalidate: false });
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not send the test event");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-3 rounded-12 border border-border-01 bg-background-tint-00 p-4">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div className="flex flex-col gap-0.5 min-w-0">
          <Text as="p" mainUiAction text05>
            Listen for a test call
          </Text>
          <Text as="p" secondaryBody text03>
            While open, calls to the test URL (<code>/api/hooks/test/…</code>) are shown here. They
            don&apos;t start the workflow.
          </Text>
        </div>
        {listening ? (
          <div className="flex items-center gap-2 flex-shrink-0">
            <Button secondary disabled={busy} onClick={handleTestEvent}>
              Send test event
            </Button>
            <Button secondary disabled={busy} onClick={handleStop}>
              Stop
            </Button>
          </div>
        ) : (
          <Button
            leftIcon={SvgLink}
            disabled={busy || webhook.revoked || !webhook.enabled}
            onClick={handleStart}
          >
            Listen
          </Button>
        )}
      </div>

      {listening && (
        <div className="flex items-center gap-2 text-[13px]" style={{ color: ACCENT }}>
          <Spinner className="w-3.5 h-3.5" />
          <span data-testid="webhook-listening">
            Listening for {status?.seconds_left ?? 0}s more…
          </span>
        </div>
      )}

      {listening && latest && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3" data-testid="webhook-capture">
          <div className="flex flex-col gap-1 min-w-0">
            <Text as="span" secondaryAction text04>
              What arrived
            </Text>
            <pre className="overflow-auto max-h-64 rounded-08 border border-border-01 bg-background-tint-01 p-3 text-[12px] text-text-04 font-mono">
              {JSON.stringify(latest.payload.body, null, 2)}
            </pre>
            <details>
              <summary className="cursor-pointer text-[12.5px] text-text-03">
                Headers (credentials removed)
              </summary>
              <pre className="overflow-auto max-h-40 mt-1 rounded-08 border border-border-01 bg-background-tint-01 p-3 text-[12px] text-text-04 font-mono">
                {JSON.stringify(latest.payload.headers, null, 2)}
              </pre>
            </details>
          </div>
          <div className="flex flex-col gap-1 min-w-0">
            <div className="flex items-center justify-between gap-2">
              <Text as="span" secondaryAction text04>
                What the workflow would receive
              </Text>
              {preview && <CopyIconButton getCopyText={() => preview} tooltip="Copy message" />}
            </div>
            <pre
              data-testid="webhook-preview"
              className="overflow-auto max-h-64 whitespace-pre-wrap rounded-08 border border-border-01 bg-background-tint-01 p-3 text-[12px] text-text-04 font-mono"
            >
              {preview ?? "…"}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}
