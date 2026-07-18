"use client";

import React, { useState, useRef, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import * as SettingsLayouts from "@/layouts/settings-layouts";
import * as GeneralLayouts from "@/layouts/general-layouts";
import Button from "@/refresh-components/buttons/Button";
import { FullAgent } from "@/app/admin/assistants/interfaces";
import { buildImgUrl } from "@/app/app/components/files/images/utils";
import { Formik, Form, FieldArray } from "formik";
import * as Yup from "yup";
import InputTypeInField from "@/refresh-components/form/InputTypeInField";
import InputTextAreaField from "@/refresh-components/form/InputTextAreaField";
import InputTypeInElementField from "@/refresh-components/form/InputTypeInElementField";
import InputDatePickerField from "@/refresh-components/form/InputDatePickerField";
import Separator from "@/refresh-components/Separator";
import * as InputLayouts from "@/layouts/input-layouts";
import { useFormikContext } from "formik";
import LLMSelector from "@/components/llm/LLMSelector";
import { parseLlmDescriptor, structureValue } from "@/lib/llm/utils";
import { useLLMProviders } from "@/lib/hooks/useLLMProviders";
import {
  STARTER_MESSAGES_EXAMPLES,
  MAX_CHARACTERS_STARTER_MESSAGE,
  MAX_CHARACTERS_AGENT_DESCRIPTION,
  MAX_CHUNKS_FED_TO_CHAT,
} from "@/lib/constants";
import {
  IMAGE_GENERATION_TOOL_ID,
  WEB_SEARCH_TOOL_ID,
  PYTHON_TOOL_ID,
  SEARCH_TOOL_ID,
  OPEN_URL_TOOL_ID,
  FILE_READER_TOOL_ID,
} from "@/app/app/components/tools/constants";
import Text from "@/refresh-components/texts/Text";
import { Card } from "@/refresh-components/cards";
import SwitchField from "@/refresh-components/form/SwitchField";
import SimpleTooltip from "@/refresh-components/SimpleTooltip";
import { useDocumentSets } from "@/app/admin/documents/sets/hooks";
import { useWorkspacesContext } from "@/providers/WorkspacesContext";
import { useCreateModal } from "@/refresh-components/contexts/ModalContext";
import { toast } from "@/hooks/useToast";
import KnowledgeFilesModal from "@/components/modals/KnowledgeFilesModal";
import {
  WorkspaceFile,
  KnowledgeFileStatus,
} from "@/app/app/workspaces/workspacesService";
import Popover, { PopoverMenu } from "@/refresh-components/Popover";
import LineItem from "@/refresh-components/buttons/LineItem";
import {
  SvgActions,
  SvgArrowLeft,
  SvgArrowRight,
  SvgBookOpen,
  SvgBubbleText,
  SvgCheck,
  SvgExpand,
  SvgFold,
  SvgImage,
  SvgLock,
  SvgOnyxOctagon,
  SvgSettings,
  SvgShield,
  SvgSliders,
  SvgSparkle,
  SvgTrash,
  SvgUser,
} from "@opal/icons";
import { cn } from "@/lib/utils";
import { IconProps } from "@opal/types";
import CustomAgentAvatar, {
  agentAvatarIconMap,
} from "@/refresh-components/avatars/CustomAgentAvatar";
import InputAvatar from "@/refresh-components/inputs/InputAvatar";
import SquareButton from "@/refresh-components/buttons/SquareButton";
import { useAgents } from "@/hooks/useAgents";
import {
  createAgent,
  updateAgent,
  AgentUpsertParameters,
} from "@/app/admin/assistants/lib";
import useMcpServersForAgentEditor from "@/hooks/useMcpServersForAgentEditor";
import useOpenApiTools from "@/hooks/useOpenApiTools";
import { useAvailableTools } from "@/hooks/useAvailableTools";
import * as ActionsLayouts from "@/layouts/actions-layouts";
import * as ExpandableCard from "@/layouts/expandable-card-layouts";
import { getActionIcon } from "@/lib/tools/mcpUtils";
import { MCPServer, MCPTool, ToolSnapshot } from "@/lib/tools/interfaces";
import InputTypeIn from "@/refresh-components/inputs/InputTypeIn";
import useFilter from "@/hooks/useFilter";
import EnabledCount from "@/refresh-components/EnabledCount";
import { useAppRouter } from "@/hooks/appNavigation";
import { deleteAgent } from "@/lib/agents";
import ConfirmationModalLayout from "@/refresh-components/layouts/ConfirmationModalLayout";
import ShareAgentModal from "@/sections/modals/ShareAgentModal";
import AgentKnowledgePane from "@/sections/knowledge/AgentKnowledgePane";
import { ValidSources } from "@/lib/types";
import { useSettingsContext } from "@/providers/SettingsProvider";

// ─── Wizard Step Configuration ───────────────────────────────────────────────

const TOTAL_STEPS = 3;

const STEP_CONFIG = [
  { label: "Identity", subtitle: "Name & personality", icon: SvgUser, color: "blue" },
  { label: "Knowledge & Tools", subtitle: "Data & capabilities", icon: SvgBookOpen, color: "purple" },
  { label: "Configure & Share", subtitle: "Fine-tune & publish", icon: SvgSettings, color: "green" },
] as const;

// Which Formik field names belong to each step (for per-step validation gating)
const STEP_FIELDS: string[][] = [
  ["name", "description", "icon_name", "uploaded_image_id", "remove_image", "instructions", "starter_messages"],
  [
    "enable_knowledge", "document_set_ids", "document_ids", "hierarchy_node_ids",
    "knowledge_file_ids", "selected_sources", "image_generation", "web_search",
    "open_url", "code_interpreter", "file_reader",
  ],
  [
    "llm_model_provider_override", "llm_model_version_override", "knowledge_cutoff_date",
    "replace_base_system_prompt", "reminders", "shared_user_ids", "shared_group_ids", "is_public",
  ],
];

// CSS variable color mapping per step color name
const DEFAULT_STEP_COLOR = { bg01: "var(--theme-blue-01)", bg05: "var(--theme-blue-05)", text04: "var(--theme-blue-04)" } as const;

const STEP_COLORS: Record<string, { bg01: string; bg05: string; text04: string }> = {
  blue:   DEFAULT_STEP_COLOR,
  purple: { bg01: "var(--theme-purple-01)", bg05: "var(--theme-purple-05)", text04: "var(--theme-purple-04)" },
  green:  { bg01: "var(--theme-green-01)",  bg05: "var(--theme-green-05)",  text04: "var(--theme-green-04)" },
};

// ─── Step Indicator Component ────────────────────────────────────────────────

function StepIndicator({ currentStep, onStepClick }: { currentStep: number; onStepClick?: (step: number) => void }) {
  return (
    <div className="flex items-center gap-2 px-4 py-5">
      {STEP_CONFIG.map((step, i) => {
        const isCurrent = i === currentStep;
        const isCompleted = i < currentStep;
        const isFuture = i > currentStep;
        const colors = STEP_COLORS[step.color] ?? DEFAULT_STEP_COLOR;
        const StepIcon = step.icon;

        return (
          <React.Fragment key={i}>
            <div
              className={cn(
                "flex items-center gap-2.5 min-w-0",
                (isCompleted && onStepClick) && "cursor-pointer"
              )}
              onClick={() => isCompleted && onStepClick?.(i)}
            >
              {/* Icon circle */}
              <div
                className="w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0 transition-all duration-300"
                style={{
                  backgroundColor: isCurrent ? colors.bg05 : isCompleted ? colors.bg01 : "var(--background-tint-03)",
                }}
              >
                {isCompleted ? (
                  <SvgCheck className="w-4 h-4" style={{ stroke: colors.bg05 }} />
                ) : (
                  <StepIcon
                    className="w-4 h-4"
                    style={{ stroke: isCurrent ? "var(--background-tint-00)" : "var(--text-02)" }}
                  />
                )}
              </div>

              {/* Label + subtitle */}
              <div className="flex flex-col min-w-0">
                <Text
                  as="span"
                  mainUiAction
                  className="truncate"
                  style={{
                    color: isCurrent ? colors.bg05 : isFuture ? "var(--text-02)" : "var(--text-04)",
                  }}
                >
                  {step.label}
                </Text>
                <Text
                  as="span"
                  secondaryBody
                  className="truncate"
                  style={{
                    color: isCurrent ? colors.text04 : "var(--text-02)",
                  }}
                >
                  {step.subtitle}
                </Text>
              </div>
            </div>

            {/* Connector line */}
            {i < STEP_CONFIG.length - 1 && (
              <div
                className="flex-1 h-0.5 rounded-full transition-colors duration-300"
                style={{
                  backgroundColor: isCompleted ? colors.bg05 : "var(--background-tint-03)",
                }}
              />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}

// ─── Section Header Component ────────────────────────────────────────────────

function WizardSectionHeader({ icon: Icon, title, description, color }: {
  icon: React.FunctionComponent<IconProps>;
  title: string;
  description: string;
  color: string;
}) {
  const colors = STEP_COLORS[color] ?? DEFAULT_STEP_COLOR;
  return (
    <div className="flex items-start gap-3 mb-1">
      <div
        className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5"
        style={{ backgroundColor: colors.bg01 }}
      >
        <Icon className="w-4 h-4" style={{ stroke: colors.bg05 }} />
      </div>
      <div className="flex flex-col">
        <Text as="p" mainContentEmphasis>{title}</Text>
        <Text as="p" secondaryBody text03>{description}</Text>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────

interface AgentIconEditorProps {
  existingAgent?: FullAgent | null;
}

function FormWarningsEffect() {
  const { values, setStatus } = useFormikContext<{
    web_search: boolean;
    open_url: boolean;
  }>();

  useEffect(() => {
    const warnings: Record<string, string> = {};
    if (values.web_search && !values.open_url) {
      warnings.open_url =
        "Web Search without the ability to open URLs can lead to significantly worse web based results.";
    }
    setStatus({ warnings });
  }, [values.web_search, values.open_url, setStatus]);

  return null;
}

function AgentIconEditor({ existingAgent }: AgentIconEditorProps) {
  const { values, setFieldValue } = useFormikContext<{
    name: string;
    icon_name: string | null;
    uploaded_image_id: string | null;
    remove_image: boolean | null;
  }>();
  const [uploadedImagePreview, setUploadedImagePreview] = useState<
    string | null
  >(null);
  const [popoverOpen, setPopoverOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  async function handleImageUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    // Clear previous preview to free memory
    setUploadedImagePreview(null);

    // Clear selected icon and remove_image flag when uploading an image
    setFieldValue("icon_name", null);
    setFieldValue("remove_image", false);

    // Show preview immediately
    const reader = new FileReader();
    reader.onloadend = () => {
      setUploadedImagePreview(reader.result as string);
    };
    reader.readAsDataURL(file);

    // Upload the file
    try {
      const formData = new FormData();
      formData.append("file", file);
      const response = await fetch("/api/admin/agent/upload-image", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        console.error("Failed to upload image");
        setUploadedImagePreview(null);
        return;
      }

      const { file_id } = await response.json();
      setFieldValue("uploaded_image_id", file_id);
      setPopoverOpen(false);
    } catch (error) {
      console.error("Upload error:", error);
      setUploadedImagePreview(null);
    }
  }

  const imageSrc = uploadedImagePreview
    ? uploadedImagePreview
    : values.uploaded_image_id
      ? buildImgUrl(values.uploaded_image_id)
      : values.icon_name
        ? undefined
        : values.remove_image
          ? undefined
          : existingAgent?.uploaded_image_id
            ? buildImgUrl(existingAgent.uploaded_image_id)
            : undefined;

  function handleIconClick(iconName: string | null) {
    setFieldValue("icon_name", iconName);
    setFieldValue("uploaded_image_id", null);
    setFieldValue("remove_image", true);
    setUploadedImagePreview(null);
    setPopoverOpen(false);

    // Reset the file input so the same file can be uploaded again later
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }

  return (
    <>
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        onChange={handleImageUpload}
        className="hidden"
      />

      <Popover open={popoverOpen} onOpenChange={setPopoverOpen}>
        <Popover.Trigger asChild>
          <InputAvatar className="group/InputAvatar relative flex flex-col items-center justify-center h-[7.5rem] w-[7.5rem]">
            {/* We take the `InputAvatar`'s height/width (in REM) and multiply it by 16 (the REM -> px conversion factor). */}
            <CustomAgentAvatar
              size={imageSrc ? 7.5 * 16 : 40}
              src={imageSrc}
              iconName={values.icon_name ?? undefined}
              name={values.name}
            />
            <Button
              className="absolute bottom-0 left-1/2 -translate-x-1/2 h-[1.75rem] mb-2 invisible group-hover/InputAvatar:visible"
              secondary
            >
              Edit
            </Button>
          </InputAvatar>
        </Popover.Trigger>
        <Popover.Content>
          <PopoverMenu>
            {[
              <LineItem
                key="upload-image"
                icon={SvgImage}
                onClick={() => fileInputRef.current?.click()}
                emphasized
              >
                Upload Image
              </LineItem>,
              null,
              <div className="grid grid-cols-4 gap-1">
                <SquareButton
                  key="default-icon"
                  icon={() => (
                    <CustomAgentAvatar name={values.name} size={30} />
                  )}
                  onClick={() => handleIconClick(null)}
                  transient={!imageSrc && values.icon_name === null}
                />
                {Object.keys(agentAvatarIconMap).map((iconName) => (
                  <SquareButton
                    key={iconName}
                    onClick={() => handleIconClick(iconName)}
                    icon={() => (
                      <CustomAgentAvatar iconName={iconName} size={30} />
                    )}
                    transient={values.icon_name === iconName}
                  />
                ))}
              </div>,
            ]}
          </PopoverMenu>
        </Popover.Content>
      </Popover>
    </>
  );
}

interface OpenApiToolCardProps {
  tool: ToolSnapshot;
}

function OpenApiToolCard({ tool }: OpenApiToolCardProps) {
  const toolFieldName = `openapi_tool_${tool.id}`;

  return (
    <ExpandableCard.Root defaultFolded>
      <ActionsLayouts.Header
        title={tool.display_name || tool.name}
        description={tool.description}
        icon={SvgActions}
        rightChildren={<SwitchField name={toolFieldName} />}
      />
    </ExpandableCard.Root>
  );
}

interface MCPServerCardProps {
  server: MCPServer;
  tools: MCPTool[];
  isLoading: boolean;
}

function MCPServerCard({
  server,
  tools: enabledTools,
  isLoading,
}: MCPServerCardProps) {
  const [isFolded, setIsFolded] = useState(false);
  const { values, setFieldValue, getFieldMeta } = useFormikContext<any>();
  const serverFieldName = `mcp_server_${server.id}`;
  const isServerEnabled = values[serverFieldName]?.enabled ?? false;
  const {
    query,
    setQuery,
    filtered: filteredTools,
  } = useFilter(enabledTools, (tool) => `${tool.name} ${tool.description}`);

  // Calculate enabled and total tool counts
  const enabledCount = enabledTools.filter((tool) => {
    const toolFieldValue = values[serverFieldName]?.[`tool_${tool.id}`];
    return toolFieldValue === true;
  }).length;

  return (
    <ExpandableCard.Root isFolded={isFolded} onFoldedChange={setIsFolded}>
      <ActionsLayouts.Header
        title={server.name}
        description={server.description}
        icon={getActionIcon(server.server_url, server.name)}
        rightChildren={
          <GeneralLayouts.Section flexDirection="row" gap={0.5}>
            <EnabledCount
              enabledCount={enabledCount}
              totalCount={enabledTools.length}
            />
            <SwitchField
              name={`${serverFieldName}.enabled`}
              onCheckedChange={(checked) => {
                enabledTools.forEach((tool) => {
                  setFieldValue(`${serverFieldName}.tool_${tool.id}`, checked);
                });
                if (!checked) return;
                setIsFolded(false);
              }}
            />
          </GeneralLayouts.Section>
        }
      >
        <GeneralLayouts.Section flexDirection="row" gap={0.5}>
          <InputTypeIn
            placeholder="Search tools..."
            variant="internal"
            leftSearchIcon
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          {enabledTools.length > 0 && (
            <Button
              internal
              rightIcon={isFolded ? SvgExpand : SvgFold}
              onClick={() => setIsFolded((prev) => !prev)}
            >
              {isFolded ? "Expand" : "Fold"}
            </Button>
          )}
        </GeneralLayouts.Section>
      </ActionsLayouts.Header>
      {isLoading ? (
        <ActionsLayouts.Content>
          {Array.from({ length: 3 }).map((_, index) => (
            <Card key={index} padding={0.75}>
              <GeneralLayouts.LineItemLayout
                // We provide dummy values here.
                // The `loading` prop will always render a pulsing box instead, so the dummy-values will actually NOT be rendered at all.
                title="..."
                description="..."
                rightChildren={<></>}
                loading
              />
            </Card>
          ))}
        </ActionsLayouts.Content>
      ) : (
        enabledTools.length > 0 &&
        filteredTools.length > 0 && (
          <ActionsLayouts.Content>
            {filteredTools.map((tool) => (
              <ActionsLayouts.Tool
                key={tool.id}
                name={`${serverFieldName}.tool_${tool.id}`}
                title={tool.name}
                description={tool.description}
                icon={tool.icon ?? SvgSliders}
                disabled={
                  !tool.isAvailable ||
                  !getFieldMeta<boolean>(`${serverFieldName}.enabled`).value
                }
                rightChildren={
                  <SwitchField
                    name={`${serverFieldName}.tool_${tool.id}`}
                    disabled={!isServerEnabled}
                  />
                }
              />
            ))}
          </ActionsLayouts.Content>
        )
      )}
    </ExpandableCard.Root>
  );
}

function StarterMessages() {
  const max_starters = STARTER_MESSAGES_EXAMPLES.length;

  const { values } = useFormikContext<{
    starter_messages: string[];
  }>();

  const starters = values.starter_messages || [];

  // Count how many non-empty starters we have
  const filledStarters = starters.filter((s) => s).length;
  const canAddMore = filledStarters < max_starters;

  // Show at least 1, or all filled ones, or filled + 1 empty (up to max)
  const visibleCount = Math.min(
    max_starters,
    Math.max(
      1,
      filledStarters === 0 ? 1 : filledStarters + (canAddMore ? 1 : 0)
    )
  );

  return (
    <FieldArray name="starter_messages">
      {(arrayHelpers) => (
        <GeneralLayouts.Section gap={0.5}>
          {Array.from({ length: visibleCount }, (_, i) => (
            <InputTypeInElementField
              key={`starter_messages.${i}`}
              name={`starter_messages.${i}`}
              placeholder={
                STARTER_MESSAGES_EXAMPLES[i] ||
                "Enter a conversation starter..."
              }
              onRemove={() => arrayHelpers.remove(i)}
            />
          ))}
        </GeneralLayouts.Section>
      )}
    </FieldArray>
  );
}

export interface AgentEditorPageProps {
  agent?: FullAgent;
  refreshAgent?: () => void;
}

export default function AgentEditorPage({
  agent: existingAgent,
  refreshAgent,
}: AgentEditorPageProps) {
  const router = useRouter();
  const appRouter = useAppRouter();
  const { refresh: refreshAgents } = useAgents();
  const shareAgentModal = useCreateModal();
  const deleteAgentModal = useCreateModal();
  const settings = useSettingsContext();
  const vectorDbEnabled = settings?.settings.vector_db_enabled !== false;

  // ─── Wizard step state ───
  const [currentStep, setCurrentStep] = useState(0);

  // Scroll to top when step changes
  useEffect(() => {
    document.getElementById("page-wrapper-scroll-container")?.scrollTo({ top: 0, behavior: "smooth" });
  }, [currentStep]);

  // Per-step validation: only block "Next" if the CURRENT step has errors
  const handleNextStep = useCallback(
    async (
      validateForm: () => Promise<Record<string, unknown>>,
      setFieldTouched: (field: string, touched: boolean) => void
    ) => {
      const errors = await validateForm();
      const stepFields = STEP_FIELDS[currentStep] ?? [];
      const hasStepErrors = Object.keys(errors).some((errorKey) =>
        stepFields.some((f) => errorKey === f || errorKey.startsWith(`${f}.`))
      );
      if (hasStepErrors) {
        stepFields.forEach((f) => setFieldTouched(f, true));
        return;
      }
      setCurrentStep((prev) => Math.min(prev + 1, TOTAL_STEPS - 1));
    },
    [currentStep]
  );

  // LLM Model Selection
  const getCurrentLlm = useCallback(
    (values: any, llmProviders: any) =>
      values.llm_model_version_override && values.llm_model_provider_override
        ? (() => {
            const provider = llmProviders?.find(
              (p: any) => p.name === values.llm_model_provider_override
            );
            return structureValue(
              values.llm_model_provider_override,
              provider?.provider || "",
              values.llm_model_version_override
            );
          })()
        : null,
    []
  );

  const onLlmSelect = useCallback(
    (selected: string | null, setFieldValue: any) => {
      if (selected === null) {
        setFieldValue("llm_model_version_override", null);
        setFieldValue("llm_model_provider_override", null);
      } else {
        const { modelName, name } = parseLlmDescriptor(selected);
        if (modelName && name) {
          setFieldValue("llm_model_version_override", modelName);
          setFieldValue("llm_model_provider_override", name);
        }
      }
    },
    []
  );

  // Hooks for Knowledge section
  const { allRecentFiles, beginUpload } = useWorkspacesContext();
  const { data: documentSets } = useDocumentSets();
  const userFilesModal = useCreateModal();
  const [presentingDocument, setPresentingDocument] = useState<{
    document_id: string;
    semantic_identifier: string;
  } | null>(null);

  const { mcpData, isLoading: isMcpLoading } = useMcpServersForAgentEditor();
  const { openApiTools: openApiToolsRaw, isLoading: isOpenApiLoading } =
    useOpenApiTools();
  const { llmProviders } = useLLMProviders(existingAgent?.id);
  const mcpServers = mcpData?.mcp_servers ?? [];
  const openApiTools = openApiToolsRaw ?? [];

  // Check if the *BUILT-IN* tools are available.
  // The built-in tools are:
  // - image-gen
  // - web-search
  // - code-interpreter
  const { tools: availableTools, isLoading: isToolsLoading } =
    useAvailableTools();
  const searchTool = availableTools?.find(
    (t) => t.in_code_tool_id === SEARCH_TOOL_ID
  );
  const imageGenTool = availableTools?.find(
    (t) => t.in_code_tool_id === IMAGE_GENERATION_TOOL_ID
  );
  const webSearchTool = availableTools?.find(
    (t) => t.in_code_tool_id === WEB_SEARCH_TOOL_ID
  );
  const openURLTool = availableTools?.find(
    (t) => t.in_code_tool_id === OPEN_URL_TOOL_ID
  );
  const codeInterpreterTool = availableTools?.find(
    (t) => t.in_code_tool_id === PYTHON_TOOL_ID
  );
  const fileReaderTool = availableTools?.find(
    (t) => t.in_code_tool_id === FILE_READER_TOOL_ID
  );
  const isImageGenerationAvailable = !!imageGenTool;
  const imageGenerationDisabledTooltip = isImageGenerationAvailable
    ? undefined
    : "Image generation requires a configured model. If you have access, set one up under Settings > Image Generation, or ask an admin.";

  // Group MCP server tools from availableTools by server ID
  const mcpServersWithTools = mcpServers.map((server) => {
    const serverTools: MCPTool[] = (availableTools || [])
      .filter((tool) => tool.mcp_server_id === server.id)
      .map((tool) => ({
        id: tool.id.toString(),
        icon: getActionIcon(server.server_url, server.name),
        name: tool.display_name || tool.name,
        description: tool.description,
        isAvailable: true,
        isEnabled: tool.enabled,
      }));

    return { server, tools: serverTools, isLoading: false };
  });

  const initialValues = {
    // General
    icon_name: existingAgent?.icon_name ?? null,
    uploaded_image_id: existingAgent?.uploaded_image_id ?? null,
    remove_image: false,
    name: existingAgent?.name ?? "",
    description: existingAgent?.description ?? "",

    // Prompts
    instructions: existingAgent?.system_prompt ?? "",
    starter_messages: Array.from(
      { length: STARTER_MESSAGES_EXAMPLES.length },
      (_, i) => existingAgent?.starter_messages?.[i]?.message ?? ""
    ),

    // Knowledge - enabled if num_chunks is greater than 0
    // (num_chunks of 0 or null means knowledge is disabled)
    enable_knowledge: (existingAgent?.num_chunks ?? 0) > 0,
    document_set_ids: existingAgent?.document_sets?.map((ds) => ds.id) ?? [],
    // Individual document IDs from hierarchy browsing
    document_ids: existingAgent?.attached_documents?.map((doc) => doc.id) ?? [],
    // Hierarchy node IDs (folders/spaces/channels) for scoped search
    hierarchy_node_ids:
      existingAgent?.hierarchy_nodes?.map((node) => node.id) ?? [],
    knowledge_file_ids: existingAgent?.knowledge_file_ids ?? [],
    // Selected sources for the new knowledge UI - derived from document sets
    selected_sources: [] as ValidSources[],

    // Advanced
    llm_model_provider_override:
      existingAgent?.llm_model_provider_override ?? null,
    llm_model_version_override:
      existingAgent?.llm_model_version_override ?? null,
    knowledge_cutoff_date: existingAgent?.search_start_date
      ? new Date(existingAgent.search_start_date)
      : null,
    replace_base_system_prompt:
      existingAgent?.replace_base_system_prompt ?? false,
    reminders: existingAgent?.task_prompt ?? "",
    max_output_tokens: existingAgent?.max_output_tokens ?? null,
    // For new assistants, default to false for optional tools to avoid
    // "Tool not available" errors when the tool isn't configured.
    // For existing assistants, preserve the current tool configuration.
    image_generation:
      !!imageGenTool &&
      (existingAgent?.tools?.some(
        (tool) => tool.in_code_tool_id === IMAGE_GENERATION_TOOL_ID
      ) ??
        false),
    web_search:
      !!webSearchTool &&
      (existingAgent?.tools?.some(
        (tool) => tool.in_code_tool_id === WEB_SEARCH_TOOL_ID
      ) ??
        false),
    open_url:
      !!openURLTool &&
      (existingAgent?.tools?.some(
        (tool) => tool.in_code_tool_id === OPEN_URL_TOOL_ID
      ) ??
        false),
    code_interpreter:
      !!codeInterpreterTool &&
      (existingAgent?.tools?.some(
        (tool) => tool.in_code_tool_id === PYTHON_TOOL_ID
      ) ??
        false),
    file_reader:
      !!fileReaderTool &&
      (existingAgent?.tools?.some(
        (tool) => tool.in_code_tool_id === FILE_READER_TOOL_ID
      ) ??
        // Default to enabled for new assistants when the tool is available
        !!fileReaderTool),

    // MCP servers - dynamically add fields for each server with nested tool fields
    ...Object.fromEntries(
      mcpServersWithTools.map(({ server, tools }) => {
        // Find all tools from existingAgent that belong to this MCP server
        const serverToolsFromAgent =
          existingAgent?.tools?.filter(
            (tool) => tool.mcp_server_id === server.id
          ) ?? [];

        // Build the tool field object with tool_{id} for ALL available tools
        const toolFields: Record<string, boolean> = {};
        tools.forEach((tool) => {
          // Set to true if this tool was enabled in existingAgent, false otherwise
          toolFields[`tool_${tool.id}`] = serverToolsFromAgent.some(
            (t) => t.id === Number(tool.id)
          );
        });

        return [
          `mcp_server_${server.id}`,
          {
            enabled: serverToolsFromAgent.length > 0, // Server is enabled if it has any tools
            ...toolFields, // Add individual tool states for ALL tools
          },
        ];
      })
    ),

    // OpenAPI tools - add a boolean field for each tool
    ...Object.fromEntries(
      openApiTools.map((openApiTool) => [
        `openapi_tool_${openApiTool.id}`,
        existingAgent?.tools?.some((t) => t.id === openApiTool.id) ?? false,
      ])
    ),

    // Sharing
    shared_user_ids: existingAgent?.users?.map((user) => user.id) ?? [],
    shared_group_ids: existingAgent?.groups ?? [],
    is_public: existingAgent?.is_public ?? true,
  };

  const validationSchema = Yup.object().shape({
    // General
    icon_name: Yup.string().nullable(),
    remove_image: Yup.boolean().optional(),
    uploaded_image_id: Yup.string().nullable(),
    name: Yup.string().required("Agent name is required."),
    description: Yup.string()
      .max(
        MAX_CHARACTERS_AGENT_DESCRIPTION,
        `Description must be ${MAX_CHARACTERS_AGENT_DESCRIPTION} characters or less`
      )
      .optional(),

    // Prompts
    instructions: Yup.string().optional(),
    starter_messages: Yup.array().of(
      Yup.string().max(
        MAX_CHARACTERS_STARTER_MESSAGE,
        `Conversation starter must be ${MAX_CHARACTERS_STARTER_MESSAGE} characters or less`
      )
    ),

    // Knowledge
    enable_knowledge: Yup.boolean(),
    document_set_ids: Yup.array().of(Yup.number()),
    document_ids: Yup.array().of(Yup.string()),
    hierarchy_node_ids: Yup.array().of(Yup.number()),
    knowledge_file_ids: Yup.array().of(Yup.string()),
    selected_sources: Yup.array().of(Yup.string()),
    num_chunks: Yup.number()
      .nullable()
      .transform((value, originalValue) =>
        originalValue === "" || originalValue === null ? null : value
      )
      .test(
        "is-non-negative-integer",
        "The number of chunks must be a non-negative integer (0, 1, 2, etc.)",
        (value) =>
          value === null ||
          value === undefined ||
          (Number.isInteger(value) && value >= 0)
      ),

    // Advanced
    llm_model_provider_override: Yup.string().nullable().optional(),
    llm_model_version_override: Yup.string().nullable().optional(),
    knowledge_cutoff_date: Yup.date().nullable().optional(),
    replace_base_system_prompt: Yup.boolean(),
    reminders: Yup.string().optional(),

    // MCP servers - dynamically add validation for each server with nested tool validation
    ...Object.fromEntries(
      mcpServers.map((server) => [
        `mcp_server_${server.id}`,
        Yup.object(), // Allow any nested tool fields as booleans
      ])
    ),

    // OpenAPI tools - add boolean validation for each tool
    ...Object.fromEntries(
      openApiTools.map((openApiTool) => [
        `openapi_tool_${openApiTool.id}`,
        Yup.boolean(),
      ])
    ),
  });

  async function handleSubmit(values: typeof initialValues) {
    try {
      // Map conversation starters
      const starterMessages = values.starter_messages
        .filter((message: string) => message.trim() !== "")
        .map((message: string) => ({
          message: message,
          name: message,
        }));

      // Send null instead of empty array if no starter messages
      const finalStarterMessages =
        starterMessages.length > 0 ? starterMessages : null;

      // Determine knowledge settings
      const numChunks = values.enable_knowledge ? MAX_CHUNKS_FED_TO_CHAT : 0;

      // Always look up tools in availableTools to ensure we can find all tools

      const toolIds = [];
      if (values.enable_knowledge) {
        if (vectorDbEnabled && searchTool) {
          toolIds.push(searchTool.id);
        }
      }
      if (values.file_reader && fileReaderTool) {
        toolIds.push(fileReaderTool.id);
      }
      if (values.image_generation && imageGenTool) {
        toolIds.push(imageGenTool.id);
      }
      if (values.web_search && webSearchTool) {
        toolIds.push(webSearchTool.id);
      }
      if (values.open_url && openURLTool) {
        toolIds.push(openURLTool.id);
      }
      if (values.code_interpreter && codeInterpreterTool) {
        toolIds.push(codeInterpreterTool.id);
      }

      // Collect enabled MCP tool IDs
      mcpServers.forEach((server) => {
        const serverFieldName = `mcp_server_${server.id}`;
        const serverData = (values as any)[serverFieldName];

        if (
          serverData &&
          typeof serverData === "object" &&
          serverData.enabled
        ) {
          // Server is enabled, collect all enabled tools
          Object.keys(serverData).forEach((key) => {
            if (key.startsWith("tool_") && serverData[key] === true) {
              // Extract tool ID from key (e.g., "tool_123" -> 123)
              const toolId = parseInt(key.replace("tool_", ""), 10);
              if (!isNaN(toolId)) {
                toolIds.push(toolId);
              }
            }
          });
        }
      });

      // Collect enabled OpenAPI tool IDs
      openApiTools.forEach((openApiTool) => {
        const toolFieldName = `openapi_tool_${openApiTool.id}`;
        if ((values as any)[toolFieldName] === true) {
          toolIds.push(openApiTool.id);
        }
      });

      // Build submission data
      const submissionData: AgentUpsertParameters = {
        name: values.name,
        description: values.description,
        document_set_ids: values.enable_knowledge
          ? values.document_set_ids
          : [],
        num_chunks: numChunks,
        is_public: values.is_public,
        // recency_bias: ...,
        // llm_filter_extraction: ...,
        llm_relevance_filter: false,
        llm_model_provider_override: values.llm_model_provider_override || null,
        llm_model_version_override: values.llm_model_version_override || null,
        starter_messages: finalStarterMessages,
        users: values.shared_user_ids,
        groups: values.shared_group_ids,
        tool_ids: toolIds,
        // uploaded_image: null, // Already uploaded separately
        remove_image: values.remove_image ?? false,
        uploaded_image_id: values.uploaded_image_id,
        icon_name: values.icon_name,
        search_start_date: values.knowledge_cutoff_date || null,
        label_ids: null,
        is_default_agent: false,
        // display_priority: ...,

        knowledge_file_ids: values.enable_knowledge ? values.knowledge_file_ids : [],
        hierarchy_node_ids: values.enable_knowledge
          ? values.hierarchy_node_ids
          : [],
        document_ids: values.enable_knowledge ? values.document_ids : [],

        system_prompt: values.instructions,
        replace_base_system_prompt: values.replace_base_system_prompt,
        task_prompt: values.reminders || "",
        datetime_aware: false,
        max_output_tokens: values.max_output_tokens ? Number(values.max_output_tokens) : null,
      };

      // Call API
      let agentResponse;
      if (!!existingAgent) {
        agentResponse = await updateAgent(existingAgent.id, submissionData);
      } else {
        agentResponse = await createAgent(submissionData);
      }

      // Handle response
      if (!agentResponse || !agentResponse.ok) {
        const error = agentResponse
          ? await agentResponse.text()
          : "No response received";
        toast.error(
          `Failed to ${existingAgent ? "update" : "create"} agent - ${error}`
        );
        return;
      }

      // Success
      const agent = await agentResponse.json();
      toast.success(
        `Agent "${agent.name}" ${
          existingAgent ? "updated" : "created"
        } successfully`
      );

      // Refresh agents list and the specific agent
      await refreshAgents();
      if (refreshAgent) {
        refreshAgent();
      }

      // Immediately start a chat with this agent.
      appRouter({ agentId: agent.id });
    } catch (error) {
      console.error("Submit error:", error);
      toast.error(`An error occurred: ${error}`);
    }
  }

  // Delete agent handler
  async function handleDeleteAgent() {
    if (!existingAgent) return;

    const error = await deleteAgent(existingAgent.id);

    if (error) {
      toast.error(`Failed to delete agent: ${error}`);
    } else {
      toast.success("Agent deleted successfully");

      deleteAgentModal.toggle(false);
      await refreshAgents();
      router.push("/app/agents");
    }
  }

  // FilePickerPopover callbacks for Knowledge section
  function handlePickRecentFile(
    file: WorkspaceFile,
    currentFileIds: string[],
    setFieldValue: (field: string, value: unknown) => void
  ) {
    if (!currentFileIds.includes(file.id)) {
      setFieldValue("knowledge_file_ids", [...currentFileIds, file.id]);
    }
  }

  function handleUnpickRecentFile(
    file: WorkspaceFile,
    currentFileIds: string[],
    setFieldValue: (field: string, value: unknown) => void
  ) {
    setFieldValue(
      "knowledge_file_ids",
      currentFileIds.filter((id) => id !== file.id)
    );
  }

  function handleFileClick(file: WorkspaceFile) {
    setPresentingDocument({
      document_id: `workspace_file__${file.file_id}`,
      semantic_identifier: file.name,
    });
  }

  async function handleUploadChange(
    e: React.ChangeEvent<HTMLInputElement>,
    currentFileIds: string[],
    setFieldValue: (field: string, value: unknown) => void
  ) {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    try {
      let selectedIds = [...(currentFileIds || [])];
      const optimistic = await beginUpload(
        Array.from(files),
        null,
        (result) => {
          const uploadedFiles = result.knowledge_files || [];
          if (uploadedFiles.length === 0) return;
          const tempToFinal = new Map(
            uploadedFiles
              .filter((f) => f.temp_id)
              .map((f) => [f.temp_id as string, f.id])
          );
          const replaced = (selectedIds || []).map(
            (id: string) => tempToFinal.get(id) ?? id
          );
          selectedIds = replaced;
          setFieldValue("knowledge_file_ids", replaced);
        }
      );
      if (optimistic) {
        const optimisticIds = optimistic.map((f) => f.id);
        selectedIds = [...selectedIds, ...optimisticIds];
        setFieldValue("knowledge_file_ids", selectedIds);
      }
    } catch (error) {
      console.error("Upload error:", error);
    }
  }

  // Wait for async tool data before rendering the form. Formik captures
  // initialValues on mount — if tools haven't loaded yet, the initial values
  // won't include MCP tool fields. Later, toggling those fields would make
  // the form permanently dirty since they have no baseline to compare against.
  if (isToolsLoading || isMcpLoading || isOpenApiLoading) {
    return null;
  }

  return (
    <>
      <div
        data-testid="AgentsEditorPage/container"
        aria-label="Agents Editor Page"
        className="h-full w-full"
      >
        <Formik
          initialValues={initialValues}
          validationSchema={validationSchema}
          onSubmit={handleSubmit}
          validateOnChange
          validateOnBlur
          validateOnMount
          initialStatus={{ warnings: {} }}
        >
          {({ isSubmitting, isValid, dirty, values, setFieldValue, validateForm, setFieldTouched }) => {
            const fileStatusMap = new Map(
              allRecentFiles.map((f) => [f.id, f.status])
            );

            const hasUploadingFiles = values.knowledge_file_ids.some(
              (fileId: string) => {
                const status = fileStatusMap.get(fileId);
                if (status === undefined) {
                  return fileId.startsWith("temp_");
                }
                return status === KnowledgeFileStatus.UPLOADING;
              }
            );

            const hasProcessingFiles = values.knowledge_file_ids.some(
              (fileId: string) =>
                fileStatusMap.get(fileId) === KnowledgeFileStatus.PROCESSING
            );

            return (
              <>
                <FormWarningsEffect />

                <userFilesModal.Provider>
                  <KnowledgeFilesModal
                    title="User Files"
                    description="All files selected for this agent"
                    recentFiles={values.knowledge_file_ids
                      .map((userFileId: string) => {
                        const rf = allRecentFiles.find(
                          (f) => f.id === userFileId
                        );
                        if (rf) return rf;
                        return {
                          id: userFileId,
                          name: `File ${userFileId.slice(0, 8)}`,
                          status: KnowledgeFileStatus.COMPLETED,
                          file_id: userFileId,
                          created_at: new Date().toISOString(),
                          workspace_id: null,
                          user_id: null,
                          file_type: "",
                          last_accessed_at: new Date().toISOString(),
                          chat_file_type: "file" as const,
                        } as unknown as WorkspaceFile;
                      })
                      .filter((f): f is WorkspaceFile => f !== null)}
                    selectedFileIds={values.knowledge_file_ids}
                    onPickRecent={(file: WorkspaceFile) => {
                      if (!values.knowledge_file_ids.includes(file.id)) {
                        setFieldValue("knowledge_file_ids", [
                          ...values.knowledge_file_ids,
                          file.id,
                        ]);
                      }
                    }}
                    onUnpickRecent={(file: WorkspaceFile) => {
                      setFieldValue(
                        "knowledge_file_ids",
                        values.knowledge_file_ids.filter((id) => id !== file.id)
                      );
                    }}
                    onView={(file: WorkspaceFile) => {
                      setPresentingDocument({
                        document_id: `workspace_file__${file.file_id}`,
                        semantic_identifier: file.name,
                      });
                    }}
                  />
                </userFilesModal.Provider>

                <shareAgentModal.Provider>
                  <ShareAgentModal
                    agentId={existingAgent?.id}
                    userIds={values.shared_user_ids}
                    groupIds={values.shared_group_ids}
                    isPublic={values.is_public}
                    onShare={(userIds, groupIds, isPublic) => {
                      setFieldValue("shared_user_ids", userIds);
                      setFieldValue("shared_group_ids", groupIds);
                      setFieldValue("is_public", isPublic);
                      shareAgentModal.toggle(false);
                    }}
                  />
                </shareAgentModal.Provider>
                <deleteAgentModal.Provider>
                  {deleteAgentModal.isOpen && (
                    <ConfirmationModalLayout
                      icon={SvgTrash}
                      title="Delete Agent"
                      submit={
                        <Button danger onClick={handleDeleteAgent}>
                          Delete Agent
                        </Button>
                      }
                      onClose={() => deleteAgentModal.toggle(false)}
                    >
                      <GeneralLayouts.Section alignItems="start" gap={0.5}>
                        <Text>
                          Anyone using this agent will no longer be able to
                          access it. Deletion cannot be undone.
                        </Text>
                        <Text>Are you sure you want to delete this agent?</Text>
                      </GeneralLayouts.Section>
                    </ConfirmationModalLayout>
                  )}
                </deleteAgentModal.Provider>

                <Form className="h-full w-full">
                  <SettingsLayouts.Root>
                    <SettingsLayouts.Header
                      icon={SvgOnyxOctagon}
                      title={existingAgent ? "Edit Agent" : "Create Agent"}
                      rightChildren={
                        <div className="flex gap-2">
                          <Button
                            type="button"
                            secondary
                            onClick={() => router.back()}
                          >
                            Cancel
                          </Button>
                          {currentStep > 0 && (
                            <Button
                              type="button"
                              secondary
                              leftIcon={SvgArrowLeft}
                              onClick={() => setCurrentStep((s) => s - 1)}
                            >
                              Back
                            </Button>
                          )}
                          {currentStep < TOTAL_STEPS - 1 ? (
                            <Button
                              type="button"
                              rightIcon={SvgArrowRight}
                              onClick={() => handleNextStep(validateForm, setFieldTouched)}
                            >
                              Next
                            </Button>
                          ) : (
                            <Button
                              type="submit"
                              leftIcon={existingAgent ? undefined : SvgSparkle}
                              disabled={
                                isSubmitting ||
                                !isValid ||
                                !dirty ||
                                hasUploadingFiles
                              }
                            >
                              {existingAgent ? "Save" : "Create"}
                            </Button>
                          )}
                        </div>
                      }
                      backButton
                      separator
                    >
                      <StepIndicator
                        currentStep={currentStep}
                        onStepClick={(step) => setCurrentStep(step)}
                      />
                    </SettingsLayouts.Header>

                    {/* Agent Form Content — Wizard Steps */}
                    <SettingsLayouts.Body>

                      {/* ═══════════════════════════════════════════════════
                          STEP 1: Identity — Name & Personality
                          ═══════════════════════════════════════════════════ */}
                      {currentStep === 0 && (
                        <>
                          <WizardSectionHeader
                            icon={SvgUser}
                            title="Who is your agent?"
                            description="Give your agent a name, look, and personality."
                            color="blue"
                          />

                          <GeneralLayouts.Section
                            flexDirection="row"
                            gap={2.5}
                            alignItems="start"
                          >
                            <GeneralLayouts.Section>
                              <InputLayouts.Vertical name="name" title="Name">
                                <InputTypeInField
                                  name="name"
                                  placeholder="Name your agent"
                                />
                              </InputLayouts.Vertical>

                              <InputLayouts.Vertical
                                name="description"
                                title="Description"
                                description="A short summary shown to users when they browse agents."
                                optional
                              >
                                <InputTextAreaField
                                  name="description"
                                  placeholder="What does this agent do?"
                                />
                              </InputLayouts.Vertical>
                            </GeneralLayouts.Section>

                            <GeneralLayouts.Section width="fit">
                              <InputLayouts.Vertical
                                name="agent_avatar"
                                title="Agent Avatar"
                                center
                              >
                                <AgentIconEditor existingAgent={existingAgent} />
                              </InputLayouts.Vertical>
                            </GeneralLayouts.Section>
                          </GeneralLayouts.Section>

                          <Separator noPadding />

                          <WizardSectionHeader
                            icon={SvgBubbleText}
                            title="How should it respond?"
                            description="Define the personality and conversation style."
                            color="blue"
                          />

                          <GeneralLayouts.Section>
                            <InputLayouts.Vertical
                              name="instructions"
                              title="Instructions"
                              optional
                              description="The system prompt tells the AI how to behave — its personality, rules, and expertise. Think of it as a job description for the agent."
                            >
                              <InputTextAreaField
                                name="instructions"
                                placeholder="Think step by step and show reasoning for complex problems. Use specific examples. Emphasize action items, and leave blanks for the human to fill in when you have unknown. Use a polite enthusiastic tone."
                              />
                            </InputLayouts.Vertical>

                            <InputLayouts.Vertical
                              name="starter_messages"
                              title="Conversation Starters"
                              description="Quick-action buttons shown when users open a new chat. Use these to showcase what your agent can do."
                              optional
                            >
                              <StarterMessages />
                            </InputLayouts.Vertical>
                          </GeneralLayouts.Section>
                        </>
                      )}

                      {/* ═══════════════════════════════════════════════════
                          STEP 2: Knowledge & Tools
                          ═══════════════════════════════════════════════════ */}
                      {currentStep === 1 && (
                        <>
                          <WizardSectionHeader
                            icon={SvgBookOpen}
                            title="What does your agent know?"
                            description="Connect knowledge sources so the agent can reference your company's documents when answering."
                            color="purple"
                          />

                          <AgentKnowledgePane
                            enableKnowledge={values.enable_knowledge}
                            onEnableKnowledgeChange={(enabled) =>
                              setFieldValue("enable_knowledge", enabled)
                            }
                            selectedSources={values.selected_sources}
                            onSourcesChange={(sources) =>
                              setFieldValue("selected_sources", sources)
                            }
                            documentSets={documentSets ?? []}
                            selectedDocumentSetIds={values.document_set_ids}
                            onDocumentSetIdsChange={(ids) =>
                              setFieldValue("document_set_ids", ids)
                            }
                            selectedDocumentIds={values.document_ids}
                            onDocumentIdsChange={(ids) =>
                              setFieldValue("document_ids", ids)
                            }
                            selectedFolderIds={values.hierarchy_node_ids}
                            onFolderIdsChange={(ids) =>
                              setFieldValue("hierarchy_node_ids", ids)
                            }
                            selectedFileIds={values.knowledge_file_ids}
                            onFileIdsChange={(ids) =>
                              setFieldValue("knowledge_file_ids", ids)
                            }
                            allRecentFiles={allRecentFiles}
                            onFileClick={handleFileClick}
                            onUploadChange={(e) =>
                              handleUploadChange(
                                e,
                                values.knowledge_file_ids,
                                setFieldValue
                              )
                            }
                            hasProcessingFiles={hasProcessingFiles}
                            initialAttachedDocuments={
                              existingAgent?.attached_documents
                            }
                            initialHierarchyNodes={existingAgent?.hierarchy_nodes}
                            vectorDbEnabled={vectorDbEnabled}
                          />

                          <Separator noPadding />

                          <WizardSectionHeader
                            icon={SvgSparkle}
                            title="What can your agent do?"
                            description="Enable tools to give your agent superpowers beyond just chatting."
                            color="purple"
                          />

                          <GeneralLayouts.Section gap={0.5}>
                            <SimpleTooltip
                              tooltip={imageGenerationDisabledTooltip}
                              side="top"
                            >
                              <Card
                                variant={
                                  isImageGenerationAvailable
                                    ? undefined
                                    : "disabled"
                                }
                              >
                                <InputLayouts.Horizontal
                                  name="image_generation"
                                  title="Image Generation"
                                  description="Create and edit images using AI. Requires an image generation model to be configured."
                                  disabled={!isImageGenerationAvailable}
                                >
                                  <SwitchField
                                    name="image_generation"
                                    disabled={!isImageGenerationAvailable}
                                  />
                                </InputLayouts.Horizontal>
                              </Card>
                            </SimpleTooltip>

                            <Card
                              variant={!!webSearchTool ? undefined : "disabled"}
                            >
                              <InputLayouts.Horizontal
                                name="web_search"
                                title="Web Search"
                                description="Search the internet for real-time information. Best paired with Open URL for full web page reading."
                                disabled={!webSearchTool}
                              >
                                <SwitchField
                                  name="web_search"
                                  disabled={!webSearchTool}
                                />
                              </InputLayouts.Horizontal>
                            </Card>

                            <Card
                              variant={!!openURLTool ? undefined : "disabled"}
                            >
                              <InputLayouts.Horizontal
                                name="open_url"
                                title="Open URL"
                                description="Read and extract content from any web page URL. Strongly recommended when Web Search is enabled."
                                disabled={!openURLTool}
                              >
                                <SwitchField
                                  name="open_url"
                                  disabled={!openURLTool}
                                />
                              </InputLayouts.Horizontal>
                            </Card>

                            <Card
                              variant={
                                !!codeInterpreterTool ? undefined : "disabled"
                              }
                            >
                              <InputLayouts.Horizontal
                                name="code_interpreter"
                                title="Code Interpreter"
                                description="Write, execute, and debug Python code. Great for data analysis, calculations, and file processing."
                                disabled={!codeInterpreterTool}
                              >
                                <SwitchField
                                  name="code_interpreter"
                                  disabled={!codeInterpreterTool}
                                />
                              </InputLayouts.Horizontal>
                            </Card>

                            <Card
                              variant={
                                !!fileReaderTool ? undefined : "disabled"
                              }
                            >
                              <InputLayouts.Horizontal
                                name="file_reader"
                                title="File Reader"
                                description="Read and process uploaded files section by section. Essential for large documents that exceed the AI's context window."
                                disabled={!fileReaderTool}
                              >
                                <SwitchField
                                  name="file_reader"
                                  disabled={!fileReaderTool}
                                />
                              </InputLayouts.Horizontal>
                            </Card>

                            {/* MCP & OpenAPI Tools */}
                            <>
                              {(mcpServers.length > 0 ||
                                openApiTools.length > 0) && (
                                <Separator noPadding className="py-1" />
                              )}

                              {mcpServersWithTools.length > 0 && (
                                <GeneralLayouts.Section gap={0.5}>
                                  {mcpServersWithTools.map(
                                    ({ server, tools, isLoading }) => (
                                      <MCPServerCard
                                        key={server.id}
                                        server={server}
                                        tools={tools}
                                        isLoading={isLoading}
                                      />
                                    )
                                  )}
                                </GeneralLayouts.Section>
                              )}

                              {openApiTools.length > 0 && (
                                <GeneralLayouts.Section gap={0.5}>
                                  {openApiTools.map((tool) => (
                                    <OpenApiToolCard
                                      key={tool.id}
                                      tool={tool}
                                    />
                                  ))}
                                </GeneralLayouts.Section>
                              )}
                            </>
                          </GeneralLayouts.Section>
                        </>
                      )}

                      {/* ═══════════════════════════════════════════════════
                          STEP 3: Configure & Share
                          ═══════════════════════════════════════════════════ */}
                      {currentStep === 2 && (
                        <>
                          <WizardSectionHeader
                            icon={SvgShield}
                            title="Who can use this agent?"
                            description="Control access and visibility."
                            color="green"
                          />

                          <GeneralLayouts.Section>
                            <Card>
                              <InputLayouts.Horizontal
                                title="Share This Agent"
                                description="Control who can find and use this agent — specific people, teams, or your entire organization."
                                center
                              >
                                <Button
                                  secondary
                                  leftIcon={SvgLock}
                                  onClick={() => shareAgentModal.toggle(true)}
                                >
                                  Share
                                </Button>
                              </InputLayouts.Horizontal>
                            </Card>
                          </GeneralLayouts.Section>

                          <Separator noPadding />

                          <WizardSectionHeader
                            icon={SvgSliders}
                            title="Fine-tune behavior"
                            description="Advanced settings for power users. Most agents work great with defaults — only change these if needed."
                            color="green"
                          />

                          <GeneralLayouts.Section>
                            <Card>
                              <InputLayouts.Horizontal
                                name="llm_model"
                                title="Default Model"
                                description="Override which AI model this agent uses. Leave empty to let each user's preferred model be used."
                              >
                                <LLMSelector
                                  name="llm_model"
                                  llmProviders={llmProviders ?? []}
                                  currentLlm={getCurrentLlm(
                                    values,
                                    llmProviders
                                  )}
                                  onSelect={(selected) =>
                                    onLlmSelect(selected, setFieldValue)
                                  }
                                />
                              </InputLayouts.Horizontal>
                              <InputLayouts.Horizontal
                                name="knowledge_cutoff_date"
                                title="Knowledge Cutoff Date"
                                description="Only reference documents created before this date. Useful for historical snapshots or compliance."
                              >
                                <InputDatePickerField name="knowledge_cutoff_date" />
                              </InputLayouts.Horizontal>
                              <InputLayouts.Horizontal
                                name="replace_base_system_prompt"
                                title="Overwrite System Prompt"
                                description="Replace ALL default system instructions. Warning: this removes helpful built-in behaviors like markdown rendering and citation formatting."
                              >
                                <SwitchField name="replace_base_system_prompt" />
                              </InputLayouts.Horizontal>
                              <InputLayouts.Horizontal
                                name="max_output_tokens"
                                title="Max Output Tokens"
                                description="Limit how many tokens the agent can produce per response. Leave empty for the default (5000). Lower values save cost; higher values allow longer answers."
                              >
                                <InputTypeInField
                                  name="max_output_tokens"
                                  type="number"
                                  placeholder="5000"
                                />
                              </InputLayouts.Horizontal>
                            </Card>

                            <GeneralLayouts.Section gap={0.25}>
                              <InputLayouts.Vertical
                                name="reminders"
                                title="Reminders"
                                description="A short note appended to every message in the conversation. Use this if the agent tends to forget certain rules as the chat gets longer. Keep it brief — 1-2 sentences max."
                              >
                                <InputTextAreaField
                                  name="reminders"
                                  placeholder="Remember, I want you to always format your response as a numbered list."
                                />
                              </InputLayouts.Vertical>
                            </GeneralLayouts.Section>
                          </GeneralLayouts.Section>

                          {existingAgent && (
                            <>
                              <Separator noPadding />

                              <Card>
                                <InputLayouts.Horizontal
                                  title="Delete This Agent"
                                  description="Anyone using this agent will no longer be able to access it."
                                  center
                                >
                                  <Button
                                    secondary
                                    danger
                                    onClick={() => deleteAgentModal.toggle(true)}
                                  >
                                    Delete Agent
                                  </Button>
                                </InputLayouts.Horizontal>
                              </Card>
                            </>
                          )}
                        </>
                      )}

                    </SettingsLayouts.Body>
                  </SettingsLayouts.Root>
                </Form>
              </>
            );
          }}
        </Formik>
      </div>
    </>
  );
}
