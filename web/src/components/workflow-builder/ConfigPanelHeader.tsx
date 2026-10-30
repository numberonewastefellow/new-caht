"use client";

import React from "react";

/** Title row with collapse/close buttons, shared by the step config panels. */
export function ConfigPanelHeader({
  title,
  onClose,
  onToggleCollapse,
}: {
  title: string;
  onClose: () => void;
  onToggleCollapse?: () => void;
}) {
  return (
    <div className="wfb-config-header">
      <div className="wfb-config-title">{title}</div>
      <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
        {onToggleCollapse && (
          <button
            className="wfb-config-close"
            onClick={onToggleCollapse}
            title="Collapse panel"
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
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
  );
}
