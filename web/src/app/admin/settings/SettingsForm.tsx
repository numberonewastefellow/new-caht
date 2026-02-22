"use client";

import { Label, SubLabel } from "@/components/Field";
import { toast } from "@/hooks/useToast";
import Title from "@/components/ui/title";
import Button from "@/refresh-components/buttons/Button";
import { Settings } from "./interfaces";
import { useRouter } from "next/navigation";
import React, { useContext, useState, useEffect } from "react";
import { SettingsContext } from "@/providers/SettingsProvider";
import { usePaidEnterpriseFeaturesEnabled } from "@/components/settings/usePaidEnterpriseFeaturesEnabled";
import Modal from "@/refresh-components/Modal";
import { AuthType, NEXT_PUBLIC_CLOUD_ENABLED } from "@/lib/constants";
import { AnonymousUserPath } from "./AnonymousUserPath";
import LLMSelector from "@/components/llm/LLMSelector";
import { useVisionProviders } from "./hooks/useVisionProviders";
import InputTextArea from "@/refresh-components/inputs/InputTextArea";
import { SvgAlertTriangle } from "@opal/icons";
import { useUser } from "@/providers/UserProvider";
import CardSection from "@/components/admin/CardSection";

export function Checkbox({
  label,
  sublabel,
  checked,
  onChange,
}: {
  label: string;
  sublabel?: string;
  checked: boolean;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
}) {
  return (
    <label className="flex text-xs cursor-pointer py-2">
      <input
        checked={checked}
        onChange={onChange}
        type="checkbox"
        className="mr-3 w-4 h-4 my-auto rounded accent-[var(--virtualai-accent,var(--theme-primary-05))]"
      />
      <div>
        <span className="block font-medium text-text-05 text-sm">
          {label}
        </span>
        {sublabel && <SubLabel>{sublabel}</SubLabel>}
      </div>
    </label>
  );
}

function IntegerInput({
  label,
  sublabel,
  value,
  onChange,
  id,
  placeholder = "Enter a number", // Default placeholder if none is provided
}: {
  label: string;
  sublabel: string;
  value: number | null;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  id?: string;
  placeholder?: string;
}) {
  return (
    <label className="flex flex-col text-sm mb-4">
      <Label>{label}</Label>
      <SubLabel>{sublabel}</SubLabel>
      <input
        type="number"
        className="mt-1.5 p-2.5 border border-border-01 rounded-08 w-full max-w-xs bg-background-neutral-00 text-text-05 placeholder:text-text-02 focus:outline-none focus:ring-2 focus:ring-[var(--virtualai-accent,var(--theme-primary-05))] focus:ring-opacity-30 transition-shadow"
        value={value ?? ""}
        onChange={onChange}
        min="1"
        step="1"
        id={id}
        placeholder={placeholder}
      />
    </label>
  );
}

export function SettingsForm() {
  const router = useRouter();
  const { authTypeMetadata } = useUser();
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [settings, setSettings] = useState<Settings | null>(null);
  const [chatRetention, setChatRetention] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [companyDescription, setCompanyDescription] = useState("");
  const isEnterpriseEnabled = usePaidEnterpriseFeaturesEnabled();

  const {
    visionProviders,
    visionLLM,
    setVisionLLM,
    updateDefaultVisionProvider,
  } = useVisionProviders();

  const combinedSettings = useContext(SettingsContext);

  useEffect(() => {
    if (combinedSettings) {
      setSettings(combinedSettings.settings);
      setChatRetention(
        combinedSettings.settings.maximum_chat_retention_days?.toString() || ""
      );
      setCompanyName(combinedSettings.settings.company_name || "");
      setCompanyDescription(
        combinedSettings.settings.company_description || ""
      );
    }
    // We don't need to fetch vision providers here anymore as the hook handles it
  }, []);

  if (!settings) {
    return null;
  }

  const showInviteOnlyModeToggle =
    authTypeMetadata.authType === AuthType.BASIC ||
    authTypeMetadata.authType === AuthType.GOOGLE_OAUTH;

  async function updateSettingField(
    updateRequests: { fieldName: keyof Settings; newValue: any }[]
  ) {
    // Optimistically update the local state
    const newSettings: Settings | null = settings
      ? {
          ...settings,
          ...updateRequests.reduce((acc, { fieldName, newValue }) => {
            acc[fieldName] = newValue ?? settings[fieldName];
            return acc;
          }, {} as Partial<Settings>),
        }
      : null;
    setSettings(newSettings);

    try {
      const response = await fetch("/api/admin/settings", {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(newSettings),
      });

      if (!response.ok) {
        const errorMsg = (await response.json()).detail;
        throw new Error(errorMsg);
      }

      router.refresh();
      toast.success("Settings updated successfully!");
    } catch (error) {
      // Revert the optimistic update
      setSettings(settings);
      console.error("Error updating settings:", error);
      toast.error("Failed to update settings");
    }
  }

  function handleToggleSettingsField(
    fieldName: keyof Settings,
    checked: boolean
  ) {
    if (fieldName === "anonymous_user_enabled" && checked) {
      setShowConfirmModal(true);
    } else {
      const updates: { fieldName: keyof Settings; newValue: any }[] = [
        { fieldName, newValue: checked },
      ];
      updateSettingField(updates);
    }
  }

  function handleConfirmAnonymousUsers() {
    const updates: { fieldName: keyof Settings; newValue: any }[] = [
      { fieldName: "anonymous_user_enabled", newValue: true },
    ];
    updateSettingField(updates);
    setShowConfirmModal(false);
  }

  function handleSetChatRetention() {
    const newValue = chatRetention === "" ? null : parseInt(chatRetention, 10);
    updateSettingField([
      { fieldName: "maximum_chat_retention_days", newValue },
    ]);
  }

  function handleClearChatRetention() {
    setChatRetention("");
    updateSettingField([
      { fieldName: "maximum_chat_retention_days", newValue: null },
    ]);
  }

  function handleCompanyNameBlur() {
    const originalValue = settings?.company_name || "";
    if (companyName !== originalValue) {
      updateSettingField([
        { fieldName: "company_name", newValue: companyName || null },
      ]);
    }
  }

  function handleCompanyDescriptionBlur() {
    const originalValue = settings?.company_description || "";
    if (companyDescription !== originalValue) {
      updateSettingField([
        {
          fieldName: "company_description",
          newValue: companyDescription || null,
        },
      ]);
    }
  }

  return (
    <div className="space-y-6">
      {/* Organization Profile Section */}
      <CardSection>
        <Title className="mb-4">Organization Profile</Title>
        <div className="space-y-4">
          <label className="flex flex-col text-sm">
            <Label>Company Name</Label>
            <SubLabel>
              Set the company name used for search and chat context.
            </SubLabel>
            <input
              type="text"
              className="mt-1.5 p-2.5 border border-border-01 rounded-08 w-full max-w-xl bg-background-neutral-00 text-text-05 placeholder:text-text-02 focus:outline-none focus:ring-2 focus:ring-[var(--virtualai-accent,var(--theme-primary-05))] focus:ring-opacity-30 transition-shadow"
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
              onBlur={handleCompanyNameBlur}
              placeholder="Enter company name"
            />
          </label>

          <label className="flex flex-col text-sm">
            <Label>Company Description</Label>
            <SubLabel>
              Provide a short description of the company for search and chat
              context.
            </SubLabel>
            <InputTextArea
              className="mt-1.5 w-full max-w-xl"
              value={companyDescription}
              onChange={(event) => setCompanyDescription(event.target.value)}
              onBlur={handleCompanyDescriptionBlur}
              placeholder="Enter company description"
              rows={4}
            />
          </label>
        </div>
      </CardSection>

      {/* AI Behavior Section */}
      <CardSection>
        <Title className="mb-4">AI Behavior</Title>
        <div className="space-y-1">
          <Checkbox
            label="Auto-scroll"
            sublabel="If set, the chat window will automatically scroll to the bottom as new lines of text are generated by the AI model. This can be overridden by individual user settings."
            checked={settings.auto_scroll}
            onChange={(e) =>
              handleToggleSettingsField("auto_scroll", e.target.checked)
            }
          />
          <Checkbox
            label="Override default temperature"
            sublabel="If set, users will be able to override the default temperature for each assistant."
            checked={settings.temperature_override_enabled}
            onChange={(e) =>
              handleToggleSettingsField(
                "temperature_override_enabled",
                e.target.checked
              )
            }
          />
          <Checkbox
            label="Deep Research Mode"
            sublabel="Enable multi-step deep research for complex queries. Uses significantly more tokens (~10x) for thorough analysis."
            checked={settings.deep_research_enabled ?? true}
            onChange={(e) =>
              handleToggleSettingsField("deep_research_enabled", e.target.checked)
            }
          />
          <Checkbox
            label="Hide Default Agent"
            sublabel="When enabled, new sessions start with the current agent instead of the default. The default agent will be hidden from all members."
            checked={settings.disable_default_assistant ?? false}
            onChange={(e) =>
              handleToggleSettingsField(
                "disable_default_assistant",
                e.target.checked
              )
            }
          />
        </div>
      </CardSection>

      {/* Access & Security Section */}
      <CardSection>
        <Title className="mb-4">Access & Security</Title>
        <div className="space-y-1">
          <Checkbox
            label="Guest Access"
            sublabel="Allow unauthenticated users to interact with AI without signing in."
            checked={settings.anonymous_user_enabled}
            onChange={(e) =>
              handleToggleSettingsField("anonymous_user_enabled", e.target.checked)
            }
          />
          {showInviteOnlyModeToggle && (
            <Checkbox
              label="Whitelist / Invite-only"
              sublabel="If set, only users on the invite list can join this workspace. If unset, users from your normal sign-up domain flow can still join even if invites exist."
              checked={settings.invite_only_enabled}
              onChange={(e) =>
                handleToggleSettingsField("invite_only_enabled", e.target.checked)
              }
            />
          )}
        </div>
        {NEXT_PUBLIC_CLOUD_ENABLED && settings.anonymous_user_enabled && (
          <div className="mt-4">
            <AnonymousUserPath />
          </div>
        )}
      </CardSection>

      {showConfirmModal && (
        <Modal open onOpenChange={() => setShowConfirmModal(false)}>
          <Modal.Content>
            <Modal.Header
              icon={SvgAlertTriangle}
              title="Enable Guest Access"
              onClose={() => setShowConfirmModal(false)}
            />
            <Modal.Body>
              <p>
                Are you sure you want to enable guest access? This will allow
                anyone to use the platform without signing in.
              </p>
            </Modal.Body>
            <Modal.Footer>
              <Button secondary onClick={() => setShowConfirmModal(false)}>
                Cancel
              </Button>
              <Button onClick={handleConfirmAnonymousUsers}>Confirm</Button>
            </Modal.Footer>
          </Modal.Content>
        </Modal>
      )}

      {/* Conversation Retention Section (Enterprise) */}
      {isEnterpriseEnabled && (
        <CardSection>
          <Title className="mb-4">Conversation Settings</Title>
          <IntegerInput
            label="Conversation Retention"
            sublabel="Maximum days to retain conversation history. Leave empty for unlimited retention."
            value={chatRetention === "" ? null : Number(chatRetention)}
            onChange={(e) => {
              const numValue = parseInt(e.target.value, 10);
              if (numValue >= 1 || e.target.value === "") {
                setChatRetention(e.target.value);
              }
            }}
            id="chatRetentionInput"
            placeholder="Infinite Retention"
          />
          <div className="flex gap-2">
            <Button onClick={handleSetChatRetention}>
              Set Retention Limit
            </Button>
            <Button secondary onClick={handleClearChatRetention}>
              Retain All
            </Button>
          </div>
        </CardSection>
      )}

      {/* Vision & Image Analysis Section */}
      <CardSection>
        <Title className="mb-4">Vision & Image Analysis</Title>
        <div className="space-y-2">
          <Checkbox
            label="Enable Image Extraction and Analysis"
            sublabel="Extract and analyze images from documents during indexing. This allows the system to process images and create searchable descriptions of them."
            checked={settings.image_extraction_and_analysis_enabled ?? false}
            onChange={(e) =>
              handleToggleSettingsField(
                "image_extraction_and_analysis_enabled",
                e.target.checked
              )
            }
          />

          <Checkbox
            label="Enable Search-time Image Analysis"
            sublabel="Analyze images at search time when a user asks about images. This provides more detailed and query-specific image analysis but may increase search-time latency."
            checked={settings.search_time_image_analysis_enabled ?? false}
            onChange={(e) =>
              handleToggleSettingsField(
                "search_time_image_analysis_enabled",
                e.target.checked
              )
            }
          />

          <IntegerInput
            label="Maximum Image Size for Analysis (MB)"
            sublabel="Images larger than this size will not be analyzed to prevent excessive resource usage."
            value={settings.image_analysis_max_size_mb ?? null}
            onChange={(e) => {
              const value = e.target.value ? parseInt(e.target.value) : null;
              if (value !== null && !isNaN(value) && value > 0) {
                updateSettingField([
                  { fieldName: "image_analysis_max_size_mb", newValue: value },
                ]);
              }
            }}
            id="image-analysis-max-size"
            placeholder="Enter maximum size in MB"
          />

          <div className="mt-4 pt-4 border-t border-border-01">
            <Label>Default Vision LLM</Label>
            <SubLabel>
              Select the default LLM to use for image analysis. This model will be
              utilized during image indexing and at query time for search results,
              if the above settings are enabled.
            </SubLabel>

            <div className="mt-2 max-w-xs">
              {!visionProviders || visionProviders.length === 0 ? (
                <div className="text-sm text-text-02">
                  No vision providers found. Please add a vision provider.
                </div>
              ) : visionProviders.length > 0 ? (
                <>
                  <LLMSelector
                    userSettings={false}
                    llmProviders={visionProviders.map((provider) => ({
                      ...provider,
                      model_names: provider.vision_models,
                      display_model_names: provider.vision_models,
                    }))}
                    currentLlm={visionLLM}
                    onSelect={(value) => setVisionLLM(value)}
                  />
                  <Button
                    onClick={() => updateDefaultVisionProvider(visionLLM)}
                  >
                    Set Default Vision LLM
                  </Button>
                </>
              ) : (
                <div className="text-sm text-text-02">
                  No vision-capable LLMs found. Please add an LLM provider that
                  supports image input.
                </div>
              )}
            </div>
          </div>
        </div>
      </CardSection>
    </div>
  );
}
