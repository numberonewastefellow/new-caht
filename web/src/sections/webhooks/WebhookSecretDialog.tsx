"use client";

import { useState } from "react";
import Modal from "@/refresh-components/Modal";
import Button from "@/refresh-components/buttons/Button";
import CopyIconButton from "@/refresh-components/buttons/CopyIconButton";
import Text from "@/refresh-components/texts/Text";
import { SvgAlertTriangle, SvgShield } from "@opal/icons";
import { curlExample, WebhookCredentials } from "@/lib/schedules/webhooks";
import { ACCENT_GLOW_STRONG, ACCENT_SUBTLE } from "@/sections/schedules/StatusPill";

function CopyRow({ label, value, testId }: { label: string; value: string; testId: string }) {
  return (
    <div className="flex flex-col gap-1">
      <Text as="span" mainUiAction text05>
        {label}
      </Text>
      <div className="flex items-start gap-1 rounded-08 border border-border-01 bg-background-tint-01 pl-3 pr-1 py-1">
        <code
          data-testid={testId}
          className="flex-1 min-w-0 break-all py-1 text-[12.5px] text-text-05 font-mono"
        >
          {value}
        </code>
        <CopyIconButton getCopyText={() => value} tooltip={`Copy ${label}`} />
      </div>
    </div>
  );
}

export interface WebhookSecretDialogProps {
  credentials: WebhookCredentials;
  /** "created" for a new webhook, "rotated" after new credentials replaced the old. */
  reason: "created" | "rotated";
  onClose: () => void;
}

/** The one time the URL and secret are visible. Closing needs a deliberate step. */
export default function WebhookSecretDialog({
  credentials,
  reason,
  onClose,
}: WebhookSecretDialogProps) {
  const [saved, setSaved] = useState(false);
  const { webhook, url, signing_secret: secret } = credentials;
  const signed = webhook.auth_mode === "standard_webhooks";

  return (
    <Modal open onOpenChange={(open) => !open && saved && onClose()}>
      <Modal.Content width="md" height="lg">
        <Modal.Header
          icon={SvgShield}
          title={reason === "created" ? "Webhook created" : "New credentials"}
          description={`Give these to the system that will call “${webhook.name}”.`}
          onClose={saved ? onClose : undefined}
        />
        <Modal.Body twoTone={false}>
          <div className="flex flex-col gap-4 w-full">
            <div
              className="flex items-start gap-2 rounded-08 border px-3 py-2"
              style={{ borderColor: ACCENT_GLOW_STRONG, backgroundColor: ACCENT_SUBTLE }}
            >
              <SvgAlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0 stroke-text-04" />
              <Text as="p" secondaryBody text04>
                Copy these now. You won&apos;t be able to see them again; if you lose them, rotate
                the webhook to get new ones.
              </Text>
            </div>
            <CopyRow label="URL" value={url} testId="webhook-url" />
            <CopyRow
              label={signed ? "Signing secret" : `Secret for the ${webhook.header_name} header`}
              value={secret}
              testId="webhook-secret"
            />
            <div className="flex flex-col gap-1">
              <Text as="span" mainUiAction text05>
                Try it
              </Text>
              <div className="flex items-start gap-1 rounded-08 border border-border-01 bg-background-tint-01 pl-3 pr-1 py-1">
                <pre className="flex-1 min-w-0 overflow-x-auto py-1 text-[12px] text-text-04 font-mono">
                  {curlExample({
                    url,
                    authMode: webhook.auth_mode,
                    headerName: webhook.header_name,
                    secret,
                  })}
                </pre>
                <CopyIconButton
                  tooltip="Copy command"
                  getCopyText={() =>
                    curlExample({
                      url,
                      authMode: webhook.auth_mode,
                      headerName: webhook.header_name,
                      secret,
                    })
                  }
                />
              </div>
              <Text as="p" secondaryBody text03>
                {signed
                  ? "This signs the request the way your system should. Most languages have a Standard Webhooks library."
                  : "This mode doesn't protect the body or prevent replays. Use signing when your system supports it."}
              </Text>
            </div>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                data-testid="webhook-saved"
                checked={saved}
                onChange={(e) => setSaved(e.target.checked)}
              />
              <Text as="span" mainUiBody text04>
                I&apos;ve saved these somewhere safe
              </Text>
            </label>
          </div>
        </Modal.Body>
        <Modal.Footer>
          <Button disabled={!saved} onClick={onClose}>
            Done
          </Button>
        </Modal.Footer>
      </Modal.Content>
    </Modal>
  );
}
