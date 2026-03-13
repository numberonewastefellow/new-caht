"use client";

import React, { useState, useMemo, type DragEvent } from "react";
import type { MinimalPersonaSnapshot } from "@/app/admin/assistants/interfaces";
import type { DragPersonaData } from "./types";
import AgentAvatar from "@/refresh-components/avatars/AgentAvatar";

/** Special drag data type for non-persona items (e.g., conditional router) */
export const CONDITION_DRAG_TYPE = "application/reactflow-condition";

// Names of utility personas that get their own section
const UTILITY_PERSONA_NAMES = new Set(["HTTP Request", "Code Executor"]);

interface AgentSidebarProps {
  agents: MinimalPersonaSnapshot[];
  isLoading: boolean;
  onCreateNew?: () => void;
}

export function AgentSidebar({ agents, isLoading, onCreateNew }: AgentSidebarProps) {
  const [search, setSearch] = useState("");

  // Split agents into utility vs regular, filter out workflow wrappers
  const { utilityAgents, regularAgents } = useMemo(() => {
    const nonWorkflow = agents.filter((a) => !a.workflow_id && a.id !== 0);
    const q = search.trim().toLowerCase();
    const matchesSearch = (a: MinimalPersonaSnapshot) =>
      !q ||
      a.name.toLowerCase().includes(q) ||
      a.description?.toLowerCase().includes(q);

    return {
      utilityAgents: nonWorkflow.filter(
        (a) => UTILITY_PERSONA_NAMES.has(a.name) && matchesSearch(a)
      ),
      regularAgents: nonWorkflow.filter(
        (a) => !UTILITY_PERSONA_NAMES.has(a.name) && matchesSearch(a)
      ),
    };
  }, [agents, search]);

  const handleDragStart = (
    event: DragEvent<HTMLDivElement>,
    agent: MinimalPersonaSnapshot
  ) => {
    const data: DragPersonaData = {
      persona_id: agent.id,
      persona_name: agent.name,
      persona_description: agent.description || "",
      persona_icon_url: agent.uploaded_image_id
        ? `/api/persona/${agent.id}/uploaded_image`
        : null,
      persona_num_tools: agent.tools?.length || 0,
      persona_tool_names: (agent.tools || []).map((t) => t.name),
      persona_llm_model: agent.llm_model_version_override || null,
      persona_llm_provider: agent.llm_model_provider_override || null,
    };
    event.dataTransfer.setData("application/reactflow", JSON.stringify(data));
    event.dataTransfer.effectAllowed = "move";
  };

  const renderAgentCard = (agent: MinimalPersonaSnapshot) => (
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

  return (
    <div className="wfb-sidebar">
      <div className="wfb-sidebar-header">
        <div className="wfb-sidebar-title">Agents</div>
        <input
          className="wfb-sidebar-search"
          type="text"
          placeholder="Search agents..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>
      <div className="wfb-sidebar-list">
        {/* Create New Agent button */}
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
        ) : regularAgents.length === 0 && utilityAgents.length === 0 ? (
          <div className="wfb-sidebar-empty">
            {search ? "No matching agents" : "No agents available"}
          </div>
        ) : (
          <>
            {/* Utilities section */}
            <div className="wfb-sidebar-section-title">Utilities</div>
            {/* Condition (If-Else) — always available */}
            <div
              className="wfb-sidebar-card wfb-sidebar-card--condition"
              draggable
              onDragStart={(e) => {
                e.dataTransfer.setData(CONDITION_DRAG_TYPE, "conditional_router");
                e.dataTransfer.effectAllowed = "move";
              }}
              title="Drag to add a conditional branch (If/Else)"
            >
              <div className="wfb-sidebar-card-avatar wfb-sidebar-card-avatar--condition">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M16 3h5v5" />
                  <path d="M8 3H3v5" />
                  <path d="M12 22v-8.3a4 4 0 00-1.172-2.872L3 3" />
                  <path d="M15 9l6-6" />
                </svg>
              </div>
              <div className="wfb-sidebar-card-info">
                <div className="wfb-sidebar-card-name">Condition (If-Else)</div>
                <div className="wfb-sidebar-card-desc">Branch based on step output</div>
              </div>
            </div>
            {utilityAgents.length > 0 && utilityAgents.map(renderAgentCard)}
            {/* Regular agents section */}
            {regularAgents.length > 0 && (
              <>
                {utilityAgents.length > 0 && (
                  <div className="wfb-sidebar-section-title">Agents</div>
                )}
                {regularAgents.map(renderAgentCard)}
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}
