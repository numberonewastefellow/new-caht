"use client";

/**
 * Version history of a workflow: list saved versions, view one (a summary of
 * its steps) and restore it. A restore is saved as a new version, so it can
 * itself be undone. Shared by the Wizard and the Visual Builder.
 */

import React, { useState } from "react";
import Modal from "@/refresh-components/Modal";
import Button from "@/refresh-components/buttons/Button";
import Text from "@/refresh-components/texts/Text";
import { SvgHistory } from "@opal/icons";
import { useUser } from "@/providers/UserProvider";
import { useWorkflowVersion, useWorkflowVersions } from "@/hooks/useWorkflows";
import { restoreWorkflowVersion } from "@/lib/workflows/api";
import type {
  WorkflowSnapshot,
  WorkflowVersionDetail,
  WorkflowVersionSummary,
} from "@/lib/workflows/interfaces";
import { type NodeCatalog, labelFor } from "@/lib/workflows/nodeRegistry";
import { cn } from "@/lib/utils";

export interface WorkflowVersionsDialogProps {
  workflowId: number;
  /** The version the editor has loaded. */
  currentVersion: number | null;
  catalog: NodeCatalog;
  onRestored: (workflow: WorkflowSnapshot) => void;
  onClose: () => void;
}

function formatDate(iso: string): string {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? iso : date.toLocaleString();
}

function authorLabel(
  createdById: string | null,
  currentUserId: string | undefined
): string {
  if (!createdById) return "unknown author";
  if (createdById === currentUserId) return "you";
  return `user ${createdById.slice(0, 8)}`;
}

function VersionRow({
  version,
  isCurrent,
  selected,
  author,
  onSelect,
}: {
  version: WorkflowVersionSummary;
  isCurrent: boolean;
  selected: boolean;
  author: string;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        "w-full text-left px-3 py-2 rounded-08 border",
        selected
          ? "border-[var(--theme-primary-05)] bg-background-tint-00"
          : "border-transparent hover:bg-background-tint-00"
      )}
    >
      <div className="flex items-center gap-2">
        <span className="text-sm font-medium text-text-05">
          Version {version.version}
        </span>
        {isCurrent && (
          <span
            className="text-[10px] px-1.5 rounded-04"
            style={{
              color: "var(--virtualai-accent, var(--theme-primary-05))",
              background: "var(--virtualai-accent-subtle, transparent)",
            }}
          >
            Current
          </span>
        )}
      </div>
      <div className="text-xs text-text-03">
        {formatDate(version.created_at)} · {author}
      </div>
    </button>
  );
}

function VersionSummary({
  detail,
  catalog,
}: {
  detail: WorkflowVersionDetail;
  catalog: NodeCatalog;
}) {
  const { definition } = detail;
  const nodes = [...definition.nodes].sort(
    (a, b) => a.step_order - b.step_order
  );
  return (
    <div className="flex flex-col gap-2 w-full">
      <Text secondaryBody text03>
        {definition.name} · {definition.orchestration_mode} · {nodes.length}{" "}
        {nodes.length === 1 ? "step" : "steps"}
      </Text>
      <table className="w-full text-xs">
        <thead>
          <tr className="text-left text-text-03">
            <th className="py-1 pr-2">#</th>
            <th className="py-1 pr-2">Step</th>
            <th className="py-1 pr-2">Type</th>
            <th className="py-1">Output</th>
          </tr>
        </thead>
        <tbody>
          {nodes.map((node, i) => (
            <tr
              key={node.node_key}
              className="border-t border-border-01 text-text-04"
            >
              <td className="py-1 pr-2">{i + 1}</td>
              <td className="py-1 pr-2">{node.name}</td>
              <td className="py-1 pr-2">
                {labelFor(catalog, node.node_type, node.type_version)} v
                {node.type_version}
              </td>
              <td className="py-1 font-mono">{node.output_key}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function WorkflowVersionsDialog({
  workflowId,
  currentVersion,
  catalog,
  onRestored,
  onClose,
}: WorkflowVersionsDialogProps) {
  const { user } = useUser();
  const { versions, isLoading, error } = useWorkflowVersions(workflowId);
  const [selected, setSelected] = useState<number | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [restoring, setRestoring] = useState(false);
  const [restoreError, setRestoreError] = useState<string | null>(null);

  const shown = selected ?? versions[0]?.version ?? null;
  const { detail, isLoading: detailLoading } = useWorkflowVersion(
    workflowId,
    shown
  );

  const select = (version: number) => {
    setSelected(version);
    setConfirming(false);
    setRestoreError(null);
  };

  const restore = async () => {
    if (shown == null) return;
    setRestoring(true);
    setRestoreError(null);
    try {
      onRestored(await restoreWorkflowVersion(workflowId, shown));
    } catch (e) {
      setRestoreError(e instanceof Error ? e.message : "Restore failed");
    } finally {
      setRestoring(false);
      setConfirming(false);
    }
  };

  return (
    <Modal open onOpenChange={(open) => !open && onClose()}>
      <Modal.Content width="md" height="lg">
        <Modal.Header
          icon={SvgHistory}
          title="Version history"
          description="Every save creates a version. Restoring one saves it as a new version."
          onClose={onClose}
        />
        <Modal.Body>
          {error ? (
            <Text secondaryBody className="text-status-error-05">
              Couldn&apos;t load the versions of this workflow.
            </Text>
          ) : isLoading ? (
            <Text secondaryBody text03>
              Loading versions...
            </Text>
          ) : versions.length === 0 ? (
            <Text secondaryBody text03>
              No saved versions yet.
            </Text>
          ) : (
            <div className="flex gap-4 w-full min-h-0">
              <div className="w-56 shrink-0 flex flex-col gap-1">
                {versions.map((v) => (
                  <VersionRow
                    key={v.version}
                    version={v}
                    isCurrent={v.version === currentVersion}
                    selected={v.version === shown}
                    author={authorLabel(v.created_by_id, user?.id)}
                    onSelect={() => select(v.version)}
                  />
                ))}
              </div>
              <div className="flex-1 min-w-0">
                {detailLoading || !detail ? (
                  <Text secondaryBody text03>
                    Loading version...
                  </Text>
                ) : (
                  <VersionSummary detail={detail} catalog={catalog} />
                )}
              </div>
            </div>
          )}
          {restoreError && (
            <Text secondaryBody className="text-status-error-05">
              {restoreError}
            </Text>
          )}
        </Modal.Body>
        <Modal.Footer>
          {confirming ? (
            <>
              <Text secondaryBody text03 className="mr-auto">
                Restore version {shown}? Unsaved changes in the editor will be
                discarded.
              </Text>
              <Button secondary onClick={() => setConfirming(false)}>
                Cancel
              </Button>
              <Button danger disabled={restoring} onClick={restore}>
                {restoring ? "Restoring..." : "Restore"}
              </Button>
            </>
          ) : (
            <>
              <Button secondary onClick={onClose}>
                Close
              </Button>
              <Button
                disabled={shown == null || shown === currentVersion}
                onClick={() => setConfirming(true)}
              >
                Restore this version
              </Button>
            </>
          )}
        </Modal.Footer>
      </Modal.Content>
    </Modal>
  );
}
