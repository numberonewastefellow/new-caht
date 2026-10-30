"use client";

/**
 * Preview and apply a node type upgrade for one step. The backend converts
 * the config (nothing is saved); applying puts the new config on the step,
 * and it persists with the next save of the workflow. Used by both editors.
 */

import React, { useEffect, useState } from "react";
import Modal from "@/refresh-components/Modal";
import Button from "@/refresh-components/buttons/Button";
import Text from "@/refresh-components/texts/Text";
import { SvgArrowUpCircle } from "@opal/icons";
import { WorkflowApiError, upgradeNodeConfig } from "@/lib/workflows/api";
import type { NodeUpgradeResult } from "@/lib/workflows/interfaces";

export interface NodeUpgradeTarget {
  stepName: string;
  stepType: string;
  fromVersion: number;
  config: Record<string, unknown> | null;
  /** Lets order-based configs be rewritten to node keys. */
  stepOrderToNodeKey: Record<number, string>;
}

type UpgradeState =
  | { status: "loading" }
  | { status: "ready"; result: NodeUpgradeResult }
  | { status: "error"; message: string };

function errorMessage(error: unknown): string {
  if (error instanceof WorkflowApiError && error.status === 409) {
    return `This upgrade is a breaking change and can't be applied automatically: ${error.message}`;
  }
  return error instanceof Error ? error.message : "The upgrade failed.";
}

function ConfigColumn({ title, config }: { title: string; config: unknown }) {
  return (
    <div className="flex-1 min-w-0 flex flex-col gap-1">
      <Text secondaryBody text03>
        {title}
      </Text>
      <pre className="text-xs text-text-04 whitespace-pre-wrap break-words bg-background-tint-00 border border-border-01 rounded-08 p-2 max-h-[22rem] overflow-auto">
        {JSON.stringify(config ?? {}, null, 2)}
      </pre>
    </div>
  );
}

export function NodeUpgradeDialog({
  target,
  onApply,
  onClose,
}: {
  target: NodeUpgradeTarget;
  onApply: (result: NodeUpgradeResult) => void;
  onClose: () => void;
}) {
  const [state, setState] = useState<UpgradeState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    upgradeNodeConfig(target.stepType, {
      from_version: target.fromVersion,
      config: target.config ?? {},
      step_order_to_node_key: target.stepOrderToNodeKey,
    })
      .then((result) => !cancelled && setState({ status: "ready", result }))
      .catch(
        (error) =>
          !cancelled &&
          setState({ status: "error", message: errorMessage(error) })
      );
    return () => {
      cancelled = true;
    };
  }, [target]);

  return (
    <Modal open onOpenChange={(open) => !open && onClose()}>
      <Modal.Content width="md" height="lg">
        <Modal.Header
          icon={SvgArrowUpCircle}
          title={`Upgrade "${target.stepName}"`}
          description="Review the converted settings. The upgrade is saved with the workflow; restore an earlier version to undo it."
          onClose={onClose}
        />
        <Modal.Body>
          {state.status === "loading" && (
            <Text secondaryBody text03>
              Converting settings...
            </Text>
          )}
          {state.status === "error" && (
            <Text secondaryBody className="text-status-error-05">
              {state.message}
            </Text>
          )}
          {state.status === "ready" && (
            <div className="flex gap-3 w-full">
              <ConfigColumn
                title={`Version ${state.result.from_version} (current)`}
                config={target.config}
              />
              <ConfigColumn
                title={`Version ${state.result.to_version}`}
                config={state.result.config}
              />
            </div>
          )}
        </Modal.Body>
        <Modal.Footer>
          <Button secondary onClick={onClose}>
            Cancel
          </Button>
          <Button
            disabled={state.status !== "ready"}
            onClick={() => state.status === "ready" && onApply(state.result)}
          >
            Apply upgrade
          </Button>
        </Modal.Footer>
      </Modal.Content>
    </Modal>
  );
}
