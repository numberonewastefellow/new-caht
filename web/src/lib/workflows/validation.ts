/**
 * Step validation shared by both workflow editors. The server re-validates
 * on save; these checks give earlier, clearer messages for the same rules.
 */

import type { OrchestrationMode } from "./interfaces";
import type { EditorStep } from "./editorModel";
import { missingRequiredFields, parseConfigSchema } from "./configSchema";
import { validateContainerStructure } from "./containerRules";
import { configProblems, stepOutputSchema } from "./nodeConfigRules";
import {
  type NodeCatalog,
  editorKindFor,
  isAllowedInMode,
  labelFor,
  resolveVersion,
} from "./nodeRegistry";
import { normalizeRouterConfig } from "./routerConfig";
import { DEFAULT_ASSISTANT_AGENT_ID } from "./stepAgents";

export interface StepValidationError {
  /** The step the error is about, when it is about one. */
  nodeKey?: string;
  message: string;
}

/** These names resolve before step outputs, so such a step could never be read. */
const RESERVED_OUTPUT_KEYS: ReadonlySet<string> = new Set(["loop", "user_input"]);

const MODE_LABEL: Record<OrchestrationMode, string> = {
  sequential: "Sequential",
  llm_decision: "LLM Decision",
};

export function stepDisplayName(step: EditorStep, index: number): string {
  return step.step_name.trim() || step.agent_name || `Step ${index + 1}`;
}

/** Steps whose node type can't be used in `mode`. */
export function stepsNotAllowedInMode(
  steps: readonly EditorStep[],
  mode: OrchestrationMode,
  catalog: NodeCatalog
): EditorStep[] {
  return steps.filter(
    (s) => !isAllowedInMode(catalog, s.step_type, s.type_version, mode)
  );
}

/** Steps are in the same block when they share container and branch. */
function sameBlock(a: EditorStep, b: EditorStep): boolean {
  return (
    (a.parent_key ?? null) === (b.parent_key ?? null) &&
    (a.branch_index ?? null) === (b.branch_index ?? null)
  );
}

function validateRouter(
  step: EditorStep,
  index: number,
  name: string,
  positionOf: ReadonlyMap<string, number>,
  byKey: ReadonlyMap<string, EditorStep>
): StepValidationError[] {
  const errors: StepValidationError[] = [];
  const config = normalizeRouterConfig(step.config);
  const nodeKey = step.node_key;

  if (!config.condition_field.trim()) {
    errors.push({
      nodeKey,
      message: `Condition "${name}" needs a condition field`,
    });
  }
  const allTargets = [...config.true_node_keys, ...config.false_node_keys];
  const targets = allTargets.filter((key) => positionOf.has(key));
  if (targets.length < allTargets.length) {
    errors.push({
      nodeKey,
      message: `Condition "${name}" branches to a step that no longer exists`,
    });
  }
  if (allTargets.length === 0) {
    errors.push({
      nodeKey,
      message: `Condition "${name}" needs at least one step in its True or False branch`,
    });
  }
  if (targets.some((key) => (positionOf.get(key) ?? 0) <= index)) {
    errors.push({
      nodeKey,
      message: `Condition "${name}" can only branch to steps that come after it`,
    });
  }
  if (targets.some((key) => !sameBlock(step, byKey.get(key)!))) {
    errors.push({
      nodeKey,
      message: `Condition "${name}" can only branch to steps in the same container branch`,
    });
  }
  return errors;
}

export interface ValidateStepsOptions {
  /** Check that each step's type can run in `mode` (default true). */
  checkModes?: boolean;
}

/**
 * Validate steps given in execution order. Returns an empty list when valid.
 */
export function validateSteps(
  steps: readonly EditorStep[],
  mode: OrchestrationMode,
  catalog: NodeCatalog,
  { checkModes = true }: ValidateStepsOptions = {}
): StepValidationError[] {
  const errors: StepValidationError[] = [];
  if (steps.length === 0) {
    errors.push({ message: "Add at least one step to the workflow" });
    return errors;
  }

  const positionOf = new Map(steps.map((s, i) => [s.node_key, i]));
  const byKey = new Map(steps.map((s) => [s.node_key, s]));
  const outputKeyOwner = new Map<string, string>();

  steps.forEach((step, index) => {
    const nodeKey = step.node_key;
    const name = stepDisplayName(step, index);
    const kind = editorKindFor(catalog, step.step_type);

    if (!step.step_name.trim()) {
      errors.push({ nodeKey, message: `Step ${index + 1} needs a step name` });
    }
    if (
      checkModes &&
      !isAllowedInMode(catalog, step.step_type, step.type_version, mode)
    ) {
      errors.push({
        nodeKey,
        message: `"${name}" is a ${labelFor(
          catalog,
          step.step_type
        )} step, which can't be used in ${MODE_LABEL[mode]} mode`,
      });
    }

    if (checkModes && mode !== "sequential" && stepOutputSchema(step) !== null) {
      errors.push({
        nodeKey,
        message: `"${name}" has an expected output, which only Sequential workflows support`,
      });
    }

    if (kind === "agent" && step.agent_id == null) {
      errors.push({ nodeKey, message: `"${name}" needs an agent` });
    } else if (kind === "agent" && step.agent_id === DEFAULT_ASSISTANT_AGENT_ID) {
      errors.push({
        nodeKey,
        message: `"${name}" uses the default Assistant; choose a dedicated agent`,
      });
    } else if (kind === "router") {
      errors.push(...validateRouter(step, index, name, positionOf, byKey));
    } else if (kind === "schema" || kind === "container") {
      const info = resolveVersion(catalog, step.step_type, step.type_version);
      const missing = info
        ? missingRequiredFields(
            parseConfigSchema(info.config_schema),
            step.config
          )
        : [];
      for (const field of missing) {
        errors.push({
          nodeKey,
          message: `"${name}" needs a value for ${field.label}`,
        });
      }
      for (const message of configProblems(step, name, steps, byKey)) {
        errors.push({ nodeKey, message });
      }
    }

    if (kind === "agent") {
      for (const message of configProblems(step, name, steps, byKey)) {
        errors.push({ nodeKey, message });
      }
    }

    const outputKey = step.output_key.trim();
    if (!outputKey) {
      errors.push({ nodeKey, message: `"${name}" needs an output key` });
    } else if (RESERVED_OUTPUT_KEYS.has(outputKey)) {
      errors.push({
        nodeKey,
        message: `"${name}" can't use the reserved output key "${outputKey}"`,
      });
    } else if (outputKeyOwner.has(outputKey)) {
      errors.push({
        nodeKey,
        message: `Duplicate output key "${outputKey}" (also used by "${outputKeyOwner.get(
          outputKey
        )}")`,
      });
    } else {
      outputKeyOwner.set(outputKey, name);
    }
  });

  const nameOf = (step: EditorStep) =>
    stepDisplayName(step, positionOf.get(step.node_key) ?? 0);
  errors.push(...validateContainerStructure(steps, nameOf, catalog));
  return errors;
}
