"use client";

import React, { useState, useMemo, useCallback } from "react";
import { Formik, Form, useFormikContext } from "formik";
import { ThreeDotsLoader } from "@/components/Loading";
import { useRouter } from "next/navigation";
import { errorHandlingFetcher } from "@/lib/fetcher";
import Text from "@/refresh-components/texts/Text";
import useSWR, { mutate } from "swr";
import { ErrorCallout } from "@/components/ErrorCallout";
import { toast } from "@/hooks/useToast";
import { useAgents } from "@/hooks/useAgents";
import Separator from "@/refresh-components/Separator";
import Button from "@/refresh-components/buttons/Button";
import { useSettingsContext } from "@/providers/SettingsProvider";
import Link from "next/link";
import { Callout } from "@/components/ui/callout";
import { ToolSnapshot, MCPServersResponse } from "@/lib/tools/interfaces";
import InputTextArea from "@/refresh-components/inputs/InputTextArea";
import {
  SvgOnyxLogo,
  SvgBubbleText,
  SvgSparkle,
  SvgSearch,
  SvgImage,
  SvgCpu,
  SvgFileText,
  SvgSliders,
  SvgServer,
  SvgActions,
  SvgInfoSmall,
  SvgChevronDown,
  SvgChevronUp,
  SvgRefreshCw,
} from "@opal/icons";
import * as SettingsLayouts from "@/layouts/settings-layouts";
import * as InputLayouts from "@/layouts/input-layouts";
import * as GeneralLayouts from "@/layouts/general-layouts";
import * as ActionsLayouts from "@/layouts/actions-layouts";
import * as ExpandableCard from "@/layouts/expandable-card-layouts";
import { Card } from "@/refresh-components/cards";
import SwitchField from "@/refresh-components/form/SwitchField";
import SimpleTooltip from "@/refresh-components/SimpleTooltip";
import { IconProps } from "@opal/types";
import {
  SEARCH_TOOL_ID,
  WEB_SEARCH_TOOL_ID,
  IMAGE_GENERATION_TOOL_ID,
  PYTHON_TOOL_ID,
  OPEN_URL_TOOL_ID,
  FILE_READER_TOOL_ID,
} from "@/app/app/components/tools/constants";
import EnabledCount from "@/refresh-components/EnabledCount";

// ─── Types ──────────────────────────────────────────────────────────────────

interface DefaultAssistantConfiguration {
  tool_ids: number[];
  system_prompt: string | null;
  default_system_prompt: string;
}

interface DefaultAssistantUpdateRequest {
  tool_ids?: number[];
  system_prompt?: string | null;
}

// ─── Section Header (matches Agent Editor wizard style) ─────────────────────

const DEFAULT_SECTION_COLOR = { bg01: "var(--theme-blue-01)", bg05: "var(--theme-blue-05)" } as const;

const SECTION_COLORS: Record<string, { bg01: string; bg05: string }> = {
  blue:   DEFAULT_SECTION_COLOR,
  purple: { bg01: "var(--theme-purple-01)", bg05: "var(--theme-purple-05)" },
  green:  { bg01: "var(--theme-green-01)",  bg05: "var(--theme-green-05)"  },
  orange: { bg01: "var(--theme-orange-01)", bg05: "var(--theme-orange-05)" },
};

function SectionHeader({ icon: Icon, title, description, color }: {
  icon: React.FunctionComponent<IconProps>;
  title: string;
  description: string;
  color: string;
}) {
  const colors = SECTION_COLORS[color] ?? DEFAULT_SECTION_COLOR;
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

// ─── Placeholder Tag ────────────────────────────────────────────────────────

function PlaceholderTag({ tag, description }: { tag: string; description: string }) {
  return (
    <div className="flex items-start gap-2">
      <code className="text-xs font-mono font-semibold px-1.5 py-0.5 rounded bg-background-tint-03 text-text-04 whitespace-nowrap flex-shrink-0">
        {tag}
      </code>
      <Text secondaryBody text03 className="text-xs">{description}</Text>
    </div>
  );
}

// ─── Built-in Tool Card ─────────────────────────────────────────────────────

function BuiltInToolCard({
  name,
  title,
  description,
  disabled,
  disabledTooltip,
}: {
  name: string;
  icon?: React.FunctionComponent<IconProps>;
  title: string;
  description: string;
  disabled?: boolean;
  disabledTooltip?: string;
}) {
  const content = (
    <Card variant={disabled ? "disabled" : undefined}>
      <InputLayouts.Horizontal
        name={name}
        title={title}
        description={description}
        disabled={disabled}
        center
      >
        <SwitchField name={name} disabled={disabled} />
      </InputLayouts.Horizontal>
    </Card>
  );

  if (disabledTooltip) {
    return <SimpleTooltip tooltip={disabledTooltip} side="top">{content}</SimpleTooltip>;
  }
  return content;
}

// ─── MCP Server Card ────────────────────────────────────────────────────────

function MCPServerToolsCard({
  serverId,
  serverName,
  serverUrl,
  serverTools,
}: {
  serverId: number;
  serverName: string;
  serverUrl: string;
  serverTools: ToolSnapshot[];
}) {
  const [isFolded, setIsFolded] = useState(true);
  const { values, setFieldValue } = useFormikContext<any>();

  const enabledCount = serverTools.filter(
    (tool) => values.enabled_tools_map[tool.id]
  ).length;

  const toggleAllServerTools = useCallback(() => {
    const shouldEnable = enabledCount !== serverTools.length;
    const updatedMap = { ...values.enabled_tools_map };
    serverTools.forEach((tool) => {
      updatedMap[tool.id] = shouldEnable;
    });
    setFieldValue("enabled_tools_map", updatedMap);
  }, [enabledCount, serverTools, values.enabled_tools_map, setFieldValue]);

  return (
    <ExpandableCard.Root isFolded={isFolded} onFoldedChange={setIsFolded}>
      <ActionsLayouts.Header
        title={serverName}
        description={`${serverUrl} · ${serverTools.length} tools`}
        icon={SvgServer}
        rightChildren={
          <div className="flex items-center gap-2">
            <EnabledCount enabledCount={enabledCount} totalCount={serverTools.length} />
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); toggleAllServerTools(); }}
              className="text-xs text-link hover:underline"
            >
              {enabledCount === serverTools.length ? "Disable all" : "Enable all"}
            </button>
            <button
              type="button"
              onClick={() => setIsFolded((f) => !f)}
              className="p-1 rounded hover:bg-background-tint-03 transition-colors"
            >
              {isFolded ? <SvgChevronDown className="w-4 h-4 stroke-text-03" /> : <SvgChevronUp className="w-4 h-4 stroke-text-03" />}
            </button>
          </div>
        }
      />
      {serverTools.length > 0 && (
        <ActionsLayouts.Content>
          {serverTools.map((tool) => (
            <ActionsLayouts.Tool
              key={tool.id}
              name={`enabled_tools_map.${tool.id}`}
              title={tool.display_name}
              description={tool.description}
              icon={SvgSliders}
              rightChildren={
                <SwitchField name={`enabled_tools_map.${tool.id}`} />
              }
            />
          ))}
        </ActionsLayouts.Content>
      )}
    </ExpandableCard.Root>
  );
}

// ─── OpenAPI Tool Card ──────────────────────────────────────────────────────

function OpenAPIToolCard({ tool }: { tool: ToolSnapshot }) {
  return (
    <Card>
      <InputLayouts.Horizontal
        name={`enabled_tools_map.${tool.id}`}
        title={tool.display_name}
        description={tool.description}
        center
      >
        <SwitchField name={`enabled_tools_map.${tool.id}`} />
      </InputLayouts.Horizontal>
    </Card>
  );
}

// ─── Main Content ───────────────────────────────────────────────────────────

function DefaultAssistantContent() {
  const router = useRouter();
  const { refresh: refreshAgents } = useAgents();
  const combinedSettings = useSettingsContext();

  const {
    data: config,
    isLoading,
    error,
  } = useSWR<DefaultAssistantConfiguration>(
    "/api/admin/default-assistant/configuration",
    errorHandlingFetcher
  );

  const { data: tools } = useSWR<ToolSnapshot[]>(
    "/api/tool",
    errorHandlingFetcher
  );

  const { data: mcpServersResponse } = useSWR<MCPServersResponse>(
    "/api/admin/mcp/servers",
    errorHandlingFetcher
  );

  const [isSubmitting, setIsSubmitting] = useState(false);

  const persistConfiguration = async (updates: DefaultAssistantUpdateRequest) => {
    const response = await fetch("/api/admin/default-assistant", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(updates),
    });
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || "Failed to update assistant");
    }
  };

  // Categorize tools
  const {
    searchTool,
    webSearchTool,
    imageGenTool,
    pythonTool,
    openUrlTool,
    fileReaderTool,
    mcpToolsByServer,
    customTools,
  } = useMemo(() => {
    if (!tools) return {
      searchTool: null, webSearchTool: null, imageGenTool: null,
      pythonTool: null, openUrlTool: null, fileReaderTool: null,
      mcpToolsByServer: {} as Record<number, ToolSnapshot[]>,
      customTools: [] as ToolSnapshot[],
    };

    const search = tools.find((t) => t.in_code_tool_id === SEARCH_TOOL_ID) ?? null;
    const webSearch = tools.find((t) => t.in_code_tool_id === WEB_SEARCH_TOOL_ID) ?? null;
    const imageGen = tools.find((t) => t.in_code_tool_id === IMAGE_GENERATION_TOOL_ID) ?? null;
    const python = tools.find((t) => t.in_code_tool_id === PYTHON_TOOL_ID) ?? null;
    const openUrl = tools.find((t) => t.in_code_tool_id === OPEN_URL_TOOL_ID) ?? null;
    const fileReader = tools.find((t) => t.in_code_tool_id === FILE_READER_TOOL_ID) ?? null;

    const allCustom = tools.filter(
      (tool) =>
        tool.in_code_tool_id !== SEARCH_TOOL_ID &&
        tool.in_code_tool_id !== IMAGE_GENERATION_TOOL_ID &&
        tool.in_code_tool_id !== WEB_SEARCH_TOOL_ID &&
        tool.in_code_tool_id !== PYTHON_TOOL_ID &&
        tool.in_code_tool_id !== OPEN_URL_TOOL_ID &&
        tool.in_code_tool_id !== FILE_READER_TOOL_ID
    );

    const mcp = allCustom.filter((tool) => tool.mcp_server_id);
    const custom = allCustom.filter((tool) => !tool.mcp_server_id);

    const groups: Record<number, ToolSnapshot[]> = {};
    mcp.forEach((tool) => {
      if (tool.mcp_server_id) {
        const sid = tool.mcp_server_id;
        if (!groups[sid]) groups[sid] = [];
        groups[sid]!.push(tool);
      }
    });

    return {
      searchTool: search,
      webSearchTool: webSearch,
      imageGenTool: imageGen,
      pythonTool: python,
      openUrlTool: openUrl,
      fileReaderTool: fileReader,
      mcpToolsByServer: groups,
      customTools: custom,
    };
  }, [tools]);

  const mcpServers = mcpServersResponse?.mcp_servers ?? [];
  const hideSearchTool = combinedSettings?.settings.vector_db_enabled === false;

  if (isLoading) return <ThreeDotsLoader />;

  if (error) {
    return (
      <ErrorCallout
        errorTitle="Failed to load configuration"
        errorMsg="Unable to fetch the default assistant configuration."
      />
    );
  }

  if (combinedSettings?.settings?.disable_default_assistant) {
    return (
      <div className="p-4">
        <Callout type="notice">
          <p className="mb-3">
            The default assistant is currently disabled in your workspace settings.
          </p>
          <p>
            To configure the default assistant, you must first enable it in{" "}
            <Link href="/admin/settings" className="text-link font-medium">
              Workspace Settings
            </Link>
            .
          </p>
        </Callout>
      </div>
    );
  }

  if (!config || !tools) return <ThreeDotsLoader />;

  const enabledToolsMap: { [key: number]: boolean } = {};
  tools.forEach((tool) => {
    enabledToolsMap[tool.id] =
      config.tool_ids.includes(tool.id) || tool.default_enabled;
  });

  return (
    <Formik
      enableReinitialize
      initialValues={{
        enabled_tools_map: enabledToolsMap,
        system_prompt: config.system_prompt ?? config.default_system_prompt,
        isUsingDefault: config.system_prompt === null,
      }}
      onSubmit={async (values) => {
        setIsSubmitting(true);
        try {
          const enabledToolIds = Object.keys(values.enabled_tools_map)
            .map((id) => Number(id))
            .filter((id) => values.enabled_tools_map[id]);

          const updates: DefaultAssistantUpdateRequest = {
            tool_ids: enabledToolIds,
          };

          const wasUsingDefault = config.system_prompt === null;
          const initialPrompt = config.system_prompt ?? config.default_system_prompt;
          const isNowUsingDefault = values.isUsingDefault;
          const promptChanged = values.system_prompt !== initialPrompt;

          if (wasUsingDefault && isNowUsingDefault && !promptChanged) {
            // No changes to prompt
          } else if (isNowUsingDefault) {
            updates.system_prompt = null;
          } else if (promptChanged || wasUsingDefault !== isNowUsingDefault) {
            updates.system_prompt = values.system_prompt;
          }

          await persistConfiguration(updates);
          await mutate("/api/admin/default-assistant/configuration");
          router.refresh();
          await refreshAgents();
          toast.success("Default assistant updated successfully!");
        } catch (error: any) {
          toast.error(error.message || "Failed to update assistant");
        } finally {
          setIsSubmitting(false);
        }
      }}
    >
      {({ values, setFieldValue }) => {
        // Auto-enable Open URL when Web Search is enabled
        const isWebSearchEnabled = webSearchTool && values.enabled_tools_map[webSearchTool.id];

        return (
          <Form className="h-full w-full">
            <SettingsLayouts.Root>
              <SettingsLayouts.Header
                icon={SvgOnyxLogo}
                title="Default Assistant"
                description="Configure the default assistant that all users see when they start a new chat. Changes apply to everyone who hasn't customized their own assistant."
                rightChildren={
                  <Button type="submit" disabled={isSubmitting}>
                    {isSubmitting ? "Saving..." : "Save Changes"}
                  </Button>
                }
                separator
              />

              <SettingsLayouts.Body>

                {/* ═══════════════════════════════════════════════════════
                    SECTION 1: Instructions
                    ═══════════════════════════════════════════════════════ */}
                <SectionHeader
                  icon={SvgBubbleText}
                  title="System Instructions"
                  description="Define how the default assistant behaves, responds, and what personality it conveys to all users."
                  color="blue"
                />

                <GeneralLayouts.Section gap={0.75}>
                  <Card>
                    <GeneralLayouts.Section gap={0.5}>
                      <InputTextArea
                        rows={8}
                        value={values.system_prompt}
                        onChange={(event) => {
                          setFieldValue("system_prompt", event.target.value);
                          if (values.isUsingDefault) {
                            setFieldValue("isUsingDefault", false);
                          }
                        }}
                        placeholder="You are a professional email writing assistant that always uses a polite enthusiastic tone, emphasizes action items, and leaves blanks for the human to fill in when you have unknowns"
                      />
                      <div className="flex justify-between items-center">
                        <button
                          type="button"
                          className="flex items-center gap-1.5 text-xs text-link hover:underline disabled:opacity-40 disabled:cursor-not-allowed transition-opacity"
                          disabled={values.isUsingDefault}
                          onClick={() => {
                            setFieldValue("system_prompt", config.default_system_prompt);
                            setFieldValue("isUsingDefault", true);
                          }}
                        >
                          <SvgRefreshCw className="w-3 h-3 stroke-current" />
                          Reset to Default
                        </button>
                        <Text as="span" secondaryBody text03>
                          {values.system_prompt.length} characters
                        </Text>
                      </div>
                    </GeneralLayouts.Section>
                  </Card>

                  {/* Placeholder variables info */}
                  <Card variant="secondary">
                    <div className="flex items-start gap-2 mb-2">
                      <SvgInfoSmall className="w-4 h-4 stroke-text-03 flex-shrink-0 mt-0.5" />
                      <Text secondaryBody text03 className="text-xs font-medium">
                        Available template variables
                      </Text>
                    </div>
                    <div className="flex flex-col gap-2 ml-6">
                      <PlaceholderTag
                        tag="{{CURRENT_DATETIME}}"
                        description="Injects the current date and day of the week"
                      />
                      <PlaceholderTag
                        tag="{{CITATION_GUIDANCE}}"
                        description="Adds instructions for citing facts from search tools"
                      />
                      <PlaceholderTag
                        tag="{{REMINDER_TAG_DESCRIPTION}}"
                        description="Adds instructions for handling system reminder tags"
                      />
                    </div>
                  </Card>
                </GeneralLayouts.Section>

                <Separator noPadding />

                {/* ═══════════════════════════════════════════════════════
                    SECTION 2: Built-in Actions
                    ═══════════════════════════════════════════════════════ */}
                <SectionHeader
                  icon={SvgSparkle}
                  title="Built-in Actions"
                  description="Enable or disable the core capabilities available to the default assistant."
                  color="purple"
                />

                <GeneralLayouts.Section gap={0.5}>
                  {!hideSearchTool && searchTool && (
                    <BuiltInToolCard
                      name={`enabled_tools_map.${searchTool.id}`}
                      icon={SvgSearch}
                      title="Knowledge Search"
                      description="Search through your organization's knowledge base and documents. Requires at least one data source to be connected."
                    />
                  )}

                  {imageGenTool && (
                    <BuiltInToolCard
                      name={`enabled_tools_map.${imageGenTool.id}`}
                      icon={SvgImage}
                      title="Image Generation"
                      description="Generate and manipulate images using AI-powered tools. Requires an OpenAI LLM provider with API key under AI Models."
                    />
                  )}

                  {webSearchTool && (
                    <Card>
                      <InputLayouts.Horizontal
                        name={`enabled_tools_map.${webSearchTool.id}`}
                        title="Web Search"
                        description="Access real-time information and search the web for up-to-date results. Automatically enables Open URL when active."
                        center
                      >
                        <SwitchField
                          name={`enabled_tools_map.${webSearchTool.id}`}
                          onCheckedChange={(checked) => {
                            if (checked && openUrlTool) {
                              setFieldValue(`enabled_tools_map.${openUrlTool.id}`, true);
                            }
                          }}
                        />
                      </InputLayouts.Horizontal>
                    </Card>
                  )}

                  {openUrlTool && (
                    <Card variant={isWebSearchEnabled ? "disabled" : undefined}>
                      <InputLayouts.Horizontal
                        name={`enabled_tools_map.${openUrlTool.id}`}
                        title="Open URL"
                        description={
                          isWebSearchEnabled
                            ? "Read and extract content from any web page URL. Required by Web Search — cannot be disabled while Web Search is active."
                            : "Read and extract content from any web page URL. Strongly recommended when Web Search is enabled."
                        }
                        disabled={!!isWebSearchEnabled}
                        center
                      >
                        <SwitchField
                          name={`enabled_tools_map.${openUrlTool.id}`}
                          disabled={!!isWebSearchEnabled}
                        />
                      </InputLayouts.Horizontal>
                    </Card>
                  )}

                  {pythonTool && (
                    <BuiltInToolCard
                      name={`enabled_tools_map.${pythonTool.id}`}
                      icon={SvgCpu}
                      title="Code Interpreter"
                      description="Execute Python code in a secure, isolated environment to analyze data, create visualizations, and perform computations."
                    />
                  )}

                  {fileReaderTool && (
                    <BuiltInToolCard
                      name={`enabled_tools_map.${fileReaderTool.id}`}
                      icon={SvgFileText}
                      title="File Reader"
                      description="Read sections of uploaded files. Essential for large documents that exceed the AI's context window."
                    />
                  )}
                </GeneralLayouts.Section>

                {/* ═══════════════════════════════════════════════════════
                    SECTION 3: MCP Actions (if any)
                    ═══════════════════════════════════════════════════════ */}
                {Object.keys(mcpToolsByServer).length > 0 && (
                  <>
                    <Separator noPadding />
                    <SectionHeader
                      icon={SvgServer}
                      title="MCP Server Tools"
                      description="Tools provided by connected MCP (Model Context Protocol) servers."
                      color="green"
                    />
                    <GeneralLayouts.Section gap={0.5}>
                      {Object.entries(mcpToolsByServer).map(([serverId, serverTools]) => {
                        const serverIdNum = parseInt(serverId);
                        const serverInfo = mcpServers.find((s) => s.id === serverIdNum);
                        const firstTool = serverTools[0];
                        const serverName =
                          serverInfo?.name ||
                          firstTool?.name?.split("_").slice(0, -1).join("_") ||
                          `MCP Server ${serverId}`;
                        const serverUrl = serverInfo?.server_url || "Unknown URL";

                        return (
                          <MCPServerToolsCard
                            key={serverId}
                            serverId={serverIdNum}
                            serverName={serverName}
                            serverUrl={serverUrl}
                            serverTools={serverTools}
                          />
                        );
                      })}
                    </GeneralLayouts.Section>
                  </>
                )}

                {/* ═══════════════════════════════════════════════════════
                    SECTION 4: OpenAPI Actions (if any)
                    ═══════════════════════════════════════════════════════ */}
                {customTools.length > 0 && (
                  <>
                    <Separator noPadding />
                    <SectionHeader
                      icon={SvgActions}
                      title="OpenAPI Actions"
                      description="Custom tools connected via OpenAPI specifications."
                      color="orange"
                    />
                    <GeneralLayouts.Section gap={0.5}>
                      {customTools.map((tool) => (
                        <OpenAPIToolCard key={tool.id} tool={tool} />
                      ))}
                    </GeneralLayouts.Section>
                  </>
                )}

              </SettingsLayouts.Body>
            </SettingsLayouts.Root>
          </Form>
        );
      }}
    </Formik>
  );
}

// ─── Page ───────────────────────────────────────────────────────────────────

export default function Page() {
  return <DefaultAssistantContent />;
}
