"use client";

import React from "react";
import { configPanelFor } from "./nodeUi";
import type { StepConfigPanelProps } from "./types";

/**
 * The right-hand panel for the selected step: a collapsed strip, or the
 * config panel registered for the node's editor kind (see nodeUi.tsx).
 */
export function StepConfigPanel({
  kind,
  collapsed,
  ...props
}: StepConfigPanelProps & {
  /** React Flow type of the node, i.e. its editor kind. */
  kind: string | undefined;
  collapsed?: boolean;
}) {
  if (collapsed) {
    return (
      <div className="wfb-config-panel wfb-config-panel--collapsed">
        <button
          className="wfb-sidebar-collapse-btn"
          onClick={props.onToggleCollapse}
          title="Expand config panel"
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <polyline points="15 18 9 12 15 6" />
          </svg>
        </button>
      </div>
    );
  }

  const Panel = configPanelFor(kind);
  // Re-mount per node so panel-local state (tabs, drafts) doesn't leak.
  return <Panel key={props.nodeId} {...props} />;
}
