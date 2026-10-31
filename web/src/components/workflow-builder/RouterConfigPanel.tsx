"use client";

import React from "react";
import { CONDITION_OPERATORS } from "@/lib/workflows/interfaces";
import type { RouterConfigV2 } from "@/lib/workflows/interfaces";
import {
  VALUELESS_OPERATORS,
  normalizeRouterConfig,
} from "@/lib/workflows/routerConfig";
import { ConfigPanelHeader } from "./ConfigPanelHeader";
import { StepOptionsSection, StepPlacementSection } from "./StepOptionsSection";
import type { StepConfigPanelProps } from "./types";

/**
 * Config panel for conditional router steps. Only the condition is edited
 * here; the branches are the node's True/False edges on the canvas, which
 * become `true_node_keys` / `false_node_keys` when the workflow is saved.
 */
export function RouterConfigPanel({
  nodeId,
  data,
  catalog,
  steps,
  onMove,
  onUpdate,
  onDelete,
  onClose,
  onToggleCollapse,
}: StepConfigPanelProps) {
  const config = normalizeRouterConfig(data.config);
  const needsMatchValue = !VALUELESS_OPERATORS.has(config.operator);

  const updateConfig = (partial: Partial<RouterConfigV2>) =>
    onUpdate(nodeId, { config: { ...config, ...partial } });

  return (
    <div className="wfb-config-panel">
      <ConfigPanelHeader
        title="Configure Condition"
        onClose={onClose}
        onToggleCollapse={onToggleCollapse}
      />

      <div className="wfb-config-body">
        {/* Step Name */}
        <div className="wfb-config-section">
          <div className="wfb-config-label">Step Name</div>
          <input
            className="wfb-config-input"
            value={data.step_name}
            onChange={(e) => onUpdate(nodeId, { step_name: e.target.value })}
            placeholder="e.g., Check for errors"
          />
        </div>

        {/* Output Key */}
        <div className="wfb-config-section">
          <div className="wfb-config-label">Output Key</div>
          <input
            className="wfb-config-input"
            value={data.output_key}
            onChange={(e) => onUpdate(nodeId, { output_key: e.target.value })}
            placeholder="e.g., condition_result"
          />
          <div className="wfb-config-hint">
            Stores &quot;true&quot; or &quot;false&quot; in workflow context
          </div>
        </div>

        {/* Condition Field */}
        <div className="wfb-config-section">
          <div className="wfb-config-label">Condition Field</div>
          <input
            className="wfb-config-input"
            value={config.condition_field}
            onChange={(e) => updateConfig({ condition_field: e.target.value })}
            placeholder="e.g., $research.output"
          />
          <div className="wfb-config-hint">
            Reference a previous step&apos;s output using $step_name.output
          </div>
        </div>

        {/* Operator */}
        <div className="wfb-config-section">
          <div className="wfb-config-label">Operator</div>
          <select
            className="wfb-config-input"
            value={config.operator}
            onChange={(e) =>
              updateConfig({
                operator: e.target.value as RouterConfigV2["operator"],
              })
            }
          >
            {CONDITION_OPERATORS.map((op) => (
              <option key={op.value} value={op.value}>
                {op.label}
              </option>
            ))}
          </select>
        </div>

        {/* Match Value */}
        {needsMatchValue && (
          <div className="wfb-config-section">
            <div className="wfb-config-label">Match Value</div>
            <input
              className="wfb-config-input"
              value={config.match_value}
              onChange={(e) => updateConfig({ match_value: e.target.value })}
              placeholder="e.g., error"
            />
          </div>
        )}

        {/* Case Sensitive */}
        <div className="wfb-config-section">
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <input
              type="checkbox"
              checked={config.case_sensitive}
              onChange={(e) =>
                updateConfig({ case_sensitive: e.target.checked })
              }
            />
            <span className="wfb-config-label" style={{ margin: 0 }}>
              Case sensitive
            </span>
          </div>
        </div>

        {/* Description */}
        <div className="wfb-config-section">
          <div className="wfb-config-label">Description (optional)</div>
          <textarea
            className="wfb-config-textarea"
            value={data.step_description}
            onChange={(e) =>
              onUpdate(nodeId, { step_description: e.target.value })
            }
            placeholder="Describe what this condition checks..."
            rows={2}
          />
        </div>

        {/* Info about branch connections */}
        <div className="wfb-config-section">
          <div
            className="wfb-config-hint"
            style={{
              padding: "8px 10px",
              background: "var(--background-tint-02, #f3f4f6)",
              borderRadius: 6,
            }}
          >
            Connect the{" "}
            <strong style={{ color: "var(--status-success-05)" }}>True</strong>{" "}
            and{" "}
            <strong style={{ color: "var(--status-error-05)" }}>False</strong>{" "}
            handles on the right side of the node to the steps that should run
            only in that branch. To put several steps in a branch, connect each
            of them to the handle; steps that follow a branch step but
            aren&apos;t connected to the handle run either way.
          </div>
        </div>

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
          canPause={false}
          onUpdate={onUpdate}
        />

        {/* Delete */}
        <div className="wfb-config-section" style={{ marginTop: 16 }}>
          <button
            className="wfb-config-danger-btn"
            onClick={() => onDelete(nodeId)}
          >
            Remove Condition
          </button>
        </div>
      </div>
    </div>
  );
}
