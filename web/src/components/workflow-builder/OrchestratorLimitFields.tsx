"use client";

import React from "react";
import {
  MAX_CALLS_PER_AGENT,
  MAX_ORCHESTRATOR_STEPS,
} from "@/lib/workflows/workflowLimits";
import type { WorkflowMeta } from "./types";

/**
 * Limits on the LLM orchestrator. Only `llm_decision` workflows have one, so a
 * Sequential workflow doesn't show them; their saved values are kept.
 */
export function OrchestratorLimitFields({
  meta,
  onUpdateMeta,
}: {
  meta: WorkflowMeta;
  onUpdateMeta: (partial: Partial<WorkflowMeta>) => void;
}) {
  if (meta.orchestration_mode !== "llm_decision") {
    return null;
  }
  return (
    <>
      <div className="wfb-settings-row">
        <div className="wfb-settings-label">Max Total Steps</div>
        <input
          className="wfb-settings-number"
          type="number"
          min={1}
          max={MAX_ORCHESTRATOR_STEPS}
          value={meta.max_steps}
          onChange={(e) =>
            onUpdateMeta({ max_steps: Number(e.target.value) || 10 })
          }
        />
      </div>

      <div className="wfb-settings-row">
        <div className="wfb-settings-label">Max Calls per Agent</div>
        <input
          className="wfb-settings-number"
          type="number"
          min={1}
          max={MAX_CALLS_PER_AGENT}
          value={meta.max_calls_per_agent}
          onChange={(e) =>
            onUpdateMeta({
              max_calls_per_agent: Number(e.target.value) || 2,
            })
          }
        />
      </div>
    </>
  );
}
