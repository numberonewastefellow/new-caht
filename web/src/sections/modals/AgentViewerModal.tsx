"use client";

import { useCallback, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import type { Route } from "next";
import { FullPersona } from "@/app/admin/assistants/interfaces";
import { useModal } from "@/refresh-components/contexts/ModalContext";
import Modal from "@/refresh-components/Modal";
import { Section, LineItemLayout } from "@/layouts/general-layouts";
import Text from "@/refresh-components/texts/Text";
import AgentAvatar from "@/refresh-components/avatars/AgentAvatar";
import Separator from "@/refresh-components/Separator";
import {
  SvgActions,
  SvgBubbleText,
  SvgExpand,
  SvgFold,
  SvgFiles,
  SvgOrganization,
  SvgStar,
  SvgUser,
} from "@opal/icons";
import * as ExpandableCard from "@/layouts/expandable-card-layouts";
import * as ActionsLayouts from "@/layouts/actions-layouts";
import useMcpServersForAgentEditor from "@/hooks/useMcpServersForAgentEditor";
import { getActionIcon } from "@/lib/tools/mcpUtils";
import { MCPServer, ToolSnapshot } from "@/lib/tools/interfaces";
import EmptyMessage from "@/refresh-components/EmptyMessage";
import { Horizontal, Title } from "@/layouts/input-layouts";
import Switch from "@/refresh-components/inputs/Switch";
import Button from "@/refresh-components/buttons/Button";
import { SEARCH_PARAM_NAMES } from "@/app/app/services/searchParams";
import AppInputBar from "@/sections/input/AppInputBar";
import { useFilters, useLlmManager } from "@/lib/hooks";
import { formatMmDdYyyy } from "@/lib/dateUtils";
import { useProjectsContext } from "@/providers/ProjectsContext";
import { FileCard } from "@/sections/cards/FileCard";
import DocumentSetCard from "@/sections/cards/DocumentSetCard";
import { getDisplayName } from "@/lib/llm/utils";
import { useLLMProviders } from "@/lib/hooks/useLLMProviders";
import { Interactive } from "@opal/core";
import { cn } from "@/lib/utils";

// ─── Tab types ────────────────────────────────────────────────────────────────

type TabId = "overview" | "tools" | "knowledge";

interface TabConfig {
  id: TabId;
  label: string;
  count?: number;
}

function TabStrip({
  tabs,
  active,
  onChange,
}: {
  tabs: TabConfig[];
  active: TabId;
  onChange: (id: TabId) => void;
}) {
  return (
    <div className="flex items-center gap-1 border-b border-border-01 pb-0 -mx-1">
      {tabs.map((tab) => {
        const isActive = tab.id === active;
        return (
          <button
            key={tab.id}
            type="button"
            onClick={() => onChange(tab.id)}
            className={cn(
              "relative flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-t-08",
              "transition-colors select-none focus:outline-none",
              isActive ? "text-text-05" : "text-text-03 hover:text-text-04"
            )}
            style={
              isActive
                ? {
                    color:
                      "var(--virtualai-accent, var(--theme-primary-05))",
                  }
                : undefined
            }
          >
            {tab.label}
            {tab.count !== undefined && tab.count > 0 && (
              <span
                className={cn(
                  "inline-flex items-center justify-center min-w-[1.25rem] h-4 px-1 rounded-full text-[10px] font-semibold leading-none",
                  isActive
                    ? "text-background-neutral-00"
                    : "text-text-02 bg-background-tint-02"
                )}
                style={
                  isActive
                    ? {
                        backgroundColor:
                          "var(--virtualai-accent, var(--theme-primary-05))",
                      }
                    : undefined
                }
              >
                {tab.count}
              </span>
            )}
            {/* Active bottom border indicator */}
            {isActive && (
              <span
                className="absolute bottom-0 left-0 right-0 h-0.5 rounded-full"
                style={{
                  backgroundColor:
                    "var(--virtualai-accent, var(--theme-primary-05))",
                }}
              />
            )}
          </button>
        );
      })}
    </div>
  );
}

// ─── MCP Server card (read-only, expandable) ──────────────────────────────────

interface ViewerMCPServerCardProps {
  server: MCPServer;
  tools: ToolSnapshot[];
}

function ViewerMCPServerCard({ server, tools }: ViewerMCPServerCardProps) {
  const [folded, setFolded] = useState(false);
  const serverIcon = getActionIcon(server.server_url, server.name);

  return (
    <ExpandableCard.Root isFolded={folded} onFoldedChange={setFolded}>
      <ExpandableCard.Header>
        <div className="p-2">
          <LineItemLayout
            icon={serverIcon}
            title={server.name}
            description={server.description}
            variant="secondary"
            rightChildren={
              <div className="flex items-center gap-2">
                {tools.length > 0 && (
                  <span
                    className="inline-flex items-center justify-center h-5 px-1.5 rounded-full text-[10px] font-semibold text-background-neutral-00 leading-none"
                    style={{
                      backgroundColor:
                        "var(--virtualai-accent, var(--theme-primary-05))",
                    }}
                  >
                    {tools.length}
                  </span>
                )}
                <Button
                  internal
                  rightIcon={folded ? SvgExpand : SvgFold}
                  onClick={() => setFolded((prev) => !prev)}
                >
                  {folded ? "Expand" : "Fold"}
                </Button>
              </div>
            }
            center
          />
        </div>
      </ExpandableCard.Header>
      {tools.length > 0 && (
        <ActionsLayouts.Content>
          {tools.map((tool) => (
            <Section key={tool.id} padding={0.25}>
              <LineItemLayout
                title={tool.display_name}
                description={tool.description}
                variant="secondary"
              />
            </Section>
          ))}
        </ActionsLayouts.Content>
      )}
    </ExpandableCard.Root>
  );
}

// ─── OpenAPI tool card (read-only, static) ────────────────────────────────────

function ViewerOpenApiToolCard({ tool }: { tool: ToolSnapshot }) {
  return (
    <ExpandableCard.Root>
      <ExpandableCard.Header>
        <div className="p-2">
          <LineItemLayout
            icon={SvgActions}
            title={tool.display_name}
            description={tool.description}
            variant="secondary"
            center
          />
        </div>
      </ExpandableCard.Header>
    </ExpandableCard.Root>
  );
}

// ─── Chat input bar ───────────────────────────────────────────────────────────

const EMPTY_DOCS: [] = [];

interface AgentChatInputProps {
  agent: FullPersona;
  onSubmit: (message: string) => void;
}
function AgentChatInput({ agent, onSubmit }: AgentChatInputProps) {
  const llmManager = useLlmManager(undefined, agent);
  const filterManager = useFilters();

  return (
    <AppInputBar
      onSubmit={onSubmit}
      llmManager={llmManager}
      chatState="input"
      filterManager={filterManager}
      selectedAssistant={agent}
      selectedDocuments={EMPTY_DOCS}
      removeDocs={() => {}}
      stopGenerating={() => {}}
      handleFileUpload={() => {}}
      toggleDocumentSidebar={() => {}}
      currentSessionFileTokenCount={0}
      availableContextTokens={Infinity}
      retrievalEnabled={false}
      deepResearchEnabled={false}
      toggleDeepResearch={() => {}}
      disabled={false}
    />
  );
}

// ─── Overview tab ─────────────────────────────────────────────────────────────

function OverviewTab({
  agent,
  defaultModel,
  onStartChat,
}: {
  agent: FullPersona;
  defaultModel: string | null | undefined;
  onStartChat: (message: string) => void;
}) {
  const hasStarters =
    agent.starter_messages && agent.starter_messages.length > 0;

  return (
    <div className="flex flex-col gap-5">
      {/* Conversation Starters */}
      {hasStarters && (
        <div className="flex flex-col gap-2">
          <Text as="p" mainContentEmphasis className="text-xs font-semibold uppercase tracking-wide text-text-02">
            Conversation Starters
          </Text>
          <div className="grid grid-cols-2 gap-2">
            {agent.starter_messages!.map((starter, index) => (
              <Interactive.Base
                key={index}
                onClick={() => onStartChat(starter.message)}
                variant="default"
                prominence="tertiary"
              >
                <div
                  className="rounded-12 border p-3 cursor-pointer transition-all duration-150 group"
                  style={{
                    borderColor:
                      "var(--virtualai-accent-glow, color-mix(in srgb, var(--virtualai-accent, var(--theme-primary-05)) 25%, transparent))",
                  }}
                  onMouseEnter={(e) => {
                    (e.currentTarget as HTMLElement).style.backgroundColor =
                      "var(--virtualai-accent-subtle, color-mix(in srgb, var(--virtualai-accent, var(--theme-primary-05)) 8%, transparent))";
                  }}
                  onMouseLeave={(e) => {
                    (e.currentTarget as HTMLElement).style.backgroundColor = "";
                  }}
                >
                  <div className="flex items-start gap-2">
                    <SvgBubbleText
                      className="w-3.5 h-3.5 mt-0.5 flex-shrink-0"
                      style={{
                        color:
                          "var(--virtualai-accent, var(--theme-primary-05))",
                      }}
                    />
                    <Text
                      as="p"
                      secondaryBody
                      className="text-text-04 text-xs leading-relaxed line-clamp-3"
                    >
                      {starter.message}
                    </Text>
                  </div>
                </div>
              </Interactive.Base>
            ))}
          </div>
        </div>
      )}

      {!hasStarters && (
        <div className="text-center py-6">
          <SvgBubbleText className="w-8 h-8 mx-auto mb-2 text-text-02" />
          <Text as="p" secondaryBody text03>
            No conversation starters configured.
          </Text>
          <Text as="p" secondaryBody text03>
            Ask anything to get started.
          </Text>
        </div>
      )}

      {/* Prompt Reminders */}
      {agent.task_prompt && (
        <>
          <Separator noPadding />
          <div className="flex flex-col gap-1.5">
            <Text as="p" mainContentEmphasis className="text-xs font-semibold uppercase tracking-wide text-text-02">
              Prompt Reminders
            </Text>
            <div className="rounded-08 bg-background-tint-02 p-3">
              <Text as="p" secondaryBody text03 className="text-xs leading-relaxed whitespace-pre-wrap">
                {agent.task_prompt}
              </Text>
            </div>
          </div>
        </>
      )}

      {/* More Info */}
      <Separator noPadding />
      <div className="flex flex-col gap-2">
        <Text as="p" mainContentEmphasis className="text-xs font-semibold uppercase tracking-wide text-text-02">
          Configuration
        </Text>
        <div className="flex flex-col gap-1">
          {agent.system_prompt && (
            <Horizontal
              title="Instructions"
              description={agent.system_prompt}
              nonInteractive
              variant="secondary"
            />
          )}
          {defaultModel && (
            <Horizontal
              title="Default Model"
              description="This model will be used by VertualAI by default in your chats."
              nonInteractive
              variant="secondary"
            >
              <Text>{defaultModel}</Text>
            </Horizontal>
          )}
          {agent.search_start_date && (
            <Horizontal
              title="Knowledge Cutoff Date"
              description="Documents with a last-updated date prior to this will be ignored."
              nonInteractive
              variant="secondary"
            >
              <Text mainUiMono>
                {formatMmDdYyyy(agent.search_start_date)}
              </Text>
            </Horizontal>
          )}
          <Horizontal
            title="Overwrite System Prompts"
            description='Remove the base system prompt which includes useful instructions (e.g. "You can use Markdown tables"). This may affect response quality.'
            nonInteractive
            variant="secondary"
          >
            <Switch disabled checked={agent.replace_base_system_prompt} />
          </Horizontal>
        </div>
      </div>
    </div>
  );
}

// ─── Tools tab ────────────────────────────────────────────────────────────────

function ToolsTab({
  mcpServersWithTools,
  openApiTools,
}: {
  mcpServersWithTools: { server: MCPServer; tools: ToolSnapshot[] }[];
  openApiTools: ToolSnapshot[];
}) {
  const hasActions = mcpServersWithTools.length > 0 || openApiTools.length > 0;

  if (!hasActions) {
    return (
      <div className="py-6">
        <EmptyMessage title="No Actions" />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {mcpServersWithTools.length > 0 && (
        <div className="flex flex-col gap-1">
          {mcpServersWithTools.length > 0 && (
            <Text as="p" mainContentEmphasis className="text-xs font-semibold uppercase tracking-wide text-text-02 mb-1">
              MCP Servers
            </Text>
          )}
          <Section gap={0.5} alignItems="start">
            {mcpServersWithTools.map(({ server, tools }) => (
              <ViewerMCPServerCard
                key={server.id}
                server={server}
                tools={tools}
              />
            ))}
          </Section>
        </div>
      )}

      {openApiTools.length > 0 && (
        <div className="flex flex-col gap-1">
          <Text as="p" mainContentEmphasis className="text-xs font-semibold uppercase tracking-wide text-text-02 mb-1">
            API Actions
          </Text>
          <Section gap={0.5} alignItems="start">
            {openApiTools.map((tool) => (
              <ViewerOpenApiToolCard key={tool.id} tool={tool} />
            ))}
          </Section>
        </div>
      )}
    </div>
  );
}

// ─── Knowledge tab ────────────────────────────────────────────────────────────

function KnowledgeTab({
  agent,
  allRecentFiles,
}: {
  agent: FullPersona;
  allRecentFiles: ReturnType<typeof useProjectsContext>["allRecentFiles"];
}) {
  const hasDocSets = agent.document_sets && agent.document_sets.length > 0;
  const hasFiles = agent.user_file_ids && agent.user_file_ids.length > 0;
  const hasKnowledge = hasDocSets || hasFiles;

  if (!hasKnowledge) {
    return (
      <div className="py-8 flex flex-col items-center gap-3">
        <div
          className="w-12 h-12 rounded-full flex items-center justify-center"
          style={{
            backgroundColor:
              "var(--virtualai-accent-subtle, color-mix(in srgb, var(--virtualai-accent, var(--theme-primary-05)) 8%, transparent))",
          }}
        >
          <SvgFiles
            className="w-6 h-6"
            style={{
              color: "var(--virtualai-accent, var(--theme-primary-05))",
            }}
          />
        </div>
        <div className="text-center">
          <Text as="p" mainContentBody className="font-medium text-text-04">
            No Knowledge Connected
          </Text>
          <Text as="p" secondaryBody text03 className="mt-0.5">
            This agent doesn&apos;t have any knowledge sources attached.
          </Text>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-5">
      {/* Document Sets */}
      {hasDocSets && (
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-2">
            <Text as="p" mainContentEmphasis className="text-xs font-semibold uppercase tracking-wide text-text-02">
              Collections
            </Text>
            <span
              className="inline-flex items-center justify-center min-w-[1.25rem] h-4 px-1 rounded-full text-[10px] font-semibold leading-none text-background-neutral-00"
              style={{
                backgroundColor:
                  "var(--virtualai-accent, var(--theme-primary-05))",
              }}
            >
              {agent.document_sets!.length}
            </span>
          </div>
          <div className="flex flex-wrap gap-2">
            {agent.document_sets!.map((docSet) => (
              <DocumentSetCard key={docSet.id} documentSet={docSet} />
            ))}
          </div>
        </div>
      )}

      {/* User Files */}
      {hasFiles && (
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-2">
            <Text as="p" mainContentEmphasis className="text-xs font-semibold uppercase tracking-wide text-text-02">
              Files
            </Text>
            <span
              className="inline-flex items-center justify-center min-w-[1.25rem] h-4 px-1 rounded-full text-[10px] font-semibold leading-none text-background-neutral-00"
              style={{
                backgroundColor:
                  "var(--virtualai-accent, var(--theme-primary-05))",
              }}
            >
              {agent.user_file_ids!.length}
            </span>
          </div>
          <div className="flex flex-wrap gap-2">
            {agent.user_file_ids!.map((fileId) => {
              const file = allRecentFiles.find((f) => f.id === fileId);
              if (!file) return null;
              return <FileCard key={fileId} file={file} />;
            })}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Main AgentViewerModal ────────────────────────────────────────────────────

export interface AgentViewerModalProps {
  agent: FullPersona;
}

export default function AgentViewerModal({ agent }: AgentViewerModalProps) {
  const agentViewerModal = useModal();
  const router = useRouter();
  const { allRecentFiles } = useProjectsContext();
  const { llmProviders } = useLLMProviders(agent.id);
  const [activeTab, setActiveTab] = useState<TabId>("overview");

  const handleStartChat = useCallback(
    (message: string) => {
      const params = new URLSearchParams({
        [SEARCH_PARAM_NAMES.PERSONA_ID]: String(agent.id),
        [SEARCH_PARAM_NAMES.USER_PROMPT]: message,
        [SEARCH_PARAM_NAMES.SEND_ON_LOAD]: "true",
      });
      router.push(`/app?${params.toString()}` as Route);
      agentViewerModal.toggle(false);
    },
    [agent.id, router, agentViewerModal]
  );

  // Categorize tools into MCP and OpenAPI
  const mcpToolsByServerId = useMemo(() => {
    const map = new Map<number, ToolSnapshot[]>();
    agent.tools.forEach((tool) => {
      if (tool.mcp_server_id != null) {
        const existing = map.get(tool.mcp_server_id) || [];
        existing.push(tool);
        map.set(tool.mcp_server_id, existing);
      }
    });
    return map;
  }, [agent.tools]);

  const openApiTools = useMemo(
    () =>
      agent.tools.filter((t) => !t.in_code_tool_id && t.mcp_server_id == null),
    [agent.tools]
  );

  const { mcpData } = useMcpServersForAgentEditor();
  const mcpServers = mcpData?.mcp_servers ?? [];

  const mcpServersWithTools = useMemo(
    () =>
      mcpServers
        .filter((server) => mcpToolsByServerId.has(server.id))
        .map((server) => ({
          server,
          tools: mcpToolsByServerId.get(server.id)!,
        })),
    [mcpServers, mcpToolsByServerId]
  );

  const totalToolCount =
    mcpServersWithTools.reduce((acc, s) => acc + s.tools.length, 0) +
    openApiTools.length;

  const knowledgeCount =
    (agent.document_sets?.length ?? 0) + (agent.user_file_ids?.length ?? 0);

  const defaultModel = getDisplayName(agent, llmProviders ?? []);

  const tabs: TabConfig[] = [
    { id: "overview", label: "Overview" },
    { id: "tools", label: "Tools", count: totalToolCount },
    { id: "knowledge", label: "Knowledge", count: knowledgeCount },
  ];

  return (
    <Modal
      open={agentViewerModal.isOpen}
      onOpenChange={agentViewerModal.toggle}
    >
      <Modal.Content
        width="md-sm"
        height="lg"
        bottomSlot={<AgentChatInput agent={agent} onSubmit={handleStartChat} />}
      >
        <Modal.Header
          icon={(props) => <AgentAvatar agent={agent} {...props} size={24} />}
          title={agent.name}
          onClose={() => agentViewerModal.toggle(false)}
        />

        <Modal.Body>
          {/* ── Metadata pills ── */}
          <div className="flex flex-wrap items-center gap-1.5">
            {!agent.is_default_persona && (
              <span
                className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold"
                style={{
                  backgroundColor:
                    "var(--virtualai-accent-subtle, color-mix(in srgb, var(--virtualai-accent, var(--theme-primary-05)) 12%, transparent))",
                  color:
                    "var(--virtualai-accent, var(--theme-primary-05))",
                }}
              >
                <SvgStar className="w-3 h-3" />
                Featured
              </span>
            )}
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs bg-background-tint-02 text-text-03">
              <SvgUser className="w-3 h-3" />
              {agent.owner?.email ?? "VertualAI"}
            </span>
            {agent.is_public && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs bg-background-tint-02 text-text-03">
                <SvgOrganization className="w-3 h-3" />
                Public to your organization
              </span>
            )}
          </div>

          {/* ── Description ── */}
          {agent.description && (
            <div className="rounded-10 bg-background-tint-02 px-3 py-2.5">
              <Text as="p" secondaryBody className="text-text-04 text-sm leading-relaxed">
                {agent.description}
              </Text>
            </div>
          )}

          {/* ── Tab strip ── */}
          <TabStrip tabs={tabs} active={activeTab} onChange={setActiveTab} />

          {/* ── Tab content ── */}
          <div className="flex flex-col">
            {activeTab === "overview" && (
              <OverviewTab
                agent={agent}
                defaultModel={defaultModel}
                onStartChat={handleStartChat}
              />
            )}
            {activeTab === "tools" && (
              <ToolsTab
                mcpServersWithTools={mcpServersWithTools}
                openApiTools={openApiTools}
              />
            )}
            {activeTab === "knowledge" && (
              <KnowledgeTab
                agent={agent}
                allRecentFiles={allRecentFiles}
              />
            )}
          </div>
        </Modal.Body>
      </Modal.Content>
    </Modal>
  );
}
