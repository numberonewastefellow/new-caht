"use client";

import React, { useEffect, useState } from "react";
import useSWR from "swr";
import { SvgSettings } from "@opal/icons";

import { AdminPageTitle } from "@/components/admin/Title";
import CardSection from "@/components/admin/CardSection";
import Text from "@/refresh-components/texts/Text";
import Button from "@/refresh-components/buttons/Button";
import Switch from "@/refresh-components/inputs/Switch";
import InputTypeIn from "@/refresh-components/inputs/InputTypeIn";
import InputTextArea from "@/refresh-components/inputs/InputTextArea";
import { ThreeDotsLoader } from "@/components/Loading";
import { errorHandlingFetcher } from "@/lib/fetcher";

// Mirror of the backend AppSettingsSchema.
interface AppSettings {
  application_name: string | null;
  use_custom_logo: boolean;
  use_custom_logotype: boolean;
  logo_display_style: "logo_and_name" | "logo_only" | "name_only" | null;
  custom_nav_items: unknown[];
  two_lines_for_chat_header: boolean | null;
  custom_lower_disclaimer_content: string | null;
  custom_header_content: string | null;
  custom_popup_header: string | null;
  custom_popup_content: string | null;
  enable_consent_screen: boolean | null;
  consent_screen_prompt: string | null;
  show_first_visit_notice: boolean | null;
  custom_greeting_message: string | null;
  feature_flags: Record<string, boolean>;
}

const FEATURE_TOGGLES: { key: string; label: string; hint: string }[] = [
  { key: "analytics", label: "Analytics", hint: "Show the analytics dashboard." },
  {
    key: "query_history",
    label: "Query history",
    hint: "Allow admins to browse past chat sessions.",
  },
  { key: "reports", label: "Reports", hint: "Enable usage report generation." },
];

function FieldRow({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1 py-3 border-b last:border-b-0">
      <Text mainUiBody>{label}</Text>
      {hint && (
        <Text secondaryBody text03>
          {hint}
        </Text>
      )}
      <div className="mt-1">{children}</div>
    </div>
  );
}

export default function AppSettingsPage() {
  const settingsUrl = "/api/enterprise-settings";
  const { data, isLoading, mutate } = useSWR<AppSettings>(
    settingsUrl,
    errorHandlingFetcher
  );

  const [draft, setDraft] = useState<AppSettings | null>(null);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState<string | null>(null);

  useEffect(() => {
    if (data) setDraft(data);
  }, [data]);

  function patch(update: Partial<AppSettings>) {
    setDraft((prev) => (prev ? { ...prev, ...update } : prev));
    setStatus(null);
  }

  function patchFlag(key: string, value: boolean) {
    setDraft((prev) =>
      prev
        ? { ...prev, feature_flags: { ...prev.feature_flags, [key]: value } }
        : prev
    );
    setStatus(null);
  }

  async function handleSave() {
    if (!draft) return;
    setSaving(true);
    setStatus(null);
    try {
      const response = await fetch("/api/admin/enterprise-settings", {
        method: "PUT",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(draft),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail || "Failed to save settings");
      }
      await mutate();
      setStatus("Saved");
    } catch (e) {
      setStatus(e instanceof Error ? e.message : "Failed to save settings");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      <AdminPageTitle
        icon={SvgSettings}
        title="App Settings"
        description="Branding, chat customization and feature toggles for this workspace."
      />

      {isLoading || !draft ? (
        <div className="mt-10">
          <ThreeDotsLoader />
        </div>
      ) : (
        <div className="flex flex-col gap-4 mt-4">
          <CardSection>
            <div className="mb-2">
              <Text mainUiBody>Branding</Text>
            </div>
            <FieldRow label="Application name">
              <InputTypeIn
                value={draft.application_name ?? ""}
                showClearButton={false}
                placeholder="VertualAI"
                onChange={(e) =>
                  patch({ application_name: e.target.value || null })
                }
              />
            </FieldRow>
            <FieldRow label="Custom greeting message">
              <InputTextArea
                value={draft.custom_greeting_message ?? ""}
                rows={2}
                placeholder="Welcome message shown on the home screen"
                onChange={(e) =>
                  patch({ custom_greeting_message: e.target.value || null })
                }
              />
            </FieldRow>
            <FieldRow label="Header content">
              <InputTextArea
                value={draft.custom_header_content ?? ""}
                rows={2}
                onChange={(e) =>
                  patch({ custom_header_content: e.target.value || null })
                }
              />
            </FieldRow>
            <FieldRow label="Lower disclaimer">
              <InputTextArea
                value={draft.custom_lower_disclaimer_content ?? ""}
                rows={2}
                onChange={(e) =>
                  patch({
                    custom_lower_disclaimer_content: e.target.value || null,
                  })
                }
              />
            </FieldRow>
          </CardSection>

          <CardSection>
            <div className="mb-2">
              <Text mainUiBody>Chat experience</Text>
            </div>
            <FieldRow
              label="Two-line chat header"
              hint="Show the assistant name on a second line."
            >
              <Switch
                checked={Boolean(draft.two_lines_for_chat_header)}
                onCheckedChange={(v) => patch({ two_lines_for_chat_header: v })}
              />
            </FieldRow>
            <FieldRow
              label="First-visit notice"
              hint="Display a popup the first time a user visits."
            >
              <Switch
                checked={Boolean(draft.show_first_visit_notice)}
                onCheckedChange={(v) => patch({ show_first_visit_notice: v })}
              />
            </FieldRow>
            <FieldRow
              label="Consent screen"
              hint="Require users to accept a consent prompt before chatting."
            >
              <Switch
                checked={Boolean(draft.enable_consent_screen)}
                onCheckedChange={(v) => patch({ enable_consent_screen: v })}
              />
            </FieldRow>
            {draft.enable_consent_screen && (
              <FieldRow label="Consent prompt">
                <InputTextArea
                  value={draft.consent_screen_prompt ?? ""}
                  rows={2}
                  onChange={(e) =>
                    patch({ consent_screen_prompt: e.target.value || null })
                  }
                />
              </FieldRow>
            )}
          </CardSection>

          <CardSection>
            <div className="mb-2">
              <Text mainUiBody>Feature toggles</Text>
            </div>
            {FEATURE_TOGGLES.map((toggle) => (
              <FieldRow key={toggle.key} label={toggle.label} hint={toggle.hint}>
                <Switch
                  checked={Boolean(draft.feature_flags?.[toggle.key])}
                  onCheckedChange={(v) => patchFlag(toggle.key, v)}
                />
              </FieldRow>
            ))}
          </CardSection>

          <div className="flex items-center gap-3">
            <Button main onClick={handleSave} disabled={saving}>
              {saving ? "Saving…" : "Save settings"}
            </Button>
            {status && (
              <Text secondaryBody text03>
                {status}
              </Text>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
