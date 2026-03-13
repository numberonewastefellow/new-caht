"use client";

import React, { memo, useCallback, useState } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import type { AgentNodeData } from "./types";

function AgentNodeComponent({
  data,
  selected,
}: NodeProps & { data: AgentNodeData }) {
  const toolNames = data.persona_tool_names || [];
  const llmModel = data.persona_llm_model;
  const [imgError, setImgError] = useState(false);

  const handleTestClick = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      // Dispatch custom event to open test modal at the page level
      window.dispatchEvent(
        new CustomEvent("wfb-test-agent", {
          detail: {
            personaId: data.persona_id,
            personaName: data.persona_name,
            stepName: data.step_name,
          },
        })
      );
    },
    [data.persona_id, data.persona_name, data.step_name]
  );

  return (
    <div
      className={`wfb-agent-node ${selected ? "wfb-agent-node--selected" : ""}`}
    >
      {/* Header */}
      <div className="wfb-agent-header">
        <div className="wfb-agent-avatar">
          {data.persona_icon_url && !imgError ? (
            <img
              src={data.persona_icon_url}
              alt=""
              className="wfb-agent-avatar-img"
              onError={() => setImgError(true)}
            />
          ) : (
            <span className="wfb-agent-avatar-text">
              {(data.persona_name || "A").charAt(0).toUpperCase()}
            </span>
          )}
        </div>
        <div className="wfb-agent-name-col">
          <div className="wfb-agent-name" title={data.persona_name}>
            {data.persona_name}
          </div>
          {data.step_name && data.step_name !== data.persona_name && (
            <div className="wfb-agent-step-name" title={data.step_name}>
              {data.step_name}
            </div>
          )}
        </div>
        {/* Test / Play button */}
        <button
          className="wfb-agent-test-btn"
          onClick={handleTestClick}
          title="Test this agent"
        >
          <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
            <polygon points="5 3 19 12 5 21 5 3" />
          </svg>
        </button>
        {typeof data.stepOrder === "number" && (
          data.orchestration_mode === "llm_decision" ? (
            <span className="wfb-agent-order wfb-agent-order--ai" title="AI-routed">
              <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path d="M9.5 2A2.5 2.5 0 0112 4.5v15a2.5 2.5 0 01-4.96.44A2.5 2.5 0 015.5 15H5a2 2 0 01-2-2v-1c0-1.1.9-2 2-2h.5A2.5 2.5 0 018 7.5V7a2 2 0 012-2h1c1.1 0 2 .9 2 2v.5A2.5 2.5 0 0115.5 10h1a2 2 0 012 2v1a2 2 0 01-2 2h-1a2.5 2.5 0 00-2.5 2.5v.5a2 2 0 01-2 2h-1a2 2 0 01-2-2v-.5"/>
              </svg>
            </span>
          ) : (
            <span className="wfb-agent-order">#{data.stepOrder + 1}</span>
          )
        )}
      </div>

      {/* Info rows */}
      <div className="wfb-agent-info-rows">
        {/* Output key */}
        <div className="wfb-agent-info-row">
          <span className="wfb-agent-info-icon">
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="15 3 21 3 21 9" />
              <path d="M21 3l-7 7" />
              <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4" />
            </svg>
          </span>
          <span className="wfb-agent-info-label">Output</span>
          <code className="wfb-agent-info-value wfb-agent-info-code">{data.output_key || "output"}</code>
        </div>

        {/* LLM Model */}
        <div className="wfb-agent-info-row">
          <span className="wfb-agent-info-icon">
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 2a4 4 0 014 4c0 1.1-.9 2-2 2h-4a2 2 0 01-2-2 4 4 0 014-4z" />
              <path d="M12 8v8" />
              <circle cx="12" cy="20" r="2" />
              <path d="M8 16h8" />
            </svg>
          </span>
          <span className="wfb-agent-info-label">LLM</span>
          <span className="wfb-agent-info-value" title={llmModel || "Default"}>
            {llmModel || "Default"}
          </span>
        </div>

        {/* Tools */}
        <div className="wfb-agent-info-row">
          <span className="wfb-agent-info-icon">
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l3.77-3.77a6 6 0 01-7.94 7.94l-6.91 6.91a2.12 2.12 0 01-3-3l6.91-6.91a6 6 0 017.94-7.94l-3.76 3.76z" />
            </svg>
          </span>
          <span className="wfb-agent-info-label">Tools</span>
          <span className="wfb-agent-info-value" title={toolNames.join(", ") || "None"}>
            {toolNames.length > 0 ? toolNames.join(", ") : "None"}
          </span>
        </div>

        {/* Description */}
        {data.step_description && (
          <div className="wfb-agent-info-row wfb-agent-info-row--desc">
            <span className="wfb-agent-info-icon">
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
                <polyline points="14 2 14 8 20 8" />
                <line x1="16" y1="13" x2="8" y2="13" />
                <line x1="16" y1="17" x2="8" y2="17" />
              </svg>
            </span>
            <span className="wfb-agent-info-desc" title={data.step_description}>
              {data.step_description.length > 50
                ? data.step_description.slice(0, 50) + "..."
                : data.step_description}
            </span>
          </div>
        )}

        {/* HITL / Terminal / Visible */}
        <div className="wfb-agent-info-row">
          <span className="wfb-agent-info-icon">
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="3" width="18" height="18" rx="2" />
              <path d="M9 12l2 2 4-4" />
            </svg>
          </span>
          <span className="wfb-agent-info-label">Flags</span>
          <div className="wfb-agent-info-badges">
            {data.can_request_input && (
              <span className="wfb-badge wfb-badge-hitl">HITL</span>
            )}
            {data.is_terminal && (
              <span className="wfb-badge wfb-badge-terminal">Terminal</span>
            )}
            {data.promote_output && (
              <span className="wfb-badge wfb-badge-visible">Visible</span>
            )}
            {!data.can_request_input && !data.is_terminal && !data.promote_output && (
              <span className="wfb-agent-info-value">None</span>
            )}
          </div>
        </div>
      </div>

      {/* Handles */}
      <Handle
        type="target"
        position={Position.Left}
        className="wfb-handle wfb-handle-target"
      />
      <Handle
        type="source"
        position={Position.Right}
        className="wfb-handle wfb-handle-source"
      />
    </div>
  );
}

export const AgentNode = memo(AgentNodeComponent);
