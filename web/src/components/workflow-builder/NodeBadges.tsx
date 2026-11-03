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

/** Marks a step no line from Start reaches: it's saved but doesn't run. */
export function DisconnectedBadge() {
  return (
    <span
      className="wfb-disconnected-badge"
      title="No line from Start reaches this step, so it's saved but doesn't run. Connect it to run it again."
    >
      Not connected — won&apos;t run
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
  if (!data.upgrade_available && !data.modeConflict && !data.disconnected) {
    return null;
  }
  return (
    <div className="wfb-node-badges">
      {data.disconnected && <DisconnectedBadge />}
      {data.upgrade_available && <UpgradeBadge nodeId={nodeId} />}
      {data.modeConflict && <ModeConflictBadge />}
    </div>
  );
}
