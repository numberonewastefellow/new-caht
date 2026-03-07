"use client";

import React, { useState } from "react";
import type { MinimalPersonaSnapshot } from "@/app/admin/assistants/interfaces";
import type { AgentNodeData } from "./types";

interface NodeConfigPanelProps {
  nodeId: string;
  data: AgentNodeData;
  agents: MinimalPersonaSnapshot[];
  onUpdate: (nodeId: string, partial: Partial<AgentNodeData>) => void;
  onDelete: (nodeId: string) => void;
  onClose: () => void;
}

export function NodeConfigPanel({
  nodeId,
  data,
  agents,
  onUpdate,
  onDelete,
  onClose,
}: NodeConfigPanelProps) {
  return (
    <div className="wfb-config-panel">
      {/* Header */}
      <div className="wfb-config-header">
        <div className="wfb-config-title">Configure Step</div>
        <button className="wfb-config-close" onClick={onClose} title="Close">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
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
              const val = e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, "");
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
  const [inputMappingError, setInputMappingError] = useState<string | null>(null);
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
          padding: 0,
          width: "100%",
          color: "inherit",
          font: "inherit",
        }}
      >
        <svg
          width="12"
          height="12"
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
        <div style={{ marginTop: 8, display: "flex", flexDirection: "column", gap: 12 }}>
          <div>
            <div className="wfb-config-toggle-label">Input Mapping</div>
            <div className="wfb-config-toggle-desc" style={{ marginBottom: 4 }}>
              JSON mapping of input keys to source output keys
            </div>
            <textarea
              className="wfb-config-textarea"
              value={inputMappingStr}
              onChange={(e) => setInputMappingStr(e.target.value)}
              onBlur={handleInputMappingBlur}
              placeholder='{"context": "research_results"}'
              rows={3}
              style={{ fontFamily: "monospace", fontSize: 12 }}
            />
            {inputMappingError && (
              <div style={{ color: "#ef4444", fontSize: 11, marginTop: 2 }}>
                {inputMappingError}
              </div>
            )}
          </div>

          <div>
            <div className="wfb-config-toggle-label">Condition</div>
            <div className="wfb-config-toggle-desc" style={{ marginBottom: 4 }}>
              JSON condition for when this step should execute
            </div>
            <textarea
              className="wfb-config-textarea"
              value={conditionStr}
              onChange={(e) => setConditionStr(e.target.value)}
              onBlur={handleConditionBlur}
              placeholder='{"requires": "analysis_complete"}'
              rows={3}
              style={{ fontFamily: "monospace", fontSize: 12 }}
            />
            {conditionError && (
              <div style={{ color: "#ef4444", fontSize: 11, marginTop: 2 }}>
                {conditionError}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Simple toggle switch ──────────────────────────────────────────────

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
          ? "var(--theme-primary-05, #6366f1)"
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
