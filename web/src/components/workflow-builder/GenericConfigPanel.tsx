"use client";

import React from "react";
import { SchemaConfigForm } from "@/components/workflows/SchemaConfigForm";
import { humanizeNodeType, resolveVersion } from "@/lib/workflows/nodeRegistry";
import { ConfigPanelHeader } from "./ConfigPanelHeader";
import { StepOptionsSection, StepPlacementSection } from "./StepOptionsSection";
import type { StepConfigPanelProps, StepNodeData } from "./types";

/** Step fields every node type has (name, description, output, flags). */
function CommonStepFields({
  nodeId,
  data,
  readOnly,
  onUpdate,
}: {
  nodeId: string;
  data: StepNodeData;
  readOnly: boolean;
  onUpdate: StepConfigPanelProps["onUpdate"];
}) {
  return (
    <>
      <div className="wfb-config-section">
        <div className="wfb-config-label">Step Name</div>
        <input
          className="wfb-config-input"
          value={data.step_name}
          disabled={readOnly}
          onChange={(e) => onUpdate(nodeId, { step_name: e.target.value })}
        />
      </div>
      <div className="wfb-config-section">
        <div className="wfb-config-label">Output Key</div>
        <input
          className="wfb-config-input"
          value={data.output_key}
          disabled={readOnly}
          onChange={(e) =>
            onUpdate(nodeId, {
              output_key: e.target.value
                .toLowerCase()
                .replace(/[^a-z0-9_]/g, ""),
            })
          }
        />
      </div>
      <div className="wfb-config-section">
        <div className="wfb-config-label">Description (optional)</div>
        <textarea
          className="wfb-config-textarea"
          rows={2}
          value={data.step_description}
          disabled={readOnly}
          onChange={(e) =>
            onUpdate(nodeId, { step_description: e.target.value })
          }
        />
      </div>
    </>
  );
}

function JsonBlock({ value }: { value: unknown }) {
  return (
    <pre className="wfb-config-json">
      {JSON.stringify(value ?? {}, null, 2)}
    </pre>
  );
}

/**
 * Config panel for node types without a dedicated UI (`schema` kind): the
 * common step fields plus a form generated from the type's config schema.
 */
export function GenericConfigPanel({
  nodeId,
  data,
  catalog,
  steps,
  onMove,
  onUpdate,
  onDelete,
  onDeleteKeepingSteps,
  onClose,
  onToggleCollapse,
}: StepConfigPanelProps) {
  const childCount = steps.filter((s) => s.parent_key === nodeId).length;
  const info = resolveVersion(catalog, data.step_type, data.type_version);
  const label = info?.label ?? humanizeNodeType(data.step_type);

  return (
    <div className="wfb-config-panel">
      <ConfigPanelHeader
        title={`Configure ${label}`}
        onClose={onClose}
        onToggleCollapse={onToggleCollapse}
      />
      <div className="wfb-config-body">
        {info?.description && (
          <div className="wfb-config-section wfb-config-hint">
            {info.description}
          </div>
        )}
        <CommonStepFields
          nodeId={nodeId}
          data={data}
          readOnly={false}
          onUpdate={onUpdate}
        />
        <StepPlacementSection
          nodeId={nodeId}
          data={data}
          steps={steps}
          catalog={catalog}
          onMove={onMove}
        />
        <StepOptionsSection
          nodeId={nodeId}
          data={data}
          canPause={info?.can_pause ?? false}
          onUpdate={onUpdate}
        />
        <div className="wfb-config-section">
          <div className="wfb-config-label">Settings</div>
          {info ? (
            <SchemaConfigForm
              schema={info.config_schema}
              value={data.config}
              onChange={(config) => onUpdate(nodeId, { config })}
            />
          ) : (
            <JsonBlock value={data.config} />
          )}
        </div>
      </div>
      <div className="wfb-config-footer">
        {childCount > 0 && onDeleteKeepingSteps && (
          <button
            className="wfb-config-delete-btn"
            onClick={() => onDeleteKeepingSteps(nodeId)}
          >
            Remove, but keep its {childCount} step{childCount === 1 ? "" : "s"}
          </button>
        )}
        <button
          className="wfb-config-delete-btn"
          onClick={() => onDelete(nodeId)}
        >
          {childCount > 0
            ? `Remove with its ${childCount} step${childCount === 1 ? "" : "s"}`
            : "Remove from workflow"}
        </button>
      </div>
    </div>
  );
}

/**
 * Read-only panel for node types the catalog doesn't know (`unsupported`).
 * The step is saved back unchanged unless it is removed.
 */
export function UnsupportedConfigPanel({
  nodeId,
  data,
  onUpdate,
  onDelete,
  onClose,
  onToggleCollapse,
}: StepConfigPanelProps) {
  return (
    <div className="wfb-config-panel">
      <ConfigPanelHeader
        title="Unsupported step"
        onClose={onClose}
        onToggleCollapse={onToggleCollapse}
      />
      <div className="wfb-config-body">
        <div className="wfb-config-section wfb-config-hint">
          This editor doesn&apos;t know the node type{" "}
          <code>{data.step_type}</code>
          {data.type_version != null ? ` (v${data.type_version})` : ""}. It is
          kept unchanged when you save; remove it if it is no longer needed.
        </div>
        <CommonStepFields
          nodeId={nodeId}
          data={data}
          readOnly
          onUpdate={onUpdate}
        />
        <div className="wfb-config-section">
          <div className="wfb-config-label">Settings (read-only)</div>
          <JsonBlock value={data.config} />
        </div>
      </div>
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
