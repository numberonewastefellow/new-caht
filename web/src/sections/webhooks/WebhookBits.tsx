"use client";

import { SvgAlertTriangle, SvgCheckCircle, SvgPauseCircle, SvgSlash } from "@opal/icons";
import { disabledReasonText, PulseWebhook, webhookState } from "@/lib/schedules/webhooks";
import { Pill } from "@/sections/schedules/StatusPill";

/** The one word that says whether a call would be accepted right now. */
export function WebhookStateBadge({ webhook }: { webhook: PulseWebhook }) {
  const state = webhookState(webhook);
  if (state === "revoked") {
    return (
      <Pill
        tone="error"
        icon={SvgSlash}
        label="Revoked"
        tooltip="Calls are refused. Rotate it to get new credentials."
      />
    );
  }
  if (state === "attention") {
    return (
      <Pill
        tone="warning"
        icon={SvgAlertTriangle}
        label="Needs attention"
        tooltip={disabledReasonText(webhook.disabled_reason) ?? undefined}
      />
    );
  }
  if (state === "paused") {
    return <Pill tone="muted" icon={SvgPauseCircle} label="Paused" tooltip="Calls are refused." />;
  }
  return <Pill tone="success" icon={SvgCheckCircle} label="Active" />;
}
