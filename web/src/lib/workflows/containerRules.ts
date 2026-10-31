/**
 * Structure rules every container type shares. They mirror `_check_containers`
 * in backend/om/workflows/saving.py, which stays the source of truth on save.
 */

import type { EditorStep } from "./editorModel";
import { type NodeCatalog, isContainer, labelFor } from "./nodeRegistry";
import type { StepValidationError } from "./validation";

export const MAX_WORKFLOW_STEPS = 100;
export const MAX_CONTAINER_DEPTH = 3;

/** The containers around `step`, innermost first. */
export function ancestorsOf(
  step: EditorStep,
  byKey: ReadonlyMap<string, EditorStep>
): EditorStep[] {
  const ancestors: EditorStep[] = [];
  const seen = new Set([step.node_key]);
  let parent = step.parent_key ? byKey.get(step.parent_key) : undefined;
  while (parent && !seen.has(parent.node_key)) {
    ancestors.push(parent);
    seen.add(parent.node_key);
    parent = parent.parent_key ? byKey.get(parent.parent_key) : undefined;
  }
  return ancestors;
}

function stepProblem(
  step: EditorStep,
  name: string,
  position: number,
  positionOf: ReadonlyMap<string, number>,
  byKey: ReadonlyMap<string, EditorStep>,
  catalog: NodeCatalog
): string | null {
  if (!step.parent_key) {
    return step.branch_index != null
      ? `"${name}" has a branch but no container`
      : null;
  }
  const parent = byKey.get(step.parent_key);
  if (!parent) {
    return `"${name}" belongs to a container that was removed; remove it too`;
  }
  if (!isContainer(catalog, parent.step_type, parent.type_version)) {
    return `"${name}" is inside "${labelFor(
      catalog,
      parent.step_type
    )}", which can't contain steps`;
  }
  if (step.branch_index == null || step.branch_index < 0) {
    return `"${name}" needs a branch`;
  }
  if (position <= (positionOf.get(parent.node_key) ?? 0)) {
    return `"${name}" must come after its container`;
  }
  if (ancestorsOf(step, byKey).length > MAX_CONTAINER_DEPTH) {
    return `Containers can be nested at most ${MAX_CONTAINER_DEPTH} levels deep`;
  }
  if (step.can_request_input || step.promote_output || step.is_terminal) {
    return `"${name}" is inside a container, so it can't ask for input, promote its output, or end the workflow`;
  }
  return null;
}

export function validateContainerStructure(
  steps: readonly EditorStep[],
  nameOf: (step: EditorStep) => string,
  catalog: NodeCatalog
): StepValidationError[] {
  const positionOf = new Map(steps.map((s, i) => [s.node_key, i]));
  const byKey = new Map(steps.map((s) => [s.node_key, s]));
  const errors: StepValidationError[] = [];
  if (steps.length > MAX_WORKFLOW_STEPS) {
    errors.push({
      message: `A workflow can have at most ${MAX_WORKFLOW_STEPS} steps`,
    });
  }
  steps.forEach((step, position) => {
    const message = stepProblem(
      step,
      nameOf(step),
      position,
      positionOf,
      byKey,
      catalog
    );
    if (message) errors.push({ nodeKey: step.node_key, message });
  });
  return errors;
}
