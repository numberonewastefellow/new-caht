/**
 * Per-node-type config rules, for clear messages before saving. They mirror each
 * node's `prepare_step` in backend/om/workflows/nodes/, the source of truth on save.
 * A new node type adds one entry to CONFIG_RULES.
 */

import { ancestorsOf } from "./containerRules";
import type { EditorStep } from "./editorModel";

const PARALLEL_NODE_TYPE = "parallel";
const LOOP_NODE_TYPE = "loop";
const CODE_NODE_TYPE = "code";

const MIN_BRANCHES = 2;
const MAX_BRANCHES = 8;
const MAX_ITERATIONS = 50;
const MAX_CODE_TIMEOUT_SECONDS = 30;
const DEFAULT_BRANCH_COUNT = 2;

const IDENTIFIER = /^[A-Za-z_]\w*$/;
const DEFINES_MAIN = /^(async\s+)?def\s+main\s*\(/m;

interface RuleContext {
  step: EditorStep;
  name: string;
  children: readonly EditorStep[];
  byKey: ReadonlyMap<string, EditorStep>;
}

type ConfigRule = (context: RuleContext) => string[];

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object"
    ? (value as Record<string, unknown>)
    : {};
}

function text(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

function outOfRange(value: unknown, min: number, max: number): boolean {
  return typeof value === "number" && (value < min || value > max);
}

/** The branch names as configured; an empty one stays empty, for editing. */
export function branchLabels(config: Record<string, unknown>): string[] {
  if (!Array.isArray(config.branches)) {
    return Array.from(
      { length: DEFAULT_BRANCH_COUNT },
      (_, i) => `Branch ${i + 1}`
    );
  }
  return config.branches.map((branch, i) => {
    const label = asRecord(branch).label;
    return typeof label === "string" ? label : `Branch ${i + 1}`;
  });
}

const parallelRules: ConfigRule = ({ step, name, children, byKey }) => {
  const errors: string[] = [];
  const config = asRecord(step.config);
  const labels = branchLabels(config);
  if (labels.length < MIN_BRANCHES || labels.length > MAX_BRANCHES) {
    errors.push(
      `Parallel step "${name}" needs ${MIN_BRANCHES} to ${MAX_BRANCHES} branches`
    );
  }
  if (new Set(labels).size !== labels.length) {
    errors.push(`Parallel step "${name}": branch names must be unique`);
  }
  if (labels.some((label) => !label.trim())) {
    errors.push(`Parallel step "${name}": every branch needs a name`);
  }
  if (outOfRange(config.max_concurrency, 1, MAX_BRANCHES)) {
    errors.push(
      `Parallel step "${name}" can run 1 to ${MAX_BRANCHES} branches at once`
    );
  }
  if (
    ancestorsOf(step, byKey).some((a) => a.step_type === PARALLEL_NODE_TYPE)
  ) {
    errors.push(`Parallel step "${name}" can't be inside another parallel step`);
  }
  const used = new Set(children.map((c) => c.branch_index));
  if (Array.from(used).some((i) => i != null && i >= labels.length)) {
    errors.push(
      `Parallel step "${name}" has steps in a branch that doesn't exist`
    );
  }
  const empty = labels.filter((_, i) => !used.has(i));
  if (empty.length > 0) {
    errors.push(
      `Parallel step "${name}": branches without steps: ${empty.join(", ")}`
    );
  }
  return errors;
};

const loopRules: ConfigRule = ({ step, name, children }) => {
  const errors: string[] = [];
  const config = asRecord(step.config);
  if (config.mode === "while") {
    if (!text(config.condition_field)) {
      errors.push(`Loop step "${name}" needs a condition`);
    }
  } else if (!text(config.items)) {
    errors.push(`Loop step "${name}" needs items (a $reference to a list)`);
  }
  if (outOfRange(config.max_iterations, 1, MAX_ITERATIONS)) {
    errors.push(`Loop step "${name}" can repeat 1 to ${MAX_ITERATIONS} times`);
  }
  if (children.length === 0) {
    errors.push(`Loop step "${name}" has no steps to repeat`);
  }
  if (children.some((c) => c.branch_index != null && c.branch_index !== 0)) {
    errors.push(`Loop step "${name}" has steps in a branch that doesn't exist`);
  }
  return errors;
};

const codeRules: ConfigRule = ({ step, name }) => {
  const errors: string[] = [];
  const config = asRecord(step.config);
  if (Array.isArray(config.outputs)) {
    const names = config.outputs.map((o) => text(asRecord(o).name));
    if (names.length === 0) {
      errors.push(`Code step "${name}" needs at least one output`);
    }
    if (names.some((n) => !n)) {
      errors.push(`Code step "${name}": every output needs a name`);
    }
    if (new Set(names).size !== names.length) {
      errors.push(`Code step "${name}": output names must be unique`);
    }
  }
  const badInputs = Object.keys(asRecord(config.inputs)).filter(
    (input) => !IDENTIFIER.test(input)
  );
  if (badInputs.length > 0) {
    errors.push(
      `Code step "${name}": invalid input names: ${badInputs.join(", ")}`
    );
  }
  if (typeof config.code === "string" && !DEFINES_MAIN.test(config.code)) {
    errors.push(
      `Code step "${name}": define a function main(inputs) that returns a dict`
    );
  }
  if (outOfRange(config.timeout_seconds, 1, MAX_CODE_TIMEOUT_SECONDS)) {
    errors.push(
      `Code step "${name}" can run for 1 to ${MAX_CODE_TIMEOUT_SECONDS} seconds`
    );
  }
  return errors;
};

const CONFIG_RULES: Readonly<Record<string, ConfigRule>> = {
  [PARALLEL_NODE_TYPE]: parallelRules,
  [LOOP_NODE_TYPE]: loopRules,
  [CODE_NODE_TYPE]: codeRules,
};

/** Problems with one step's config; empty for types without rules. */
export function configProblems(
  step: EditorStep,
  name: string,
  steps: readonly EditorStep[],
  byKey: ReadonlyMap<string, EditorStep>
): string[] {
  const rule = CONFIG_RULES[step.step_type];
  if (!rule) return [];
  const children = steps.filter((s) => s.parent_key === step.node_key);
  return rule({ step, name, children, byKey });
}
