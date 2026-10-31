"use client";

import React from "react";
import { StepPlacementFields } from "@/components/workflows/StepPlacementFields";
import type { StepConfigPanelProps, StepNodeData } from "./types";

export function ToggleSwitch({
  checked,
  onChange,
  disabled,
}: {
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => !disabled && onChange(!checked)}
      style={{
        position: "relative",
        width: 36,
        height: 20,
        borderRadius: 10,
        border: "none",
        cursor: disabled ? "not-allowed" : "pointer",
        opacity: disabled ? 0.5 : 1,
        background: checked
          ? "var(--virtualai-accent, var(--theme-primary-05))"
          : "var(--border-02)",
        transition: "background 0.2s",
        flexShrink: 0,
      }}
    >
      <span
        style={{
          position: "absolute",
          top: 2,
          left: checked ? 18 : 2,
          width: 16,
          height: 16,
          borderRadius: "50%",
          background: "#fff",
          transition: "left 0.2s",
          boxShadow: "0 1px 3px rgba(0,0,0,0.2)",
        }}
      />
    </button>
  );
}

function OptionRow({
  label,
  description,
  checked,
  onChange,
}: {
  label: string;
  description: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <div className="wfb-config-toggle-row">
      <div>
        <div className="wfb-config-toggle-label">{label}</div>
        <div className="wfb-config-toggle-desc">{description}</div>
      </div>
      <ToggleSwitch checked={checked} onChange={onChange} />
    </div>
  );
}

/**
 * The options every step type shares (the Wizard shows the same ones). A step
 * inside a Parallel or Loop has none: it can't pause, promote its output, or end
 * the workflow.
 */
export function StepOptionsSection({
  nodeId,
  data,
  canPause,
  onUpdate,
}: {
  nodeId: string;
  data: StepNodeData;
  canPause: boolean;
  onUpdate: StepConfigPanelProps["onUpdate"];
}) {
  if (data.parent_key) {
    return null;
  }
  return (
    <div className="wfb-config-section">
      <div className="wfb-config-label">Options</div>
      <OptionRow
        label="Terminal Step"
        description="Marks this as a final step"
        checked={data.is_terminal}
        onChange={(v) => onUpdate(nodeId, { is_terminal: v })}
      />
      {canPause && (
        <OptionRow
          label="Can Request Input (HITL)"
          description="Agent can pause for user input"
          checked={data.can_request_input}
          onChange={(v) => onUpdate(nodeId, { can_request_input: v })}
        />
      )}
      <OptionRow
        label="Show as Message"
        description="Output appears in chat"
        checked={data.promote_output}
        onChange={(v) => onUpdate(nodeId, { promote_output: v })}
      />
    </div>
  );
}

const PLACEMENT_CLASSES = {
  section: "wfb-config-section",
  label: "wfb-config-label",
  select: "wfb-config-input",
};

/** Where this step runs (Sequential workflows only; others have no containers). */
export function StepPlacementSection({
  nodeId,
  data,
  steps,
  catalog,
  onMove,
}: Pick<StepConfigPanelProps, "nodeId" | "data" | "steps" | "catalog" | "onMove">) {
  if (data.orchestration_mode !== "sequential") return null;
  return (
    <StepPlacementFields
      step={data}
      steps={steps}
      catalog={catalog}
      classes={PLACEMENT_CLASSES}
      onMove={(place) => onMove(nodeId, place)}
    />
  );
}
