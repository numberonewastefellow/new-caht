"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import {
  createPersona,
  type PersonaUpsertParameters,
} from "@/app/admin/assistants/lib";
import type { DragPersonaData } from "./types";

interface QuickCreateAgentModalProps {
  onCreated: (dragData: DragPersonaData) => void;
  onClose: () => void;
}

export function QuickCreateAgentModal({
  onCreated,
  onClose,
}: QuickCreateAgentModalProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [systemPrompt, setSystemPrompt] = useState("");
  const [showPrompt, setShowPrompt] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const nameRef = useRef<HTMLInputElement>(null);

  // Focus name input on mount
  useEffect(() => {
    nameRef.current?.focus();
  }, []);

  // Close on Escape
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const handleCreate = useCallback(async () => {
    const trimmedName = name.trim();
    if (!trimmedName) {
      setError("Name is required");
      return;
    }

    setSaving(true);
    setError(null);

    const params: PersonaUpsertParameters = {
      name: trimmedName,
      description: description.trim(),
      system_prompt: systemPrompt.trim(),
      replace_base_system_prompt: false,
      task_prompt: "",
      datetime_aware: false,
      document_set_ids: [],
      num_chunks: 0,
      is_public: true,
      llm_relevance_filter: false,
      llm_model_provider_override: null,
      llm_model_version_override: null,
      starter_messages: null,
      groups: [],
      tool_ids: [],
      search_start_date: null,
      uploaded_image_id: null,
      icon_name: null,
      is_default_persona: false,
      label_ids: null,
      user_file_ids: [],
    };

    try {
      const resp = await createPersona(params);
      if (!resp || !resp.ok) {
        const errText = resp ? await resp.text() : "Failed to create agent";
        setError(errText);
        setSaving(false);
        return;
      }

      const persona = await resp.json();
      const dragData: DragPersonaData = {
        persona_id: persona.id,
        persona_name: persona.name,
        persona_description: persona.description || "",
        persona_icon_url: null,
        persona_num_tools: persona.tools?.length || 0,
        persona_tool_names: (persona.tools || []).map((t: any) => t.name),
        persona_llm_model: persona.llm_model_version_override || null,
        persona_llm_provider: persona.llm_model_provider_override || null,
      };

      onCreated(dragData);
    } catch (err: any) {
      setError(err?.message || "An error occurred");
      setSaving(false);
    }
  }, [name, description, systemPrompt, onCreated]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey && e.target instanceof HTMLInputElement) {
        e.preventDefault();
        handleCreate();
      }
    },
    [handleCreate]
  );

  return (
    <div className="wfb-test-overlay" onClick={onClose}>
      <div className="wfb-create-modal" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="wfb-test-header">
          <div className="wfb-test-title">
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
          </div>
          <button
            className="wfb-config-close"
            onClick={onClose}
            title="Close"
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="wfb-create-body">
          {/* Name */}
          <div className="wfb-create-field">
            <label className="wfb-create-label">
              Name <span style={{ color: "var(--theme-red-05, #dc2626)" }}>*</span>
            </label>
            <input
              ref={nameRef}
              className="wfb-create-input"
              type="text"
              placeholder="e.g. Research Analyst"
              value={name}
              onChange={(e) => setName(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={saving}
            />
          </div>

          {/* Description */}
          <div className="wfb-create-field">
            <label className="wfb-create-label">Description</label>
            <textarea
              className="wfb-create-textarea"
              placeholder="What does this agent do?"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
              disabled={saving}
            />
          </div>

          {/* System Prompt (collapsible) */}
          <div className="wfb-create-field">
            <button
              className="wfb-create-toggle"
              onClick={() => setShowPrompt(!showPrompt)}
              type="button"
            >
              <svg
                width="10"
                height="10"
                viewBox="0 0 24 24"
                fill="currentColor"
                style={{
                  transform: showPrompt ? "rotate(90deg)" : "rotate(0deg)",
                  transition: "transform 0.15s",
                }}
              >
                <polygon points="6 4 18 12 6 20" />
              </svg>
              System Prompt (optional)
            </button>
            {showPrompt && (
              <textarea
                className="wfb-create-textarea wfb-create-textarea--tall"
                placeholder="Instructions for the agent..."
                value={systemPrompt}
                onChange={(e) => setSystemPrompt(e.target.value)}
                rows={4}
                disabled={saving}
              />
            )}
          </div>

          {/* Error */}
          {error && (
            <div className="wfb-create-error">{error}</div>
          )}
        </div>

        {/* Footer */}
        <div className="wfb-create-footer">
          <button
            className="wfb-create-cancel-btn"
            onClick={onClose}
            disabled={saving}
          >
            Cancel
          </button>
          <button
            className="wfb-create-submit-btn"
            onClick={handleCreate}
            disabled={saving || !name.trim()}
          >
            {saving ? "Creating..." : "Create & Add"}
          </button>
        </div>
      </div>
    </div>
  );
}
