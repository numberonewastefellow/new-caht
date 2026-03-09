"use client";

import React, { useState, useEffect, useCallback } from "react";

interface JsonViewModalProps {
  workflowJson: object;
  agentIds: number[];
  onClose: () => void;
}

export function JsonViewModal({
  workflowJson,
  agentIds,
  onClose,
}: JsonViewModalProps) {
  const [tab, setTab] = useState<"workflow" | "agents">("workflow");
  const [agents, setAgents] = useState<object[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  // Fetch agent details when agents tab selected
  useEffect(() => {
    if (tab !== "agents" || agents !== null || agentIds.length === 0) return;
    setLoading(true);
    Promise.all(
      Array.from(new Set(agentIds)).map((id) =>
        fetch(`/api/persona/${id}`, { credentials: "include" })
          .then((r) => (r.ok ? r.json() : null))
          .catch(() => null)
      )
    ).then((results) => {
      setAgents(results.filter(Boolean));
      setLoading(false);
    });
  }, [tab, agents, agentIds]);

  const currentJson =
    tab === "workflow"
      ? JSON.stringify(workflowJson, null, 2)
      : loading
        ? "Loading agents..."
        : JSON.stringify(agents ?? [], null, 2);

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(currentJson).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }, [currentJson]);

  // Close on Escape
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="wfb-test-overlay" onClick={onClose}>
      <div className="wfb-json-modal" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="wfb-test-header">
          <div className="wfb-test-title">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="16 18 22 12 16 6" />
              <polyline points="8 6 2 12 8 18" />
            </svg>
            JSON View
          </div>
          <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
            <button
              className="wfb-create-cancel-btn"
              onClick={handleCopy}
              style={{ padding: "5px 12px", fontSize: 12 }}
            >
              {copied ? "Copied!" : "Copy"}
            </button>
            <button className="wfb-config-close" onClick={onClose} title="Close">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="wfb-json-tabs">
          <button
            className={`wfb-json-tab ${tab === "workflow" ? "wfb-json-tab--active" : ""}`}
            onClick={() => setTab("workflow")}
          >
            Workflow
          </button>
          <button
            className={`wfb-json-tab ${tab === "agents" ? "wfb-json-tab--active" : ""}`}
            onClick={() => setTab("agents")}
          >
            Agents ({Array.from(new Set(agentIds)).length})
          </button>
        </div>

        {/* JSON content */}
        <pre className="wfb-json-content">{currentJson}</pre>
      </div>
    </div>
  );
}
