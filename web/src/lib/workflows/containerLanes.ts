/**
 * A container's lanes, and where a step may be placed. Shared by both editors; the
 * server's save rules (saving.py, nodes/parallel.py) stay the source of truth.
 */

import type { EditorStep } from "./editorModel";
import { MAX_CONTAINER_DEPTH, ancestorsOf } from "./containerRules";
import { type NodeCatalog, isContainer } from "./nodeRegistry";
import { descendantKeys } from "./stepTree";

const PARALLEL_NODE_TYPE = "parallel";
const LOOP_LANE_LABEL = "Each iteration";

/**
 * The lanes a container shows: one per configured branch. A branch in use beyond the
 * configured ones gets a lane too, so its steps stay visible.
 */
export function laneLabels(
  container: Pick<EditorStep, "node_key" | "step_type" | "config">,
  steps: readonly Pick<EditorStep, "parent_key" | "branch_index">[]
): string[] {
  if (container.step_type !== PARALLEL_NODE_TYPE) return [LOOP_LANE_LABEL];
  const branches = (container.config as { branches?: unknown } | null)?.branches;
  const labels = Array.isArray(branches)
    ? branches.map((branch, i) => {
        const label = (branch as { label?: unknown } | null)?.label;
        return typeof label === "string" && label ? label : `Branch ${i + 1}`;
      })
    : ["Branch 1", "Branch 2"];
  const used = steps
    .filter((s) => s.parent_key === container.node_key)
    .map((s) => s.branch_index ?? 0);
  const count = Math.max(labels.length, Math.max(-1, ...used) + 1);
  return Array.from(
    { length: count },
    (_, branch) => labels[branch] ?? `Branch ${branch + 1}`
  );
}

export interface PlacementChoice {
  /** Null is the top level of the workflow. */
  parent_key: string | null;
  label: string;
  lanes: string[];
}

function hasParallel(step: EditorStep, steps: readonly EditorStep[]): boolean {
  const inside = descendantKeys(steps, step.node_key);
  return (
    step.step_type === PARALLEL_NODE_TYPE ||
    steps.some(
      (s) => inside.has(s.node_key) && s.step_type === PARALLEL_NODE_TYPE
    )
  );
}

function nestingBelow(step: EditorStep, steps: readonly EditorStep[]): number {
  const children = steps.filter((s) => s.parent_key === step.node_key);
  return children.length === 0
    ? 0
    : 1 + Math.max(...children.map((c) => nestingBelow(c, steps)));
}

/**
 * Where `step` may run: the top level, or a lane of any container that would accept
 * it. Containers inside `step` are excluded, and so is anything that would put a
 * parallel inside a parallel or nest too deep.
 */
export function placementChoices(
  step: EditorStep,
  steps: readonly EditorStep[],
  catalog: NodeCatalog
): PlacementChoice[] {
  const byKey = new Map(steps.map((s) => [s.node_key, s]));
  const inside = descendantKeys(steps, step.node_key);
  const movesParallel = hasParallel(step, steps);
  const depthBelow = nestingBelow(step, steps);

  const choices: PlacementChoice[] = [
    { parent_key: null, label: "Top level", lanes: [] },
  ];
  for (const candidate of steps) {
    if (candidate.node_key === step.node_key || inside.has(candidate.node_key)) {
      continue;
    }
    if (!isContainer(catalog, candidate.step_type, candidate.type_version)) {
      continue;
    }
    const around = [candidate, ...ancestorsOf(candidate, byKey)];
    if (movesParallel && around.some((a) => a.step_type === PARALLEL_NODE_TYPE)) {
      continue;
    }
    if (around.length + depthBelow > MAX_CONTAINER_DEPTH) continue;
    choices.push({
      parent_key: candidate.node_key,
      label: candidate.step_name || candidate.node_key,
      lanes: laneLabels(candidate, steps),
    });
  }
  return choices;
}
