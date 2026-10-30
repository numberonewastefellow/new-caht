/**
 * The one conversion between the workflow API shapes and the editor model,
 * used by both the Wizard and the Visual Builder.
 *
 *   WorkflowSnapshot --snapshotToEditorSteps/snapshotToMeta--> editor model
 *   editor model --buildWorkflowCreate/buildWorkflowUpdate--> save payload
 *
 * Every step field is carried through (node_key, type_version, config,
 * input_mapping, all overrides), so saving never drops data the editor does
 * not display. Router branch targets are node keys, never step orders.
 */

import type {
  OrchestrationMode,
  StepOverrides,
  WorkflowCreate,
  WorkflowSnapshot,
  WorkflowStepCreate,
  WorkflowStepSnapshot,
  WorkflowUpdate,
} from "./interfaces";
import {
  type EditorStep,
  type WorkflowMeta,
  STEP_OVERRIDE_FIELDS,
} from "./editorModel";
import { ROUTER_NODE_TYPE } from "./nodeRegistry";
import {
  ROUTER_CONFIG_VERSION,
  isRouterConfigV2,
  normalizeRouterConfig,
  pruneRouterTargets,
  routerConfigFromV1,
} from "./routerConfig";

// ── Snapshot → editor ────────────────────────────────────────────────────

function toOrchestrationMode(mode: string): OrchestrationMode {
  return mode === "sequential" ? "sequential" : "llm_decision";
}

export function snapshotToMeta(workflow: WorkflowSnapshot): WorkflowMeta {
  return {
    name: workflow.name,
    description: workflow.description ?? "",
    orchestration_mode: toOrchestrationMode(workflow.orchestration_mode),
    orchestrator_prompt: workflow.orchestrator_prompt ?? "",
    orchestrator_llm_provider: workflow.orchestrator_llm_provider ?? "",
    orchestrator_llm_model: workflow.orchestrator_llm_model ?? "",
    max_steps: workflow.max_steps,
    max_calls_per_agent: workflow.max_calls_per_agent,
    timeout_seconds: workflow.timeout_seconds,
    is_public: workflow.is_public,
    icon_name: workflow.icon_name ?? "",
  };
}

function overridesOf(source: StepOverrides): StepOverrides {
  const overrides: Record<string, unknown> = {};
  for (const field of STEP_OVERRIDE_FIELDS) {
    overrides[field] = source[field] ?? null;
  }
  return overrides as StepOverrides;
}

/** A router step's config in v2 form, converting legacy v1 on the fly. */
function routerStepFields(
  step: WorkflowStepSnapshot,
  orderToKey: ReadonlyMap<number, string>
): Pick<EditorStep, "config" | "type_version" | "upgrade_available"> {
  const config = isRouterConfigV2(step.config)
    ? normalizeRouterConfig(step.config)
    : routerConfigFromV1(step.condition ?? step.config, orderToKey);
  return {
    config: { ...config },
    type_version: ROUTER_CONFIG_VERSION,
    upgrade_available: (step.latest_type_version ?? 0) > ROUTER_CONFIG_VERSION,
  };
}

function stepToEditor(
  step: WorkflowStepSnapshot,
  orderToKey: ReadonlyMap<number, string>
): EditorStep {
  const isRouter = step.step_type === ROUTER_NODE_TYPE;
  const editorStep: EditorStep = {
    node_key: step.node_key,
    step_type: step.step_type || "agent",
    type_version: step.type_version ?? null,
    latest_type_version: step.latest_type_version ?? null,
    upgrade_available: step.upgrade_available ?? false,
    agent_id: step.agent_id,
    agent_name: step.agent_name,
    step_name: step.step_name,
    step_description: step.step_description ?? "",
    output_key: step.output_key || "output",
    input_mapping: step.input_mapping ?? null,
    condition: isRouter ? null : step.condition ?? null,
    config: step.config ?? null,
    parent_key: step.parent_key ?? null,
    branch_index: step.branch_index ?? null,
    is_terminal: step.is_terminal,
    can_request_input: step.can_request_input,
    promote_output: step.promote_output,
    ...overridesOf(step),
  };
  return isRouter
    ? { ...editorStep, ...routerStepFields(step, orderToKey) }
    : editorStep;
}

/** The workflow's steps in execution order, as editor steps. */
export function snapshotToEditorSteps(
  workflow: WorkflowSnapshot
): EditorStep[] {
  const sorted = [...workflow.steps].sort(
    (a, b) => a.step_order - b.step_order
  );
  const orderToKey = new Map(sorted.map((s) => [s.step_order, s.node_key]));
  return sorted.map((step) => stepToEditor(step, orderToKey));
}

// ── Editor → payload ─────────────────────────────────────────────────────

function emptyToNull<T>(value: T | "" | undefined): T | null {
  return value === undefined || value === "" ? null : value;
}

function stepToPayload(
  step: EditorStep,
  order: number,
  existingKeys: ReadonlySet<string>
): WorkflowStepCreate {
  const isRouter = step.step_type === ROUTER_NODE_TYPE;
  const overrides: Record<string, unknown> = {};
  for (const field of STEP_OVERRIDE_FIELDS) {
    overrides[field] = emptyToNull(step[field]);
  }

  const payload: WorkflowStepCreate = {
    node_key: step.node_key,
    step_type: step.step_type,
    agent_id: step.agent_id,
    step_order: order,
    step_name: step.step_name,
    step_description: step.step_description || null,
    output_key: step.output_key || "output",
    input_mapping: step.input_mapping,
    condition: isRouter ? null : step.condition,
    config: isRouter
      ? {
          ...pruneRouterTargets(
            normalizeRouterConfig(step.config),
            existingKeys
          ),
        }
      : step.config,
    parent_key: step.parent_key,
    branch_index: step.branch_index,
    is_terminal: step.is_terminal,
    can_request_input: step.can_request_input,
    promote_output: step.promote_output,
    ...overrides,
  };
  if (step.type_version != null) payload.type_version = step.type_version;
  return payload;
}

/** Steps in the given order as save payloads (step_order = position). */
export function editorStepsToPayload(
  steps: readonly EditorStep[]
): WorkflowStepCreate[] {
  const keys = new Set(steps.map((s) => s.node_key));
  return steps.map((step, i) => stepToPayload(step, i, keys));
}

function metaToPayload(meta: WorkflowMeta) {
  return {
    name: meta.name,
    description: meta.description || null,
    orchestration_mode: meta.orchestration_mode,
    orchestrator_prompt: meta.orchestrator_prompt || null,
    orchestrator_llm_provider: meta.orchestrator_llm_provider || null,
    orchestrator_llm_model: meta.orchestrator_llm_model || null,
    max_steps: meta.max_steps,
    max_calls_per_agent: meta.max_calls_per_agent,
    timeout_seconds: meta.timeout_seconds,
    is_public: meta.is_public,
    icon_name: meta.icon_name || null,
  };
}

export function buildWorkflowCreate(
  meta: WorkflowMeta,
  steps: readonly EditorStep[]
): WorkflowCreate {
  return { ...metaToPayload(meta), steps: editorStepsToPayload(steps) };
}

/**
 * An update payload. `expectedVersion` is the `version` the editor loaded;
 * the server rejects the save (409) if someone else saved in between.
 */
export function buildWorkflowUpdate(
  meta: WorkflowMeta,
  steps: readonly EditorStep[],
  expectedVersion: number | null
): WorkflowUpdate {
  return {
    ...buildWorkflowCreate(meta, steps),
    expected_version: expectedVersion,
  };
}

/** Step order -> node key for the steps in their current order. */
export function stepOrderToNodeKey(
  steps: readonly EditorStep[]
): Record<number, string> {
  return Object.fromEntries(steps.map((s, i) => [i, s.node_key]));
}
