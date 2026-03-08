"use client";

import React, { useState, useCallback, useMemo } from "react";
import type { MinimalPersonaSnapshot } from "@/app/admin/assistants/interfaces";
import type { ToolSnapshot } from "@/lib/tools/interfaces";
import type { DocumentSetSummary } from "@/lib/types";
import type { LLMProviderDescriptor } from "@/app/admin/configuration/llm/interfaces";
import type { AgentNodeData } from "./types";
import {
  SEARCH_TOOL_ID,
  WEB_SEARCH_TOOL_ID,
  IMAGE_GENERATION_TOOL_ID,
  PYTHON_TOOL_ID,
  OPEN_URL_TOOL_ID,
  FILE_READER_TOOL_ID,
} from "@/app/app/components/tools/constants";
import { structureValue, parseLlmDescriptor } from "@/lib/llm/utils";

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
];

interface NodeConfigPanelProps {
  nodeId: string;
  data: AgentNodeData;
  agents: MinimalPersonaSnapshot[];
  availableTools: ToolSnapshot[];
  documentSets: DocumentSetSummary[];
  llmProviders: LLMProviderDescriptor[];
  onUpdate: (nodeId: string, partial: Partial<AgentNodeData>) => void;
  onDelete: (nodeId: string) => void;
  onClose: () => void;
}

export function NodeConfigPanel({
  nodeId,
  data,
  agents,
  availableTools,
  documentSets,
  llmProviders,
  onUpdate,
  onDelete,
  onClose,
}: NodeConfigPanelProps) {
  // Current persona from agents list (has tools and document_sets)
  const currentPersona = agents.find((a) => a.id === data.persona_id);

  // Effective tool IDs: step override > persona tools
  const effectiveToolIds = useMemo(() => {
    if (data.tool_ids_override != null) {
      return new Set(data.tool_ids_override);
    }
    return new Set((currentPersona?.tools || []).map((t) => t.id));
  }, [data.tool_ids_override, currentPersona?.tools]);

  // Effective document set IDs: step override > persona doc sets
  const effectiveDocSetIds = useMemo(() => {
    if (data.document_set_ids_override != null) {
      return new Set(data.document_set_ids_override);
    }
    return new Set(
      (currentPersona?.document_sets || []).map((d) => d.id)
    );
  }, [data.document_set_ids_override, currentPersona?.document_sets]);

  return (
    <div className="wfb-config-panel">
      {/* Header */}
      <div className="wfb-config-header">
        <div className="wfb-config-title">Configure Step</div>
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

      {/* Body */}
      <div className="wfb-config-body">
        {/* Agent selection */}
        <div className="wfb-config-section">
          <div className="wfb-config-label">Agent</div>
          <select
            className="wfb-agent-select"
            value={data.persona_id}
            onChange={(e) => {
              const id = Number(e.target.value);
              const agent = agents.find((a) => a.id === id);
              if (agent) {
                onUpdate(nodeId, {
                  persona_id: agent.id,
                  persona_name: agent.name,
                  persona_description: agent.description || "",
                  persona_icon_url: agent.uploaded_image_id
                    ? `/api/persona/${agent.id}/uploaded_image`
                    : null,
                  persona_num_tools: agent.tools?.length || 0,
                  persona_tool_names: (agent.tools || []).map((t) => t.name),
                  persona_llm_model:
                    agent.llm_model_version_override || null,
                  persona_llm_provider:
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

        {/* ── LLM Section ──────────────────────────────────── */}
        <LlmSection
          nodeId={nodeId}
          data={data}
          currentPersona={currentPersona}
          llmProviders={llmProviders}
          onUpdate={onUpdate}
        />

        {/* ── Tools Section ──────────────────────────────────── */}
        <ToolsSection
          nodeId={nodeId}
          data={data}
          effectiveToolIds={effectiveToolIds}
          availableTools={availableTools}
          currentPersona={currentPersona}
          onUpdate={onUpdate}
        />

        {/* ── Knowledge Section ──────────────────────────────── */}
        <KnowledgeSection
          nodeId={nodeId}
          data={data}
          effectiveToolIds={effectiveToolIds}
          effectiveDocSetIds={effectiveDocSetIds}
          availableTools={availableTools}
          documentSets={documentSets}
          currentPersona={currentPersona}
          onUpdate={onUpdate}
        />

        {/* Advanced: input_mapping & condition */}
        <AdvancedSection nodeId={nodeId} data={data} onUpdate={onUpdate} />

        {/* Agent info (read-only) */}
        {data.persona_description && (
          <div className="wfb-config-section">
            <div className="wfb-config-label">Agent Description</div>
            <div
              style={{
                fontSize: 12,
                color: "var(--text-03, #9ca3af)",
                lineHeight: 1.5,
              }}
            >
              {data.persona_description}
            </div>
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
  currentPersona,
  llmProviders,
  onUpdate,
}: {
  nodeId: string;
  data: AgentNodeData;
  currentPersona: MinimalPersonaSnapshot | undefined;
  llmProviders: LLMProviderDescriptor[];
  onUpdate: (nodeId: string, partial: Partial<AgentNodeData>) => void;
}) {
  // Effective LLM: step override > persona value > default
  const effectiveProvider =
    data.llm_provider_override ?? currentPersona?.llm_model_provider_override ?? null;
  const effectiveModel =
    data.llm_model_override ?? currentPersona?.llm_model_version_override ?? null;
  const isLlmOverridden = data.llm_provider_override != null || data.llm_model_override != null;

  // Effective max_output_tokens: step override > persona > null
  const effectiveMaxTokens =
    data.max_output_tokens_override ?? currentPersona?.max_output_tokens ?? null;
  const isMaxTokensOverridden = data.max_output_tokens_override != null;

  // Effective replace_base_system_prompt
  const effectiveReplace =
    data.replace_base_system_prompt_override ?? currentPersona?.replace_base_system_prompt ?? false;
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
        // Reset to persona default
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
  currentPersona,
  onUpdate,
}: {
  nodeId: string;
  data: AgentNodeData;
  effectiveToolIds: Set<number>;
  availableTools: ToolSnapshot[];
  currentPersona: MinimalPersonaSnapshot | undefined;
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
  currentPersona,
  onUpdate,
}: {
  nodeId: string;
  data: AgentNodeData;
  effectiveToolIds: Set<number>;
  effectiveDocSetIds: Set<number>;
  availableTools: ToolSnapshot[];
  documentSets: DocumentSetSummary[];
  currentPersona: MinimalPersonaSnapshot | undefined;
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
