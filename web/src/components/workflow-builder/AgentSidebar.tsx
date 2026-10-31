"use client";

import React, { useState, useMemo, useCallback, type DragEvent } from "react";
import type { MinimalAgentSnapshot } from "@/app/admin/assistants/interfaces";
import type { LLMProviderDescriptor } from "@/app/admin/configuration/llm/interfaces";
import type { DragAgentData, WorkflowMeta } from "./types";
import { AGENT_DRAG_MIME, NODE_TYPE_DRAG_MIME } from "./types";
import AgentAvatar from "@/refresh-components/avatars/AgentAvatar";
import LLMSelector from "@/components/llm/LLMSelector";
import { parseLlmDescriptor, structureValue } from "@/lib/llm/utils";
import {
  type NodeCatalog,
  editorKindFor,
  latestVersion,
  paletteTypes,
} from "@/lib/workflows/nodeRegistry";
import { nodeKindUi } from "./nodeUi";
import { selectableStepAgents } from "@/lib/workflows/stepAgents";
import { OrchestratorLimitFields } from "./OrchestratorLimitFields";
import {
  MAX_TIMEOUT_SECONDS,
  MIN_TIMEOUT_SECONDS,
} from "@/lib/workflows/workflowLimits";

// Names of utility agents that get their own section
const UTILITY_AGENT_NAMES = new Set(["HTTP Request", "Code Executor"]);

type SidebarTab = "agents" | "utilities" | "settings";

interface AgentSidebarProps {
  agents: MinimalAgentSnapshot[];
  isLoading: boolean;
  onCreateNew?: () => void;
  /** Workflow-level settings (for Settings tab) */
  meta?: WorkflowMeta;
  onUpdateMeta?: (partial: Partial<WorkflowMeta>) => void;
  llmProviders?: LLMProviderDescriptor[];
  /** Collapse state */
  collapsed?: boolean;
  onToggleCollapse?: () => void;
  /** Node type catalog; the Utils palette lists its types for the mode. */
  catalog: NodeCatalog;
  catalogLoading?: boolean;
}

/** Utils palette: every catalog node type usable in the current mode. */
function NodeTypePalette({
  catalog,
  mode,
  loading,
}: {
  catalog: NodeCatalog;
  mode: WorkflowMeta["orchestration_mode"];
  loading: boolean;
}) {
  const types = paletteTypes(catalog, mode).filter(
    (t) => nodeKindUi(editorKindFor(catalog, t.type)).inUtilsPalette
  );

  if (loading) {
    return <div className="wfb-sidebar-empty">Loading node types...</div>;
  }
  if (types.length === 0) {
    return (
      <div className="wfb-sidebar-empty">
        {mode === "llm_decision"
          ? "No extra node types are available in LLM Decision mode. Switch to Sequential to use conditions and other nodes."
          : "No node types available."}
      </div>
    );
  }

  return (
    <>
      {types.map((t) => {
        const ui = nodeKindUi(editorKindFor(catalog, t.type));
        const info = latestVersion(catalog, t.type);
        const label = info?.label ?? t.type;
        return (
          <div
            key={t.type}
            className={`wfb-sidebar-card wfb-sidebar-card--${ui.paletteVariant}`}
            draggable
            onDragStart={(e) => {
              e.dataTransfer.setData(NODE_TYPE_DRAG_MIME, t.type);
              e.dataTransfer.effectAllowed = "move";
            }}
            title={`Drag to add a ${label} step`}
          >
            <div
              className={`wfb-sidebar-card-avatar wfb-sidebar-card-avatar--${ui.paletteVariant}`}
            >
              <ui.PaletteIcon />
            </div>
            <div className="wfb-sidebar-card-info">
              <div className="wfb-sidebar-card-name">{label}</div>
              <div className="wfb-sidebar-card-desc">{info?.description}</div>
            </div>
          </div>
        );
      })}
    </>
  );
}

export function AgentSidebar({
  agents,
  isLoading,
  onCreateNew,
  meta,
  onUpdateMeta,
  llmProviders,
  collapsed,
  onToggleCollapse,
  catalog,
  catalogLoading = false,
}: AgentSidebarProps) {
  const [activeTab, setActiveTab] = useState<SidebarTab>("agents");
  const [search, setSearch] = useState("");

  // Split agents into utility vs regular, filter out workflow wrappers
  const { utilityAgents, regularAgents } = useMemo(() => {
    const nonWorkflow = selectableStepAgents(agents);
    const q = search.trim().toLowerCase();
    const matchesSearch = (a: MinimalAgentSnapshot) =>
      !q ||
      a.name.toLowerCase().includes(q) ||
      a.description?.toLowerCase().includes(q);

    return {
      utilityAgents: nonWorkflow.filter(
        (a) => UTILITY_AGENT_NAMES.has(a.name) && matchesSearch(a)
      ),
      regularAgents: nonWorkflow.filter(
        (a) => !UTILITY_AGENT_NAMES.has(a.name) && matchesSearch(a)
      ),
    };
  }, [agents, search]);

  const handleDragStart = (
    event: DragEvent<HTMLDivElement>,
    agent: MinimalAgentSnapshot
  ) => {
    const data: DragAgentData = {
      agent_id: agent.id,
      agent_name: agent.name,
      agent_description: agent.description || "",
      agent_icon_url: agent.uploaded_image_id
        ? `/api/agent/${agent.id}/uploaded_image`
        : null,
      agent_num_tools: agent.tools?.length || 0,
      agent_tool_names: (agent.tools || []).map((t) => t.name),
      agent_llm_model: agent.llm_model_version_override || null,
      agent_llm_provider: agent.llm_model_provider_override || null,
    };
    event.dataTransfer.setData(AGENT_DRAG_MIME, JSON.stringify(data));
    event.dataTransfer.effectAllowed = "move";
  };

  const renderAgentCard = (agent: MinimalAgentSnapshot) => (
    <div
      key={agent.id}
      className="wfb-sidebar-card"
      draggable
      onDragStart={(e) => handleDragStart(e, agent)}
      title={`Drag "${agent.name}" onto the canvas`}
    >
      <div className="wfb-sidebar-card-avatar">
        <AgentAvatar agent={agent} size={28} />
      </div>
      <div className="wfb-sidebar-card-info">
        <div className="wfb-sidebar-card-name">{agent.name}</div>
        <div className="wfb-sidebar-card-desc">
          {agent.description
            ? agent.description.length > 50
              ? agent.description.slice(0, 50) + "..."
              : agent.description
            : "No description"}
        </div>
      </div>
    </div>
  );

  // Collapsed state: render thin strip
  if (collapsed) {
    return (
      <div className="wfb-sidebar wfb-sidebar--collapsed">
        <button
          className="wfb-sidebar-collapse-btn"
          onClick={onToggleCollapse}
          title="Expand sidebar"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="9 18 15 12 9 6" />
          </svg>
        </button>
      </div>
    );
  }

  return (
    <div className="wfb-sidebar">
      {/* Tab bar */}
      <div className="wfb-sidebar-tabs">
        <button
          className={`wfb-sidebar-tab ${activeTab === "agents" ? "wfb-sidebar-tab--active" : ""}`}
          onClick={() => setActiveTab("agents")}
        >
          Agents
        </button>
        <button
          className={`wfb-sidebar-tab ${activeTab === "utilities" ? "wfb-sidebar-tab--active" : ""}`}
          onClick={() => setActiveTab("utilities")}
        >
          Utils
        </button>
        <button
          className={`wfb-sidebar-tab ${activeTab === "settings" ? "wfb-sidebar-tab--active" : ""}`}
          onClick={() => setActiveTab("settings")}
        >
          Config
        </button>
        {onToggleCollapse && (
          <button
            className="wfb-sidebar-collapse-btn wfb-sidebar-collapse-btn--inline"
            onClick={onToggleCollapse}
            title="Collapse sidebar"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="15 18 9 12 15 6" />
            </svg>
          </button>
        )}
      </div>

      {/* Tab content */}
      {activeTab === "agents" && (
        <>
          <div className="wfb-sidebar-header">
            <input
              className="wfb-sidebar-search"
              type="text"
              placeholder="Search agents..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <div className="wfb-sidebar-list">
            {onCreateNew && (
              <button
                className="wfb-sidebar-create-btn"
                onClick={onCreateNew}
                title="Create a new agent"
              >
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <line x1="12" y1="5" x2="12" y2="19" />
                  <line x1="5" y1="12" x2="19" y2="12" />
                </svg>
                New Agent
              </button>
            )}
            {isLoading ? (
              <div className="wfb-sidebar-empty">Loading agents...</div>
            ) : regularAgents.length === 0 ? (
              <div className="wfb-sidebar-empty">
                {search ? "No matching agents" : "No agents available"}
              </div>
            ) : (
              regularAgents.map(renderAgentCard)
            )}
          </div>
        </>
      )}

      {activeTab === "utilities" && (
        <div className="wfb-sidebar-list">
          <div className="wfb-sidebar-section-title">Drag to canvas</div>
          <NodeTypePalette
            catalog={catalog}
            mode={meta?.orchestration_mode ?? "llm_decision"}
            loading={catalogLoading}
          />
          {/* Utility agents (HTTP Request, Code Executor) */}
          {utilityAgents.map(renderAgentCard)}
          {utilityAgents.length === 0 && !isLoading && (
            <div className="wfb-sidebar-empty" style={{ marginTop: 8 }}>
              No utility agents found. HTTP Request and Code Executor agents will appear here.
            </div>
          )}
        </div>
      )}

      {activeTab === "settings" && meta && onUpdateMeta && (
        <div className="wfb-sidebar-list wfb-sidebar-settings">
          <SettingsTab
            meta={meta}
            onUpdateMeta={onUpdateMeta}
            llmProviders={llmProviders || []}
          />
        </div>
      )}
    </div>
  );
}

// ── Settings Tab Content ──────────────────────────────────────────────

function SettingsTab({
  meta,
  onUpdateMeta,
  llmProviders,
}: {
  meta: WorkflowMeta;
  onUpdateMeta: (partial: Partial<WorkflowMeta>) => void;
  llmProviders: LLMProviderDescriptor[];
}) {
  const currentLlm = useMemo(() => {
    if (meta.orchestrator_llm_model && meta.orchestrator_llm_provider) {
      const provider = llmProviders.find(
        (p) => p.name === meta.orchestrator_llm_provider
      );
      return structureValue(
        meta.orchestrator_llm_provider,
        provider?.provider || "",
        meta.orchestrator_llm_model
      );
    }
    return null;
  }, [meta.orchestrator_llm_model, meta.orchestrator_llm_provider, llmProviders]);

  const onLlmSelect = useCallback(
    (selected: string | null) => {
      if (selected === null) {
        onUpdateMeta({
          orchestrator_llm_model: "",
          orchestrator_llm_provider: "",
        });
      } else {
        const { modelName, name } = parseLlmDescriptor(selected);
        if (modelName && name) {
          onUpdateMeta({
            orchestrator_llm_model: modelName,
            orchestrator_llm_provider: name,
          });
        }
      }
    },
    [onUpdateMeta]
  );

  return (
    <>
      <div className="wfb-settings-row">
        <div className="wfb-settings-label">Description</div>
        <textarea
          className="wfb-config-textarea"
          value={meta.description}
          onChange={(e) => onUpdateMeta({ description: e.target.value })}
          placeholder="Workflow description..."
          rows={2}
        />
      </div>

      {meta.orchestration_mode === "llm_decision" && (
        <>
          <div className="wfb-settings-row">
            <div className="wfb-settings-label">Orchestrator Prompt</div>
            <textarea
              className="wfb-config-textarea"
              value={meta.orchestrator_prompt}
              onChange={(e) =>
                onUpdateMeta({ orchestrator_prompt: e.target.value })
              }
              placeholder="Instructions for the orchestrator LLM..."
              rows={4}
            />
          </div>

          <div className="wfb-settings-row">
            <div className="wfb-settings-label">Orchestrator Model</div>
            <div className="wfb-settings-hint">
              LLM for routing decisions. Leave empty for system default.
            </div>
            <LLMSelector
              name="orchestrator_llm"
              llmProviders={llmProviders}
              currentLlm={currentLlm}
              onSelect={onLlmSelect}
            />
          </div>
        </>
      )}

      <OrchestratorLimitFields meta={meta} onUpdateMeta={onUpdateMeta} />

      <div className="wfb-settings-row">
        <div className="wfb-settings-label">Timeout (seconds)</div>
        <input
          className="wfb-settings-number"
          type="number"
          min={MIN_TIMEOUT_SECONDS}
          max={MAX_TIMEOUT_SECONDS}
          value={meta.timeout_seconds}
          onChange={(e) =>
            onUpdateMeta({
              timeout_seconds: Number(e.target.value) || 1800,
            })
          }
        />
      </div>

      <div className="wfb-config-toggle-row">
        <div className="wfb-config-toggle-label">Public</div>
        <ToggleSwitch
          checked={meta.is_public}
          onChange={(v) => onUpdateMeta({ is_public: v })}
        />
      </div>
    </>
  );
}

// ── Toggle Switch ───────────────────────────────────────────────────────

function ToggleSwitch({
  checked,
  onChange,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <button
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      style={{
        width: 36,
        height: 20,
        borderRadius: 10,
        border: "none",
        cursor: "pointer",
        position: "relative",
        flexShrink: 0,
        background: checked
          ? "var(--virtualai-accent, #6366f1)"
          : "var(--border-02, #d1d5db)",
        transition: "background 0.2s",
      }}
    >
      <span
        style={{
          display: "block",
          width: 16,
          height: 16,
          borderRadius: "50%",
          background: "#fff",
          position: "absolute",
          top: 2,
          left: checked ? 18 : 2,
          transition: "left 0.2s",
          boxShadow: "0 1px 3px rgba(0,0,0,0.2)",
        }}
      />
    </button>
  );
}
