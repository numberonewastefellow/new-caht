"use client";

import { useEffect, useState } from "react";
import Modal from "@/refresh-components/Modal";
import Button from "@/refresh-components/buttons/Button";
import Text from "@/refresh-components/texts/Text";
import InputTypeIn from "@/refresh-components/inputs/InputTypeIn";
import InputTextArea from "@/refresh-components/inputs/InputTextArea";
import InputSelect from "@/refresh-components/inputs/InputSelect";
import { toast } from "@/hooks/useToast";
import { useWorkflows } from "@/hooks/useWorkflows";
import { useWebhookConfig, useWebhookWorkflowTools } from "@/hooks/useWebhooks";
import { SvgAlertTriangle, SvgLink } from "@opal/icons";
import {
  AUTH_MODE_LABELS,
  createWebhook,
  dedupNeedsPath,
  dedupOptions,
  DEFAULT_SECRET_HEADER,
  defaultDedupSource,
  PulseWebhook,
  refreshWebhooks,
  updateWebhook,
  validateWebhookForm,
  WebhookAuthMode,
  WebhookCredentials,
  WebhookDedupSource,
} from "@/lib/schedules/webhooks";
import { FieldLabel } from "@/sections/schedules/ScheduleModal";
import { ACCENT_GLOW_STRONG, ACCENT_SUBTLE } from "@/sections/schedules/StatusPill";

export interface WebhookModalProps {
  /** Null to create. */
  webhook?: PulseWebhook | null;
  onClose: () => void;
  /** After creating: the URL and secret, which are shown only once. */
  onCreated?: (credentials: WebhookCredentials) => void;
}

function Note({ children, testId }: { children: React.ReactNode; testId?: string }) {
  return (
    <div
      data-testid={testId}
      className="flex items-start gap-2 rounded-08 border px-3 py-2"
      style={{ borderColor: ACCENT_GLOW_STRONG, backgroundColor: ACCENT_SUBTLE }}
    >
      <SvgAlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0 stroke-text-04" />
      <Text as="p" secondaryBody text04>
        {children}
      </Text>
    </div>
  );
}

export default function WebhookModal({ webhook, onClose, onCreated }: WebhookModalProps) {
  const isEdit = !!webhook;
  const { workflows, isLoading: workflowsLoading } = useWorkflows();
  const { config } = useWebhookConfig();

  const [workflowId, setWorkflowId] = useState<number | null>(webhook?.workflow_id ?? null);
  const [name, setName] = useState(webhook?.name ?? "");
  const [message, setMessage] = useState(webhook?.input_message ?? "");
  const [authMode, setAuthMode] = useState<WebhookAuthMode>(webhook?.auth_mode ?? "standard_webhooks");
  const [headerName, setHeaderName] = useState(webhook?.header_name ?? DEFAULT_SECRET_HEADER);
  const [dedupSource, setDedupSource] = useState<WebhookDedupSource>(
    webhook?.dedup_source ?? "webhook_id"
  );
  const [dedupPath, setDedupPath] = useState(webhook?.dedup_path ?? "");
  const [allowedTools, setAllowedTools] = useState<number[]>(webhook?.allowed_tool_ids ?? []);
  const { tools, isLoading: toolsLoading, error: toolsError } = useWebhookWorkflowTools(workflowId);
  // A tool taken off the workflow has no checkbox, so it can't stay in what's saved. If the
  // list didn't load, leave what's saved alone.
  const toolsReady = workflowId != null && !toolsLoading && !toolsError;
  const chosenTools = toolsReady
    ? allowedTools.filter((id) => tools.some((tool) => tool.id === id))
    : undefined;
  const [notifyOnSuccess, setNotifyOnSuccess] = useState(webhook?.notify_on_success ?? false);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // The default template is shown so the owner can see what will be sent, and edit it.
  useEffect(() => {
    if (!isEdit && !message && config?.default_input_message) {
      setMessage(config.default_input_message);
    }
  }, [config?.default_input_message, isEdit, message]);

  // An error is about what was submitted, so it goes once the form changes.
  useEffect(() => {
    setFormError(null);
  }, [workflowId, name, dedupSource, dedupPath]);

  function handleAuthMode(next: WebhookAuthMode) {
    setAuthMode(next);
    setDedupSource(defaultDedupSource(next));
    setDedupPath("");
  }

  async function handleSave() {
    const problem = validateWebhookForm({ name, workflowId, dedupSource, dedupPath });
    if (problem) {
      setFormError(problem);
      return;
    }
    setFormError(null);
    setSaving(true);
    try {
      const path = dedupNeedsPath(dedupSource) ? dedupPath.trim() : null;
      if (webhook) {
        await updateWebhook(webhook.id, {
          name: name.trim(),
          input_message: message,
          dedup_source: dedupSource,
          dedup_path: path,
          allowed_tool_ids: chosenTools,
          notify_on_success: notifyOnSuccess,
        });
        toast.success("Webhook saved");
        onClose();
      } else {
        const credentials = await createWebhook({
          workflow_id: workflowId as number,
          name: name.trim(),
          input_message: message,
          timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
          auth_mode: authMode,
          header_name: authMode === "header_token" ? headerName.trim() : null,
          dedup_source: dedupSource,
          dedup_path: path,
          allowed_tool_ids: chosenTools,
          notify_on_success: notifyOnSuccess,
        });
        onCreated?.(credentials);
      }
      await refreshWebhooks();
    } catch (e) {
      setFormError(e instanceof Error ? e.message : "Could not save the webhook");
    } finally {
      setSaving(false);
    }
  }

  const path = dedupNeedsPath(dedupSource);
  return (
    <Modal open onOpenChange={(open) => !open && onClose()}>
      <Modal.Content width="md" height="lg">
        <Modal.Header
          icon={SvgLink}
          title={isEdit ? "Edit webhook" : "New webhook"}
          description="An outside system calls a URL, and Pulse runs the workflow. Each run becomes its own chat."
          onClose={onClose}
        />
        <Modal.Body twoTone={false}>
          <div className="flex flex-col gap-5 w-full">
            {!isEdit && (
              <Note testId="webhook-runs-as-you">
                Runs use your access: your documents, files and connected accounts. Anyone holding
                this webhook&apos;s credentials can start them, and the data they send is untrusted.
                It&apos;s marked as data for the AI, but that can&apos;t fully prevent an instruction
                hidden in it from being followed, so check what tools the workflow can use.
              </Note>
            )}
            {!isEdit && config && !config.secret_encryption_configured && (
              <Note testId="webhook-no-encryption">
                This server has no encryption key set, so the signing secret is stored unencrypted,
                like other credentials on this server. Ask your admin to set
                ENCRYPTION_KEY_SECRET before using this in production.
              </Note>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <FieldLabel>Workflow</FieldLabel>
                <InputSelect
                  value={workflowId != null ? String(workflowId) : ""}
                  onValueChange={(v) => {
                    setWorkflowId(Number(v));
                    setAllowedTools([]);
                  }}
                  disabled={isEdit}
                >
                  <InputSelect.Trigger
                    placeholder={workflowsLoading ? "Loading workflows…" : "Pick a workflow"}
                  />
                  <InputSelect.Content>
                    {workflows.map((w) => (
                      <InputSelect.Item key={w.id} value={String(w.id)}>
                        {w.name}
                      </InputSelect.Item>
                    ))}
                    {webhook && !workflows.some((w) => w.id === webhook.workflow_id) && (
                      <InputSelect.Item value={String(webhook.workflow_id)}>
                        {webhook.workflow_name ?? `Workflow #${webhook.workflow_id}`}
                      </InputSelect.Item>
                    )}
                  </InputSelect.Content>
                </InputSelect>
              </div>
              <div>
                <FieldLabel htmlFor="webhook-name">Name</FieldLabel>
                <InputTypeIn
                  id="webhook-name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Citizen portal complaints"
                />
              </div>
            </div>

            <div>
              <FieldLabel htmlFor="webhook-message">What the workflow receives</FieldLabel>
              <InputTextArea
                id="webhook-message"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                rows={4}
              />
              <Text as="p" secondaryBody text03 className="pt-1.5">
                {"Use {{payload}} for the whole event, {{payload.ticket.title}} or {{payload.items[0]}} for one value, and {{date}} or {{now}} for the time."}
              </Text>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <FieldLabel>How the caller proves itself</FieldLabel>
                <InputSelect
                  value={authMode}
                  onValueChange={(v) => handleAuthMode(v as WebhookAuthMode)}
                  disabled={isEdit}
                >
                  <InputSelect.Trigger />
                  <InputSelect.Content>
                    {(Object.keys(AUTH_MODE_LABELS) as WebhookAuthMode[]).map((mode) => (
                      <InputSelect.Item key={mode} value={mode}>
                        {AUTH_MODE_LABELS[mode]}
                      </InputSelect.Item>
                    ))}
                  </InputSelect.Content>
                </InputSelect>
                <Text as="p" secondaryBody text03 className="pt-1.5">
                  {authMode === "standard_webhooks"
                    ? "Recommended. Protects the data from being changed and from being replayed later."
                    : "For systems that can't sign. It doesn't protect the body or stop replays."}
                </Text>
              </div>
              {authMode === "header_token" && (
                <div>
                  <FieldLabel htmlFor="webhook-header">Header name</FieldLabel>
                  <InputTypeIn
                    id="webhook-header"
                    value={headerName}
                    onChange={(e) => setHeaderName(e.target.value)}
                    variant={isEdit ? "disabled" : undefined}
                  />
                </div>
              )}
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <FieldLabel>What makes an event a repeat</FieldLabel>
                <InputSelect
                  value={dedupSource}
                  onValueChange={(v) => {
                    setDedupSource(v as WebhookDedupSource);
                    setDedupPath("");
                  }}
                >
                  <InputSelect.Trigger />
                  <InputSelect.Content>
                    {dedupOptions(authMode).map((option) => (
                      <InputSelect.Item key={option.value} value={option.value}>
                        {option.label}
                      </InputSelect.Item>
                    ))}
                  </InputSelect.Content>
                </InputSelect>
                <Text as="p" secondaryBody text03 className="pt-1.5">
                  Systems often retry. A repeat doesn&apos;t run again; the caller gets the first
                  run&apos;s id back.
                </Text>
              </div>
              {path && (
                <div>
                  <FieldLabel htmlFor="webhook-dedup-path">
                    {dedupSource === "header" ? "Header name" : "Field path"}
                  </FieldLabel>
                  <InputTypeIn
                    id="webhook-dedup-path"
                    value={dedupPath}
                    onChange={(e) => setDedupPath(e.target.value)}
                    placeholder={dedupSource === "header" ? "e.g. X-Delivery-Id" : "e.g. event.id"}
                  />
                </div>
              )}
            </div>

            {workflowId != null && (
              <div className="flex flex-col gap-1.5" data-testid="webhook-tools">
                <FieldLabel>Tools its runs can use</FieldLabel>
                <Text as="p" secondaryBody text03>
                  Text sent by the other system is in these runs, and could try to direct the
                  AI. So they can only use the tools you tick. Be careful with tools that send
                  or change things.
                </Text>
                {!toolsReady ? (
                  <Text as="p" secondaryBody text03>
                    {toolsError ? "Couldn't load this workflow's tools." : "Loading tools…"}
                  </Text>
                ) : tools.length === 0 ? (
                  <Text as="p" secondaryBody text03>
                    This workflow&apos;s steps don&apos;t use any tools.
                  </Text>
                ) : (
                  tools.map((tool) => (
                    <label key={tool.id} className="flex items-start gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        className="mt-1"
                        checked={allowedTools.includes(tool.id)}
                        onChange={(e) =>
                          setAllowedTools((current) =>
                            e.target.checked
                              ? [...current, tool.id]
                              : current.filter((id) => id !== tool.id)
                          )
                        }
                      />
                      <span className="flex flex-col min-w-0">
                        <Text as="span" mainUiBody text04>
                          {tool.name}
                        </Text>
                        <Text as="span" secondaryBody text03>
                          Used by: {tool.steps.join(", ")}
                        </Text>
                      </span>
                    </label>
                  ))
                )}
              </div>
            )}

            <label className="flex items-start gap-2 cursor-pointer" data-testid="webhook-notify-on-success">
              <input
                type="checkbox"
                className="mt-1"
                checked={notifyOnSuccess}
                onChange={(e) => setNotifyOnSuccess(e.target.checked)}
              />
              <span className="flex flex-col min-w-0">
                <Text as="span" mainUiBody text04>
                  Notify me when a run succeeds
                </Text>
                <Text as="span" secondaryBody text03>
                  Shows the result in your notifications. Failures notify you either way.
                </Text>
              </span>
            </label>

            {formError && (
              <Text as="p" mainUiBody className="text-status-text-error-05" data-testid="webhook-form-error">
                {formError}
              </Text>
            )}
          </div>
        </Modal.Body>
        <Modal.Footer>
          <Button secondary onClick={onClose}>
            Cancel
          </Button>
          <Button disabled={saving} onClick={handleSave}>
            {isEdit ? "Save" : "Create webhook"}
          </Button>
        </Modal.Footer>
      </Modal.Content>
    </Modal>
  );
}
