"use client";

import React, { useCallback } from "react";
import type { StepNodeData } from "./types";

/**
 * Window event a node fires to ask the page to open the upgrade dialog
 * (nodes render inside React Flow and can't reach page state directly).
 */
export const UPGRADE_NODE_EVENT = "wfb-upgrade-node";

export interface UpgradeNodeEventDetail {
  nodeId: string;
}

/** "Upgrade available" button, shown when a newer node type version exists. */
export function UpgradeBadge({ nodeId }: { nodeId: string }) {
  const handleClick = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      window.dispatchEvent(
        new CustomEvent<UpgradeNodeEventDetail>(UPGRADE_NODE_EVENT, {
          detail: { nodeId },
        })
      );
    },
    [nodeId]
  );
  return (
    <button
      type="button"
      className="wfb-upgrade-badge nodrag"
      onClick={handleClick}
      title="A newer version of this node type is available"
    >
      Upgrade available
    </button>
  );
}

/** Marks a step whose type can't run in the workflow's orchestration mode. */
export function ModeConflictBadge() {
  return (
    <span
      className="wfb-mode-conflict-badge"
      title="This step type isn't supported in the current orchestration mode"
    >
      Not available in this mode
    </span>
  );
}

/** The status badges every step node shows, when they apply. */
export function StepNodeBadges({
  nodeId,
  data,
}: {
  nodeId: string;
  data: StepNodeData;
}) {
  const childCount = data.childCount ?? 0;
  if (
    !data.upgrade_available &&
    !data.modeConflict &&
    childCount === 0 &&
    !data.containerName
  ) {
    return null;
  }
  return (
    <div className="wfb-node-badges">
      {data.upgrade_available && <UpgradeBadge nodeId={nodeId} />}
      {data.modeConflict && <ModeConflictBadge />}
      {childCount > 0 && (
        <span className="wfb-container-badge">
          Contains {childCount} {childCount === 1 ? "step" : "steps"}
        </span>
      )}
      {data.containerName && (
        <span className="wfb-container-badge">
          In {data.containerName}
          {data.branch_index != null
            ? ` · branch ${data.branch_index + 1}`
            : ""}
        </span>
      )}
    </div>
  );
}
