"use client";

import React, { useState, useCallback, useMemo } from "react";
import type { MinimalAgentSnapshot } from "@/app/admin/assistants/interfaces";
import type { ToolSnapshot } from "@/lib/tools/interfaces";
import type { DocumentSetSummary } from "@/lib/types";
import type { LLMProviderDescriptor } from "@/app/admin/configuration/llm/interfaces";
import type { AgentNodeData, ConditionalRouterNodeData } from "./types";
import {
  SEARCH_TOOL_ID,
  WEB_SEARCH_TOOL_ID,
  IMAGE_GENERATION_TOOL_ID,
  PYTHON_TOOL_ID,
  OPEN_URL_TOOL_ID,
  FILE_READER_TOOL_ID,
  HTTP_REQUEST_TOOL_ID,
} from "@/app/app/components/tools/constants";
import { structureValue, parseLlmDescriptor } from "@/lib/llm/utils";
import { CONDITION_OPERATORS } from "@/lib/workflows/interfaces";

// Built-in tool display config
const BUILTIN_TOOLS: {
  id: string;
  label: string;
  desc: string;
}[] = [
  {
    id: IMAGE_GENERATION_TOOL_ID,
    label: "Image Generation",
    desc: "Create and edit images using AI. Requires an image generation model to be configured.",
  },
  {
    id: WEB_SEARCH_TOOL_ID,
    label: "Web Search",
    desc: "Search the internet for real-time information. Best paired with Open URL for full web page reading.",
  },
  {
    id: OPEN_URL_TOOL_ID,
    label: "Open URL",
    desc: "Read and extract content from any web page URL. Strongly recommended when Web Search is enabled.",
  },
  {
    id: PYTHON_TOOL_ID,
    label: "Code Interpreter",
    desc: "Write, execute, and debug Python code. Great for data analysis, calculations, and file processing.",
  },
  {
    id: FILE_READER_TOOL_ID,
    label: "File Reader",
    desc: "Read and process uploaded files section by section. Essential for large documents that exceed the AI's context window.",
  },
  {
    id: HTTP_REQUEST_TOOL_ID,
    label: "HTTP Request",
    desc: "Make HTTP requests to any URL. Supports GET, POST, PUT, DELETE, PATCH methods with custom headers and body.",
  },
];

// CONDITION_OPERATORS imported from @/lib/workflows/interfaces (single source of truth)

type ConfigTab = "properties" | "advanced" | "json";

interface NodeConfigPanelProps {
  nodeId: string;
  nodeType?: string;
  data: AgentNodeData | ConditionalRouterNodeData;
  agents: MinimalAgentSnapshot[];
  availableTools: ToolSnapshot[];
  documentSets: DocumentSetSummary[];
  llmProviders: LLMProviderDescriptor[];
  onUpdate: (nodeId: string, partial: Partial<AgentNodeData> | Partial<ConditionalRouterNodeData>) => void;
  onDelete: (nodeId: string) => void;
  onClose: () => void;
  /** Collapse state */
  collapsed?: boolean;
  onToggleCollapse?: () => void;
}

export function NodeConfigPanel({
  nodeId,
  nodeType,
  data: rawData,
  agents,
  availableTools,
  documentSets,
  llmProviders,
  onUpdate,
  onDelete,
  onClose,
  collapsed,
  onToggleCollapse,
}: NodeConfigPanelProps) {
  const [activeTab, setActiveTab] = useState<ConfigTab>("properties");

  // Collapsed state: render thin strip
  if (collapsed) {
    return (
      <div className="wfb-config-panel wfb-config-panel--collapsed">
        <button
          className="wfb-sidebar-collapse-btn"
          onClick={onToggleCollapse}
          title="Expand config panel"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="15 18 9 12 15 6" />
          </svg>
        </button>
      </div>
    );
  }

  // If this is a conditional router node, render specialized config
  if (nodeType === "conditional_router") {
    return (
      <ConditionConfigPanel
        nodeId={nodeId}
        data={rawData as ConditionalRouterNodeData}
        onUpdate={onUpdate}
        onDelete={onDelete}
        onClose={onClose}
        onToggleCollapse={onToggleCollapse}
      />
    );
  }

  // After the early return above, rawData is guaranteed to be AgentNodeData.
  const data = rawData as AgentNodeData;
  const currentAgent = agents.find((a) => a.id === data.agent_id);

  // Check if current agent is a utility agent
  const isHttpRequestAgent = data.agent_name === "HTTP Request";
  const isCodeExecutorAgent = data.agent_name === "Code Executor";
  const isUtilityAgent = isHttpRequestAgent || isCodeExecutorAgent;

  // Effective tool IDs: step override > agent tools
  const effectiveToolIds = useMemo(() => {
    if (data.tool_ids_override != null) {
      return new Set(data.tool_ids_override);
    }
    return new Set((currentAgent?.tools || []).map((t) => t.id));
  }, [data.tool_ids_override, currentAgent?.tools]);

  // Effective document set IDs: step override > agent doc sets
  const effectiveDocSetIds = useMemo(() => {
    if (data.document_set_ids_override != null) {
      return new Set(data.document_set_ids_override);
    }
    return new Set(
      (currentAgent?.document_sets || []).map((d) => d.id)
    );
  }, [data.document_set_ids_override, currentAgent?.document_sets]);

  // JSON view of node data
  const nodeJson = useMemo(() => {
    try {
      const clean = { ...data };
      // Remove display-only fields for cleaner JSON
      delete (clean as Record<string, unknown>).isSelected;
      return JSON.stringify(clean, null, 2);
    } catch {
      return "{}";
    }
  }, [data]);

  return (
    <div className="wfb-config-panel">
      {/* Header */}
      <div className="wfb-config-header">
        <div className="wfb-config-title">Configure Step</div>
        <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
          {onToggleCollapse && (
            <button className="wfb-config-close" onClick={onToggleCollapse} title="Collapse panel">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="9 18 15 12 9 6" />
              </svg>
            </button>
          )}
          <button className="wfb-config-close" onClick={onClose} title="Close">
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <path d="M18 6L6 18M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

      {/* Tab bar */}
      <div className="wfb-config-tabs">
        <button
          className={`wfb-config-tab ${activeTab === "properties" ? "wfb-config-tab--active" : ""}`}
          onClick={() => setActiveTab("properties")}
        >
          Properties
        </button>
        {!isUtilityAgent && (
          <button
            className={`wfb-config-tab ${activeTab === "advanced" ? "wfb-config-tab--active" : ""}`}
            onClick={() => setActiveTab("advanced")}
          >
            Advanced
          </button>
        )}
        <button
          className={`wfb-config-tab ${activeTab === "json" ? "wfb-config-tab--active" : ""}`}
          onClick={() => setActiveTab("json")}
        >
          JSON
        </button>
      </div>

      {/* Body */}
      <div className="wfb-config-body">
        {/* ── Properties Tab ─────────────────────────────── */}
        {activeTab === "properties" && (
          <>
            {/* Agent selection */}
            <div className="wfb-config-section">
              <div className="wfb-config-label">Agent</div>
              <select
                className="wfb-agent-select"
                value={data.agent_id}
                onChange={(e) => {
                  const id = Number(e.target.value);
                  const agent = agents.find((a) => a.id === id);
                  if (agent) {
                    onUpdate(nodeId, {
                      agent_id: agent.id,
                      agent_name: agent.name,
                      agent_description: agent.description || "",
                      agent_icon_url: agent.uploaded_image_id
                        ? `/api/agent/${agent.id}/uploaded_image`
                        : null,
                      agent_num_tools: agent.tools?.length || 0,
                      agent_tool_names: (agent.tools || []).map((t) => t.name),
                      agent_llm_model:
                        agent.llm_model_version_override || null,
                      agent_llm_provider:
                        agent.llm_model_provider_override || null,
                      // Clear all overrides when switching agent
                      llm_provider_override: null,
                      llm_model_override: null,
                      max_output_tokens_override: null,
                      system_prompt_override: null,
                      task_prompt_override: null,
                      tool_ids_override: null,
                      document_set_ids_override: null,
                      replace_base_system_prompt_override: null,
                    });
                  }
                }}
              >
                {agents
                  .filter((a) => !a.workflow_id && a.id !== 0)
                  .map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.name}
                    </option>
                  ))}
              </select>
            </div>

            {/* Step name */}
            <div className="wfb-config-section">
              <div className="wfb-config-label">Step Name</div>
              <input
                className="wfb-config-input"
                type="text"
                value={data.step_name}
                onChange={(e) => onUpdate(nodeId, { step_name: e.target.value })}
                placeholder="e.g. Research Topic"
              />
            </div>

            {/* Step description */}
            <div className="wfb-config-section">
              <div className="wfb-config-label">Step Description</div>
              <textarea
                className="wfb-config-textarea"
                value={data.step_description}
                onChange={(e) =>
                  onUpdate(nodeId, { step_description: e.target.value })
                }
                placeholder="What this step does..."
                rows={3}
              />
            </div>

            {/* Output key */}
            <div className="wfb-config-section">
              <div className="wfb-config-label">Output Key</div>
              <input
                className="wfb-config-input"
                type="text"
                value={data.output_key}
                onChange={(e) => {
                  const val = e.target.value
                    .toLowerCase()
                    .replace(/[^a-z0-9_]/g, "");
                  onUpdate(nodeId, { output_key: val });
                }}
                placeholder="e.g. research_results"
              />
            </div>

            {/* Utility agent specialized config */}
            {isHttpRequestAgent && (
              <HttpRequestConfigSection
                nodeId={nodeId}
                data={data}
                onUpdate={onUpdate}
              />
            )}
            {isCodeExecutorAgent && (
              <CodeExecutorConfigSection
                nodeId={nodeId}
                data={data}
                onUpdate={onUpdate}
              />
            )}

            {/* Toggles */}
            <div className="wfb-config-section">
              <div className="wfb-config-label">Options</div>

              <div className="wfb-config-toggle-row">
                <div>
                  <div className="wfb-config-toggle-label">Terminal Step</div>
                  <div className="wfb-config-toggle-desc">
                    Marks this as a final step
                  </div>
                </div>
                <ToggleSwitch
                  checked={data.is_terminal}
                  onChange={(v) => onUpdate(nodeId, { is_terminal: v })}
                />
              </div>

              {!isUtilityAgent && (
                <div className="wfb-config-toggle-row">
                  <div>
                    <div className="wfb-config-toggle-label">
                      Can Request Input (HITL)
                    </div>
                    <div className="wfb-config-toggle-desc">
                      Agent can pause for user input
                    </div>
                  </div>
                  <ToggleSwitch
                    checked={data.can_request_input}
                    onChange={(v) => onUpdate(nodeId, { can_request_input: v })}
                  />
                </div>
              )}

              <div className="wfb-config-toggle-row">
                <div>
                  <div className="wfb-config-toggle-label">Show as Message</div>
                  <div className="wfb-config-toggle-desc">
                    Output appears in chat
                  </div>
                </div>
                <ToggleSwitch
                  checked={data.promote_output}
                  onChange={(v) => onUpdate(nodeId, { promote_output: v })}
                />
              </div>
            </div>

            {/* Agent info (read-only) */}
            {data.agent_description && (
              <div className="wfb-config-section">
                <div className="wfb-config-label">Agent Description</div>
                <div
                  style={{
                    fontSize: 12,
                    color: "var(--text-03, #9ca3af)",
                    lineHeight: 1.5,
                  }}
                >
                  {data.agent_description}
                </div>
              </div>
            )}
          </>
        )}

        {/* ── Advanced Tab ───────────────────────────────── */}
        {activeTab === "advanced" && !isUtilityAgent && (
          <>
            <LlmSection
              nodeId={nodeId}
              data={data}
              currentAgent={currentAgent}
              llmProviders={llmProviders}
              onUpdate={onUpdate}
            />

            <ToolsSection
              nodeId={nodeId}
              data={data}
              effectiveToolIds={effectiveToolIds}
              availableTools={availableTools}
              currentAgent={currentAgent}
              onUpdate={onUpdate}
            />

            <KnowledgeSection
              nodeId={nodeId}
              data={data}
              effectiveToolIds={effectiveToolIds}
              effectiveDocSetIds={effectiveDocSetIds}
              availableTools={availableTools}
              documentSets={documentSets}
              currentAgent={currentAgent}
              onUpdate={onUpdate}
            />

            <AdvancedSection nodeId={nodeId} data={data} onUpdate={onUpdate} />
          </>
        )}

        {/* ── JSON Tab ───────────────────────────────────── */}
        {activeTab === "json" && (
          <div className="wfb-config-section">
            <div className="wfb-config-label">Node Configuration (read-only)</div>
            <pre
              style={{
                fontSize: 11,
                fontFamily: "monospace",
                background: "var(--background-tint-02, #f3f4f6)",
                border: "1px solid var(--border-01, #e5e7eb)",
                borderRadius: 6,
                padding: 10,
                overflowX: "auto",
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
                color: "var(--text-05, #374151)",
                lineHeight: 1.5,
                maxHeight: "100%",
              }}
            >
              {nodeJson}
            </pre>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="wfb-config-footer">
        <button
          className="wfb-config-delete-btn"
          onClick={() => onDelete(nodeId)}
        >
          Remove from workflow
        </button>
      </div>
    </div>
  );
}

// ── Override badge ──────────────────────────────────────────────────────

function OverrideBadge({ onReset }: { onReset: () => void }) {
  return (
    <span
      style={{
        fontSize: 10,
        color: "var(--virtualai-accent, var(--theme-primary-05))",
        marginLeft: 6,
        cursor: "pointer",
      }}
      onClick={onReset}
      title="Reset to agent default"
    >
      (customized — reset)
    </span>
  );
}

// ── LLM Section ──────────────────────────────────────────────────────

function LlmSection({
  nodeId,
  data,
  currentAgent,
  llmProviders,
  onUpdate,
}: {
  nodeId: string;
  data: AgentNodeData;
  currentAgent: MinimalAgentSnapshot | undefined;
  llmProviders: LLMProviderDescriptor[];
  onUpdate: (nodeId: string, partial: Partial<AgentNodeData>) => void;
}) {
  // Effective LLM: step override > agent value > default
  const effectiveProvider =
    data.llm_provider_override ?? currentAgent?.llm_model_provider_override ?? null;
  const effectiveModel =
    data.llm_model_override ?? currentAgent?.llm_model_version_override ?? null;
  const isLlmOverridden = data.llm_provider_override != null || data.llm_model_override != null;

  // Effective max_output_tokens: step override > agent > null
  const effectiveMaxTokens =
    data.max_output_tokens_override ?? currentAgent?.max_output_tokens ?? null;
  const isMaxTokensOverridden = data.max_output_tokens_override != null;

  // Effective replace_base_system_prompt
  const effectiveReplace =
    data.replace_base_system_prompt_override ?? currentAgent?.replace_base_system_prompt ?? false;
  const isReplaceOverridden = data.replace_base_system_prompt_override != null;

  // Build current LLM value in structured format
  const currentLlmValue = useMemo(() => {
    if (!effectiveProvider || !effectiveModel) return "default";
    const provider = llmProviders.find((p) => p.name === effectiveProvider);
    if (!provider) return "default";
    return structureValue(provider.name, provider.provider, effectiveModel);
  }, [effectiveProvider, effectiveModel, llmProviders]);

  // Build LLM options list
  const llmOptions = useMemo(() => {
    const options: { value: string; label: string; group: string }[] = [];
    const seenKeys = new Set<string>();
    for (const provider of llmProviders) {
      for (const config of provider.model_configurations) {
        if (!config.is_visible) continue;
        const key = `${provider.provider}:${config.name}`;
        if (seenKeys.has(key)) continue;
        seenKeys.add(key);
        options.push({
          value: structureValue(provider.name, provider.provider, config.name),
          label: config.display_name || config.name,
          group: provider.provider_display_name || provider.provider,
        });
      }
    }
    return options;
  }, [llmProviders]);

  const handleLlmChange = useCallback(
    (value: string) => {
      if (value === "default") {
        // Reset to agent default
        onUpdate(nodeId, {
          llm_provider_override: null,
          llm_model_override: null,
        });
      } else {
        const { name, modelName } = parseLlmDescriptor(value);
        onUpdate(nodeId, {
          llm_provider_override: name,
          llm_model_override: modelName,
        });
      }
    },
    [nodeId, onUpdate]
  );

  const handleMaxTokensBlur = useCallback(
    (e: React.FocusEvent<HTMLInputElement>) => {
      const raw = e.target.value.trim();
      const val = raw === "" ? null : parseInt(raw, 10);
      if (val !== null && isNaN(val)) return;
      onUpdate(nodeId, { max_output_tokens_override: val });
    },
    [nodeId, onUpdate]
  );

  const handleReplacePromptToggle = useCallback(
    (enabled: boolean) => {
      onUpdate(nodeId, { replace_base_system_prompt_override: enabled });
    },
    [nodeId, onUpdate]
  );

  const defaultProvider = llmProviders.find((p) => p.is_default_provider);
  const defaultModelName = defaultProvider
    ? defaultProvider.model_configurations.find(
        (m) => m.name === defaultProvider.default_model_name
      )?.display_name || defaultProvider.default_model_name
    : "System Default";

  return (
    <div className="wfb-config-section">
      <div className="wfb-config-label">
        LLM Model
        {isLlmOverridden && (
          <OverrideBadge
            onReset={() =>
              onUpdate(nodeId, {
                llm_provider_override: null,
                llm_model_override: null,
              })
            }
          />
        )}
      </div>

      {/* Model selector */}
      <select
        className="wfb-agent-select"
        value={currentLlmValue}
        onChange={(e) => handleLlmChange(e.target.value)}
      >
        <option value="default">Default ({defaultModelName})</option>
        {llmOptions.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.group} — {opt.label}
          </option>
        ))}
      </select>

      {/* Max output tokens */}
      <div className="wfb-config-toggle-row" style={{ marginTop: 8 }}>
        <div>
          <div className="wfb-config-toggle-label">
            Max Output Tokens
            {isMaxTokensOverridden && (
              <OverrideBadge
                onReset={() =>
                  onUpdate(nodeId, { max_output_tokens_override: null })
                }
              />
            )}
          </div>
          <div className="wfb-config-toggle-desc">
            Limit response length (leave empty for default)
          </div>
        </div>
        <input
          type="number"
          className="wfb-config-input"
          style={{ width: 80, textAlign: "right" }}
          defaultValue={effectiveMaxTokens ?? ""}
          key={`max-tokens-${effectiveMaxTokens}`}
          onBlur={handleMaxTokensBlur}
          placeholder="Auto"
          min={1}
        />
      </div>

      {/* Replace base system prompt */}
      <div className="wfb-config-toggle-row">
        <div>
          <div className="wfb-config-toggle-label">
            Replace Base System Prompt
            {isReplaceOverridden && (
              <OverrideBadge
                onReset={() =>
                  onUpdate(nodeId, {
                    replace_base_system_prompt_override: null,
                  })
                }
              />
            )}
          </div>
          <div className="wfb-config-toggle-desc">
            Use agent&apos;s prompt as the only system prompt
          </div>
        </div>
        <ToggleSwitch
          checked={effectiveReplace}
          onChange={handleReplacePromptToggle}
        />
      </div>
    </div>
  );
}

// ── Tools Section ──────────────────────────────────────────────────────

function ToolsSection({
  nodeId,
  data,
  effectiveToolIds,
  availableTools,
  currentAgent,
  onUpdate,
}: {
  nodeId: string;
  data: AgentNodeData;
  effectiveToolIds: Set<number>;
  availableTools: ToolSnapshot[];
  currentAgent: MinimalAgentSnapshot | undefined;
  onUpdate: (nodeId: string, partial: Partial<AgentNodeData>) => void;
}) {
  const isToolsOverridden = data.tool_ids_override != null;

  // Split tools into built-in vs MCP/custom
  const { builtinTools, mcpTools, customTools } = useMemo(() => {
    const builtinIds = new Set(BUILTIN_TOOLS.map((b) => b.id));
    const builtin: (ToolSnapshot & { meta: (typeof BUILTIN_TOOLS)[0] })[] = [];
    const mcp: ToolSnapshot[] = [];
    const custom: ToolSnapshot[] = [];

    for (const tool of availableTools) {
      // SearchTool is handled in the Knowledge section
      if (tool.in_code_tool_id === SEARCH_TOOL_ID) continue;
      // Only show tools marked as selectable for agent creation
      if (!tool.agent_creation_selectable) continue;

      if (tool.in_code_tool_id && builtinIds.has(tool.in_code_tool_id)) {
        const meta = BUILTIN_TOOLS.find(
          (b) => b.id === tool.in_code_tool_id
        )!;
        builtin.push({ ...tool, meta });
      } else if (tool.mcp_server_id) {
        mcp.push(tool);
      } else {
        custom.push(tool);
      }
    }
    return { builtinTools: builtin, mcpTools: mcp, customTools: custom };
  }, [availableTools]);

  // Group MCP tools by server
  const mcpByServer = useMemo(() => {
    const groups: Record<number, ToolSnapshot[]> = {};
    for (const tool of mcpTools) {
      const sid = tool.mcp_server_id!;
      (groups[sid] || (groups[sid] = [])).push(tool);
    }
    return groups;
  }, [mcpTools]);

  const [mcpExpanded, setMcpExpanded] = useState<Set<number>>(new Set());

  const updateToolOverride = useCallback(
    (newIds: number[]) => {
      onUpdate(nodeId, { tool_ids_override: newIds });
    },
    [nodeId, onUpdate]
  );

  const handleToggle = useCallback(
    (toolId: number, enabled: boolean) => {
      const newIds = enabled
        ? [...Array.from(effectiveToolIds), toolId]
        : Array.from(effectiveToolIds).filter((id) => id !== toolId);
      updateToolOverride(newIds);
    },
    [effectiveToolIds, updateToolOverride]
  );

  const handleToggleMcpServer = useCallback(
    (serverId: number) => {
      const serverTools = mcpByServer[serverId] || [];
      const enabledCount = serverTools.filter((t) =>
        effectiveToolIds.has(t.id)
      ).length;
      const shouldEnable = enabledCount !== serverTools.length;
      const serverToolIdSet = new Set(serverTools.map((t) => t.id));
      let newIds = Array.from(effectiveToolIds).filter(
        (id) => !serverToolIdSet.has(id)
      );
      if (shouldEnable) {
        newIds = [...newIds, ...serverTools.map((t) => t.id)];
      }
      updateToolOverride(newIds);
    },
    [effectiveToolIds, mcpByServer, updateToolOverride]
  );

  return (
    <div className="wfb-config-section">
      <div className="wfb-config-label">
        Tools
        {isToolsOverridden && (
          <OverrideBadge
            onReset={() => onUpdate(nodeId, { tool_ids_override: null })}
          />
        )}
      </div>
      <div className="wfb-config-toggle-desc" style={{ marginBottom: 6 }}>
        Enable tools to give this agent superpowers beyond chatting.
      </div>

      {/* Built-in tools */}
      {builtinTools.map((tool) => (
        <div className="wfb-config-toggle-row" key={tool.id}>
          <div>
            <div className="wfb-config-toggle-label">
              {tool.meta.label}
            </div>
            <div className="wfb-config-toggle-desc">{tool.meta.desc}</div>
          </div>
          <ToggleSwitch
            checked={effectiveToolIds.has(tool.id)}
            onChange={(v) => handleToggle(tool.id, v)}
          />
        </div>
      ))}

      {/* Custom (OpenAPI) tools */}
      {customTools.length > 0 && (
        <>
          <div
            style={{
              fontSize: 11,
              fontWeight: 500,
              color: "var(--text-03, #9ca3af)",
              marginTop: 8,
              marginBottom: 4,
            }}
          >
            OpenAPI Actions
          </div>
          {customTools.map((tool) => (
            <div className="wfb-config-toggle-row" key={tool.id}>
              <div>
                <div className="wfb-config-toggle-label">
                  {tool.display_name || tool.name}
                </div>
                {tool.description && (
                  <div className="wfb-config-toggle-desc">
                    {tool.description.length > 60
                      ? tool.description.slice(0, 60) + "..."
                      : tool.description}
                  </div>
                )}
              </div>
              <ToggleSwitch
                checked={effectiveToolIds.has(tool.id)}
                onChange={(v) => handleToggle(tool.id, v)}
              />
            </div>
          ))}
        </>
      )}

      {/* MCP tools */}
      {Object.entries(mcpByServer).length > 0 && (
        <>
          <div
            style={{
              fontSize: 11,
              fontWeight: 500,
              color: "var(--text-03, #9ca3af)",
              marginTop: 8,
              marginBottom: 4,
            }}
          >
            MCP Actions
          </div>
          {Object.entries(mcpByServer).map(([serverIdStr, tools]) => {
            const serverId = Number(serverIdStr);
            const enabledCount = tools.filter((t) =>
              effectiveToolIds.has(t.id)
            ).length;
            const isExpanded = mcpExpanded.has(serverId);
            const firstName = tools[0]?.display_name || tools[0]?.name || "";
            const serverName =
              firstName.split(" - ")[0] ||
              firstName.split("_").slice(0, -1).join(" ") ||
              `MCP Server ${serverId}`;

            return (
              <div key={serverId} style={{ marginBottom: 4 }}>
                <div
                  className="wfb-config-toggle-row"
                  style={{ cursor: "pointer" }}
                >
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 4,
                      flex: 1,
                    }}
                    onClick={() =>
                      setMcpExpanded((prev) => {
                        const next = new Set(prev);
                        if (next.has(serverId)) next.delete(serverId);
                        else next.add(serverId);
                        return next;
                      })
                    }
                  >
                    <svg
                      width="10"
                      height="10"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      style={{
                        transform: isExpanded
                          ? "rotate(90deg)"
                          : "rotate(0deg)",
                        transition: "transform 0.15s",
                      }}
                    >
                      <path d="M9 18l6-6-6-6" />
                    </svg>
                    <div className="wfb-config-toggle-label">
                      {serverName}
                    </div>
                    <span
                      style={{
                        fontSize: 10,
                        color: "var(--text-03, #9ca3af)",
                      }}
                    >
                      {enabledCount}/{tools.length}
                    </span>
                  </div>
                  <ToggleSwitch
                    checked={enabledCount === tools.length}
                    onChange={() => handleToggleMcpServer(serverId)}
                  />
                </div>
                {isExpanded &&
                  tools.map((tool) => (
                    <div
                      className="wfb-config-toggle-row"
                      key={tool.id}
                      style={{ paddingLeft: 20 }}
                    >
                      <div>
                        <div
                          className="wfb-config-toggle-label"
                          style={{ fontSize: 12 }}
                        >
                          {tool.display_name || tool.name}
                        </div>
                        {tool.description && (
                          <div className="wfb-config-toggle-desc">
                            {tool.description.length > 50
                              ? tool.description.slice(0, 50) + "..."
                              : tool.description}
                          </div>
                        )}
                      </div>
                      <ToggleSwitch
                        checked={effectiveToolIds.has(tool.id)}
                        onChange={(v) => handleToggle(tool.id, v)}
                      />
                    </div>
                  ))}
              </div>
            );
          })}
        </>
      )}

      {availableTools.length === 0 && (
        <div
          style={{
            fontSize: 12,
            color: "var(--text-03, #9ca3af)",
            padding: "4px 0",
          }}
        >
          No tools available
        </div>
      )}
    </div>
  );
}

// ── Knowledge Section ──────────────────────────────────────────────────

function KnowledgeSection({
  nodeId,
  data,
  effectiveToolIds,
  effectiveDocSetIds,
  availableTools,
  documentSets,
  currentAgent,
  onUpdate,
}: {
  nodeId: string;
  data: AgentNodeData;
  effectiveToolIds: Set<number>;
  effectiveDocSetIds: Set<number>;
  availableTools: ToolSnapshot[];
  documentSets: DocumentSetSummary[];
  currentAgent: MinimalAgentSnapshot | undefined;
  onUpdate: (nodeId: string, partial: Partial<AgentNodeData>) => void;
}) {
  const isDocSetsOverridden = data.document_set_ids_override != null;

  // Find the SearchTool from available tools
  const searchTool = availableTools.find(
    (t) => t.in_code_tool_id === SEARCH_TOOL_ID
  );
  const isKnowledgeEnabled = searchTool
    ? effectiveToolIds.has(searchTool.id)
    : false;

  const handleKnowledgeToggle = useCallback(
    (enabled: boolean) => {
      if (!searchTool) return;
      const newIds = enabled
        ? [...Array.from(effectiveToolIds), searchTool.id]
        : Array.from(effectiveToolIds).filter((id) => id !== searchTool.id);
      onUpdate(nodeId, { tool_ids_override: newIds });
    },
    [nodeId, searchTool, effectiveToolIds, onUpdate]
  );

  const handleDocSetToggle = useCallback(
    (docSetId: number, enabled: boolean) => {
      const newIds = enabled
        ? [...Array.from(effectiveDocSetIds), docSetId]
        : Array.from(effectiveDocSetIds).filter((id) => id !== docSetId);
      onUpdate(nodeId, { document_set_ids_override: newIds });
    },
    [nodeId, effectiveDocSetIds, onUpdate]
  );

  return (
    <div className="wfb-config-section">
      <div className="wfb-config-label">
        Knowledge
        {isDocSetsOverridden && (
          <OverrideBadge
            onReset={() =>
              onUpdate(nodeId, { document_set_ids_override: null })
            }
          />
        )}
      </div>
      <div className="wfb-config-toggle-desc" style={{ marginBottom: 6 }}>
        Connect knowledge sources so the agent can reference your
        company&apos;s documents when answering.
      </div>

      {/* Use Knowledge master toggle (controls SearchTool) */}
      {searchTool && (
        <div className="wfb-config-toggle-row">
          <div>
            <div className="wfb-config-toggle-label">Use Knowledge</div>
            <div className="wfb-config-toggle-desc">
              Let this agent reference these documents to inform its
              responses.
            </div>
          </div>
          <ToggleSwitch
            checked={isKnowledgeEnabled}
            onChange={handleKnowledgeToggle}
          />
        </div>
      )}

      {/* Document sets (only shown when knowledge is enabled) */}
      {isKnowledgeEnabled && (
        <>
          <div
            className="wfb-config-toggle-desc"
            style={{ marginTop: 6, marginBottom: 4 }}
          >
            Add documents or connected sources to use for this agent.
          </div>
          {documentSets.length > 0 ? (
            documentSets.map((ds) => (
              <div
                className="wfb-config-toggle-row"
                key={ds.id}
                style={{ paddingLeft: 8 }}
              >
                <div>
                  <div className="wfb-config-toggle-label">{ds.name}</div>
                  {ds.description && (
                    <div className="wfb-config-toggle-desc">
                      {ds.description.length > 50
                        ? ds.description.slice(0, 50) + "..."
                        : ds.description}
                    </div>
                  )}
                </div>
                <ToggleSwitch
                  checked={effectiveDocSetIds.has(ds.id)}
                  onChange={(v) => handleDocSetToggle(ds.id, v)}
                />
              </div>
            ))
          ) : (
            <div
              style={{
                fontSize: 12,
                color: "var(--text-03, #9ca3af)",
                padding: "4px 0",
              }}
            >
              No document sets available
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ── Advanced collapsible section ──────────────────────────────────────

function AdvancedSection({
  nodeId,
  data,
  onUpdate,
}: {
  nodeId: string;
  data: AgentNodeData;
  onUpdate: (nodeId: string, partial: Partial<AgentNodeData>) => void;
}) {
  const [open, setOpen] = useState(false);
  const [inputMappingStr, setInputMappingStr] = useState(() =>
    data.input_mapping ? JSON.stringify(data.input_mapping, null, 2) : ""
  );
  const [conditionStr, setConditionStr] = useState(() =>
    data.condition ? JSON.stringify(data.condition, null, 2) : ""
  );
  const [inputMappingError, setInputMappingError] = useState<string | null>(
    null
  );
  const [conditionError, setConditionError] = useState<string | null>(null);

  const handleInputMappingBlur = () => {
    if (!inputMappingStr.trim()) {
      onUpdate(nodeId, { input_mapping: null });
      setInputMappingError(null);
      return;
    }
    try {
      const parsed = JSON.parse(inputMappingStr);
      onUpdate(nodeId, { input_mapping: parsed });
      setInputMappingError(null);
    } catch {
      setInputMappingError("Invalid JSON");
    }
  };

  const handleConditionBlur = () => {
    if (!conditionStr.trim()) {
      onUpdate(nodeId, { condition: null });
      setConditionError(null);
      return;
    }
    try {
      const parsed = JSON.parse(conditionStr);
      onUpdate(nodeId, { condition: parsed });
      setConditionError(null);
    } catch {
      setConditionError("Invalid JSON");
    }
  };

  return (
    <div className="wfb-config-section">
      <button
        className="wfb-config-label"
        onClick={() => setOpen(!open)}
        style={{
          background: "none",
          border: "none",
          cursor: "pointer",
          display: "flex",
          alignItems: "center",
          gap: 6,
          width: "100%",
          padding: 0,
          color: "inherit",
          font: "inherit",
        }}
      >
        <svg
          width="10"
          height="10"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          style={{
            transform: open ? "rotate(90deg)" : "rotate(0deg)",
            transition: "transform 0.15s",
          }}
        >
          <path d="M9 18l6-6-6-6" />
        </svg>
        Advanced
      </button>
      {open && (
        <div style={{ marginTop: 8 }}>
          <div style={{ marginBottom: 8 }}>
            <div className="wfb-config-toggle-label">Input Mapping (JSON)</div>
            <textarea
              className="wfb-config-textarea"
              value={inputMappingStr}
              onChange={(e) => setInputMappingStr(e.target.value)}
              onBlur={handleInputMappingBlur}
              placeholder='{"context": "$step_1.output"}'
              rows={3}
              style={{ fontFamily: "monospace", fontSize: 11 }}
            />
            {inputMappingError && (
              <div style={{ fontSize: 11, color: "#ef4444", marginTop: 2 }}>
                {inputMappingError}
              </div>
            )}
          </div>

          <div>
            <div className="wfb-config-toggle-label">Condition (JSON)</div>
            <textarea
              className="wfb-config-textarea"
              value={conditionStr}
              onChange={(e) => setConditionStr(e.target.value)}
              onBlur={handleConditionBlur}
              placeholder='{"field": "$step_1.output", "contains": "technical"}'
              rows={3}
              style={{ fontFamily: "monospace", fontSize: 11 }}
            />
            {conditionError && (
              <div style={{ fontSize: 11, color: "#ef4444", marginTop: 2 }}>
                {conditionError}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ── HTTP Request Config ─────────────────────────────────────────────────

interface HttpConfig {
  method: string;
  url: string;
  headers: { key: string; value: string }[];
  body: string;
}

function parseHttpConfig(taskPrompt: string | null | undefined): HttpConfig {
  const config: HttpConfig = {
    method: "GET",
    url: "",
    headers: [],
    body: "",
  };
  if (!taskPrompt) return config;

  const methodMatch = taskPrompt.match(/Method:\s*(\w+)/);
  if (methodMatch?.[1]) config.method = methodMatch[1].toUpperCase();

  const urlMatch = taskPrompt.match(/URL:\s*(.+)/);
  if (urlMatch?.[1]) config.url = urlMatch[1].trim();

  // Parse headers block
  const headersMatch = taskPrompt.match(
    /Headers:\n((?:\s{2}\S+:.*\n?)*)/
  );
  if (headersMatch?.[1]) {
    const lines = headersMatch[1].trim().split("\n");
    for (const line of lines) {
      const colonIdx = line.indexOf(":");
      if (colonIdx > 0) {
        config.headers.push({
          key: line.slice(0, colonIdx).trim(),
          value: line.slice(colonIdx + 1).trim(),
        });
      }
    }
  }

  const bodyMatch = taskPrompt.match(/Body:\n([\s\S]*?)\n\nReturn/);
  if (bodyMatch?.[1]) config.body = bodyMatch[1].trim();

  return config;
}

function buildHttpTaskPrompt(config: HttpConfig): string {
  let prompt = `Call the following HTTP endpoint and return the full response:\n\nMethod: ${config.method}\nURL: ${config.url}`;
  if (config.headers.length > 0) {
    prompt += "\nHeaders:";
    for (const h of config.headers) {
      if (h.key.trim()) prompt += `\n  ${h.key}: ${h.value}`;
    }
  }
  if (config.body.trim() && ["POST", "PUT", "PATCH"].includes(config.method)) {
    prompt += `\nBody:\n${config.body}`;
  }
  prompt += "\n\nReturn the response body exactly as received.";
  return prompt;
}

function HttpRequestConfigSection({
  nodeId,
  data,
  onUpdate,
}: {
  nodeId: string;
  data: AgentNodeData;
  onUpdate: (nodeId: string, partial: Partial<AgentNodeData>) => void;
}) {
  const [config, setConfig] = useState<HttpConfig>(() =>
    parseHttpConfig(data.task_prompt_override)
  );

  const updateConfig = (partial: Partial<HttpConfig>) => {
    const updated = { ...config, ...partial };
    setConfig(updated);
    onUpdate(nodeId, { task_prompt_override: buildHttpTaskPrompt(updated) });
  };

  return (
    <div className="wfb-config-section">
      <div className="wfb-config-label">HTTP Request</div>

      {/* Method */}
      <div style={{ marginBottom: 8 }}>
        <div className="wfb-config-toggle-label">Method</div>
        <select
          className="wfb-agent-select"
          value={config.method}
          onChange={(e) => updateConfig({ method: e.target.value })}
        >
          {["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD"].map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>
      </div>

      {/* URL */}
      <div style={{ marginBottom: 8 }}>
        <div className="wfb-config-toggle-label">URL</div>
        <input
          className="wfb-config-input"
          type="text"
          value={config.url}
          onChange={(e) => updateConfig({ url: e.target.value })}
          placeholder="https://api.example.com/data"
        />
        <div className="wfb-config-toggle-desc">
          Use $step_name.output to reference previous step outputs
        </div>
      </div>

      {/* Headers */}
      <div style={{ marginBottom: 8 }}>
        <div
          className="wfb-config-toggle-label"
          style={{ display: "flex", alignItems: "center", gap: 6 }}
        >
          Headers
          <button
            type="button"
            onClick={() =>
              updateConfig({
                headers: [...config.headers, { key: "", value: "" }],
              })
            }
            style={{
              background: "none",
              border: "1px solid var(--border-01)",
              borderRadius: 4,
              padding: "1px 6px",
              fontSize: 11,
              cursor: "pointer",
              color: "var(--text-02)",
            }}
          >
            + Add
          </button>
        </div>
        {config.headers.map((h, i) => (
          <div
            key={i}
            style={{
              display: "flex",
              gap: 4,
              marginBottom: 4,
              alignItems: "center",
            }}
          >
            <input
              className="wfb-config-input"
              type="text"
              value={h.key}
              onChange={(e) => {
                const headers = [...config.headers];
                headers[i] = { key: e.target.value, value: headers[i]?.value ?? "" };
                updateConfig({ headers });
              }}
              placeholder="Header name"
              style={{ flex: 1 }}
            />
            <input
              className="wfb-config-input"
              type="text"
              value={h.value}
              onChange={(e) => {
                const headers = [...config.headers];
                headers[i] = { key: headers[i]?.key ?? "", value: e.target.value };
                updateConfig({ headers });
              }}
              placeholder="Value"
              style={{ flex: 2 }}
            />
            <button
              type="button"
              onClick={() => {
                const headers = config.headers.filter((_, j) => j !== i);
                updateConfig({ headers });
              }}
              style={{
                background: "none",
                border: "none",
                cursor: "pointer",
                color: "var(--text-03)",
                fontSize: 14,
                padding: 2,
              }}
            >
              ×
            </button>
          </div>
        ))}
      </div>

      {/* Body */}
      {["POST", "PUT", "PATCH"].includes(config.method) && (
        <div style={{ marginBottom: 8 }}>
          <div className="wfb-config-toggle-label">Body</div>
          <textarea
            className="wfb-config-textarea"
            value={config.body}
            onChange={(e) => updateConfig({ body: e.target.value })}
            placeholder='{"key": "value"}'
            rows={4}
            style={{ fontFamily: "monospace", fontSize: 11 }}
          />
        </div>
      )}
    </div>
  );
}

// ── Code Executor Config ──────────────────────────────────────────────

function buildCodeTaskPrompt(code: string): string {
  return `Execute the following Python code using the run_python tool. Do not modify the code.\n\n\`\`\`python\n${code}\n\`\`\`\n\nReturn only the printed output.`;
}

function parseCodeFromTaskPrompt(
  taskPrompt: string | null | undefined
): string {
  if (!taskPrompt) return "";
  const match = taskPrompt.match(/```python\n([\s\S]*?)\n```/);
  return match?.[1] ?? "";
}

function CodeExecutorConfigSection({
  nodeId,
  data,
  onUpdate,
}: {
  nodeId: string;
  data: AgentNodeData;
  onUpdate: (nodeId: string, partial: Partial<AgentNodeData>) => void;
}) {
  const [code, setCode] = useState(() =>
    parseCodeFromTaskPrompt(data.task_prompt_override)
  );

  const handleChange = (newCode: string) => {
    setCode(newCode);
    onUpdate(nodeId, { task_prompt_override: buildCodeTaskPrompt(newCode) });
  };

  return (
    <div className="wfb-config-section">
      <div className="wfb-config-label">Python Code</div>
      <div className="wfb-config-toggle-desc" style={{ marginBottom: 6 }}>
        Write the Python code to execute. Use $step_name.output in string
        literals to reference previous step outputs. Output is captured from
        stdout (print statements).
      </div>
      <textarea
        className="wfb-config-textarea"
        value={code}
        onChange={(e) => handleChange(e.target.value)}
        placeholder={`import json\ndata = json.loads("""$api_response.output""")\nresult = data['items'][0]['name']\nprint(result)`}
        rows={10}
        style={{
          fontFamily: "monospace",
          fontSize: 12,
          lineHeight: 1.5,
          background: "var(--background-tint-02, #f3f4f6)",
          borderRadius: 8,
          tabSize: 4,
        }}
      />
    </div>
  );
}

// ── Toggle Switch ─────────────────────────────────────────────────────

function ToggleSwitch({
  checked,
  onChange,
  disabled,
}: {
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => !disabled && onChange(!checked)}
      style={{
        position: "relative",
        width: 36,
        height: 20,
        borderRadius: 10,
        border: "none",
        cursor: disabled ? "not-allowed" : "pointer",
        opacity: disabled ? 0.5 : 1,
        background: checked
          ? "var(--virtualai-accent, var(--theme-primary-05))"
          : "var(--border-02, #d1d5db)",
        transition: "background 0.2s",
        flexShrink: 0,
      }}
    >
      <div
        style={{
          position: "absolute",
          width: 16,
          height: 16,
          borderRadius: "50%",
          background: "white",
          top: 2,
          left: checked ? 18 : 2,
          transition: "left 0.2s",
          boxShadow: "0 1px 3px rgba(0,0,0,0.2)",
        }}
      />
    </button>
  );
}


// ── Condition Config Panel ──────────────────────────────────────────

function ConditionConfigPanel({
  nodeId,
  data,
  onUpdate,
  onDelete,
  onClose,
  onToggleCollapse,
}: {
  nodeId: string;
  data: ConditionalRouterNodeData;
  onUpdate: (nodeId: string, partial: Partial<ConditionalRouterNodeData>) => void;
  onDelete: (nodeId: string) => void;
  onClose: () => void;
  onToggleCollapse?: () => void;
}) {
  const needsMatchValue = !["is_empty", "is_not_empty"].includes(data.operator);

  return (
    <div className="wfb-config-panel">
      {/* Header */}
      <div className="wfb-config-header">
        <div className="wfb-config-title">Configure Condition</div>
        <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
          {onToggleCollapse && (
            <button className="wfb-config-close" onClick={onToggleCollapse} title="Collapse panel">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="9 18 15 12 15 6" />
              </svg>
            </button>
          )}
          <button className="wfb-config-close" onClick={onClose} title="Close">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M18 6L6 18M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

      <div className="wfb-config-body">
        {/* Step Name */}
        <div className="wfb-config-section">
          <div className="wfb-config-label">Step Name</div>
          <input
            className="wfb-config-input"
            value={data.step_name}
            onChange={(e) => onUpdate(nodeId, { step_name: e.target.value })}
            placeholder="e.g., Check for errors"
          />
        </div>

        {/* Output Key */}
        <div className="wfb-config-section">
          <div className="wfb-config-label">Output Key</div>
          <input
            className="wfb-config-input"
            value={data.output_key}
            onChange={(e) => onUpdate(nodeId, { output_key: e.target.value })}
            placeholder="e.g., condition_result"
          />
          <div className="wfb-config-hint">
            Stores &quot;true&quot; or &quot;false&quot; in workflow context
          </div>
        </div>

        {/* Condition Field */}
        <div className="wfb-config-section">
          <div className="wfb-config-label">Condition Field</div>
          <input
            className="wfb-config-input"
            value={data.condition_field}
            onChange={(e) => onUpdate(nodeId, { condition_field: e.target.value })}
            placeholder="e.g., $research.output"
          />
          <div className="wfb-config-hint">
            Reference a previous step&apos;s output using $step_name.output
          </div>
        </div>

        {/* Operator */}
        <div className="wfb-config-section">
          <div className="wfb-config-label">Operator</div>
          <select
            className="wfb-config-input"
            value={data.operator}
            onChange={(e) => onUpdate(nodeId, { operator: e.target.value })}
          >
            {CONDITION_OPERATORS.map((op) => (
              <option key={op.value} value={op.value}>
                {op.label}
              </option>
            ))}
          </select>
        </div>

        {/* Match Value */}
        {needsMatchValue && (
          <div className="wfb-config-section">
            <div className="wfb-config-label">Match Value</div>
            <input
              className="wfb-config-input"
              value={data.match_value}
              onChange={(e) => onUpdate(nodeId, { match_value: e.target.value })}
              placeholder="e.g., error"
            />
          </div>
        )}

        {/* Case Sensitive */}
        <div className="wfb-config-section">
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <input
              type="checkbox"
              checked={data.case_sensitive}
              onChange={(e) => onUpdate(nodeId, { case_sensitive: e.target.checked })}
            />
            <span className="wfb-config-label" style={{ margin: 0 }}>Case sensitive</span>
          </div>
        </div>

        {/* Description */}
        <div className="wfb-config-section">
          <div className="wfb-config-label">Description (optional)</div>
          <textarea
            className="wfb-config-textarea"
            value={data.step_description}
            onChange={(e) => onUpdate(nodeId, { step_description: e.target.value })}
            placeholder="Describe what this condition checks..."
            rows={2}
          />
        </div>

        {/* Info about branch connections */}
        <div className="wfb-config-section">
          <div className="wfb-config-hint" style={{ padding: "8px 10px", background: "var(--bg-02, #f3f4f6)", borderRadius: 6 }}>
            Connect the <strong style={{ color: "#22c55e" }}>True</strong> and{" "}
            <strong style={{ color: "#ef4444" }}>False</strong> handles on the right
            side of the node to the agents that should run for each branch.
          </div>
        </div>

        {/* Delete */}
        <div className="wfb-config-section" style={{ marginTop: 16 }}>
          <button
            className="wfb-config-danger-btn"
            onClick={() => onDelete(nodeId)}
          >
            Remove Condition
          </button>
        </div>
      </div>
    </div>
  );
}
