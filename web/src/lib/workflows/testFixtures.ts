/**
 * Shared fixtures for the workflow editor tests (not used by app code).
 * The catalog mirrors what `GET /workflow/node-types` serves today.
 */

import type {
  NodeTypeInfo,
  NodeTypeVersionInfo,
  WorkflowSnapshot,
  WorkflowStepSnapshot,
} from "./interfaces";

function version(
  overrides: Partial<NodeTypeVersionInfo> & { version: number }
): NodeTypeVersionInfo {
  return {
    label: "Step",
    description: "",
    category: "core",
    config_schema: { type: "object", properties: {} },
    modes: ["sequential"],
    can_pause: false,
    is_container: false,
    deprecated: false,
    upgradable_from_previous: false,
    ...overrides,
  };
}

export const CATALOG: NodeTypeInfo[] = [
  {
    type: "agent",
    latest_version: 1,
    versions: [
      version({
        version: 1,
        label: "Agent",
        modes: ["llm_decision", "sequential"],
        can_pause: true,
      }),
    ],
  },
  {
    type: "conditional_router",
    latest_version: 2,
    versions: [
      version({
        version: 1,
        label: "Condition",
        category: "logic",
        deprecated: true,
      }),
      version({
        version: 2,
        label: "Condition",
        category: "logic",
        upgradable_from_previous: true,
      }),
    ],
  },
  // Shaped like the backend's code v1 (pydantic JSON schema).
  {
    type: "code",
    latest_version: 1,
    versions: [
      version({
        version: 1,
        label: "Code",
        category: "data",
        config_schema: {
          type: "object",
          $defs: {
            CodeOutputSpec: {
              type: "object",
              properties: {
                name: { type: "string" },
                type: { type: "string" },
              },
            },
          },
          properties: {
            code: {
              type: "string",
              title: "Code",
              default: "def main(inputs):\n    return {}",
              "x-ui": "code",
              "x-language": "python",
            },
            inputs: {
              type: "object",
              title: "Inputs",
              additionalProperties: { type: "string" },
            },
            outputs: {
              type: "array",
              title: "Outputs",
              items: { $ref: "#/$defs/CodeOutputSpec" },
              minItems: 1,
            },
            timeout_seconds: {
              type: "integer",
              title: "Timeout Seconds",
              default: 5,
              minimum: 1,
              maximum: 30,
            },
          },
        },
      }),
    ],
  },
  // Shaped like the backend's parallel v1: a container.
  {
    type: "parallel",
    latest_version: 1,
    versions: [
      version({
        version: 1,
        label: "Parallel",
        category: "logic",
        is_container: true,
        config_schema: {
          type: "object",
          properties: {
            branches: {
              type: "array",
              title: "Branches",
              items: { type: "object" },
            },
            join: {
              enum: ["wait_all", "first_success"],
              type: "string",
              default: "wait_all",
            },
            on_branch_error: {
              enum: ["fail", "continue"],
              type: "string",
              default: "fail",
            },
            max_concurrency: { type: "integer", default: 4, minimum: 1 },
          },
        },
      }),
    ],
  },
  // A made-up type with a required field (no backend type has one yet).
  {
    type: "transform",
    latest_version: 1,
    versions: [
      version({
        version: 1,
        label: "Transform",
        config_schema: {
          type: "object",
          properties: {
            source: { type: "string", title: "Source" },
            timeout_seconds: { type: "integer", default: 30 },
          },
          required: ["source"],
        },
      }),
    ],
  },
];

export function makeStep(
  overrides: Partial<WorkflowStepSnapshot> & {
    id: number;
    step_order: number;
  }
): WorkflowStepSnapshot {
  return {
    workflow_id: 1,
    node_key: `s${overrides.id}`,
    step_type: "agent",
    type_version: 1,
    latest_type_version: 1,
    upgrade_available: false,
    config: null,
    parent_key: null,
    branch_index: null,
    agent_id: 10 + overrides.id,
    agent_name: `Agent ${overrides.id}`,
    step_name: `Step ${overrides.id}`,
    step_description: null,
    input_mapping: null,
    output_key: `out_${overrides.id}`,
    condition: null,
    is_terminal: false,
    can_request_input: false,
    promote_output: false,
    ...overrides,
  };
}

export function makeWorkflow(
  steps: WorkflowStepSnapshot[],
  overrides: Partial<WorkflowSnapshot> = {}
): WorkflowSnapshot {
  return {
    id: 1,
    name: "Fixture workflow",
    description: "A workflow for tests",
    user_id: null,
    orchestration_mode: "sequential",
    orchestrator_prompt: null,
    orchestrator_llm_provider: null,
    orchestrator_llm_model: null,
    max_steps: 10,
    max_calls_per_agent: 2,
    timeout_seconds: 1800,
    is_public: true,
    is_visible: true,
    deleted: false,
    icon_name: "rocket",
    version: 7,
    schema_version: 1,
    created_at: "2026-10-30T00:00:00Z",
    updated_at: "2026-10-30T00:00:00Z",
    steps,
    ...overrides,
  };
}
