"use client";

/**
 * Wizard fields of a conditional router step: the condition, plus the steps
 * of each branch, picked by name and stored as node keys (router v2). The
 * Visual Builder edits the same config through the router's canvas edges.
 */

import React from "react";
import Text from "@/refresh-components/texts/Text";
import { CONDITION_OPERATORS } from "@/lib/workflows/interfaces";
import type { RouterConfigV2 } from "@/lib/workflows/interfaces";
import {
  type RouterBranch,
  VALUELESS_OPERATORS,
  branchTargets,
  normalizeRouterConfig,
  withBranchTargets,
} from "@/lib/workflows/routerConfig";

export interface BranchCandidate {
  node_key: string;
  label: string;
}

const INPUT_CLASS =
  "w-full h-9 px-3 rounded-08 border border-border bg-background-tint-00 text-text-05 text-sm";

const BRANCHES: { branch: RouterBranch; title: string }[] = [
  { branch: "true", title: "Run only if TRUE" },
  { branch: "false", title: "Run only if FALSE" },
];

/** Put `key` in `branch` (or take it out); a step is in at most one branch. */
export function toggleBranchTarget(
  config: RouterConfigV2,
  branch: RouterBranch,
  key: string,
  include: boolean
): RouterConfigV2 {
  const other: RouterBranch = branch === "true" ? "false" : "true";
  const without = (keys: string[]) => keys.filter((k) => k !== key);
  let next = withBranchTargets(
    config,
    other,
    include
      ? without(branchTargets(config, other))
      : branchTargets(config, other)
  );
  const current = without(branchTargets(config, branch));
  next = withBranchTargets(next, branch, include ? [...current, key] : current);
  return next;
}

export function RouterStepFields({
  config: rawConfig,
  laterSteps,
  onChange,
}: {
  config: Record<string, unknown> | null;
  /** Steps after the router: the only valid branch targets. */
  laterSteps: BranchCandidate[];
  onChange: (config: RouterConfigV2) => void;
}) {
  const config = normalizeRouterConfig(rawConfig);
  const update = (partial: Partial<RouterConfigV2>) =>
    onChange({ ...config, ...partial });

  return (
    <div className="space-y-3 p-3 rounded-08 border border-border bg-background-tint-01">
      <Text secondaryBody text04 className="text-xs font-medium">
        Condition Configuration
      </Text>

      <div className="grid grid-cols-2 gap-3">
        <label className="flex flex-col gap-0.5">
          <Text secondaryBody text04 className="text-xs">
            Condition Field
          </Text>
          <input
            type="text"
            className={`${INPUT_CLASS} font-mono`}
            value={config.condition_field}
            onChange={(e) => update({ condition_field: e.target.value })}
            placeholder="$step_name.output"
          />
          <Text secondaryBody text03 className="text-xs">
            Reference a previous step output (e.g. $research.output) or
            $user_input
          </Text>
        </label>

        <label className="flex flex-col gap-0.5">
          <Text secondaryBody text04 className="text-xs">
            Operator
          </Text>
          <select
            className={INPUT_CLASS}
            value={config.operator}
            onChange={(e) =>
              update({ operator: e.target.value as RouterConfigV2["operator"] })
            }
          >
            {CONDITION_OPERATORS.map((op) => (
              <option key={op.value} value={op.value}>
                {op.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      {!VALUELESS_OPERATORS.has(config.operator) && (
        <label className="flex flex-col gap-0.5">
          <Text secondaryBody text04 className="text-xs">
            Match Value
          </Text>
          <input
            type="text"
            className={INPUT_CLASS}
            value={config.match_value}
            onChange={(e) => update({ match_value: e.target.value })}
            placeholder="Value to compare against"
          />
        </label>
      )}

      <label className="flex items-center gap-2">
        <input
          type="checkbox"
          className="accent-[var(--theme-primary-05)]"
          checked={config.case_sensitive}
          onChange={(e) => update({ case_sensitive: e.target.checked })}
        />
        <Text secondaryBody text04 className="text-xs">
          Case sensitive
        </Text>
      </label>

      <div className="grid grid-cols-2 gap-3">
        {BRANCHES.map(({ branch, title }) => {
          const selected = new Set(branchTargets(config, branch));
          return (
            <fieldset key={branch} className="flex flex-col gap-1">
              <legend>
                <Text secondaryBody text04 className="text-xs font-medium">
                  {title}
                </Text>
              </legend>
              {laterSteps.length === 0 ? (
                <Text secondaryBody text03 className="text-xs">
                  Add steps after this condition to branch to them.
                </Text>
              ) : (
                laterSteps.map((candidate) => (
                  <label
                    key={candidate.node_key}
                    className="flex items-center gap-2"
                  >
                    <input
                      type="checkbox"
                      className="accent-[var(--theme-primary-05)]"
                      checked={selected.has(candidate.node_key)}
                      onChange={(e) =>
                        onChange(
                          toggleBranchTarget(
                            config,
                            branch,
                            candidate.node_key,
                            e.target.checked
                          )
                        )
                      }
                    />
                    <Text secondaryBody text04 className="text-xs">
                      {candidate.label}
                    </Text>
                  </label>
                ))
              )}
            </fieldset>
          );
        })}
      </div>
      <Text secondaryBody text03 className="text-xs">
        Steps in neither branch always run. Branches only skip later steps.
      </Text>
    </div>
  );
}
