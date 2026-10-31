"use client";

import React from "react";
import {
  placementChoices,
  type PlacementChoice,
} from "@/lib/workflows/containerLanes";
import type { EditorStep } from "@/lib/workflows/editorModel";
import type { NodeCatalog } from "@/lib/workflows/nodeRegistry";
import type { BlockPlace } from "@/lib/workflows/stepTree";

const TOP_LEVEL_VALUE = "";

export interface PlacementFieldClasses {
  section: string;
  label: string;
  select: string;
}

/**
 * Where a step runs: at the top level, or in a lane of a Parallel or Loop. Used by
 * both workflow editors; moving the step is up to them.
 */
export function StepPlacementFields({
  step,
  steps,
  catalog,
  classes,
  onMove,
}: {
  step: EditorStep;
  steps: readonly EditorStep[];
  catalog: NodeCatalog;
  classes: PlacementFieldClasses;
  onMove: (place: BlockPlace) => void;
}) {
  const choices = placementChoices(step, steps, catalog);
  // A step already inside a container can always go back to the top level.
  if (choices.length <= 1 && !step.parent_key) return null;

  const current: PlacementChoice | undefined = choices.find(
    (c) => c.parent_key === step.parent_key
  );
  const lanes = current?.lanes ?? [];

  const onContainerChange = (value: string) => {
    onMove(
      value === TOP_LEVEL_VALUE
        ? { parent_key: null, branch_index: null }
        : { parent_key: value, branch_index: 0 }
    );
  };

  return (
    <>
      <div className={classes.section}>
        <label className={classes.label}>
          Run inside
          <select
            className={classes.select}
            value={step.parent_key ?? TOP_LEVEL_VALUE}
            onChange={(e) => onContainerChange(e.target.value)}
          >
            {choices.map((choice) => (
              <option
                key={choice.parent_key ?? TOP_LEVEL_VALUE}
                value={choice.parent_key ?? TOP_LEVEL_VALUE}
              >
                {choice.label}
              </option>
            ))}
          </select>
        </label>
      </div>
      {step.parent_key && lanes.length > 1 && (
        <div className={classes.section}>
          <label className={classes.label}>
            Branch
            <select
              className={classes.select}
              value={step.branch_index ?? 0}
              onChange={(e) =>
                onMove({
                  parent_key: step.parent_key,
                  branch_index: Number(e.target.value),
                })
              }
            >
              {lanes.map((label, branch) => (
                <option key={branch} value={branch}>
                  {label}
                </option>
              ))}
            </select>
          </label>
        </div>
      )}
    </>
  );
}
