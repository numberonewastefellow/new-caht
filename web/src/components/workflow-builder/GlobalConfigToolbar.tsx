"use client";

import React, { useState, useRef, useEffect, useMemo, useCallback } from "react";
import type { WorkflowMeta } from "./types";
import type { LLMProviderDescriptor } from "@/app/admin/configuration/llm/interfaces";
import LLMSelector from "@/components/llm/LLMSelector";
import { parseLlmDescriptor, structureValue } from "@/lib/llm/utils";

interface GlobalConfigToolbarProps {
  meta: WorkflowMeta;
  onUpdateMeta: (partial: Partial<WorkflowMeta>) => void;
  onSave: () => void;
  onAutoLayout: () => void;
  onBack: () => void;
  isSaving: boolean;
  isEditMode: boolean;
  llmProviders: LLMProviderDescriptor[];
}

export function GlobalConfigToolbar({
  meta,
  onUpdateMeta,
  onSave,
  onAutoLayout,
  onBack,
  isSaving,
  isEditMode,
  llmProviders,
}: GlobalConfigToolbarProps) {
  const [showSettings, setShowSettings] = useState(false);
  const settingsRef = useRef<HTMLDivElement>(null);

  // LLM selector helpers (mirrors WorkflowEditorPage pattern)
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

  // Close settings popover on outside click
  useEffect(() => {
    if (!showSettings) return;
    const handle = (e: MouseEvent) => {
      if (
        settingsRef.current &&
        !settingsRef.current.contains(e.target as Node)
      ) {
        setShowSettings(false);
      }
    };
    document.addEventListener("mousedown", handle);
    return () => document.removeEventListener("mousedown", handle);
  }, [showSettings]);

  return (
    <div className="wfb-toolbar">
      {/* Left: back + name */}
      <div className="wfb-toolbar-left">
        <button className="wfb-back-btn" onClick={onBack} title="Back to workflows">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M19 12H5M12 19l-7-7 7-7" />
          </svg>
        </button>
        <input
          className="wfb-toolbar-name"
          type="text"
          value={meta.name}
          onChange={(e) => onUpdateMeta({ name: e.target.value })}
          placeholder="Workflow name..."
        />
      </div>

      {/* Center: mode toggle */}
      <div className="wfb-toolbar-center">
        <div className="wfb-mode-toggle">
          <button
            className={`wfb-mode-btn ${meta.orchestration_mode === "sequential" ? "wfb-mode-btn--active" : ""}`}
            onClick={() => onUpdateMeta({ orchestration_mode: "sequential" })}
          >
            Sequential
          </button>
          <button
            className={`wfb-mode-btn ${meta.orchestration_mode === "llm_decision" ? "wfb-mode-btn--active" : ""}`}
            onClick={() => onUpdateMeta({ orchestration_mode: "llm_decision" })}
          >
            LLM Decision
          </button>
        </div>
      </div>

      {/* Right: settings, auto-layout, save */}
      <div className="wfb-toolbar-right">
        <button
          className="wfb-toolbar-btn-icon"
          onClick={onAutoLayout}
          title="Auto-layout nodes"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="3" y="3" width="7" height="7" rx="1" />
            <rect x="14" y="3" width="7" height="7" rx="1" />
            <rect x="3" y="14" width="7" height="7" rx="1" />
            <rect x="14" y="14" width="7" height="7" rx="1" />
          </svg>
        </button>

        {/* Settings popover */}
        <div style={{ position: "relative" }} ref={settingsRef}>
          <button
            className="wfb-toolbar-btn-icon"
            onClick={() => setShowSettings(!showSettings)}
            title="Workflow settings"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="3" />
              <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z" />
            </svg>
          </button>

          {showSettings && (
            <div
              className="wfb-settings-popover"
              style={{
                position: "absolute",
                top: "calc(100% + 8px)",
                right: 0,
                zIndex: 50,
              }}
            >
              <div className="wfb-settings-title">Workflow Settings</div>

              <div className="wfb-settings-row">
                <div className="wfb-settings-label">Description</div>
                <textarea
                  className="wfb-config-textarea"
                  value={meta.description}
                  onChange={(e) =>
                    onUpdateMeta({ description: e.target.value })
                  }
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
                      LLM for routing decisions. Use a fast model (e.g. GPT-4.1).
                      Leave empty for system default.
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

              <div className="wfb-settings-row">
                <div className="wfb-settings-label">Max Total Steps</div>
                <input
                  className="wfb-settings-number"
                  type="number"
                  min={1}
                  max={50}
                  value={meta.max_steps}
                  onChange={(e) =>
                    onUpdateMeta({ max_steps: Number(e.target.value) || 10 })
                  }
                />
              </div>

              <div className="wfb-settings-row">
                <div className="wfb-settings-label">Max Calls per Agent</div>
                <input
                  className="wfb-settings-number"
                  type="number"
                  min={1}
                  max={10}
                  value={meta.max_calls_per_agent}
                  onChange={(e) =>
                    onUpdateMeta({
                      max_calls_per_agent: Number(e.target.value) || 2,
                    })
                  }
                />
              </div>

              <div className="wfb-settings-row">
                <div className="wfb-settings-label">Timeout (seconds)</div>
                <input
                  className="wfb-settings-number"
                  type="number"
                  min={30}
                  max={7200}
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
            </div>
          )}
        </div>

        <button
          className="wfb-toolbar-btn wfb-toolbar-save"
          onClick={onSave}
          disabled={isSaving}
        >
          {isSaving ? "Saving..." : isEditMode ? "Update" : "Save"}
        </button>
      </div>
    </div>
  );
}

// ── Toggle (same as in NodeConfigPanel) ───────────────────────────────

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
