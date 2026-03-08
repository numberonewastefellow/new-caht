"use client";

import React, { useState, useMemo, type DragEvent } from "react";
import type { MinimalPersonaSnapshot } from "@/app/admin/assistants/interfaces";
import type { DragPersonaData } from "./types";
import AgentAvatar from "@/refresh-components/avatars/AgentAvatar";

interface AgentSidebarProps {
  agents: MinimalPersonaSnapshot[];
  isLoading: boolean;
  onCreateNew?: () => void;
}

export function AgentSidebar({ agents, isLoading, onCreateNew }: AgentSidebarProps) {
  const [search, setSearch] = useState("");

  // Filter out workflow wrapper personas and filter by search
  const filtered = useMemo(() => {
    const nonWorkflow = agents.filter((a) => !a.workflow_id && a.id !== 0);
    if (!search.trim()) return nonWorkflow;
    const q = search.toLowerCase();
    return nonWorkflow.filter(
      (a) =>
        a.name.toLowerCase().includes(q) ||
        a.description?.toLowerCase().includes(q)
    );
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
        ) : filtered.length === 0 ? (
          <div className="wfb-sidebar-empty">
            {search ? "No matching agents" : "No agents available"}
          </div>
        ) : (
          filtered.map((agent) => (
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
          ))
        )}
      </div>
    </div>
  );
}
