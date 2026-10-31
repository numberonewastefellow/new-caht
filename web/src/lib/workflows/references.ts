/**
 * The `$references` a step can read: the user's input, its loop's variables, and
 * the output of steps that have already run by the time it runs. A step in a
 * parallel branch can't read a sibling branch, which runs at the same time. Mirrors
 * backend/om/workflows/reference_check.py, which is checked on save.
 */

import type { EditorStep } from "./editorModel";
import { ancestorsOf } from "./containerRules";
import { blockKey } from "./stepTree";

const LOOP_NODE_TYPE = "loop";
const CODE_NODE_TYPE = "code";

const USER_INPUT = "$user_input";
const LOOP_VARIABLES = ["$loop.item", "$loop.index", "$loop.previous"];

function referencesOf(step: EditorStep): string[] {
  const key = step.output_key.trim();
  if (!key) return [];
  const whole = `$${key}.output`;
  if (step.step_type !== CODE_NODE_TYPE) return [whole];
  const outputs = (step.config as { outputs?: unknown } | null)?.outputs;
  const named = Array.isArray(outputs)
    ? outputs
        .map((o) => (o as { name?: unknown } | null)?.name)
        .filter((n): n is string => typeof n === "string" && n !== "")
        .map((name) => `${whole}.${name}`)
    : [];
  return [whole, ...named];
}

/** Steps earlier in `step`'s own block. */
function earlierInBlock(
  step: EditorStep,
  steps: readonly EditorStep[]
): EditorStep[] {
  const block = steps.filter((s) => blockKey(s) === blockKey(step));
  return block.slice(0, block.indexOf(step));
}

/** What `step` may reference, nearest scope last. */
export function availableReferences(
  step: EditorStep,
  steps: readonly EditorStep[]
): string[] {
  const byKey = new Map(steps.map((s) => [s.node_key, s]));
  const scopes = [step, ...ancestorsOf(step, byKey)].reverse();
  const insideLoop = scopes
    .slice(0, -1)
    .some((s) => s.step_type === LOOP_NODE_TYPE);
  return [
    USER_INPUT,
    ...(insideLoop ? LOOP_VARIABLES : []),
    ...scopes.flatMap((scope) =>
      earlierInBlock(scope, steps).flatMap((earlier) => [
        ...referencesOf(earlier),
        // A container's direct children are merged when it ends.
        ...steps
          .filter((s) => s.parent_key === earlier.node_key)
          .flatMap(referencesOf),
      ])
    ),
  ];
}
