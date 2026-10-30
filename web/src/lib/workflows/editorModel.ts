/**
 * The editor-side model of a workflow, shared by the Wizard and the Visual
 * Builder. `serializer.ts` converts it to and from the API shapes.
 */

import type { OrchestrationMode, StepOverrides } from "./interfaces";
import { configDefaults, parseConfigSchema } from "./configSchema";
import {
  type NodeCatalog,
  ROUTER_NODE_TYPE,
  latestVersion,
} from "./nodeRegistry";
import { ROUTER_CONFIG_VERSION, defaultRouterConfig } from "./routerConfig";

/** Every step-level override field (all optional, null = inherit). */
export const STEP_OVERRIDE_FIELDS = [
  "llm_provider_override",
  "llm_model_override",
  "max_output_tokens_override",
  "system_prompt_override",
  "task_prompt_override",
  "tool_ids_override",
  "document_set_ids_override",
  "replace_base_system_prompt_override",
] as const satisfies readonly (keyof StepOverrides)[];

/**
 * One workflow step as the editors hold it. Field names match the API so the
 * conversion is mechanical. A router's branch targets live in `config` as
 * node keys (router v2), so they survive re-ordering.
 */
export interface EditorStep extends StepOverrides {
  /** Stable identity; new steps get a client-generated key (see newNodeKey). */
  node_key: string;
  step_type: string;
  /** The pinned node type version (null = let the server use the latest). */
  type_version: number | null;
  /** Display only: the newest version of the type, from the snapshot. */
  latest_type_version: number | null;
  /** Display only: a newer version of the type exists. */
  upgrade_available: boolean;
  agent_id: number | null;
  /** Display only. */
  agent_name: string | null;
  step_name: string;
  step_description: string;
  output_key: string;
  input_mapping: Record<string, unknown> | null;
  /** Legacy `condition` of non-router steps, carried so it round-trips. */
  condition: Record<string, unknown> | null;
  config: Record<string, unknown> | null;
  /** node_key of the container holding this step (null = top level). */
  parent_key: string | null;
  /** The container branch the step is in (null = top level). */
  branch_index: number | null;
  is_terminal: boolean;
  can_request_input: boolean;
  promote_output: boolean;
}

/** Workflow-level settings (everything except the steps). */
export interface WorkflowMeta {
  name: string;
  description: string;
  orchestration_mode: OrchestrationMode;
  orchestrator_prompt: string;
  orchestrator_llm_provider: string;
  orchestrator_llm_model: string;
  max_steps: number;
  max_calls_per_agent: number;
  timeout_seconds: number;
  is_public: boolean;
  icon_name: string;
}

export const DEFAULT_WORKFLOW_META: WorkflowMeta = {
  name: "",
  description: "",
  orchestration_mode: "llm_decision",
  orchestrator_prompt: "",
  orchestrator_llm_provider: "",
  orchestrator_llm_model: "",
  max_steps: 10,
  max_calls_per_agent: 2,
  timeout_seconds: 1800,
  is_public: true,
  icon_name: "",
};

function randomHex(length: number): string {
  const bytes = new Uint8Array(Math.ceil(length / 2));
  globalThis.crypto.getRandomValues(bytes);
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0"))
    .join("")
    .slice(0, length);
}

/**
 * A node key for a new step, in the server's `n_<8 hex>` format. Keys are
 * generated client-side so router branches can target steps that have not
 * been saved yet; the server keeps keys it is sent.
 */
export function newNodeKey(taken: Iterable<string> = []): string {
  const used = new Set(taken);
  let key = `n_${randomHex(8)}`;
  while (used.has(key)) key = `n_${randomHex(8)}`;
  return key;
}

/** How a step relates to containers (parallel, loop), for display. */
export interface ContainerInfo {
  /** Number of steps directly inside this step (0 = not a container). */
  childCount: number;
  /** Name of the container this step is inside, if any. */
  containerName: string | null;
  branchIndex: number | null;
}

export function containerInfo(
  step: EditorStep,
  steps: readonly EditorStep[]
): ContainerInfo {
  const parent = step.parent_key
    ? steps.find((s) => s.node_key === step.parent_key)
    : undefined;
  return {
    childCount: steps.filter((s) => s.parent_key === step.node_key).length,
    containerName: step.parent_key
      ? parent?.step_name || step.parent_key
      : null,
    branchIndex: step.branch_index,
  };
}

/** The first free `<prefix>_<n>` output key (n = 0, 1, ...). */
export function nextOutputKey(
  prefix: string,
  steps: readonly Pick<EditorStep, "output_key">[]
): string {
  const taken = new Set(steps.map((s) => s.output_key));
  let n = 0;
  while (taken.has(`${prefix}_${n}`)) n++;
  return `${prefix}_${n}`;
}

/** The starting config of a new step of `type`. */
function initialConfig(
  catalog: NodeCatalog,
  type: string
): Record<string, unknown> | null {
  if (type === ROUTER_NODE_TYPE) return { ...defaultRouterConfig() };
  const latest = latestVersion(catalog, type);
  if (!latest) return null;
  const defaults = configDefaults(parseConfigSchema(latest.config_schema));
  return Object.keys(defaults).length > 0 ? defaults : null;
}

/**
 * A new step of `type` with the type's defaults, pinned to the version the
 * editor creates it with (so a later backend upgrade never silently applies).
 */
export function createEditorStep(
  type: string,
  catalog: NodeCatalog,
  init: Partial<EditorStep> & { node_key: string }
): EditorStep {
  const version =
    type === ROUTER_NODE_TYPE
      ? ROUTER_CONFIG_VERSION
      : latestVersion(catalog, type)?.version ?? null;
  return {
    step_type: type,
    type_version: version,
    latest_type_version: version,
    upgrade_available: false,
    agent_id: null,
    agent_name: null,
    step_name: "",
    step_description: "",
    output_key: "output",
    input_mapping: null,
    condition: null,
    config: initialConfig(catalog, type),
    parent_key: null,
    branch_index: null,
    is_terminal: false,
    can_request_input: false,
    promote_output: false,
    ...init,
  };
}
